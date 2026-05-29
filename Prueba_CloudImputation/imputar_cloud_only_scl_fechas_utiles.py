#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import json, time

def log(x):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {x}", flush=True)

def interp_1d(y):
    y=np.asarray(y,dtype=np.float32)
    ok=np.isfinite(y)
    idx=np.arange(len(y),dtype=np.float32)
    if ok.all():
        return y
    if ok.sum()>=2:
        return np.interp(idx,idx[ok],y[ok]).astype(np.float32)
    if ok.sum()==1:
        return np.full_like(y,y[ok][0],dtype=np.float32)
    return np.zeros_like(y,dtype=np.float32)

base=Path("/zine/HPC02S1/SIRIS/tesis_saits")
root=base/"outputs_piloto_cloud_scl"
out=root/"cloud_only_imputed"
out.mkdir(exist_ok=True)

fechas=[int(x.strip()) for x in open(root/"fechas_utiles_cloud_lt70.txt") if x.strip()]
files=[root/f"date_{f}"/"tile_r00000_c01536_bands_scl.npy" for f in fechas]

log(f"fechas útiles: {len(files)}")
log(fechas)

stack=np.stack([np.load(p) for p in files],axis=0).astype(np.float32)
bands=stack[:,:4,:,:].copy()
scl=stack[:,4,:,:]

cloud_mask=np.isin(scl,[3,8,9,10])

working=bands.copy()
for t in range(working.shape[0]):
    m=cloud_mask[t]
    for b in range(working.shape[1]):
        working[t,b,m]=np.nan

T,B,H,W=working.shape
arr=np.transpose(working,(2,3,1,0)).reshape(H*W*B,T)

log(f"series: {arr.shape[0]}")

for i in range(arr.shape[0]):
    if np.isnan(arr[i]).any():
        arr[i]=interp_1d(arr[i])
    if i>0 and i%200000==0:
        log(f"series {i}/{arr.shape[0]}")

imp=np.transpose(arr.reshape(H,W,B,T),(3,2,0,1)).astype(np.float32)

final=bands.copy()
for t in range(T):
    m=cloud_mask[t]
    for b in range(B):
        final[t,b,m]=imp[t,b,m]

for t,fecha in enumerate(fechas):
    od=out/f"date_{fecha}"
    od.mkdir(exist_ok=True)
    np.save(od/"tile_r00000_c01536_cloud_only_imputed.npy", final[t])
    np.save(od/"tile_r00000_c01536_cloud_mask.npy", cloud_mask[t].astype(np.uint8))

summary={
    "n_fechas":len(fechas),
    "fechas":fechas,
    "cloud_threshold":"<70%",
    "method":"cloud-only temporal interpolation using SCL 3,8,9,10",
    "nan_after":float(np.isnan(final).mean()),
    "cloud_fraction":float(cloud_mask.mean()),
    "note":"Only cloud pixels replaced; non-cloud original pixels preserved."
}
json.dump(summary,open(out/"summary_cloud_only_imputation.json","w"),indent=2)

log(summary)
log("COMPLETADO")
