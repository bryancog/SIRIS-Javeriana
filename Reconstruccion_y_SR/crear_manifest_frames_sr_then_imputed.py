#!/usr/bin/env python3
from pathlib import Path
import numpy as np

base=Path("/zine/HPC02S1/SIRIS/tesis_saits")
fechas=np.load(base/"SAITS_fechas.npy").astype(int)

out=base/"outputs_piloto_sr_then_imputed_vis"
out.mkdir(exist_ok=True)

every=5
selected=list(range(0,len(fechas),every))

with open(out/"manifest_frames.tsv","w") as f:
    for task,ti in enumerate(selected):
        f.write(f"{task}\t{ti}\t{int(fechas[ti])}\n")

print("frames:",len(selected))
print(out/"manifest_frames.tsv")
