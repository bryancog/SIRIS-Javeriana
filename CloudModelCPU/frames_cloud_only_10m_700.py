#!/usr/bin/env python3
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import json

def normalize_rgb(x):
    # x viene en escala Sentinel aprox 0-20000
    rgb=np.stack([x[0],x[1],x[2]],axis=-1).astype(np.float32)
    rgb=np.nan_to_num(rgb,nan=0.0)
    rgb=np.clip(rgb/10000.0,0,1)
    return (rgb*255).astype(np.uint8)

base=Path("/zine/HPC02S1/SIRIS/tesis_saits")
inp=base/"outputs_cloud_scl_real/tile_r00000_c01536_cloud_only_10m_700"
out=base/"outputs_cloud_scl_real/tile_r00000_c01536_cloud_only_10m_700_vis"
frames=out/"frames_png"
frames.mkdir(parents=True,exist_ok=True)

files=sorted(inp.glob("date_*/tile_r00000_c01536_cloud_only_10m.npy"))

# Para video liviano: una de cada 5 fechas
selected=files[::5]

for i,p in enumerate(selected):
    fecha=p.parent.name.replace("date_","")
    x=np.load(p,mmap_mode="r")
    rgb8=normalize_rgb(x)

    img=Image.fromarray(rgb8)
    img=img.resize((1024,1024),Image.Resampling.NEAREST)

    draw=ImageDraw.Draw(img)
    draw.rectangle((10,10,320,55),fill=(0,0,0))
    draw.text((25,25),fecha,fill=(255,255,255))

    outp=frames/f"frame_{i:04d}_{fecha}.png"
    img.save(outp,optimize=True)

    if i==0 or (i+1)%20==0 or i==len(selected)-1:
        print(f"{i+1}/{len(selected)} {outp}",flush=True)

json.dump(
    {"frames":len(selected),"source_files":len(files),"every":5,"sr_applied":False},
    open(out/"summary_frames.json","w"),
    indent=2
)
