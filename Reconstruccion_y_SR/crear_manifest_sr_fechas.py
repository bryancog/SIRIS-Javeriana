#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import numpy as np

BASE = Path("/zine/HPC02S1/SIRIS/tesis_saits")
OUTDIR = BASE / "outputs_sr_input"
OUTDIR.mkdir(exist_ok=True)

fechas = np.load(BASE / "SAITS_fechas.npy").astype(int)

manifest = OUTDIR / "manifest_fechas.tsv"

with open(manifest, "w") as f:
    for i, fecha in enumerate(fechas):
        f.write(f"{i}\t{int(fecha)}\n")

print(f"Manifest creado: {manifest}")
print(f"Total fechas: {len(fechas)}")
print(f"Para lanzar todo: sbatch --array=0-{len(fechas)-1}%8 job_reconstruir_sr_tiles.sh")
print("Primeras fechas:", fechas[:10])
print("Últimas fechas:", fechas[-10:])
