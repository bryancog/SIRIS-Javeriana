#!/usr/bin/env python3
import argparse, json, time
from pathlib import Path
import numpy as np
import pandas as pd

def log(x):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {x}", flush=True)

ap=argparse.ArgumentParser()
ap.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
ap.add_argument("--tile-row0", type=int, default=0)
ap.add_argument("--tile-col0", type=int, default=1536)
ap.add_argument("--tile-size", type=int, default=512)
args=ap.parse_args()

base=Path(args.base_dir)
out_root=base/"outputs_piloto_cloud_scl"
out_root.mkdir(exist_ok=True)

fechas=set(int(x.strip()) for x in open(out_root/"fechas_piloto.txt"))

with open(base/"grid_metadata.json") as f:
    grid=json.load(f)

row_min=int(grid["row_min"])
col_min=int(grid["col_min"])

r0=args.tile_row0 + row_min
c0=args.tile_col0 + col_min
r1=r0 + args.tile_size
c1=c0 + args.tile_size

log(f"Tile abs rows [{r0},{r1}) cols [{c0},{c1})")
log(f"Fechas piloto: {len(fechas)}")

data={}
for fecha in fechas:
    arr=np.full((5,args.tile_size,args.tile_size), np.nan, dtype=np.float32)
    arr[4,:,:]=0
    data[fecha]=arr

cols=["fecha","row","col","B02","B03","B04","B08","SCL"]

parquets=sorted((base/"parquets_procesados").glob("*.parquet"))
log(f"parquets: {len(parquets)}")

for i,p in enumerate(parquets,1):
    log(f"{i}/{len(parquets)} leyendo {p.name}")
    try:
        df=pd.read_parquet(p, engine="fastparquet", columns=cols)
    except Exception as e:
        log(f"ERROR leyendo {p}: {e}")
        raise

    df=df[
        df["fecha"].isin(fechas) &
        (df["row"]>=r0) & (df["row"]<r1) &
        (df["col"]>=c0) & (df["col"]<c1)
    ]

    if df.empty:
        continue

    for fecha,grp in df.groupby("fecha"):
        fecha=int(fecha)
        rr=(grp["row"].to_numpy()-r0).astype(int)
        cc=(grp["col"].to_numpy()-c0).astype(int)

        data[fecha][0,rr,cc]=grp["B04"].to_numpy(dtype=np.float32)
        data[fecha][1,rr,cc]=grp["B03"].to_numpy(dtype=np.float32)
        data[fecha][2,rr,cc]=grp["B02"].to_numpy(dtype=np.float32)
        data[fecha][3,rr,cc]=grp["B08"].to_numpy(dtype=np.float32)
        data[fecha][4,rr,cc]=grp["SCL"].to_numpy(dtype=np.float32)

for fecha,arr in sorted(data.items()):
    od=out_root/f"date_{fecha}"
    od.mkdir(exist_ok=True)
    np.save(od/"tile_r00000_c01536_bands_scl.npy", arr)

summary={
    "tile":"tile_r00000_c01536",
    "n_fechas":len(fechas),
    "shape":"5,512,512",
    "bands":"B04,B03,B02,B08,SCL",
    "cloud_scl_classes":[3,8,9,10]
}
json.dump(summary, open(out_root/"summary_reconstruccion.json","w"), indent=2)
log(summary)
