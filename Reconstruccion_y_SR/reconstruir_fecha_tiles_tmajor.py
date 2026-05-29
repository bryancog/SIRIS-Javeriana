#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import time
from pathlib import Path
import numpy as np


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--date", type=int, required=True)
    parser.add_argument("--tile-size", type=int, default=512)
    parser.add_argument("--stride", type=int, default=512)
    parser.add_argument("--min-valid", type=float, default=0.80)
    parser.add_argument("--band-order", choices=["original", "RGBN"], default="RGBN")
    args = parser.parse_args()

    base = Path(args.base_dir)
    tdir = base / "outputs_interp_tmajor"
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
        raise ValueError(f"Fecha {args.date} no existe")

    ti = int(matches[0])

    log("=" * 80)
    log(f"Reconstruyendo fecha {args.date}")
    log(f"Time index: {ti}")
    log(f"Grid: {height} x {width}")
    log("=" * 80)

    canvas = np.zeros((height, width, 4), dtype=np.float32)
    valid_mask = np.zeros((height, width), dtype=bool)

    meta_files = sorted(tdir.glob("meta_*.npz"))
    if not meta_files:
        raise FileNotFoundError(f"No hay meta_*.npz en {tdir}")

    for i, meta_file in enumerate(meta_files, 1):
        tag = meta_file.stem.replace("meta_", "")
        x_file = tdir / f"XimpT_{tag}.npy"

        if not x_file.exists():
            raise FileNotFoundError(f"Falta {x_file}")

        meta = np.load(meta_file)
        rows = meta["rows"].astype(np.int64) - row_min
        cols = meta["cols"].astype(np.int64) - col_min

        X = np.load(x_file, mmap_mode="r")
        vals = np.asarray(X[ti, :, :], dtype=np.float32)

        canvas[rows, cols, :] = vals
        valid_mask[rows, cols] = True

        if i == 1 or i == len(meta_files) or i % 10 == 0:
            log(f"  Bloques cargados: {i}/{len(meta_files)}")

    if args.band_order == "RGBN":
        canvas = canvas[:, :, [2, 1, 0, 3]]
        band_names = ["B04", "B03", "B02", "B08"]
    else:
        band_names = ["B02", "B03", "B04", "B08"]

    n_tiles = 0
    n_saved = 0

    for r0 in range(0, height, args.stride):
        for c0 in range(0, width, args.stride):
            r1 = r0 + args.tile_size
            c1 = c0 + args.tile_size

            if r1 > height or c1 > width:
                continue

            valid_fraction = float(valid_mask[r0:r1, c0:c1].mean())
            n_tiles += 1

            if valid_fraction < args.min_valid:
                continue

            tile = canvas[r0:r1, c0:c1, :]
            tile_chw = np.transpose(tile, (2, 0, 1)).astype(np.float32)

            name = f"tile_r{r0:05d}_c{c0:05d}"
            np.save(out_dir / f"{name}.npy", tile_chw)
            np.savez(
                out_dir / f"{name}_meta.npz",
                date=np.array(args.date, dtype=np.int32),
                time_index=np.array(ti, dtype=np.int32),
                row0=np.array(r0 + row_min, dtype=np.int32),
                col0=np.array(c0 + col_min, dtype=np.int32),
                tile_size=np.array(args.tile_size, dtype=np.int32),
                stride=np.array(args.stride, dtype=np.int32),
                valid_fraction=np.array(valid_fraction, dtype=np.float32),
                band_names=np.array(band_names),
                band_order=np.array(args.band_order),
                shape=np.array(tile_chw.shape, dtype=np.int32),
            )
            n_saved += 1

    summary = {
        "date": int(args.date),
        "time_index": int(ti),
        "height": int(height),
        "width": int(width),
        "tile_size": int(args.tile_size),
        "stride": int(args.stride),
        "min_valid": float(args.min_valid),
        "tiles_evaluated": int(n_tiles),
        "tiles_saved": int(n_saved),
        "band_order": args.band_order,
        "band_names": band_names,
        "global_valid_fraction": float(valid_mask.mean()),
    }

    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log(json.dumps(summary, indent=2))
    log(f"Salida: {out_dir}")
    log("COMPLETADO")


if __name__ == "__main__":
    main()
