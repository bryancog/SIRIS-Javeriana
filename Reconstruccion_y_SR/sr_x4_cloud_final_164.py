#!/usr/bin/env python3
from pathlib import Path
import numpy as np
from PIL import Image
import time, json

def log(x):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {x}", flush=True)

def normalize(x):
    x=x.astype(np.float32)
    if np.nanmax(x)>2:
        x=x/10000.0
    x=np.nan_to_num(x,nan=0.0)
    return np.clip(x,0,1)

def resize_band(b,scale=4):
    b=normalize(b)
    img=Image.fromarray(b,mode="F")
    out=img.resize((b.shape[1]*scale,b.shape[0]*scale),resample=Image.Resampling.LANCZOS)
    return np.clip(np.asarray(out,dtype=np.float32),0,1)

base=Path("/zine/HPC02S1/SIRIS/tesis_saits")
inp=base/"outputs_cloud_scl_real/final_164_cloud_imputed"
out=base/"outputs_cloud_scl_real/final_164_cloud_imputed_sr_x4"
out.mkdir(exist_ok=True)

files=sorted(inp.glob("date_*/tile_r00000_c01536_cloud_imputed.npy"))
log(f"fechas: {len(files)}")

for i,p in enumerate(files,1):
    fecha=p.parent.name.replace("date_","")
    od=out/f"date_{fecha}"
    od.mkdir(exist_ok=True)
    of=od/"tile_r00000_c01536_cloud_imputed_x4.npy"

    if of.exists():
        continue

    x=np.load(p,mmap_mode="r")
    y=np.empty((4,2048,2048),dtype=np.float32)

    for b in range(4):
        y[b]=resize_band(x[b],4)

    np.save(of,y)

    if i==1 or i%20==0 or i==len(files):
        log(f"{i}/{len(files)} {fecha}")

json.dump(
    {"n_fechas":len(files),"shape":"4,2048,2048","range":"0-1"},
    open(out/"summary.json","w"),
    indent=2
)

log("COMPLETADO")
