#!/usr/bin/env python3
import argparse, time, json
from pathlib import Path
import numpy as np
from PIL import Image

def log(x):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {x}", flush=True)

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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    ap.add_argument("--input-root", default="outputs_piloto_raw_nan_tile")
    ap.add_argument("--output-root", default="outputs_piloto_raw_nan_sr_x4")
    ap.add_argument("--scale", type=int, default=4)
    args=ap.parse_args()

    base=Path(args.base_dir)
    in_files=sorted((base/args.input_root).glob("date_*/tile_r00000_c01536_raw_nan.npy"))
    out_root=base/args.output_root
    out_root.mkdir(exist_ok=True)

    log(f"archivos entrada: {len(in_files)}")

    for i,p in enumerate(in_files,1):
        fecha=p.parent.name.replace("date_","")
        out_dir=out_root/f"date_{fecha}"
        out_dir.mkdir(exist_ok=True)

        out_file=out_dir/"tile_r00000_c01536_raw_nan_x4.npy"
        if out_file.exists():
            continue

        x=np.load(p, mmap_mode="r").astype(np.float32)
        c,h,w=x.shape
        y=np.empty((c,h*args.scale,w*args.scale), dtype=np.float32)

        for b in range(c):
            y[b]=resize_nan_band(x[b], args.scale)

        np.save(out_file, y)

        if i==1 or i%25==0 or i==len(in_files):
            log(f"{i}/{len(in_files)} fecha {fecha} NaN% salida={np.isnan(y).mean()*100:.2f}")

    summary={"n_files":len(in_files),"scale":args.scale,"output":"float32 con NaN preservados"}
    with open(out_root/"summary_raw_nan_sr_x4.json","w") as f:
        json.dump(summary,f,indent=2)

    log("COMPLETADO")

if __name__=="__main__":
    main()
