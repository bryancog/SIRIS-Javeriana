#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def parse_tile(tile_name):
    parts = tile_name.split("_")
    r0 = int(parts[1].replace("r", ""))
    c0 = int(parts[2].replace("c", ""))
    return r0, c0


def rgb_uint8_from_chw(tile_chw, mode="p1p99"):
    """
    tile_chw: 4,H,W en orden B04,B03,B02,B08.
    Devuelve RGB uint8.
    """
    rgb = tile_chw[:3].astype(np.float32)

    if rgb.max() > 1.5:
        rgb = rgb / 65535.0

    out = []

    for i in range(3):
        band = rgb[i]

        if mode == "raw":
            band_norm = np.clip(band, 0.0, 1.0)

        elif mode == "p1p99":
            lo, hi = np.nanpercentile(band, [1, 99])
            if hi <= lo:
                band_norm = np.zeros_like(band, dtype=np.float32)
            else:
                band_norm = (band - lo) / (hi - lo)
                band_norm = np.clip(band_norm, 0.0, 1.0)

        elif mode == "p2p98":
            lo, hi = np.nanpercentile(band, [2, 98])
            if hi <= lo:
                band_norm = np.zeros_like(band, dtype=np.float32)
            else:
                band_norm = (band - lo) / (hi - lo)
                band_norm = np.clip(band_norm, 0.0, 1.0)

        else:
            raise ValueError(f"Modo no reconocido: {mode}")

        out.append((band_norm * 255).round().astype(np.uint8))

    return np.stack(out, axis=-1)


def save_jpg(tile_chw, out_path, mode="p1p99", quality=90):
    rgb = rgb_uint8_from_chw(tile_chw, mode=mode)
    Image.fromarray(rgb).save(out_path, quality=quality, optimize=True)
    log(f"Guardado JPG: {out_path}")


def resize_band_lanczos(band, scale):
    band = np.asarray(band, dtype=np.float32)
    h, w = band.shape
    img = Image.fromarray(band, mode="F")
    img_resized = img.resize((w * scale, h * scale), resample=Image.Resampling.LANCZOS)
    arr = np.asarray(img_resized, dtype=np.float32)
    arr = np.clip(arr, 0.0, 1.0)
    return arr


def sr_lanczos_x4_uint16(tile_chw, scale=4):
    c, h, w = tile_chw.shape
    out = np.empty((c, h * scale, w * scale), dtype=np.uint16)

    for b in range(c):
        band_sr = resize_band_lanczos(tile_chw[b], scale)
        out[b] = np.round(band_sr * 65535.0).astype(np.uint16)

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--date", type=int, default=20160103)
    parser.add_argument("--tile", default="tile_r00000_c01536")
    parser.add_argument("--tile-size", type=int, default=512)
    parser.add_argument("--scale", type=int, default=4)
    args = parser.parse_args()

    base = Path(args.base_dir)
    interp_dir = base / "outputs_interp"
    out_dir = base / "test_tile_v2" / f"date_{args.date}" / args.tile
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(base / "grid_metadata.json", "r") as f:
        grid = json.load(f)

    row_min = int(grid["row_min"])
    col_min = int(grid["col_min"])

    fechas = np.load(base / "SAITS_fechas.npy").astype(int)
    pos = np.where(fechas == args.date)[0]

    if len(pos) == 0:
        raise ValueError(f"Fecha {args.date} no encontrada en SAITS_fechas.npy")

    time_index = int(pos[0])
    r0, c0 = parse_tile(args.tile)
    tile_size = int(args.tile_size)

    log("=" * 80)
    log("Prueba V2 tile")
    log(f"Fecha: {args.date} | time_index={time_index}")
    log(f"Tile: {args.tile} | r0={r0}, c0={c0}")
    log("=" * 80)

    # Canvas en orden original: B02, B03, B04, B08
    canvas = np.zeros((tile_size, tile_size, 4), dtype=np.float32)
    valid_mask = np.zeros((tile_size, tile_size), dtype=bool)

    meta_files = sorted(interp_dir.glob("meta_*.npz"))

    if not meta_files:
        raise FileNotFoundError("No hay archivos meta_*.npz en outputs_interp")

    n_hits = 0
    n_pixels = 0

    for meta_path in meta_files:
        tag = meta_path.stem.replace("meta_", "")
        x_path = interp_dir / f"Ximp_{tag}.npy"

        if not x_path.exists():
            raise FileNotFoundError(f"Falta {x_path}")

        meta = np.load(meta_path)
        rows_abs = meta["rows"].astype(np.int64)
        cols_abs = meta["cols"].astype(np.int64)

        rows_rel = rows_abs - row_min
        cols_rel = cols_abs - col_min

        inside = (
            (rows_rel >= r0) &
            (rows_rel < r0 + tile_size) &
            (cols_rel >= c0) &
            (cols_rel < c0 + tile_size)
        )

        if not inside.any():
            continue

        X = np.load(x_path, mmap_mode="r")
        vals = np.asarray(X[inside, time_index, :], dtype=np.float32)

        rr = rows_rel[inside] - r0
        cc = cols_rel[inside] - c0

        canvas[rr, cc, :] = vals
        valid_mask[rr, cc] = True

        n_hits += 1
        n_pixels += int(inside.sum())

        log(f"  Bloque con pixeles: {tag} | pixeles={int(inside.sum()):,}")

    log(f"Bloques con interseccion: {n_hits}")
    log(f"Pixeles asignados: {n_pixels:,}")
    log(f"Fraccion valida tile: {valid_mask.mean():.2%}")

    # Reordenar a RGBN: B04, B03, B02, B08
    tile_10m_rgbn = np.transpose(canvas[:, :, [2, 1, 0, 3]], (2, 0, 1)).astype(np.float32)

    out_10m = out_dir / f"{args.tile}_10m_v2.npy"
    np.save(out_10m, tile_10m_rgbn)
    log(f"Guardado 10m NPY: {out_10m}")

    save_jpg(tile_10m_rgbn, out_dir / f"{args.tile}_10m_v2_raw.jpg", mode="raw")
    save_jpg(tile_10m_rgbn, out_dir / f"{args.tile}_10m_v2_p1p99.jpg", mode="p1p99")
    save_jpg(tile_10m_rgbn, out_dir / f"{args.tile}_10m_v2_p2p98.jpg", mode="p2p98")

    tile_x4 = sr_lanczos_x4_uint16(tile_10m_rgbn, scale=args.scale)

    out_x4 = out_dir / f"{args.tile}_x4_v2_uint16.npy"
    np.save(out_x4, tile_x4)
    log(f"Guardado SR x4 NPY: {out_x4}")

    save_jpg(tile_x4, out_dir / f"{args.tile}_x4_v2_raw.jpg", mode="raw")
    save_jpg(tile_x4, out_dir / f"{args.tile}_x4_v2_p1p99.jpg", mode="p1p99")
    save_jpg(tile_x4, out_dir / f"{args.tile}_x4_v2_p2p98.jpg", mode="p2p98")

    summary = {
        "date": int(args.date),
        "tile": args.tile,
        "time_index": int(time_index),
        "row0_relative": int(r0),
        "col0_relative": int(c0),
        "tile_size_10m": int(tile_size),
        "scale_factor": int(args.scale),
        "tile_size_x4": int(tile_size * args.scale),
        "band_order": ["B04", "B03", "B02", "B08"],
        "valid_fraction_tile": float(valid_mask.mean()),
        "n_pixels_assigned": int(n_pixels),
        "output_10m": str(out_10m),
        "output_x4": str(out_x4),
    }

    summary_path = out_dir / "summary_test_tile_v2.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    log(json.dumps(summary, indent=2))
    log("COMPLETADO")


if __name__ == "__main__":
    main()
