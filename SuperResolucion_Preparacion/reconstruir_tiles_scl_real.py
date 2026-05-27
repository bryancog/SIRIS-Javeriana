#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd
import json, time

def log(x):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {x}", flush=True)

base=Path("/zine/HPC02S1/SIRIS/tesis_saits")

tiles_txt=base/"outputs_cloud_scl_real/tiles_piloto.txt"
tiles=[x.strip() for x in open(tiles_txt) if x.strip()]

fechas=np.load(base/"SAITS_fechas.npy").astype(int)

with open(base/"grid_metadata.json") as f:
    grid=json.load(f)

row_min=int(grid["row_min"])
col_min=int(grid["col_min"])

tile_size=512

# preparar estructura
tile_info={}

for tile in tiles:
    parts=tile.split("_")
    r0=int(parts[1][1:])
    c0=int(parts[2][1:])

    abs_r0=r0+row_min
    abs_c0=c0+col_min

    tile_info[tile]={
        "r0":r0,
        "c0":c0,
        "abs_r0":abs_r0,
        "abs_c0":abs_c0
    }

cols=["fecha","row","col","B02","B03","B04","B08","SCL"]

parquets=sorted((base/"parquets_procesados").glob("*.parquet"))

log(f"tiles: {len(tiles)}")
log(f"fechas: {len(fechas)}")
log(f"parquets: {len(parquets)}")

for pi,p in enumerate(parquets,1):

    log(f"{pi}/{len(parquets)} leyendo {p.name}")

    df=pd.read_parquet(p, engine="fastparquet", columns=cols)

    for tile,info in tile_info.items():

        r0=info["abs_r0"]
        c0=info["abs_c0"]

        r1=r0+tile_size
        c1=c0+tile_size

        sub=df[
            (df["row"]>=r0) & (df["row"]<r1) &
            (df["col"]>=c0) & (df["col"]<c1)
        ]

        if sub.empty:
            continue

        for fecha,grp in sub.groupby("fecha"):

            fecha=int(fecha)

            outdir=base/"outputs_cloud_scl_real"/tile/f"date_{fecha}"
            outdir.mkdir(parents=True,exist_ok=True)

            outfile=outdir/"bands_scl.npy"

            if outfile.exists():
                arr=np.load(outfile)
            else:
                arr=np.full((5,tile_size,tile_size), np.nan, dtype=np.float32)
                arr[4,:,:]=-9999

            rr=(grp["row"].to_numpy()-r0).astype(int)
            cc=(grp["col"].to_numpy()-c0).astype(int)

            arr[0,rr,cc]=grp["B04"].to_numpy(dtype=np.float32)
            arr[1,rr,cc]=grp["B03"].to_numpy(dtype=np.float32)
            arr[2,rr,cc]=grp["B02"].to_numpy(dtype=np.float32)
            arr[3,rr,cc]=grp["B08"].to_numpy(dtype=np.float32)
            arr[4,rr,cc]=grp["SCL"].to_numpy(dtype=np.float32)

            np.save(outfile,arr)

summary={
    "tiles":tiles,
    "n_tiles":len(tiles),
    "n_fechas":len(fechas),
    "bands":["B04","B03","B02","B08","SCL"]
}

json.dump(summary,open(base/"outputs_cloud_scl_real/summary_reconstruccion.json","w"),indent=2)

log(summary)
log("COMPLETADO")
