import os
import pandas as pd
import pyarrow.parquet as pq
import time

carpeta = r"D:\salida_sentinel\parquets_procesados"

archivos = sorted([
    f for f in os.listdir(carpeta)
    if f.endswith(".parquet")
])

fechas_globales = set()
pixeles_globales = set()
total_filas = 0

t0 = time.time()

print("=" * 100)
print("DIAGNÓSTICO GLOBAL DE PARQUETS")
print("=" * 100)
print("Archivos encontrados:", len(archivos))
print()

for i, archivo in enumerate(archivos, 1):
    path = os.path.join(carpeta, archivo)

    pf = pq.ParquetFile(path)
    filas = pf.metadata.num_rows
    total_filas += filas

    print(f"[{i}/{len(archivos)}] {archivo}")
    print(f"  Filas metadata: {filas:,}")

    df = pd.read_parquet(path, columns=["fecha", "row", "col"])

    fechas = df["fecha"].unique()
    fechas_globales.update([int(x) for x in fechas])

    pares = zip(df["row"].astype("int32"), df["col"].astype("int32"))
    pixeles_globales.update(pares)

    print(f"  Fechas en archivo: {len(fechas)}")
    print(f"  Píxeles acumulados: {len(pixeles_globales):,}")
    print("-" * 100)

fechas_globales = sorted(fechas_globales)

print()
print("=" * 100)
print("RESUMEN GLOBAL")
print("=" * 100)
print("Total archivos:", len(archivos))
print("Total filas:", f"{total_filas:,}")
print("Total fechas únicas:", len(fechas_globales))
print("Primera fecha:", fechas_globales[0])
print("Última fecha:", fechas_globales[-1])
print("Total píxeles únicos row-col:", f"{len(pixeles_globales):,}")

n_pixeles = len(pixeles_globales)
n_fechas = len(fechas_globales)
n_bandas = 4

gb_matriz = n_pixeles * n_fechas * n_bandas * 4 / 1024**3

print()
print("Matriz densa estimada:")
print(f"  Shape: ({n_pixeles:,}, {n_fechas:,}, {n_bandas})")
print(f"  Tamaño solo X float32: {gb_matriz:.2f} GB")

print()
print("Tiempo total min:", round((time.time() - t0) / 60, 2))