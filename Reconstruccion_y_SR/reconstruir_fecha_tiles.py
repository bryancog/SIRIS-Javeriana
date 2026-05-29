#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import time
from pathlib import Path

import numpy as np


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_minmax(base):
    meta_path = base / "SAITS_metadata.json"
    if not meta_path.exists():
        return None

    with open(meta_path, "r") as f:
        meta = json.load(f)

    mm = meta.get("minmax", None)
    if mm is None:
        return None

    bands = ["B02", "B03", "B04", "B08"]
    mins = np.array([mm[b]["min"] for b in bands], dtype=np.float32)
    maxs = np.array([mm[b]["max"] for b in bands], dtype=np.float32)
    return mins, maxs


def scale_values(vals, mode, minmax):
    vals = vals.astype(np.float32, copy=True)

    if mode == "normalized":
        return vals

    if minmax is None:
        raise RuntimeError("SAITS_metadata.json does not contain minmax values")

    mins, maxs = minmax
    vals = vals * (maxs - mins) + mins

    if mode == "raw_dn":
        return vals

    if mode == "sen2sr":
        return vals / 10000.0

    raise ValueError(f"Unknown value scale: {mode}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--date", type=int, required=True)
    parser.add_argument("--tile-size", type=int, default=512)
    parser.add_argument("--stride", type=int, default=512)
    parser.add_argument("--min-valid", type=float, default=0.80)
    parser.add_argument("--band-order", choices=["original", "RGBN"], default="RGBN")
    parser.add_argument("--value-scale", choices=["normalized", "raw_dn", "sen2sr"], default="normalized")
    parser.add_argument("--fill-value", type=float, default=0.0)
    args = parser.parse_args()

    base = Path(args.base_dir)
    interp_dir = base / "outputs_interp"
    out_dir = base / "outputs_sr_input" / f"date_{args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(base / "grid_metadata.json", "r") as f:
        grid = json.load(f)

    row_min = int(grid["row_min"])
    col_min = int(grid["col_min"])
    height = int(grid["height"])
    width = int(grid["width"])

    fechas = np.load(base / "SAITS_fechas.npy").astype(int)
    matches = np.where(fechas == args.date)[0]
    if len(matches) == 0:
        raise ValueError(f"Date {args.date} is not present in SAITS_fechas.npy")

    time_index = int(matches[0])

    log("=" * 80)
    log(f"Reconstructing date: {args.date}")
    log(f"Time index: {time_index}")
    log(f"Grid: height={height}, width={width}")
    log(f"Tile size={args.tile_size}, stride={args.stride}, min_valid={args.min_valid}")
    log(f"Band order={args.band_order}, value_scale={args.value_scale}")
    log("=" * 80)

    canvas = np.full((height, width, 4), args.fill_value, dtype=np.float32)
    valid_mask = np.zeros((height, width), dtype=bool)

    minmax = load_minmax(base)
    meta_files = sorted(interp_dir.glob("meta_*.npz"))

    if not meta_files:
        raise FileNotFoundError(f"No meta_*.npz files found in {interp_dir}")

    log(f"Meta blocks found: {len(meta_files)}")

    for i, meta_file in enumerate(meta_files, start=1):
        tag = meta_file.stem.replace("meta_", "")
        x_file = interp_dir / f"Ximp_{tag}.npy"

        if not x_file.exists():
            raise FileNotFoundError(f"Missing block file: {x_file}")

        meta = np.load(meta_file)
        rows = meta["rows"].astype(np.int64) - row_min
        cols = meta["cols"].astype(np.int64) - col_min

        X = np.load(x_file, mmap_mode="r")
        vals = np.asarray(X[:, time_index, :], dtype=np.float32)
        vals = scale_values(vals, args.value_scale, minmax)

        canvas[rows, cols, :] = vals
        valid_mask[rows, cols] = True

        if i == 1 or i == len(meta_files) or i % 10 == 0:
            log(f"  Loaded blocks: {i}/{len(meta_files)}")

    global_valid_fraction = float(valid_mask.mean())
    log(f"Global valid fraction: {global_valid_fraction:.2%}")

    if args.band_order == "RGBN":
        # Input order:  B02, B03, B04, B08
        # Output order: B04, B03, B02, B08
        canvas = canvas[:, :, [2, 1, 0, 3]]
        band_names = ["B04", "B03", "B02", "B08"]
    else:
        band_names = ["B02", "B03", "B04", "B08"]

    n_tiles = 0
    n_saved = 0

    for r0 in range(0, height, args.stride):
        for c0 in range(0, width, args.stride):
            r1 = min(r0 + args.tile_size, height)
            c1 = min(c0 + args.tile_size, width)

            if (r1 - r0) != args.tile_size:
                continue
            if (c1 - c0) != args.tile_size:
                continue

            mask_tile = valid_mask[r0:r1, c0:c1]
            valid_fraction = float(mask_tile.mean())
            n_tiles += 1

            if valid_fraction < args.min_valid:
                continue

            tile_hwc = canvas[r0:r1, c0:c1, :]
            tile_chw = np.transpose(tile_hwc, (2, 0, 1)).astype(np.float32)

            tile_name = f"tile_r{r0:05d}_c{c0:05d}"
            out_tile = out_dir / f"{tile_name}.npy"
            out_meta = out_dir / f"{tile_name}_meta.npz"

            np.save(out_tile, tile_chw)
            np.savez(
                out_meta,
                date=np.array(args.date, dtype=np.int32),
                time_index=np.array(time_index, dtype=np.int32),
                row0=np.array(r0 + row_min, dtype=np.int32),
                col0=np.array(c0 + col_min, dtype=np.int32),
                tile_size=np.array(args.tile_size, dtype=np.int32),
                stride=np.array(args.stride, dtype=np.int32),
                valid_fraction=np.array(valid_fraction, dtype=np.float32),
                band_names=np.array(band_names),
                value_scale=np.array(args.value_scale),
                band_order=np.array(args.band_order),
                shape=np.array(tile_chw.shape, dtype=np.int32),
            )

            n_saved += 1

    summary = {
        "date": int(args.date),
        "time_index": int(time_index),
        "height": int(height),
        "width": int(width),
        "tile_size": int(args.tile_size),
        "stride": int(args.stride),
        "min_valid": float(args.min_valid),
        "tiles_evaluated": int(n_tiles),
        "tiles_saved": int(n_saved),
        "band_order": args.band_order,
        "band_names": band_names,
        "value_scale": args.value_scale,
        "global_valid_fraction": global_valid_fraction,
    }

    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log(json.dumps(summary, indent=2))
    log(f"Output directory: {out_dir}")
    log("COMPLETED")


if __name__ == "__main__":
    main()
