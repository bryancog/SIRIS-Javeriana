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


def resize_band_lanczos(band, scale):
    """
    band: 2D float32, expected range [0,1]
    returns 2D float32 resized with Lanczos.
    """
    band = np.asarray(band, dtype=np.float32)
    h, w = band.shape
    out_size = (w * scale, h * scale)  # PIL usa (width, height)

    img = Image.fromarray(band, mode="F")
    img_resized = img.resize(out_size, resample=Image.Resampling.LANCZOS)

    arr = np.asarray(img_resized, dtype=np.float32)
    arr = np.clip(arr, 0.0, 1.0)
    return arr


def sr_tile_x4_uint16(tile, scale):
    """
    Entrada:
      tile: C,H,W float32 normalizado [0,1]

    Salida:
      C,H*scale,W*scale uint16 en [0,65535]
    """
    if tile.ndim != 3:
        raise ValueError(f"Tile debe ser C,H,W. Shape recibido: {tile.shape}")

    c, h, w = tile.shape
    out = np.empty((c, h * scale, w * scale), dtype=np.uint16)

    for b in range(c):
        band_sr = resize_band_lanczos(tile[b], scale)
        out[b] = np.round(band_sr * 65535.0).astype(np.uint16)

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--date", type=int, required=True)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--input-root", default="outputs_sr_input")
    parser.add_argument("--output-root", default="outputs_sr_x4_lanczos")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    base = Path(args.base_dir)
    in_dir = base / args.input_root / f"date_{args.date}"
    out_dir = base / args.output_root / f"date_{args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_dir.exists():
        raise FileNotFoundError(f"No existe carpeta de entrada: {in_dir}")

    tiles = sorted(in_dir.glob("tile_r*_c*.npy"))
    tiles = [t for t in tiles if not t.name.endswith("_meta.npy")]

    if not tiles:
        raise FileNotFoundError(f"No se encontraron tiles .npy en {in_dir}")

    log("=" * 80)
    log(f"SR x{args.scale} Lanczos fecha {args.date}")
    log(f"Entrada: {in_dir}")
    log(f"Salida:  {out_dir}")
    log(f"Tiles:   {len(tiles)}")
    log("=" * 80)

    t0 = time.time()
    processed = 0
    skipped = 0

    for tile_path in tiles:
        tile_name = tile_path.stem
        out_tile = out_dir / f"{tile_name}_x{args.scale}_uint16.npy"
        out_meta = out_dir / f"{tile_name}_x{args.scale}_meta.npz"

        if out_tile.exists() and out_meta.exists() and not args.overwrite:
            skipped += 1
            continue

        tile = np.load(tile_path, mmap_mode="r")
        tile = np.asarray(tile, dtype=np.float32)

        # Seguridad: entrada normalizada
        tile = np.clip(tile, 0.0, 1.0)

        sr = sr_tile_x4_uint16(tile, args.scale)
        np.save(out_tile, sr)

        meta_in_path = in_dir / f"{tile_name}_meta.npz"
        if meta_in_path.exists():
            meta_in = np.load(meta_in_path)
            valid_fraction = float(meta_in["valid_fraction"]) if "valid_fraction" in meta_in else np.nan
            band_names = meta_in["band_names"] if "band_names" in meta_in else np.array(["B04", "B03", "B02", "B08"])
            row0 = int(meta_in["row0"]) if "row0" in meta_in else -1
            col0 = int(meta_in["col0"]) if "col0" in meta_in else -1
        else:
            valid_fraction = np.nan
            band_names = np.array(["B04", "B03", "B02", "B08"])
            row0 = -1
            col0 = -1

        np.savez(
            out_meta,
            date=np.array(args.date, dtype=np.int32),
            method=np.array("lanczos"),
            scale_factor=np.array(args.scale, dtype=np.int32),
            input_shape=np.array(tile.shape, dtype=np.int32),
            output_shape=np.array(sr.shape, dtype=np.int32),
            input_dtype=np.array(str(tile.dtype)),
            output_dtype=np.array(str(sr.dtype)),
            input_value_range=np.array([0.0, 1.0], dtype=np.float32),
            output_value_range=np.array([0, 65535], dtype=np.uint16),
            uint16_scale=np.array(1.0 / 65535.0, dtype=np.float32),
            band_names=band_names,
            row0=np.array(row0, dtype=np.int32),
            col0=np.array(col0, dtype=np.int32),
            valid_fraction=np.array(valid_fraction, dtype=np.float32),
        )

        processed += 1

        if processed == 1 or processed % 5 == 0 or processed == len(tiles):
            log(f"  Procesados {processed}/{len(tiles)} tiles")

    elapsed = (time.time() - t0) / 60.0

    summary = {
        "date": int(args.date),
        "method": "lanczos",
        "scale_factor": int(args.scale),
        "input_resolution_m": 10.0,
        "output_resolution_m": 10.0 / float(args.scale),
        "input_dtype": "float32_normalized_0_1",
        "output_dtype": "uint16_0_65535",
        "tiles_found": int(len(tiles)),
        "tiles_processed": int(processed),
        "tiles_skipped": int(skipped),
        "elapsed_min": float(elapsed),
    }

    with open(out_dir / "summary_x4.json", "w") as f:
        json.dump(summary, f, indent=2)

    log(json.dumps(summary, indent=2))
    log("COMPLETADO")


if __name__ == "__main__":
    main()
