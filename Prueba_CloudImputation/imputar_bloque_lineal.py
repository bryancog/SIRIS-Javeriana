#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import time
from pathlib import Path

import numpy as np


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def impute_1d(y):
    y = y.astype(np.float32, copy=True)
    idx = np.arange(y.shape[0], dtype=np.float32)
    valid = np.isfinite(y)

    n_valid = int(valid.sum())

    if n_valid == 0:
        return np.zeros_like(y, dtype=np.float32)

    if n_valid == 1:
        y[:] = y[valid][0]
        return y

    y[~valid] = np.interp(idx[~valid], idx[valid], y[valid]).astype(np.float32)
    return y


def impute_block(X):
    out = X.astype(np.float32, copy=True)
    n_series, _, n_bands = out.shape

    for i in range(n_series):
        for b in range(n_bands):
            out[i, :, b] = impute_1d(out[i, :, b])

        if (i + 1) % 10000 == 0:
            log(f"  imputadas {i+1:,}/{n_series:,} series")

    return out


def decode_keys(keys):
    rows = (keys >> np.int64(32)).astype(np.int32)
    cols = (keys & np.int64(0xFFFFFFFF)).astype(np.int64).astype(np.int32)
    return rows, cols


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--manifest", default="outputs_interp/manifest.tsv")
    parser.add_argument("--task-id", type=int, required=True)
    args = parser.parse_args()

    base = Path(args.base_dir)
    manifest_path = base / args.manifest
    outdir = base / "outputs_interp"
    outdir.mkdir(exist_ok=True)

    lines = [x.strip() for x in open(manifest_path) if x.strip()]
    row = lines[args.task_id].split("\t")

    _, split, input_path, start, end, block_tag = row
    input_path = Path(input_path)
    start = int(start)
    end = int(end)

    log("=" * 80)
    log(f"TASK {args.task_id}")
    log(f"Split: {split}")
    log(f"Input: {input_path}")
    log(f"Rango: {start:,} - {end:,}")
    log(f"Block tag: {block_tag}")
    log("=" * 80)

    X = np.load(input_path, mmap_mode="r")
    block = np.array(X[start:end, :, :], dtype=np.float32, copy=True)

    log(f"Bloque cargado: shape={block.shape}, missing={np.isnan(block).mean():.2%}")

    t0 = time.time()
    X_imp = impute_block(block)
    elapsed = (time.time() - t0) / 60

    log(f"Imputacion terminada en {elapsed:.2f} min")
    log(f"Missing final: {np.isnan(X_imp).mean():.2%}")

    out_data = outdir / f"Ximp_{block_tag}.npy"
    np.save(out_data, X_imp)

    key_file = base / f"SAITS_pixel_keys_{split}.npy"
    keys_all = np.load(key_file, mmap_mode="r")
    keys = np.array(keys_all[start:end], copy=True)

    rows, cols = decode_keys(keys)
    fechas = np.load(base / "SAITS_fechas.npy")

    out_meta = outdir / f"meta_{block_tag}.npz"
    np.savez(
        out_meta,
        split=split,
        start=start,
        end=end,
        keys=keys,
        rows=rows,
        cols=cols,
        fechas=fechas,
        shape=X_imp.shape,
    )

    log(f"Guardado: {out_data}")
    log(f"Guardado: {out_meta}")
    log("COMPLETADO")


if __name__ == "__main__":
    main()
