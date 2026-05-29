#!/usr/bin/env python3
import argparse, time
from pathlib import Path
import numpy as np
from PIL import Image

def resize_float(arr, scale):
    img=Image.fromarray(arr.astype(np.float32), mode="F")
    out=img.resize((arr.shape[1]*scale, arr.shape[0]*scale), resample=Image.Resampling.LANCZOS)
    return np.asarray(out, dtype=np.float32)

def resize_nan_band(band, scale):
    valid=np.isfinite(band).astype(np.float32)
    filled=np.nan_to_num(band, nan=0.0).astype(np.float32)
    num=resize_float(filled*valid, scale)
    den=resize_float(valid, scale)
    out=np.full(num.shape, np.nan, dtype=np.float32)
    mask=den > 0.5
    out[mask]=num[mask]/den[mask]
    return np.clip(out,0,1)

ap=argparse.ArgumentParser()
ap.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
ap.add_argument("--date", type=int, required=True)
ap.add_argument("--scale", type=int, default=4)
args=ap.parse_args()

base=Path(args.base_dir)
inp=base/"outputs_piloto_raw_nan_tile"/f"date_{args.date}"/"tile_r00000_c01536_raw_nan.npy"
outdir=base/"outputs_piloto_raw_nan_sr_x4"/f"date_{args.date}"
outdir.mkdir(parents=True, exist_ok=True)
out=outdir/"tile_r00000_c01536_raw_nan_x4.npy"

if out.exists():
    print("ya existe:", out)
    raise SystemExit(0)

x=np.load(inp, mmap_mode="r").astype(np.float32)
c,h,w=x.shape
y=np.empty((c,h*args.scale,w*args.scale), dtype=np.float32)

for b in range(c):
    y[b]=resize_nan_band(x[b], args.scale)

np.save(out,y)
print("OK", args.date, y.shape, y.dtype, "NaN%", np.isnan(y).mean()*100)
