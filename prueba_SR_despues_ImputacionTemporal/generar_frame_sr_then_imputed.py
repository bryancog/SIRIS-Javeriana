#!/usr/bin/env python3
from pathlib import Path
import argparse
import numpy as np
from PIL import Image, ImageDraw

def stretch(rgb):
    out=np.zeros_like(rgb,dtype=np.uint8)
    for c in range(3):
        b=rgb[:,:,c].astype(np.float32)
        lo,hi=np.percentile(b,[2,98])
        if hi<=lo:
            out[:,:,c]=0
        else:
            out[:,:,c]=np.clip((b-lo)/(hi-lo)*255,0,255).astype(np.uint8)
    return out

ap=argparse.ArgumentParser()
ap.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
ap.add_argument("--task-id", type=int, required=True)
args=ap.parse_args()

base=Path(args.base_dir)
manifest=base/"outputs_piloto_sr_then_imputed_vis/manifest_frames.tsv"

rows=[]
with open(manifest) as f:
    for line in f:
        task,ti,fecha=line.strip().split("\t")
        rows.append((int(task),int(ti),int(fecha)))

task,ti,fecha=rows[args.task_id]

blocks=sorted((base/"outputs_piloto_sr_then_imputed/blocks").glob("*_imputed.npy"))
canvas=np.zeros((4,2048,2048),dtype=np.float32)

for bp in blocks:
    parts=bp.name.split("_")
    r0=int(parts[2][1:])
    c0=int(parts[3][1:])
    x=np.load(bp,mmap_mode="r")
    canvas[:,r0:r0+256,c0:c0+256]=x[ti]

rgb=np.stack([canvas[0],canvas[1],canvas[2]],axis=-1)
rgb8=stretch(rgb)

img=Image.fromarray(rgb8)
draw=ImageDraw.Draw(img)
draw.rectangle((10,10,260,50),fill=(0,0,0))
draw.text((20,22),str(fecha),fill=(255,255,255))

outdir=base/"outputs_piloto_sr_then_imputed_vis/frames_png"
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/f"frame_{task:04d}_{fecha}.png"
img.save(out,optimize=True)

print("OK",task,fecha,out)
