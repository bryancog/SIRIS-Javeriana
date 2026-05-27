#!/usr/bin/env python3
from pathlib import Path
import numpy as np
from PIL import Image
import time, json

def log(x):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {x}", flush=True)

def normalize_reflectance(x):
    x=x.astype(np.float32)
    if np.nanmax(x) > 2.0:
        x=x/10000.0
    return np.clip(x,0,1)

def resize_band(b, scale=4):
    b=np.nan_to_num(normalize_reflectance(b), nan=0.0)
    img=Image.fromarray(b.astype(np.float32), mode="F")
    out=img.resize((b.shape[1]*scale,b.shape[0]*scale), resample=Image.Resampling.LANCZOS)
    return np.clip(np.asarray(out,dtype=np.float32),0,1)

base=Path("/zine/HPC02S1/SIRIS/tesis_saits")
inp=base/"outputs_piloto_cloud_scl/cloud_only_imputed"
out=base/"outputs_piloto_cloud_scl/cloud_only_imputed_sr_x4"

if out.exists():
    import shutil
    shutil.rmtree(out)

out.mkdir(exist_ok=True)

files=sorted(inp.glob("date_*/tile_r00000_c01536_cloud_only_imputed.npy"))

log(f"fechas útiles: {len(files)}")

for i,p in enumerate(files,1):
    fecha=p.parent.name.replace("date_","")
    od=out/f"date_{fecha}"
    od.mkdir(exist_ok=True)

    of=od/"tile_r00000_c01536_cloud_only_imputed_x4.npy"

    x=np.load(p,mmap_mode="r")
    y=np.empty((4,2048,2048),dtype=np.float32)

    for b in range(4):
        y[b]=resize_band(x[b],4)

    np.save(of,y)

    log(f"{i}/{len(files)} {fecha} min={np.nanmin(y):.4f} max={np.nanmax(y):.4f}")

summary={
    "n_fechas":len(files),
    "scale":4,
    "output_shape":"4,2048,2048",
    "output_range":"0-1 float32",
    "normalization":"if max>2 divide by 10000"
}
json.dump(summary,open(out/"summary_sr_x4.json","w"),indent=2)

log("COMPLETADO")
