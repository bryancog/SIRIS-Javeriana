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
ap.add_argument("--every", type=int, default=5)
ap.add_argument("--max-size", type=int, default=1024)
ap.add_argument("--duration", type=int, default=180)
args=ap.parse_args()

base=Path(args.base_dir)
fechas=np.load(base/"SAITS_fechas.npy").astype(int)
blocks=sorted((base/"outputs_piloto_sr_then_imputed/blocks").glob("*_imputed.npy"))

out=base/"outputs_piloto_sr_then_imputed_vis"
frames_dir=out/"frames_png"
frames_dir.mkdir(parents=True, exist_ok=True)

frames=[]

selected=list(range(0,len(fechas),args.every))

for k,ti in enumerate(selected,1):
    fecha=fechas[ti]
    canvas=np.zeros((4,2048,2048),dtype=np.float32)

    for bp in blocks:
        name=bp.name
        parts=name.split("_")
        r0=int(parts[2][1:])
        c0=int(parts[3][1:])
        x=np.load(bp,mmap_mode="r")
        canvas[:,r0:r0+256,c0:c0+256]=x[ti]

    rgb=np.stack([canvas[0],canvas[1],canvas[2]],axis=-1)
    rgb8=stretch(rgb)

    img=Image.fromarray(rgb8)
    if args.max_size:
        img.thumbnail((args.max_size,args.max_size),Image.Resampling.LANCZOS)

    draw=ImageDraw.Draw(img)
    draw.rectangle((10,10,230,45),fill=(0,0,0))
    draw.text((18,18),str(fecha),fill=(255,255,255))

    png=frames_dir/f"{fecha}.png"
    img.save(png,optimize=True)
    frames.append(img.copy())

    print(f"{k}/{len(selected)} {fecha}",flush=True)

gif=out/"animacion_sr_then_imputed_tile_r00000_c01536.gif"
frames[0].save(gif,save_all=True,append_images=frames[1:],duration=args.duration,loop=0,optimize=True)

print("GIF:",gif)
print("frames:",len(frames))
