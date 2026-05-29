#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def list_date_dirs(root):
    return sorted([p for p in root.glob("date_*") if p.is_dir()])


def compute_global_scale(tile_files, sample_stride=32, p_low=2, p_high=98):
    samples = [[], [], []]

    log("Calculando escala visual global para toda la serie...")

    for i, tile_path in enumerate(tile_files, 1):
        x = np.load(tile_path, mmap_mode="r")

        # x: B04, B03, B02, B08 en uint16
        rgb = x[:3, ::sample_stride, ::sample_stride].astype(np.float32)

        for b in range(3):
            samples[b].append(rgb[b].ravel())

        if i == 1 or i == len(tile_files) or i % 50 == 0:
            log(f"  escala global: {i}/{len(tile_files)} tiles muestreados")

    lows = []
    highs = []

    for b in range(3):
        vals = np.concatenate(samples[b])
        lows.append(float(np.percentile(vals, p_low)))
        highs.append(float(np.percentile(vals, p_high)))

    scale = {
        "p_low": p_low,
        "p_high": p_high,
        "low": lows,
        "high": highs,
        "band_order": ["B04", "B03", "B02"],
        "input_dtype": "uint16",
        "input_range": [0, 65535],
    }

    log(f"Escala global: {scale}")
    return scale


def rgb_to_uint8_global(x, scale, gamma=1.0):
    rgb = x[:3].astype(np.float32)
    out = []

    for b in range(3):
        lo = scale["low"][b]
        hi = scale["high"][b]

        if hi <= lo:
            y = np.zeros_like(rgb[b], dtype=np.float32)
        else:
            y = (rgb[b] - lo) / (hi - lo)
            y = np.clip(y, 0.0, 1.0)

        if gamma != 1.0:
            y = np.power(y, gamma)

        out.append((y * 255).round().astype(np.uint8))

    return np.stack(out, axis=-1)


def add_label(img, text):
    draw = ImageDraw.Draw(img)

    # Fondo semitransparente simulado en negro sólido
    margin = 12
    box_w = 260
    box_h = 38
    draw.rectangle([margin, margin, margin + box_w, margin + box_h], fill=(0, 0, 0))
    draw.text((margin + 10, margin + 10), text, fill=(255, 255, 255))

    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--tile", default="tile_r00000_c01536")
    parser.add_argument("--input-root", default="outputs_sr_x4_lanczos")
    parser.add_argument("--output-root", default="series_tile_sr")
    parser.add_argument("--quality", type=int, default=90)
    parser.add_argument("--resize-width", type=int, default=1024, help="0 conserva 2048 px")
    parser.add_argument("--sample-stride", type=int, default=32)
    parser.add_argument("--p-low", type=float, default=2)
    parser.add_argument("--p-high", type=float, default=98)
    parser.add_argument("--gamma", type=float, default=0.9)
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    base = Path(args.base_dir)
    input_root = base / args.input_root
    out_root = base / args.output_root / args.tile
    frames_dir = out_root / "frames_jpg"
    frames_dir.mkdir(parents=True, exist_ok=True)

    date_dirs = list_date_dirs(input_root)

    if not date_dirs:
        raise FileNotFoundError(f"No hay carpetas date_* en {input_root}")

    tile_files = []
    dates = []

    for d in date_dirs:
        date = d.name.replace("date_", "")
        tile_path = d / f"{args.tile}_x4_uint16.npy"

        if tile_path.exists():
            tile_files.append(tile_path)
            dates.append(date)

    if not tile_files:
        raise FileNotFoundError(f"No encontré tile {args.tile} en {input_root}")

    log("=" * 80)
    log("EXTRACCIÓN DE SERIE TEMPORAL SR X4")
    log(f"Tile: {args.tile}")
    log(f"Fechas encontradas: {len(tile_files)}")
    log(f"Salida: {out_root}")
    log("=" * 80)

    scale_path = out_root / "visual_scale_global.json"

    if scale_path.exists() and not args.overwrite:
        with open(scale_path, "r", encoding="utf-8") as f:
            scale = json.load(f)
        log(f"Escala global existente cargada: {scale_path}")
    else:
        scale = compute_global_scale(
            tile_files,
            sample_stride=args.sample_stride,
            p_low=args.p_low,
            p_high=args.p_high,
        )
        with open(scale_path, "w", encoding="utf-8") as f:
            json.dump(scale, f, indent=2)

    manifest_path = out_root / "manifest_frames.csv"

    written = 0

    with open(manifest_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["date", "source_npy", "output_jpg", "shape", "dtype"],
        )
        writer.writeheader()

        for i, (date, tile_path) in enumerate(zip(dates, tile_files), 1):
            out_jpg = frames_dir / f"{i:04d}_{date}_{args.tile}.jpg"

            if out_jpg.exists() and not args.overwrite:
                continue

            x = np.load(tile_path, mmap_mode="r")
            rgb = rgb_to_uint8_global(x, scale=scale, gamma=args.gamma)

            img = Image.fromarray(rgb)

            if args.resize_width and args.resize_width > 0:
                w, h = img.size
                new_w = args.resize_width
                new_h = int(round(h * (new_w / w)))
                img = img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

            if args.annotate:
                img = add_label(img, date)

            img.save(out_jpg, quality=args.quality, optimize=True)

            writer.writerow({
                "date": date,
                "source_npy": str(tile_path),
                "output_jpg": str(out_jpg),
                "shape": tuple(x.shape),
                "dtype": str(x.dtype),
            })

            written += 1

            if i == 1 or i == len(tile_files) or i % 50 == 0:
                log(f"  Frames generados: {i}/{len(tile_files)}")

    summary = {
        "tile": args.tile,
        "n_dates": len(tile_files),
        "frames_dir": str(frames_dir),
        "quality": args.quality,
        "resize_width": args.resize_width,
       
cale_path),
        "manifest": str(manifest_path),
        "written
    }

    with open(out_root / "summary_series_tile.json", "w", encoding="utf-8
        json.dump(summary, f, indent=2)

    log(json.dumps(sum
    log("COMPLETADO")


if __name__ == "__main__":
    main()
