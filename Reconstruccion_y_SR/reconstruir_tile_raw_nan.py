#!/usr/bin/env python3
import json, argparse, time
from pathlib import Path
import numpy as np

def log(x):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {x}", flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-dir", default="/zine/HPC02S1/SIRIS/tesis_saits")
    ap.add_argument("--tile-row0", type=int, default=0)
    ap.add_argument("--tile-col0", type=int, default=1536)
    ap.add_argument("--tile-size", type=int, default=512)
    ap.add_argument("--out-root", default="outputs_piloto_raw_nan_tile")
    args=ap.parse_args()

    base=Path(args.base_dir)
    fechas=np.load(base/"SAITS_fechas.npy").astype(int)

    with open(base/"grid_metadata.json") as f:
        grid=json.load(f)

    row_min=int(grid["row_min"])
    col_min=int(grid["col_min"])

    r0_abs=args.tile_row0 + row_min
    c0_abs=args.tile_col0 + col_min
    r1_abs=r0_abs + args.tile_size
    c1_abs=c0_abs + args.tile_size

    out_root=base/args.out_root
    out_root.mkdir(exist_ok=True)

    split_files={
        "train": base/"SAITS_X_train.npy",
        "val": base/"SAITS_X_val.npy",
        "test": base/"SAITS_X_test.npy",
    }

    split_arrays={k:np.load(v, mmap_mode="r") for k,v in split_files.items()}

    tile=np.full((len(fechas), args.tile_size, args.tile_size, 4), np.nan, dtype=np.float32)

    metas=sorted((base/"outputs_interp_tmajor").glob("meta_*.npz"))
    log(f"metas: {len(metas)}")
    log(f"tile abs rows [{r0_abs},{r1_abs}) cols [{c0_abs},{c1_abs})")

    total_pix=0

    for mi,mf in enumerate(metas,1):
        m=np.load(mf)
        split=str(m["split"])
        start=int(m["start"])
        rows=m["rows"].astype(np.int64)
        cols=m["cols"].astype(np.int64)

        mask=(rows>=r0_abs)&(rows<r1_abs)&(cols>=c0_abs)&(cols<c1_abs)
        if not mask.any():
            continue

        local_idx=np.where(mask)[0]
        rr=(rows[mask]-r0_abs).astype(np.int64)
        cc=(cols[mask]-c0_abs).astype(np.int64)

        X=split_arrays[split]
        vals=np.asarray(X[start+local_idx,:,:], dtype=np.float32)  # pix,time,band
        vals=np.transpose(vals, (1,0,2))                            # time,pix,band

        tile[:,rr,cc,:]=vals
        total_pix += len(local_idx)

        log(f"{mf.name}: split={split}, pix={len(local_idx)}, acumulado={total_pix}")

    # Pasar a orden C,H,W por fecha y orden RGBN: B04,B03,B02,B08
    for ti,fecha in enumerate(fechas):
        out_dir=out_root/f"date_{fecha}"
        out_dir.mkdir(exist_ok=True)
        arr=tile[ti,:,:,:][:,:,[2,1,0,3]]          # H,W,4 RGBN
        arr=np.transpose(arr,(2,0,1)).astype(np.float32)
        np.save(out_dir/"tile_r00000_c01536_raw_nan.npy", arr)

    summary={
        "tile":"tile_r00000_c01536",
        "dates":int(len(fechas)),
        "pixels_found":int(total_pix),
        "shape_saved":"4x512x512 por fecha",
        "nan_fraction":float(np.isnan(tile).mean()),
        "band_order":"B04,B03,B02,B08",
    }

    with open(out_root/"summary_raw_nan.json","w") as f:
        json.dump(summary,f,indent=2)

    log(summary)

if __name__=="__main__":
    main()
