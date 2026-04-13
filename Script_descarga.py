import dask.distributed
import dask.utils
import planetary_computer as pc
from pystac_client import Client
import os
from odc.stac import configure_rio, stac_load
import argparse
from datetime import datetime

argParser = argparse.ArgumentParser("Sentinel 2 L2A downloader from Planetary Computer.")
argParser.add_argument("-i", "--id", help="Id of the scene to be downloaded.")
argParser.add_argument("-b", "--band", help="Band of the scene to be downloaded.")
argParser.add_argument("-w", "--workers", default=1, help="Number of workers.")
argParser.add_argument("-r", "--resolution", default=10, help="Spatial resolution for resampling (in meters).")
argParser.add_argument("-o", "--output", default="/tmp", help="Path for download.")
args = argParser.parse_args()

cfg = {
    "sentinel-2-l2a": {
        "assets": {
            "*": {"data_type": "uint16", "nodata": 0},
            "SLC": {"data_type": "uint8", "nodata": 0},
        },
    },
    "*": {"warnings": "ignore"},
}

def clocktime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def to_float(imagery):
    _imagery = imagery.astype("float32")
    nodata = imagery.attrs.get("nodata", None)
    if nodata is None:
        return _imagery
    return _imagery.where(_imagery != nodata)

if _name_ == "_main_":
    with dask.distributed.LocalCluster(n_workers=int(args.workers), dashboard_address=':8100') as cluster:
        with dask.distributed.Client(cluster) as client:
            print(cluster)
            print(client)
            configure_rio(cloud_defaults=True, client=client)
    
            # Abrir catálogo sin modifier deprecado
            catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
            
            sid = args.id 
            ban = [args.band]
    
            print(f"INFO\t{clocktime()}\tBULK\tDOWNLOAD\tSTART")
            
            # Extract the year and month from the scene ID...
            year_month = sid.split("_")[2][:6]
            year = year_month[:4]
            month = year_month[4:]
            
            # Definir los filtros basados en el ID
	   relative_orbit = 68   # El "R068"
	   mgrs_tile = "18NTG"   # El "T18NTG"

	   search = catalog.search(
    		collections=["sentinel-2-l2a"],
    		datetime=f"{year}-{month}",
    		query={
        		"sat:relative_orbit": {"eq": relative_orbit},
        		"s2:mgrs_tile": {"eq": mgrs_tile}
    		}
		)
	    items = list(search.items())
            
            # Check if the scene was found...
            if len(items) != 0:
                print(f"INFO\t{clocktime()}\t{sid}\tSCENE\tFOUND")
                
                # Firmar los items explícitamente
                signed_items = [pc.sign(item) for item in items]
                
                resolution = int(args.resolution)
            
                try:
                    # Usar signed_items sin patch_url
                    imagery = stac_load(
                        signed_items, 
                        bands=ban,
                        chunks={"x": 2048, "y": 2048}, 
                        stac_cfg=cfg,
                        resolution=resolution,
                    )
                    bands = list(imagery.data_vars)
            
                    print(f"INFO\t{clocktime()}\t{sid}\tSCENE\tDOWNLOAD")
                    for band in bands:
                        print(f"INFO\t{clocktime()}\t{sid}\t{band}\tSTART")
                        output_path = os.path.join(args.output, f"{sid}_{band}.tif")
                        to_float(imagery.get(band)).compute().odc.write_cog(output_path, overwrite=False)
                        print(f"INFO\t{clocktime()}\t{sid}\t{band}\tEND")
                    print(f"INFO\t{clocktime()}\t{sid}\tSCENE\tDONE")
                    
                except Exception as e:
                    print(f"INFO\t{clocktime()}\t{sid}\tSCENE\tERROR: {e}")
            else:
                print(f"INFO\t{clocktime()}\t{sid}\tSCENE\tNOT FOUND")
                
        print(f"INFO\t{clocktime()}\tBULK\tDOWNLOAD\tEND")