from pathlib import Path
import argparse
import csv
import json
import math
import re
import zipfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import rasterio
from rasterio.transform import Affine
from pyproj import Transformer


TILE_SIZE_RAW = 512
SCALE = 4
TILE_SIZE_SR = TILE_SIZE_RAW * SCALE
BAND_NAMES = ["B04", "B03", "B02", "B08"]


def parse_tile(tile_name):
    m = re.match(r"tile_r(\d+)_c(\d+)$", tile_name)
    if not m:
        raise ValueError(f"Nombre de tile inválido: {tile_name}")
    return int(m.group(1)), int(m.group(2))


def tile_bounds_sr(tile_name):
    r_raw, c_raw = parse_tile(tile_name)
    r0 = r_raw * SCALE
    c0 = c_raw * SCALE
    return r0, c0, r0 + TILE_SIZE_SR, c0 + TILE_SIZE_SR


def intersects(a, b):
    ar0, ac0, ar1, ac1 = a
    br0, bc0, br1, bc1 = b
    return not (ar1 <= br0 or ar0 >= br1 or ac1 <= bc0 or ac0 >= bc1)


def normalize_to_chw(arr):
    if arr.ndim != 3:
        raise ValueError(f"Array con dimensiones inesperadas: {arr.shape}")

    if arr.shape[0] in (3, 4):
        return arr

    if arr.shape[-1] in (3, 4):
        return np.moveaxis(arr, -1, 0)

    raise ValueError(f"No reconozco el orden de bandas: {arr.shape}")


def polygon_to_sr_bbox(polygon_file, grid_georef):
    polygon = json.loads(Path(polygon_file).read_text(encoding="utf-8"))
    meta = json.loads(Path(grid_georef).read_text(encoding="utf-8"))

    crs = meta["crs"]
    a, b, c, d, e, f = meta["transform"]
    scale = int(meta.get("sr_scale", 4))

    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)

    rows = []
    cols = []

    for p in polygon:
        lng = float(p["lng"])
        lat = float(p["lat"])

        x, y = transformer.transform(lng, lat)

        col = (x - c) / a
        row = (y - f) / e

        rows.append(row * scale)
        cols.append(col * scale)

    row0 = math.floor(min(rows))
    row1 = math.ceil(max(rows))
    col0 = math.floor(min(cols))
    col1 = math.ceil(max(cols))

    return row0, col0, row1 - row0, col1 - col0


def get_sr_transform(grid_georef):
    meta = json.loads(Path(grid_georef).read_text(encoding="utf-8"))

    a, b, c, d, e, f = meta["transform"]
    scale = int(meta.get("sr_scale", 4))

    transform_sr = Affine(
        a / scale,
        b / scale,
        c,
        d / scale,
        e / scale,
        f
    )

    return meta["crs"], transform_sr


def find_npy_file(npy_roots, fecha, tile):
    for root in npy_roots:
        root = Path(root)
        date_dir = root / f"date_{fecha}"

        p = date_dir / f"{tile}_x4_uint16.npy"
        if p.exists():
            return p

        matches = sorted(date_dir.glob(f"{tile}*.npy"))
        matches = [m for m in matches if "mask" not in m.name.lower()]

        if matches:
            return matches[0]

    return None


def find_mask_file(mask_root, fecha, tile):
    if not mask_root:
        return None

    date_dir = Path(mask_root) / f"date_{fecha}"

    candidates = [
        date_dir / f"{tile}_imputed_mask.npy",
        date_dir / f"{tile}_mask.npy"
    ]

    for p in candidates:
        if p.exists():
            return p

    matches = sorted(date_dir.glob(f"{tile}*mask*.npy"))
    return matches[0] if matches else None


def list_all_dates(npy_roots, date_from=None, date_to=None):
    dates = set()

    for root in npy_roots:
        for d in Path(root).glob("date_*"):
            if not d.is_dir():
                continue

            fecha = d.name.replace("date_", "")

            if date_from and fecha < date_from:
                continue

            if date_to and fecha > date_to:
                continue

            dates.add(fecha)

    return sorted(dates)


def list_all_tiles(npy_roots):
    tiles = set()

    for root in npy_roots:
        for p in Path(root).glob("date_*/*.npy"):
            name = p.name

            if "mask" in name.lower():
                continue

            tile = name.replace("_x4_uint16.npy", "")
            tile = re.sub(r"_x4.*\.npy$", "", tile)
            tile = tile.replace(".npy", "")

            if tile.startswith("tile_r"):
                tiles.add(tile)

    return sorted(tiles)


def zip_outputs(zip_path, geotiff_dir, csv_path, readme_path):
    zip_path = Path(zip_path)

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as z:
        for tif in sorted(Path(geotiff_dir).glob("*.tif")):
            z.write(tif, Path("geotiff") / tif.name)

        if Path(csv_path).exists():
            z.write(csv_path, Path(csv_path).name)

        if Path(readme_path).exists():
            z.write(readme_path, Path(readme_path).name)


def write_mask_rows(writer, mask, fecha, tile, area, transform_sr):
    """
    Escribe únicamente los píxeles imputados que intersectan el área seleccionada.
    La máscara está en resolución original 512x512.
    El área está en resolución SR x4.
    """

    ar0, ac0, ar1, ac1 = area
    tile_r_raw, tile_c_raw = parse_tile(tile)

    if mask.ndim == 3:
        if mask.shape[0] in (1, 3, 4):
            mask_pixel = np.any(mask > 0, axis=0)
        elif mask.shape[-1] in (1, 3, 4):
            mask_pixel = np.any(mask > 0, axis=-1)
        else:
            raise ValueError(f"Máscara con dimensiones inesperadas: {mask.shape}")
    elif mask.ndim == 2:
        mask_pixel = mask > 0
    else:
        raise ValueError(f"Máscara con dimensiones inesperadas: {mask.shape}")

    # Convertir el área SR x4 al sistema raw 512x512
    raw_r0_global = max(tile_r_raw, ar0 // SCALE)
    raw_c0_global = max(tile_c_raw, ac0 // SCALE)
    raw_r1_global = min(tile_r_raw + TILE_SIZE_RAW, math.ceil(ar1 / SCALE))
    raw_c1_global = min(tile_c_raw + TILE_SIZE_RAW, math.ceil(ac1 / SCALE))

    if raw_r0_global >= raw_r1_global or raw_c0_global >= raw_c1_global:
        return 0

    r0_rel = raw_r0_global - tile_r_raw
    r1_rel = raw_r1_global - tile_r_raw
    c0_rel = raw_c0_global - tile_c_raw
    c1_rel = raw_c1_global - tile_c_raw

    mask_crop = mask_pixel[r0_rel:r1_rel, c0_rel:c1_rel]

    rows, cols = np.where(mask_crop)

    written = 0

    for row_rel_crop, col_rel_crop in zip(rows, cols):
        row_raw_global = raw_r0_global + int(row_rel_crop)
        col_raw_global = raw_c0_global + int(col_rel_crop)

        row_sr0 = row_raw_global * SCALE
        col_sr0 = col_raw_global * SCALE
        row_sr1 = row_sr0 + SCALE
        col_sr1 = col_sr0 + SCALE

        clip_row_sr0 = max(row_sr0, ar0)
        clip_col_sr0 = max(col_sr0, ac0)
        clip_row_sr1 = min(row_sr1, ar1)
        clip_col_sr1 = min(col_sr1, ac1)

        center_col = (clip_col_sr0 + clip_col_sr1) / 2
        center_row = (clip_row_sr0 + clip_row_sr1) / 2

        x_center, y_center = transform_sr * (center_col, center_row)
        x_min, y_max = transform_sr * (clip_col_sr0, clip_row_sr0)
        x_max, y_min = transform_sr * (clip_col_sr1, clip_row_sr1)

        writer.writerow({
            "fecha": fecha,
            "tile": tile,
            "row_raw_global": row_raw_global,
            "col_raw_global": col_raw_global,
            "row_sr0": clip_row_sr0,
            "col_sr0": clip_col_sr0,
            "row_sr1_exclusive": clip_row_sr1,
            "col_sr1_exclusive": clip_col_sr1,
            "x_center": x_center,
            "y_center": y_center,
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
            "sr_pixels_afectados": int((clip_row_sr1 - clip_row_sr0) * (clip_col_sr1 - clip_col_sr0))
        })

        written += 1

    return written

def process_one_date(
    fecha,
    date_idx,
    total_dates,
    npy_roots,
    mask_root,
    tiles_needed,
    row0,
    col0,
    height,
    width,
    area,
    transform_sr,
    crop_transform,
    crs,
    geotiff_dir,
    tmp_csv_dir,
    csv_fields
):
    print(f"Procesando fecha {date_idx + 1}/{total_dates}: {fecha}", flush=True)

    crop = None
    missing_masks = []
    total_csv_rows = 0

    tmp_csv_path = tmp_csv_dir / f"pixeles_imputados_{fecha}.csv"

    with open(tmp_csv_path, "w", newline="", encoding="utf-8") as fcsv:
        writer = csv.DictWriter(fcsv, fieldnames=csv_fields)
        writer.writeheader()

        for tile, tb in tiles_needed:
            npy_path = find_npy_file(npy_roots, fecha, tile)

            if npy_path is None:
                raise FileNotFoundError(f"No se encontró NPY para fecha={fecha}, tile={tile}")

            x = np.load(npy_path, mmap_mode="r")
            x = normalize_to_chw(x)

            if crop is None:
                crop = np.zeros((x.shape[0], height, width), dtype=x.dtype)

            tr0, tc0, tr1, tc1 = tb

            # Intersección entre el área seleccionada y el tile actual
            ir0 = max(row0, tr0)
            ic0 = max(col0, tc0)
            ir1 = min(row0 + height, tr1)
            ic1 = min(col0 + width, tc1)

            if ir0 >= ir1 or ic0 >= ic1:
                continue

            # Ventana fuente dentro del tile SR x4
            src_r0 = ir0 - tr0
            src_r1 = ir1 - tr0
            src_c0 = ic0 - tc0
            src_c1 = ic1 - tc0

            # Ventana destino dentro del recorte final
            dst_r0 = ir0 - row0
            dst_r1 = ir1 - row0
            dst_c0 = ic0 - col0
            dst_c1 = ic1 - col0

            crop[:, dst_r0:dst_r1, dst_c0:dst_c1] = x[:, src_r0:src_r1, src_c0:src_c1]

            mask_path = find_mask_file(mask_root, fecha, tile)

            if mask_path:
                mask = np.load(mask_path, mmap_mode="r")
                total_csv_rows += write_mask_rows(
                    writer=writer,
                    mask=mask,
                    fecha=fecha,
                    tile=tile,
                    area=area,
                    transform_sr=transform_sr
                )
            else:
                missing_masks.append(f"{fecha}/{tile}")

    if crop is None:
        raise RuntimeError(f"No se pudo construir el recorte para la fecha {fecha}")

    tif_path = geotiff_dir / f"area_{fecha}.tif"

    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=crop.shape[1],
        width=crop.shape[2],
        count=crop.shape[0],
        dtype=str(crop.dtype),
        crs=crs,
        transform=crop_transform,
        compress="lzw",
        tiled=True,
        blockxsize=256,
        blockysize=256,
        nodata=0,
        BIGTIFF="IF_SAFER",
        NUM_THREADS="2"
    ) as dst:
        for band_idx in range(crop.shape[0]):
            dst.write(crop[band_idx], band_idx + 1)
            if band_idx < len(BAND_NAMES):
                dst.set_band_description(band_idx + 1, BAND_NAMES[band_idx])

    print(f"GeoTIFF listo: {tif_path}", flush=True)

    return {
        "fecha": fecha,
        "tif_path": str(tif_path),
        "csv_path": str(tmp_csv_path),
        "total_csv_rows": total_csv_rows,
        "missing_masks": missing_masks
    }

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--npy-roots", nargs="+", required=True)
    ap.add_argument("--mask-root", required=False)
    ap.add_argument("--polygon-file", required=True)
    ap.add_argument("--grid-georef", required=True)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--out-name", required=True)
    ap.add_argument("--date-from", required=False)
    ap.add_argument("--date-to", required=False)
    ap.add_argument("--workers", type=int, default=2)

    args = ap.parse_args()

    npy_roots = [Path(p) for p in args.npy_roots]

    row0, col0, height, width = polygon_to_sr_bbox(args.polygon_file, args.grid_georef)
    area = (row0, col0, row0 + height, col0 + width)

    crs, transform_sr = get_sr_transform(args.grid_georef)
    crop_transform = transform_sr * Affine.translation(col0, row0)

    out_root = Path(args.out_root) / args.out_name
    geotiff_dir = out_root / "geotiff"
    geotiff_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_root / "pixeles_imputados.csv"
    readme_path = out_root / "README_GEOTIFF_IMPUTACION.txt"
    zip_path = out_root / f"{args.out_name}_geotiff_csv.zip"

    all_tiles = list_all_tiles(npy_roots)

    tiles_needed = []

    for tile in all_tiles:
        tb = tile_bounds_sr(tile)
        if intersects(area, tb):
            tiles_needed.append((tile, tb))

    if not tiles_needed:
        raise SystemExit("El área no intersecta ningún tile disponible en los NPY SR x4.")

    dates = list_all_dates(npy_roots, args.date_from, args.date_to)

    if not dates:
        raise SystemExit("No se encontraron fechas en el rango solicitado.")

    valid_dates = []

    for fecha in dates:
        missing = [tile for tile, _ in tiles_needed if find_npy_file(npy_roots, fecha, tile) is None]
        if not missing:
            valid_dates.append(fecha)

    if not valid_dates:
        raise SystemExit("No hay fechas con todos los tiles necesarios para el área seleccionada.")

    print("Área SR:", area, flush=True)
    print("Tiles necesarios:", [t[0] for t in tiles_needed], flush=True)
    print("Fechas seleccionadas:", len(valid_dates), flush=True)

    mr0 = min(tb[0] for _, tb in tiles_needed)
    mc0 = min(tb[1] for _, tb in tiles_needed)
    mr1 = max(tb[2] for _, tb in tiles_needed)
    mc1 = max(tb[3] for _, tb in tiles_needed)

    mosaic_h = mr1 - mr0
    mosaic_w = mc1 - mc0

    crop_left = col0 - mc0
    crop_top = row0 - mr0
    crop_right = crop_left + width
    crop_bottom = crop_top + height

    csv_fields = [
        "fecha",
        "tile",
        "row_raw_global",
        "col_raw_global",
        "row_sr0",
        "col_sr0",
        "row_sr1_exclusive",
        "col_sr1_exclusive",
        "x_center",
        "y_center",
        "x_min",
        "y_min",
        "x_max",
        "y_max",
        "sr_pixels_afectados"
    ]

    total_csv_rows = 0
    missing_masks = []

    workers = max(1, int(args.workers))

    tmp_csv_dir = out_root / "_csv_tmp"

    if tmp_csv_dir.exists():
        shutil.rmtree(tmp_csv_dir)

    tmp_csv_dir.mkdir(parents=True, exist_ok=True)

    print(f"Workers GeoTIFF: {workers}", flush=True)

    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []

        for date_idx, fecha in enumerate(valid_dates):
            futures.append(
                executor.submit(
                    process_one_date,
                    fecha,
                    date_idx,
                    len(valid_dates),
                    npy_roots,
                    args.mask_root,
                    tiles_needed,
                    row0,
                    col0,
                    height,
                    width,
                    area,
                    transform_sr,
                    crop_transform,
                    crs,
                    geotiff_dir,
                    tmp_csv_dir,
                    csv_fields
                )
            )

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            total_csv_rows += int(result["total_csv_rows"])
            missing_masks.extend(result["missing_masks"])

            print(
                f"Fecha terminada: {result['fecha']} | "
                f"filas CSV: {result['total_csv_rows']}",
                flush=True
            )

    # Unir CSV parciales en un solo CSV final, ordenado por fecha
    with open(csv_path, "w", newline="", encoding="utf-8") as fcsv:
        writer = csv.DictWriter(fcsv, fieldnames=csv_fields)
        writer.writeheader()

        for result in sorted(results, key=lambda item: item["fecha"]):
            with open(result["csv_path"], "r", newline="", encoding="utf-8") as part:
                reader = csv.DictReader(part)
                for row in reader:
                    writer.writerow(row)

    # Borrar CSV temporales
    shutil.rmtree(tmp_csv_dir, ignore_errors=True)

    readme_lines = [
        "Exportación SIRIS: GeoTIFF + CSV de imputación temporal",
        "",
        f"Área SR exportada: row0={row0}, col0={col0}, height={height}, width={width}",
        f"Fechas exportadas: {len(valid_dates)}",
        f"Tiles usados: {', '.join(tile for tile, _ in tiles_needed)}",
        "",
        "GeoTIFF:",
        "- Cada archivo area_YYYYMMDD.tif contiene las bandas en este orden: B04, B03, B02, B08.",
        "- Los GeoTIFF se generan desde los NPY SR x4.",
        "",
        "CSV pixeles_imputados.csv:",
        "- Cada fila representa un píxel original 512x512 marcado como imputado temporalmente.",
        "- Las columnas row_sr0/col_sr0/row_sr1_exclusive/col_sr1_exclusive indican el bloque afectado en resolución SR x4.",
        "- sr_pixels_afectados indica cuántos píxeles SR x4 quedan cubiertos dentro del área exportada.",
        "",
        f"Filas CSV generadas: {total_csv_rows}",
        f"Máscaras faltantes: {len(missing_masks)}"
    ]

    if missing_masks:
        readme_lines.append("")
        readme_lines.append("Primeras máscaras faltantes:")
        readme_lines.extend(missing_masks[:50])

    readme_path.write_text("\n".join(readme_lines), encoding="utf-8")

    zip_outputs(zip_path, geotiff_dir, csv_path, readme_path)

    print("CSV:", csv_path, flush=True)
    print("README:", readme_path, flush=True)
    print("ZIP:", zip_path, flush=True)
    print("Filas CSV:", total_csv_rows, flush=True)


if __name__ == "__main__":
    main()