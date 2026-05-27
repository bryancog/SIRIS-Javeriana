#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import time
from pathlib import Path
import numpy as np


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--manifest", default="outputs_interp/manifest.tsv")
    args = parser.parse_args()

    base = Path(args.base_dir)
    manifest = base / args.manifest
    outdir = base / "outputs_interp_tmajor"
    outdir.mkdir(exist_ok=True)

    lines = [x.strip() for x in open(manifest) if x.strip()]
    row = lines[args.task_id].split("\t")

    _, split, input_path, start, end, block_tag = row
    ximp = base / "outputs_interp" / f"Ximp_{block_tag}.npy"
    meta = base / "outputs_interp" / f"meta_{block_tag}.npz"

    if not ximp.exists():
        raise FileNotFoundError(f"No existe {ximp}")

    if not meta.exists():
        raise FileNotFoundError(f"No existe {meta}")

    out_x = outdir / f"XimpT_{block_tag}.npy"
    out_meta = outdir / f"meta_{block_tag}.npz"

    if out_x.exists() and out_meta.exists():
        log(f"Ya existe, se omite: {out_x}")
        return

    log("=" * 80)
    log(f"TASK {args.task_id}")
    log(f"Block: {block_tag}")
    log(f"Input: {ximp}")
    log("=" * 80)

    X = np.load(ximp, mmap_mode="r")
    log(f"Shape original: {X.shape}")

    # Original: series, fechas, bandas
    # Nuevo:    fechas, series, bandas
    Xt = np.transpose(np.asarray(X, dtype=np.float32), (1, 0, 2)).copy()

    log(f"Shape transpuesta: {Xt.shape}")
    np.save(out_x, Xt)

    # Copiamos metadata del bloque
    m = np.load(meta)
    np.savez(
        out_meta,
        split=m["split"],
        start=m["start"],
        end=m["end"],
        keys=m["keys"],
        rows=m["rows"],
        cols=m["cols"],
        fechas=m["fechas"],
        shape_tmajor=np.array(Xt.shape, dtype=np.int32),
        source_shape=np.array(X.shape, dtype=np.int32),
    )

    log(f"Guardado: {out_x}")
    log(f"Guardado: {out_meta}")
    log("COMPLETADO")


if __name__ == "__main__":
    main()
