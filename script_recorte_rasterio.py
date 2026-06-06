import requests
import os
import argparse
import gzip
import json
from datetime import datetime

import rasterio
from rasterio.mask import mask
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
import geopandas as gpd
import numpy as np
import pandas as pd

# ============================
# CONFIG
# ============================
# Bandas principales que necesitas como imagen recortada y como columnas en la tabla
BANDS = ["B02", "B03", "B04", "B08"]
# SCL tambien se guarda como imagen recortada y como columna en la tabla
RASTER_ASSETS = BANDS + ["SCL"]

argParser = argparse.ArgumentParser(
    description=(
        "Descarga/recorta bandas Sentinel-2 L2A a la zona de estudio y, adicionalmente, "
        "genera una tabla de pixeles con B02, B03, B04, B08 y SCL. "
        "No rechaza imagenes por SCL."
    )
)

argParser.add_argument("-s", "--start", required=True, help="Fecha inicial YYYY-MM-DD")
argParser.add_argument("-e", "--end", required=True, help="Fecha final YYYY-MM-DD")
argParser.add_argument("-o", "--output", default="./recortes", help="Carpeta de salida")
argParser.add_argument("--cutline", required=True, help="Ruta al GPKG/SHP del area de estudio")
argParser.add_argument("--overwrite", action="store_true", help="Sobrescribir salidas existentes")

# Mantiene la busqueda liviana como en tu script original: se busca por punto.
argParser.add_argument("--point-lon", type=float, default=-77.281, help="Longitud del punto de busqueda STAC")
argParser.add_argument("--point-lat", type=float, default=1.213, help="Latitud del punto de busqueda STAC")
argParser.add_argument("--limit", type=int, default=50, help="Numero maximo de escenas a consultar")

# Filtro local por tile, util para Pasto: 18NTG
argParser.add_argument("--mgrs-tile", default=None, help="Procesar solo este tile MGRS. Ejemplo: 18NTG")

# Etiqueta para la tabla/resumen cuando corres por semestre.
argParser.add_argument("--period-label", default=None, help="Etiqueta del periodo. Ejemplo: 2016_S1")

# Tabla de pixeles
argParser.add_argument("--no-table", action="store_true", help="Solo descarga rasters; no genera tabla de pixeles")
argParser.add_argument("--chunk-size", type=int, default=300000, help="Numero de pixeles por bloque para escribir la tabla")
argParser.add_argument("--skip-existing-rasters", action="store_true", help="Si el raster ya existe, no lo vuelve a recortar")

args = argParser.parse_args()


# ============================
# UTILIDADES
# ============================
def validar_fecha(fecha: str) -> None:
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Fecha invalida: {fecha}. Usa formato YYYY-MM-DD, por ejemplo 2016-06-30")


def safe_name(texto: str) -> str:
    return "".join(c if c.isalnum() or c in ["_", "-", "."] else "_" for c in texto)


def get_fecha(item):
    scene_id = item["id"]
    try:
        return scene_id.split("_")[2][:8]
    except Exception:
        return item["properties"].get("datetime", "SIN_FECHA")[:10].replace("-", "")


def asegurar_carpetas(output, period_label):
    rasters_dir = os.path.join(output, "rasters")
    if period_label:
        rasters_dir = os.path.join(rasters_dir, period_label)

    tablas_dir = os.path.join(output, "tablas")
    resumen_dir = os.path.join(output, "resumen")

    os.makedirs(rasters_dir, exist_ok=True)
    os.makedirs(tablas_dir, exist_ok=True)
    os.makedirs(resumen_dir, exist_ok=True)

    return rasters_dir, tablas_dir, resumen_dir


# ============================
# TOKEN
# ============================
def get_token():
    url = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel2l2a01/sentinel2-l2"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["token"]


# ============================
# BUSQUEDA STAC
# ============================
def search(start, end, point_lon, point_lat, limit=50):
    """
    Busqueda liviana por punto, como en tu script original.
    Importante: el punto solo sirve para encontrar escenas; el recorte real usa el GPKG completo.
    """
    url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"

    payload = {
        "collections": ["sentinel-2-l2a"],
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "intersects": {
            "type": "Point",
            "coordinates": [point_lon, point_lat]
        },
        "limit": limit
    }

    response = requests.post(url, json=payload)

    if response.status_code != 200:
        print("ERROR STAC")
        print("Status:", response.status_code)
        print("Respuesta del servidor:")
        print(response.text)
        response.raise_for_status()

    return response.json()["features"]


# ============================
# RECORTE Y GUARDADO DE RASTERS
# ============================
def recortar_guardar_raster(url, salida, gdf):
    """
    Abre una banda remota, recorta con el GPKG y guarda SOLO el recorte.
    No descarga la escena completa al disco.
    """
    with rasterio.open(url) as src:
        gdf_proj = gdf.to_crs(src.crs)
        shapes = [geom for geom in gdf_proj.geometry]

        out_img, out_transform = mask(src, shapes, crop=True)

        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_img.shape[1],
            "width": out_img.shape[2],
            "transform": out_transform,
            "driver": "GTiff"
        })

        with rasterio.open(salida, "w", **out_meta) as dest:
            dest.write(out_img)


def descargar_rasters_escena(item, token, gdf, rasters_dir, overwrite=False, skip_existing=False):
    """
    Guarda B02, B03, B04, B08 y SCL como archivos .tif recortados.
    Devuelve un diccionario con las rutas locales de cada raster.
    """
    scene_id = item["id"]
    tile = item["properties"].get("s2:mgrs_tile", "SIN_TILE")
    fecha = get_fecha(item)
    scene_short = safe_name(scene_id)

    faltantes = [asset for asset in RASTER_ASSETS if asset not in item["assets"]]
    if faltantes:
        raise RuntimeError(f"Assets faltantes {faltantes}")

    rutas = {}

    for asset in RASTER_ASSETS:
        url = item["assets"][asset]["href"] + "?" + token
        salida = os.path.join(
            rasters_dir,
            f"{fecha}_{tile}_{scene_short}_{asset}_clip.tif"
        )
        rutas[asset] = salida

        if os.path.exists(salida):
            if skip_existing:
                print(f"   [X] Ya existe {asset}, se conserva: {salida}")
                continue
            if not overwrite:
                print(f"   [X] Ya existe {asset}, usa --overwrite para reemplazar")
                continue

        print(f"   [✂] Recortando/guardando {asset}...", end=" ")
        recortar_guardar_raster(url, salida, gdf)
        print("OK")

    return rutas


# ============================
# TABLA DE PIXELES CON SCL
# ============================
def leer_referencia_local(path_b02, gdf):
    """
    Lee B02 local y vuelve a aplicar la mascara del GPKG para que la tabla incluya
    pixeles reales de la zona de estudio, no el rectangulo externo del recorte.
    """
    with rasterio.open(path_b02) as src:
        gdf_proj = gdf.to_crs(src.crs)
        shapes = [geom for geom in gdf_proj.geometry]

        # crop=False mantiene la misma grilla del raster recortado guardado.
        arr, _ = mask(src, shapes, crop=False, filled=False)

        ref_meta = {
            "height": src.height,
            "width": src.width,
            "transform": src.transform,
            "crs": src.crs
        }

    return arr[0], ref_meta


def leer_alineada_local(path_raster, ref_meta, ref_mask, resampling=Resampling.nearest):
    """
    Alinea una banda local a la grilla de B02.
    SCL es categorica, por eso se usa nearest.
    """
    height = ref_meta["height"]
    width = ref_meta["width"]
    transform = ref_meta["transform"]
    crs = ref_meta["crs"]

    with rasterio.open(path_raster) as src:
        with WarpedVRT(
            src,
            crs=crs,
            transform=transform,
            width=width,
            height=height,
            resampling=resampling
        ) as vrt:
            arr = vrt.read(1, masked=True)

    arr = np.ma.array(arr, mask=np.logical_or(np.ma.getmaskarray(arr), ref_mask))
    return arr


def valores_float_chunk(arr, idx):
    data = np.ma.getdata(arr).ravel()[idx].astype(np.float32)
    mask_arr = np.ma.getmaskarray(arr).ravel()[idx]
    if mask_arr.any():
        data[mask_arr] = np.nan
    return data


def valores_scl_chunk(arr, idx):
    # SCL suele venir como uint8; se convierte primero a int16 para permitir -9999 si hubiera mascara.
    data = np.ma.getdata(arr).ravel()[idx].astype(np.int16)
    mask_arr = np.ma.getmaskarray(arr).ravel()[idx]
    if mask_arr.any():
        data[mask_arr] = -9999
    return data


def escribir_tabla_pixeles_escena(item, rutas, gdf, table_handle, writer_state, chunk_size=300000):
    """
    Escribe por chunks en un CSV comprimido ya abierto.
    Cada fila es un pixel de la zona de estudio con B02, B03, B04, B08 y SCL.
    """
    scene_id = item["id"]
    tile = item["properties"].get("s2:mgrs_tile", "SIN_TILE")
    fecha = get_fecha(item)
    anio = fecha[:4]

    b02, ref_meta = leer_referencia_local(rutas["B02"], gdf)
    ref_mask = np.ma.getmaskarray(b02)

    height = ref_meta["height"]
    width = ref_meta["width"]
    transform = ref_meta["transform"]

    valid = ~ref_mask
    valid_idx = np.flatnonzero(valid.ravel())

    if valid_idx.size == 0:
        print("   [!] Sin pixeles validos dentro del area de estudio")
        return 0, {}

    datos = {"B02": b02}

    for band in ["B03", "B04", "B08"]:
        datos[band] = leer_alineada_local(
            rutas[band],
            ref_meta=ref_meta,
            ref_mask=ref_mask,
            resampling=Resampling.nearest
        )

    datos["SCL"] = leer_alineada_local(
        rutas["SCL"],
        ref_meta=ref_meta,
        ref_mask=ref_mask,
        resampling=Resampling.nearest
    )

    total = 0
    conteo_scl = {}

    for start in range(0, valid_idx.size, chunk_size):
        idx = valid_idx[start:start + chunk_size]

        rows = (idx // width).astype(np.int32)
        cols = (idx % width).astype(np.int32)

        xs = (
            transform.c
            + (cols.astype(np.float64) + 0.5) * transform.a
            + (rows.astype(np.float64) + 0.5) * transform.b
        ).astype(np.float32)

        ys = (
            transform.f
            + (cols.astype(np.float64) + 0.5) * transform.d
            + (rows.astype(np.float64) + 0.5) * transform.e
        ).astype(np.float32)

        scl_vals = valores_scl_chunk(datos["SCL"], idx)

        # Conteo SCL por escena
        clases, cuentas = np.unique(scl_vals, return_counts=True)
        for clase, cuenta in zip(clases, cuentas):
            clase_i = int(clase)
            conteo_scl[clase_i] = conteo_scl.get(clase_i, 0) + int(cuenta)

        df = pd.DataFrame({
            "scene_id": np.repeat(scene_id, idx.size),
            "fecha": np.repeat(fecha, idx.size),
            "anio": np.repeat(anio, idx.size),
            "tile": np.repeat(tile, idx.size),
            "row": rows,
            "col": cols,
            "x": xs,
            "y": ys,
            "B02": valores_float_chunk(datos["B02"], idx),
            "B03": valores_float_chunk(datos["B03"], idx),
            "B04": valores_float_chunk(datos["B04"], idx),
            "B08": valores_float_chunk(datos["B08"], idx),
            "SCL": scl_vals
        })

        df.to_csv(table_handle, index=False, header=writer_state["first_chunk"])
        writer_state["first_chunk"] = False
        total += len(df)

    return total, dict(sorted(conteo_scl.items()))


# ============================
# MAIN
# ============================
if __name__ == "__main__":
    validar_fecha(args.start)
    validar_fecha(args.end)

    period_label = args.period_label
    if not period_label:
        period_label = f"{args.start}_{args.end}"

    rasters_dir, tablas_dir, resumen_dir = asegurar_carpetas(args.output, period_label)

    print("Cargando area de estudio...")
    gdf = gpd.read_file(args.cutline)

    if gdf.empty:
        raise ValueError("El archivo de area de estudio esta vacio")

    if args.mgrs_tile:
        args.mgrs_tile = args.mgrs_tile.upper()
        print(f"Filtro MGRS activo: {args.mgrs_tile}")

    table_path = os.path.join(tablas_dir, f"{period_label}_pixeles_con_SCL.csv.gz")
    resumen_path = os.path.join(resumen_dir, f"{period_label}_resumen_escenas.csv")

    if not args.no_table:
        if os.path.exists(table_path):
            if args.overwrite:
                os.remove(table_path)
            else:
                raise FileExistsError(f"Ya existe la tabla {table_path}. Usa --overwrite para reemplazar.")
        print(f"Tabla de pixeles: {table_path}")
    else:
        print("Modo --no-table activo: solo se guardaran rasters recortados")

    print("Obteniendo token...")
    token = get_token()

    print("Buscando escenas Sentinel-2 L2A...")
    escenas = search(
        start=args.start,
        end=args.end,
        point_lon=args.point_lon,
        point_lat=args.point_lat,
        limit=args.limit
    )

    print(f"{len(escenas)} escenas encontradas")

    procesadas = 0
    omitidas = 0
    resumen = []

    table_handle = None
    writer_state = {"first_chunk": True}

    try:
        if not args.no_table:
            table_handle = gzip.open(table_path, "wt", newline="")

        for item in escenas:
            scene_id = item["id"]
            tile = item["properties"].get("s2:mgrs_tile", "SIN_TILE")
            fecha = get_fecha(item)

            print("\n--------------------------------------")
            print(f"Escena: {scene_id}")
            print(f"Tile: {tile}")
            print(f"Fecha: {fecha}")

            if args.mgrs_tile and tile.upper() != args.mgrs_tile:
                print(f"   [!] Omitida por tile. Tile escena={tile}, requerido={args.mgrs_tile}")
                omitidas += 1
                resumen.append({
                    "scene_id": scene_id,
                    "fecha": fecha,
                    "tile": tile,
                    "estado": "omitida_tile",
                    "pixeles_tabla": 0,
                    "conteo_scl": "{}"
                })
                continue

            try:
                # 1) Descargar/recortar imagenes de cada banda, incluida SCL.
                rutas = descargar_rasters_escena(
                    item=item,
                    token=token,
                    gdf=gdf,
                    rasters_dir=rasters_dir,
                    overwrite=args.overwrite,
                    skip_existing=args.skip_existing_rasters
                )

                # 2) Crear tabla de pixeles con SCL como columna.
                pixeles = 0
                conteo_scl = {}
                if not args.no_table:
                    print("   [📄] Agregando pixeles a tabla...", end=" ")
                    pixeles, conteo_scl = escribir_tabla_pixeles_escena(
                        item=item,
                        rutas=rutas,
                        gdf=gdf,
                        table_handle=table_handle,
                        writer_state=writer_state,
                        chunk_size=args.chunk_size
                    )
                    print(f"OK ({pixeles} pixeles)")
                    print(f"   [INFO] Conteo SCL escena: {conteo_scl}")

                procesadas += 1
                resumen.append({
                    "scene_id": scene_id,
                    "fecha": fecha,
                    "tile": tile,
                    "estado": "procesada",
                    "pixeles_tabla": pixeles,
                    "conteo_scl": json.dumps(conteo_scl, ensure_ascii=False)
                })

            except Exception as e:
                print(f"   [ERROR] No se pudo procesar la escena: {e}")
                omitidas += 1
                resumen.append({
                    "scene_id": scene_id,
                    "fecha": fecha,
                    "tile": tile,
                    "estado": f"error: {e}",
                    "pixeles_tabla": 0,
                    "conteo_scl": "{}"
                })

    finally:
        if table_handle is not None:
            table_handle.close()

    # Resumen final
    if resumen:
        pd.DataFrame(resumen).to_csv(resumen_path, index=False)

    print("\n======================================")
    print("Proceso terminado")
    print(f"Escenas procesadas: {procesadas}")
    print(f"Escenas omitidas/error: {omitidas}")
    print(f"Rasters recortados en: {rasters_dir}")
    if not args.no_table:
        print(f"Tabla de pixeles: {table_path}")
    print(f"Resumen: {resumen_path}")
    print("======================================")