#!/usr/bin/env python3
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import json

base=Path("/zine/HPC02S1/SIRIS/tesis_saits")
inp=base/"outputs_piloto_cloud_scl/cloud_only_imputed_sr_x4"
out=base/"outputs_piloto_cloud_scl/cloud_only_vis"
frames=out/"frames_png"
frames.mkdir(parents=True,exist_ok=True)

files=sorted(inp.glob("date_*/tile_r00000_c01536_cloud_only_imputed_x4.npy"))

for i,p in enumerate(files):
    fecha=p.parent.name.replace("date_","")
    x=np.load(p,mmap_mode="r")

    rgb=np.stack([x[0],x[1],x[2]],axis=-1)
    rgb8=np.clip(rgb*255,0,255).astype(np.uint8)

    img=Image.fromarray(rgb8)
    draw=ImageDraw.Draw(img)
    draw.rectangle((10,10,300,55),fill=(0,0,0))
    draw.text((25,25),fecha,fill=(255,255,255))

    outp=frames/f"frame_{i:04d}_{fecha}.png"
    img.save(outp,optimize=True)
    print("OK",outp,flush=True)

json.dump({"frames":len(files)},open(out/"summary_frames.json","w"),indent=2)
