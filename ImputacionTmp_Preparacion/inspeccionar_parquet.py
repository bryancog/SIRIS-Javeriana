import os
import pandas as pd
import pyarrow.parquet as pq

# Cambia este nombre por el parquet que quieras revisar
archivo = r"D:\salida_sentinel\parquets_procesados\2018_S1_1_pixeles_con_SCL.parquet"

print("=" * 80)
print("ARCHIVO")
print("=" * 80)
print(archivo)
print("Tamaño en disco GB:", round(os.path.getsize(archivo) / 1024**3, 3))

pf = pq.ParquetFile(archivo)

print("\n" + "=" * 80)
print("METADATA")
print("=" * 80)
print("Filas:", f"{pf.metadata.num_rows:,}")
print("Columnas:", pf.metadata.num_columns)
print("Row groups:", pf.metadata.num_row_groups)

print("\n" + "=" * 80)
print("SCHEMA")
print("=" * 80)
print(pf.schema)

print("\n" + "=" * 80)
print("COLUMNAS")
print("=" * 80)
print(pf.schema.names)

print("\n" + "=" * 80)
print("PRIMERAS 10 FILAS")
print("=" * 80)
df_head = pf.read_row_group(0).slice(0, 10).to_pandas()
print(df_head)

print("\nDtypes:")
print(df_head.dtypes)

print("\n" + "=" * 80)
print("RESUMEN COLUMNAS PRINCIPALES")
print("=" * 80)

cols = ["fecha", "row", "col", "B02", "B03", "B04", "B08", "SCL"]
cols_existentes = [c for c in cols if c in pf.schema.names]

df = pd.read_parquet(archivo, columns=cols_existentes)

print("Filas leídas:", f"{len(df):,}")
print("Columnas leídas:", list(df.columns))

if "fecha" in df.columns:
    fechas = sorted(df["fecha"].unique())
    print("\nFechas únicas:", df["fecha"].nunique())
    print("Primeras fechas:", fechas[:20])
    print("Últimas fechas:", fechas[-20:])

if "row" in df.columns and "col" in df.columns:
    print("\nPíxeles únicos row-col:", f"{df.groupby(['row', 'col']).ngroups:,}")

print("\nFaltantes por columna:")
print(df.isna().mean().sort_values(ascending=False))

bandas = [c for c in ["B02", "B03", "B04", "B08", "SCL"] if c in df.columns]
if bandas:
    print("\nDescripción de bandas:")
    print(df[bandas].describe())