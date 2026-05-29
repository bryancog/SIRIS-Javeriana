#!/usr/bin/env python3
"""
Fusionador Sentinel-2 para ZINE/HPC — versión optimizada por fecha.

Cambios frente a la versión memmap original:
- La matriz temporal raw se guarda como (fecha, pixel, banda), no como (pixel, fecha, banda).
  Esto hace que el llenado por fecha desde los parquets escriba de forma mucho más secuencial.
- El primer recorrido puede tomar los pixeles desde el primer parquet (--pixel-source first-file),
  porque en este dataset el primer parquet ya contiene los 9,901,338 pixeles globales.
- Los .npy finales se escriben en el formato que espera SAITS: (pixel, fecha, banda).

Entradas:
  BASE/parquets_procesados/*.parquet

Salidas:
  BASE/SAITS_X_train.npy
  BASE/SAITS_X_val.npy
  BASE/SAITS_X_val_ori.npy
  BASE/SAITS_X_test.npy
  BASE/SAITS_X_test_ori.npy
  BASE/SAITS_test_mask.npy
  BASE/SAITS_metadata.json
  BASE/tmp/X_raw_date_pixel_float32.dat
"""

from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def gb(nbytes: int | float) -> float:
    return float(nbytes) / 1024**3


def make_pixel_keys(row: np.ndarray, col: np.ndarray) -> np.ndarray:
    r = row.astype(np.int64, copy=False)
    c = col.astype(np.int64, copy=False)
    return (r << np.int64(32)) | (c & np.int64(0xFFFFFFFF))


def list_parquets(parquet_dir: Path) -> list[Path]:
    files = sorted(parquet_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No encontré .parquet en: {parquet_dir}")
    return files


def read_row_group_to_pandas(pf: pq.ParquetFile, rg: int, columns: list[str]) -> pd.DataFrame:
    table = pf.read_row_group(rg, columns=columns)
    return table.to_pandas(split_blocks=True, self_destruct=True)


def collect_fechas_from_file(path: Path) -> tuple[set[int], int, int]:
    pf = pq.ParquetFile(path)
    fechas_file: set[int] = set()
    for rg in range(pf.metadata.num_row_groups):
        df = read_row_group_to_pandas(pf, rg, ["fecha"])
        fechas = np.unique(df["fecha"].to_numpy(dtype=np.int32, copy=False))
        fechas_file.update(int(x) for x in fechas)
        del df, fechas
        gc.collect()
    return fechas_file, int(pf.metadata.num_rows), int(pf.metadata.num_row_groups)


def collect_pixels_from_file(path: Path) -> np.ndarray:
    pf = pq.ParquetFile(path)
    keys_list: list[np.ndarray] = []
    log(f"  Recolectando pixeles desde {path.name} | row_groups={pf.metadata.num_row_groups}")
    for rg in range(pf.metadata.num_row_groups):
        df = read_row_group_to_pandas(pf, rg, ["row", "col"])
        keys = make_pixel_keys(
            df["row"].to_numpy(dtype=np.int32, copy=False),
            df["col"].to_numpy(dtype=np.int32, copy=False),
        )
        keys_list.append(np.unique(keys))
        if rg == 0 or rg == pf.metadata.num_row_groups - 1 or (rg + 1) % 10 == 0:
            log(f"    pixeles row_group {rg+1}/{pf.metadata.num_row_groups}")
        del df, keys
        gc.collect()
    pixel_keys = np.unique(np.concatenate(keys_list)).astype(np.int64, copy=False)
    del keys_list
    gc.collect()
    return np.sort(pixel_keys)


def collect_pixels_all_files(files: list[Path]) -> np.ndarray:
    # Más robusto, pero mucho más lento. Se deja disponible por seguridad.
    pixel_key_set: set[int] = set()
    for i, path in enumerate(files, start=1):
        pf = pq.ParquetFile(path)
        log(f"  Pixeles all-files [{i}/{len(files)}] {path.name}")
        for rg in range(pf.metadata.num_row_groups):
            df = read_row_group_to_pandas(pf, rg, ["row", "col"])
            keys = make_pixel_keys(
                df["row"].to_numpy(dtype=np.int32, copy=False),
                df["col"].to_numpy(dtype=np.int32, copy=False),
            )
            pixel_key_set.update(np.unique(keys).tolist())
            del df, keys
            gc.collect()
        log(f"    pixeles acumulados={len(pixel_key_set):,}")
    return np.array(sorted(pixel_key_set), dtype=np.int64)


def first_pass_fast(files: list[Path], pixel_source: str) -> tuple[np.ndarray, np.ndarray, dict]:
    log("PASO 1/6 — Primer recorrido optimizado: fechas globales y pixeles")
    fechas_set: set[int] = set()
    resumen_archivos: list[dict] = []
    total_rows = 0

    for i, path in enumerate(files, start=1):
        fechas_file, n_rows, n_rgs = collect_fechas_from_file(path)
        total_rows += n_rows
        fechas_set.update(fechas_file)
        resumen_archivos.append({
            "archivo": path.name,
            "filas": int(n_rows),
            "row_groups": int(n_rgs),
            "fechas_en_archivo": int(len(fechas_file)),
        })
        log(f"  [{i}/{len(files)}] {path.name} | filas={n_rows:,} | fechas={len(fechas_file)} | row_groups={n_rgs}")

    fechas = np.array(sorted(fechas_set), dtype=np.int32)
    log(f"  Fechas únicas: {len(fechas):,} | {fechas[0]} → {fechas[-1]}")

    if pixel_source == "first-file":
        pixel_keys = collect_pixels_from_file(files[0])
        log("  Pixel source: first-file")
    else:
        pixel_keys = collect_pixels_all_files(files)
        log("  Pixel source: all-files")

    info = {
        "total_archivos": len(files),
        "total_filas": int(total_rows),
        "pixel_source": pixel_source,
        "archivos": resumen_archivos,
    }
    log(f"  Píxeles únicos: {len(pixel_keys):,}")
    log(f"  Filas totales metadata: {total_rows:,}")
    return fechas, pixel_keys, info


def maybe_sample_pixels(pixel_keys: np.ndarray, max_pixels: int, seed: int) -> np.ndarray:
    if max_pixels <= 0 or max_pixels >= len(pixel_keys):
        return pixel_keys
    log(f"MODO PRUEBA — seleccionando muestra aleatoria de {max_pixels:,} pixeles")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(pixel_keys), size=max_pixels, replace=False)
    return np.sort(pixel_keys[idx])


def create_raw_date_major(raw_path: Path, shape: tuple[int, int, int], init_chunk_dates: int) -> np.memmap:
    log("PASO 2/6 — Creando matriz raw DATE-MAJOR en disco")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    nbytes = int(np.prod(shape) * np.dtype(np.float32).itemsize)
    log(f"  Archivo: {raw_path}")
    log(f"  Shape raw date-major: {shape} = (fechas, pixeles, bandas)")
    log(f"  Tamaño estimado: {gb(nbytes):.2f} GB")
    X = np.memmap(raw_path, dtype="float32", mode="w+", shape=shape)
    log("  Inicializando con NaN por bloques de fechas...")
    n_dates = shape[0]
    for start in range(0, n_dates, init_chunk_dates):
        end = min(start + init_chunk_dates, n_dates)
        X[start:end, :, :] = np.nan
        X.flush()
        log(f"    inicializadas fechas {end:,}/{n_dates:,}")
    return X


def fill_memmap_date_major(files: list[Path], X: np.memmap, fechas: np.ndarray, pixel_keys: np.ndarray, bandas: list[str]) -> None:
    log("PASO 3/6 — Llenando matriz DATE-MAJOR desde parquets")
    n_pixels = len(pixel_keys)
    n_written = 0
    cols = ["fecha", "row", "col"] + bandas

    for i, path in enumerate(files, start=1):
        pf = pq.ParquetFile(path)
        n_rgs = pf.metadata.num_row_groups
        log(f"  [{i}/{len(files)}] {path.name} | row_groups={n_rgs}")

        for rg in range(n_rgs):
            t_rg = time.time()
            df = read_row_group_to_pandas(pf, rg, cols)

            keys = make_pixel_keys(
                df["row"].to_numpy(dtype=np.int32, copy=False),
                df["col"].to_numpy(dtype=np.int32, copy=False),
            )
            pos = np.searchsorted(pixel_keys, keys)
            valid = pos < n_pixels
            matched = np.zeros(len(keys), dtype=bool)
            matched[valid] = pixel_keys[pos[valid]] == keys[valid]

            if matched.any():
                fechas_vals = df["fecha"].to_numpy(dtype=np.int32, copy=False)
                ti_all = np.searchsorted(fechas, fechas_vals)
                unique_t = np.unique(ti_all[matched])

                vals_all = df[bandas].to_numpy(dtype=np.float32, copy=False)

                for t_idx in unique_t:
                    m = matched & (ti_all == t_idx)
                    if not m.any():
                        continue
                    pi = pos[m]
                    vals = vals_all[m, :]
                    good = ~np.isnan(vals).all(axis=1)
                    if not good.any():
                        continue
                    pi = pi[good]
                    vals = vals[good, :]

                    order = np.argsort(pi, kind="mergesort")
                    pi_sorted = pi[order]
                    vals_sorted = vals[order, :]

                    # Date-major: para una fecha dada, los pixeles quedan contiguos o casi contiguos.
                    X[int(t_idx), pi_sorted, :] = vals_sorted
                    n_written += int(vals_sorted.size)

            elapsed = time.time() - t_rg
            log(f"    row_group {rg+1}/{n_rgs} procesado | filas={len(df):,} | matched={int(matched.sum()):,} | {elapsed:.1f}s")

            del df, keys, pos, valid, matched
            gc.collect()

        X.flush()
        log(f"    acumulado valores escritos: {n_written:,}")

    X.flush()
    log(f"  Total valores escritos en bandas: {n_written:,}")


def compute_valid_pixels_date_major(X: np.memmap, threshold_ratio: float, chunk_pixels: int) -> tuple[np.ndarray, np.ndarray, float]:
    log("PASO 4/6 — Filtrando pixeles por mínimo de fechas válidas")
    n_steps, n_pixels, _ = X.shape
    threshold = max(1, int(n_steps * threshold_ratio))
    valid_counts = np.empty(n_pixels, dtype=np.uint16)

    missing_total = 0
    elems_total = 0
    for start in range(0, n_pixels, chunk_pixels):
        end = min(start + chunk_pixels, n_pixels)
        block0 = np.asarray(X[:, start:end, 0])
        valid_counts[start:end] = np.sum(~np.isnan(block0), axis=0).astype(np.uint16)
        block = np.asarray(X[:, start:end, :])
        missing_total += int(np.isnan(block).sum())
        elems_total += int(block.size)
        if start == 0 or end == n_pixels or (start // chunk_pixels) % 20 == 0:
            log(f"    evaluados {end:,}/{n_pixels:,} pixeles")
        del block0, block
        gc.collect()

    good_idx = np.where(valid_counts >= threshold)[0].astype(np.int64)
    missing_rate = missing_total / elems_total if elems_total else np.nan
    log(f"  Umbral válido: >= {threshold} fechas observadas de {n_steps}")
    log(f"  Pixeles conservados: {len(good_idx):,}/{n_pixels:,}")
    log(f"  Missing rate global raw: {missing_rate:.2%}")
    return good_idx, valid_counts, float(missing_rate)


def compute_minmax_date_major(X: np.memmap, good_idx: np.ndarray, bandas: list[str], chunk_pixels: int) -> tuple[np.ndarray, np.ndarray]:
    log("PASO 5/6 — Calculando MinMax por banda")
    n_bands = len(bandas)
    mins = np.full(n_bands, np.inf, dtype=np.float64)
    maxs = np.full(n_bands, -np.inf, dtype=np.float64)

    # good_idx viene ordenado. Esto mejora lecturas desde X[:, ids, :].
    for start in range(0, len(good_idx), chunk_pixels):
        end = min(start + chunk_pixels, len(good_idx))
        ids = good_idx[start:end]
        block = np.asarray(X[:, ids, :])  # (fechas, pixeles, bandas)
        for b in range(n_bands):
            vals = block[:, :, b]
            if np.isfinite(vals).any():
                mins[b] = min(mins[b], float(np.nanmin(vals)))
                maxs[b] = max(maxs[b], float(np.nanmax(vals)))
        if start == 0 or end == len(good_idx) or (start // chunk_pixels) % 20 == 0:
            log(f"    minmax {end:,}/{len(good_idx):,} pixeles")
        del block
        gc.collect()

    for b, banda in enumerate(bandas):
        log(f"  {banda}: min={mins[b]:.6g} | max={maxs[b]:.6g}")
    return mins.astype(np.float32), maxs.astype(np.float32)


def normalize_pixel_major_block(block: np.ndarray, mins: np.ndarray, maxs: np.ndarray) -> np.ndarray:
    # block: (pixeles, fechas, bandas)
    block = block.astype(np.float32, copy=True)
    for b in range(block.shape[2]):
        denom = float(maxs[b] - mins[b])
        if denom <= 0 or not np.isfinite(denom):
            continue
        band = block[:, :, b]
        m = ~np.isnan(band)
        band[m] = (band[m] - mins[b]) / denom
        band[m] = np.clip(band[m], 0.0, 1.0)
    return block


def open_npy_memmap(path: Path, shape: tuple[int, int, int], dtype: str = "float32") -> np.memmap:
    path.parent.mkdir(parents=True, exist_ok=True)
    nbytes = int(np.prod(shape) * np.dtype(dtype).itemsize)
    log(f"  Creando {path.name}: shape={shape}, dtype={dtype}, tamaño={gb(nbytes):.2f} GB")
    return np.lib.format.open_memmap(path, mode="w+", dtype=dtype, shape=shape)


def write_split_date_major(
    split_name: str,
    base_dir: Path,
    X: np.memmap,
    idx: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray,
    chunk_pixels: int,
    write_ori: bool = False,
    write_mask: bool = False,
) -> dict:
    n_steps, _, n_bands = X.shape
    n = len(idx)
    out_path = base_dir / f"SAITS_X_{split_name}.npy"
    out = open_npy_memmap(out_path, (n, n_steps, n_bands), "float32")

    ori = None
    mask = None
    ori_path = None
    mask_path = None
    if write_ori:
        ori_path = base_dir / f"SAITS_X_{split_name}_ori.npy"
        ori = open_npy_memmap(ori_path, (n, n_steps, n_bands), "float32")
    if write_mask:
        mask_path = base_dir / "SAITS_test_mask.npy"
        log(f"  Creando {mask_path.name}: shape={(n, n_steps, n_bands)}, dtype=bool")
        mask = np.lib.format.open_memmap(mask_path, mode="w+", dtype=bool, shape=(n, n_steps, n_bands))

    missing_count = 0
    elem_count = 0
    for start in range(0, n, chunk_pixels):
        end = min(start + chunk_pixels, n)
        src_ids = idx[start:end]
        # X está en (fechas, pixeles, bandas). SAITS necesita (pixeles, fechas, bandas).
        block_date_major = np.asarray(X[:, src_ids, :])
        block_pixel_major = np.transpose(block_date_major, (1, 0, 2))
        block_norm = normalize_pixel_major_block(block_pixel_major, mins, maxs)
        out[start:end, :, :] = block_norm
        if ori is not None:
            ori[start:end, :, :] = block_norm
        if mask is not None:
            mask[start:end, :, :] = np.isnan(block_norm)
        missing_count += int(np.isnan(block_norm).sum())
        elem_count += int(block_norm.size)
        if start == 0 or end == n or (start // chunk_pixels) % 20 == 0:
            log(f"    {split_name}: escritos {end:,}/{n:,} pixeles")
        del block_date_major, block_pixel_major, block_norm
        gc.collect()

    out.flush()
    if ori is not None:
        ori.flush()
    if mask is not None:
        mask.flush()

    return {
        "path": str(out_path),
        "ori_path": str(ori_path) if ori_path else None,
        "mask_path": str(mask_path) if mask_path else None,
        "shape": [int(n), int(n_steps), int(n_bands)],
        "missing_rate": float(missing_count / elem_count) if elem_count else None,
    }


def write_outputs_date_major(
    base_dir: Path,
    X: np.memmap,
    good_idx: np.ndarray,
    fechas: np.ndarray,
    pixel_keys: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray,
    bandas: list[str],
    train_ratio: float,
    val_ratio: float,
    seed: int,
    chunk_pixels: int,
    metadata_extra: dict,
    missing_rate_raw: float,
) -> None:
    log("PASO 6/6 — Creando train/val/test .npy SAITS por bloques")
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(good_idx))
    n = len(good_idx)
    nt = int(n * train_ratio)
    nv = int(n * val_ratio)

    # Membresía aleatoria, pero se ordena cada split para mejorar lectura desde memmap.
    idx_train = np.sort(good_idx[perm[:nt]])
    idx_val = np.sort(good_idx[perm[nt:nt + nv]])
    idx_test = np.sort(good_idx[perm[nt + nv:]])

    log(f"  Train={len(idx_train):,} | Val={len(idx_val):,} | Test={len(idx_test):,}")
    split_info: dict[str, dict] = {}
    split_info["train"] = write_split_date_major("train", base_dir, X, idx_train, mins, maxs, chunk_pixels)
    split_info["val"] = write_split_date_major("val", base_dir, X, idx_val, mins, maxs, chunk_pixels, write_ori=True)
    split_info["test"] = write_split_date_major("test", base_dir, X, idx_test, mins, maxs, chunk_pixels, write_ori=True, write_mask=True)

    np.save(base_dir / "SAITS_good_pixel_indices.npy", good_idx)
    np.save(base_dir / "SAITS_pixel_keys.npy", pixel_keys)
    np.save(base_dir / "SAITS_fechas.npy", fechas)

    meta = {
        "base_dir": str(base_dir),
        "bandas": bandas,
        "layout_raw": "date_pixel_band",
        "n_pixeles_global": int(len(pixel_keys)),
        "n_pixeles_conservados": int(len(good_idx)),
        "n_fechas": int(len(fechas)),
        "n_bandas": int(len(bandas)),
        "fechas": [int(x) for x in fechas.tolist()],
        "shape_raw_date_major": [int(x) for x in X.shape],
        "shape_train": split_info["train"]["shape"],
        "shape_val": split_info["val"]["shape"],
        "shape_test": split_info["test"]["shape"],
        "train_ratio": train_ratio,
        "val_ratio": val_ratio,
        "test_ratio": 1.0 - train_ratio - val_ratio,
        "seed": seed,
        "minmax": {banda: {"min": float(mins[i]), "max": float(maxs[i])} for i, banda in enumerate(bandas)},
        "missing_rate_raw": float(missing_rate_raw),
        "splits": split_info,
        **metadata_extra,
    }
    with open(base_dir / "SAITS_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    log(f"  Metadata guardada en {base_dir / 'SAITS_metadata.json'}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fusionar parquets Sentinel-2 para SAITS usando memmap date-major")
    p.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    p.add_argument("--parquet-dir", default=None)
    p.add_argument("--bands", nargs="+", default=["B02", "B03", "B04", "B08"])
    p.add_argument("--valid-threshold", type=float, default=0.10)
    p.add_argument("--train-ratio", type=float, default=0.70)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--chunk-pixels", type=int, default=50_000)
    p.add_argument("--init-chunk-dates", type=int, default=8)
    p.add_argument("--max-pixels", type=int, default=0)
    p.add_argument("--pixel-source", choices=["first-file", "all-files"], default="first-file")
    p.add_argument("--delete-raw", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    t0 = time.time()
    base_dir = Path(args.base_dir).resolve()
    parquet_dir = Path(args.parquet_dir).resolve() if args.parquet_dir else base_dir / "parquets_procesados"
    tmp_dir = base_dir / "tmp"
    logs_dir = base_dir / "logs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 80)
    log("FUSIONADOR DATE-MAJOR — SENTINEL-2 → SAITS")
    log("=" * 80)
    log(f"Base dir: {base_dir}")
    log(f"Parquet dir: {parquet_dir}")
    log(f"Bandas: {args.bands}")
    log(f"Pixel source: {args.pixel_source}")

    files = list_parquets(parquet_dir)
    fechas, pixel_keys, info = first_pass_fast(files, args.pixel_source)
    pixel_keys = maybe_sample_pixels(pixel_keys, args.max_pixels, args.seed)

    shape = (len(fechas), len(pixel_keys), len(args.bands))
    raw_path = tmp_dir / "X_raw_date_pixel_float32.dat"
    X = create_raw_date_major(raw_path, shape, args.init_chunk_dates)
    fill_memmap_date_major(files, X, fechas, pixel_keys, args.bands)

    good_idx, valid_counts, missing_rate_raw = compute_valid_pixels_date_major(X, args.valid_threshold, args.chunk_pixels)
    np.save(base_dir / "SAITS_valid_counts.npy", valid_counts)

    mins, maxs = compute_minmax_date_major(X, good_idx, args.bands, args.chunk_pixels)
    write_outputs_date_major(
        base_dir=base_dir,
        X=X,
        good_idx=good_idx,
        fechas=fechas,
        pixel_keys=pixel_keys,
        mins=mins,
        maxs=maxs,
        bandas=args.bands,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
        chunk_pixels=args.chunk_pixels,
        metadata_extra=info,
        missing_rate_raw=missing_rate_raw,
    )

    X.flush()
    del X
    gc.collect()

    if args.delete_raw:
        log(f"Eliminando raw memmap: {raw_path}")
        raw_path.unlink(missing_ok=True)

    total_min = (time.time() - t0) / 60
    log("=" * 80)
    log(f"FUSIÓN COMPLETADA en {total_min:.2f} minutos")
    log("Archivos listos para entrenamiento SAITS")
    log("=" * 80)


if __name__ == "__main__":
    main()
