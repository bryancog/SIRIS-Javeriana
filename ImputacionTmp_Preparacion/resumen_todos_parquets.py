import os
import pyarrow.parquet as pq

carpeta = r"D:\salida_sentinel\parquets_procesados"

archivos = sorted([
    f for f in os.listdir(carpeta)
    if f.endswith(".parquet")
])

total_filas = 0

print("Archivos encontrados:", len(archivos))
print("=" * 100)

for archivo in archivos:
    path = os.path.join(carpeta, archivo)
    pf = pq.ParquetFile(path)
    filas = pf.metadata.num_rows
    columnas = pf.metadata.num_columns
    row_groups = pf.metadata.num_row_groups
    gb = os.path.getsize(path) / 1024**3

    total_filas += filas

    print(f"{archivo}")
    print(f"  Tamaño GB:   {gb:.3f}")
    print(f"  Filas:       {filas:,}")
    print(f"  Columnas:    {columnas}")
    print(f"  Row groups:  {row_groups}")
    print("-" * 100)

print("TOTAL FILAS:", f"{total_filas:,}")