#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    parser.add_argument("--block-size", type=int, default=100000)
    args = parser.parse_args()

    base = Path(args.base_dir)
    outdir = base / "outputs_interp"
    outdir.mkdir(exist_ok=True)

    good_idx = np.load(base / "SAITS_good_pixel_indices.npy")
    pixel_keys = np.load(base / "SAITS_pixel_keys.npy")

    rng = np.random.default_rng(42)
    perm = rng.permutation(len(good_idx))

    n = len(good_idx)
    nt = int(n * 0.70)
    nv = int(n * 0.15)

    # IMPORTANTE:
    # El fusionador escribió train/val/test con índices ordenados para mejorar I/O.
    # Por eso aquí debemos usar el mismo orden con np.sort(...).
    idx_train = np.sort(good_idx[perm[:nt]])
    idx_val = np.sort(good_idx[perm[nt:nt + nv]])
    idx_test = np.sort(good_idx[perm[nt + nv:]])

    split_indices = {
        "train": idx_train,
        "val": idx_val,
        "test": idx_test,
    }

    for split, idx in split_indices.items():
        keys = pixel_keys[idx]
        np.save(base / f"SAITS_pixel_keys_{split}.npy", keys)
        print(f"{split}: {len(keys):,} keys guardadas")

    datasets = [
        ("train", base / "SAITS_X_train.npy"),
        ("val", base / "SAITS_X_val.npy"),
        ("test", base / "SAITS_X_test.npy"),
    ]

    manifest_path = outdir / "manifest.tsv"
    task_id = 0

    with open(manifest_path, "w") as f:
        for split, path in datasets:
            arr = np.load(path, mmap_mode="r")
            n_series = arr.shape[0]

            for start in range(0, n_series, args.block_size):
                end = min(start + args.block_size, n_series)
                block_tag = f"{split}_{start:08d}_{end:08d}"

                f.write(
                    f"{task_id}\t{split}\t{path}\t{start}\t{end}\t{block_tag}\n"
                )
                task_id += 1

    print(f"Manifest creado: {manifest_path}")
    print(f"Tareas totales: {task_id}")
    print(f"Para lanzar: sbatch --array=0-{task_id-1}%4 job_interp_blocks.sh")


if __name__ == "__main__":
    main()
