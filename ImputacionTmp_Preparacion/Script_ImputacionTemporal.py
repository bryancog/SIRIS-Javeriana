"""
=============================================================================
PIPELINE SATELITAL → SAITS
Versión ajustada para leer un archivo .csv.gz pasado como parámetro

Uso:
    python Script_ImputacionTemporal.py "D:\\salida_sentinel\\tablas\\archivo.csv.gz"

Ejemplo:
    python Script_ImputacionTemporal.py "D:\\salida_sentinel\\tablas\\2023_S1_1_pixeles_con_SCL.csv.gz"

Salida:
    D:\\salida_sentinel\\parquets_procesados\\archivo.parquet
=============================================================================
"""

import os
import sys
import gc
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

if len(sys.argv) < 2:
    raise ValueError(
        "\nDebes pasar la ruta del archivo .csv.gz como parámetro.\n\n"
        "Ejemplo:\n"
        'python Script_ImputacionTemporal.py "D:\\salida_sentinel\\tablas\\2023_S1_1_pixeles_con_SCL.csv.gz"\n'
    )

RUTA_ARCHIVO = sys.argv[1]

CARPETA_SALIDA = r"D:\salida_sentinel\parquets_procesados"

BANDAS = ["B02", "B03", "B04", "B08"]

SCL_INVALIDOS = {-9999, 0, 1, 2, 3, 8, 9, 10, 11}

os.makedirs(CARPETA_SALIDA, exist_ok=True)

t0 = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# VALIDACIONES INICIALES
# ─────────────────────────────────────────────────────────────────────────────

if not os.path.exists(RUTA_ARCHIVO):
    raise FileNotFoundError(f"No existe el archivo indicado:\n{RUTA_ARCHIVO}")

if not RUTA_ARCHIVO.lower().endswith(".csv.gz"):
    raise ValueError(
        "Este script está ajustado para leer archivos .csv.gz. "
        f"Archivo recibido: {RUTA_ARCHIVO}"
    )


def leer_csv_gz(**kwargs):
    """
    Lee un archivo .csv.gz sin descomprimirlo manualmente.
    """
    return pd.read_csv(
        RUTA_ARCHIVO,
        compression="gzip",
        **kwargs
    )


# Nombre base para la salida
nombre_archivo = os.path.basename(RUTA_ARCHIVO)

if nombre_archivo.lower().endswith(".csv.gz"):
    nombre_base = nombre_archivo[:-7]
else:
    nombre_base = os.path.splitext(nombre_archivo)[0]

ruta_salida = os.path.join(CARPETA_SALIDA, f"{nombre_base}.parquet")


# Si ya fue procesado, saltar
if os.path.exists(ruta_salida):
    print(f"✓ Ya procesado: {ruta_salida} — saltando.")
    sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1 — INSPECCIÓN
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 70)
print(f"  PROCESANDO: {nombre_archivo}")
print(f"  Tamaño:     {os.path.getsize(RUTA_ARCHIVO) / 1e9:.2f} GB")
print("=" * 70)

muestra = leer_csv_gz(nrows=3)

columnas_requeridas = BANDAS + ["SCL", "fecha", "row", "col"]

for col in columnas_requeridas:
    if col not in muestra.columns:
        raise ValueError(
            f"Columna requerida no encontrada: '{col}'\n"
            f"Columnas encontradas en el CSV:\n{list(muestra.columns)}"
        )

print("✓ Estructura validada")
print(f"✓ Columnas disponibles: {list(muestra.columns)}")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2 — LEER COLUMNAS NECESARIAS
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("  PASO 2 — Leyendo columnas necesarias en memoria")
print("=" * 70)

print("Leyendo archivo...")

df = leer_csv_gz(
    usecols=["fecha", "row", "col", "SCL"] + BANDAS,
    dtype={
        "fecha": "int32",
        "row": "int32",
        "col": "int32",
        "SCL": "Int16",
        "B02": "float32",
        "B03": "float32",
        "B04": "float32",
        "B08": "float32",
    }
)

print(f"✓ Leído: {len(df):,} filas en {(time.time() - t0) / 60:.1f} min")
print(f"✓ RAM usada aproximada: {df.memory_usage(deep=True).sum() / 1e6:.0f} MB")


# ─────────────────────────────────────────────────────────────────────────────
# DISTRIBUCIÓN SCL
# ─────────────────────────────────────────────────────────────────────────────

print("\nDistribución SCL:")

etiquetas = {
    -9999: "Sin dato",
    0: "Sin clasif.",
    1: "Defectuoso",
    2: "Sombra oscura",
    3: "Sombra nube",
    4: "Vegetación",
    5: "Suelo desnudo",
    6: "Agua",
    7: "Nube baja",
    8: "Nube media",
    9: "Nube alta",
    10: "Cirros",
    11: "Nieve",
}

conteos_scl = df["SCL"].value_counts(dropna=False).sort_index()

for k, cnt in conteos_scl.items():
    if pd.isna(k):
        print(f"  SCL  <NA>: {cnt:>10,} ({cnt / len(df) * 100:5.1f}%)  Sin dato ← INVÁLIDO")
    else:
        k_int = int(k)
        flag = " ← INVÁLIDO" if k_int in SCL_INVALIDOS else ""
        print(
            f"  SCL {k_int:>5}: {cnt:>10,} ({cnt / len(df) * 100:5.1f}%)  "
            f"{etiquetas.get(k_int, 'Otro')}{flag}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3 — MARCAR NUBES / INVÁLIDOS Y CONSTRUIR MATRIZ 3D
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("  PASO 3 — Construyendo matriz 3D")
print("=" * 70)

mascara_invalida = df["SCL"].isin(SCL_INVALIDOS) | df["SCL"].isna()

df.loc[mascara_invalida, BANDAS] = np.nan

print(
    f"Píxeles inválidos o con nube → NaN: "
    f"{mascara_invalida.sum():,} ({mascara_invalida.mean():.1%})"
)

fechas_unicas = sorted(df["fecha"].unique())
fecha_a_idx = {f: i for i, f in enumerate(fechas_unicas)}

print("Creando identificador único de píxel...")

df["pixel_id"] = df["row"].astype(str) + "_" + df["col"].astype(str)

pixel_ids, pixeles_unicos = pd.factorize(df["pixel_id"], sort=True)

df["pi"] = pixel_ids.astype(np.int32)
df["ti"] = df["fecha"].map(fecha_a_idx).astype(np.int32)

n_fechas = len(fechas_unicas)
n_pixeles = len(pixeles_unicos)
n_bandas = len(BANDAS)

print(f"Fechas encontradas: {fechas_unicas}")
print(f"Píxeles únicos: {n_pixeles:,}")
print(f"Construyendo matriz ({n_pixeles:,} × {n_fechas} × {n_bandas})...")

X = np.full((n_pixeles, n_fechas, n_bandas), np.nan, dtype=np.float32)

pi_arr = df["pi"].values
ti_arr = df["ti"].values
vals = df[BANDAS].values.astype(np.float32)

for b in range(n_bandas):
    mask = ~np.isnan(vals[:, b])
    X[pi_arr[mask], ti_arr[mask], b] = vals[mask, b]

del pi_arr, ti_arr, vals
gc.collect()

print(f"✓ Matriz construida: {X.shape}")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4 — CONVERTIR MATRIZ A DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("  PASO 4 — Convirtiendo matriz a DataFrame")
print("=" * 70)

rows_arr = np.array(
    [int(p.split("_")[0]) for p in pixeles_unicos],
    dtype=np.int32
)

cols_arr = np.array(
    [int(p.split("_")[1]) for p in pixeles_unicos],
    dtype=np.int32
)

registros = []

for ti, fecha in enumerate(fechas_unicas):
    df_f = pd.DataFrame({
        "fecha": np.int32(fecha),
        "row": rows_arr,
        "col": cols_arr,
    })

    for b, banda in enumerate(BANDAS):
        df_f[banda] = X[:, ti, b]

    mask_valido = ~np.all(np.isnan(X[:, ti, :]), axis=1)

    registros.append(df_f[mask_valido])

df_agg = pd.concat(registros, ignore_index=True)

del X, registros, df
gc.collect()

print(f"✓ Filas con datos válidos: {len(df_agg):,}")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 5 — GUARDAR COMO PARQUET
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("  PASO 5 — Guardando como .parquet")
print("=" * 70)

df_agg.to_parquet(
    ruta_salida,
    index=False,
    compression="snappy"
)

tam_salida_mb = os.path.getsize(ruta_salida) / 1e6
tam_entrada_mb = os.path.getsize(RUTA_ARCHIVO) / 1e6

print(f"✓ Guardado: {ruta_salida}")
print(f"✓ Tamaño salida: {tam_salida_mb:.0f} MB")
print(f"✓ Tamaño archivo original: {tam_entrada_mb:.0f} MB")

t_total = (time.time() - t0) / 60

print("\n" + "=" * 70)
print(f"✓ COMPLETADO: {nombre_base}")
print("=" * 70)

print(f"""
Resumen:
  Archivo procesado:
    {RUTA_ARCHIVO}

  Parquet generado:
    {ruta_salida}

  Fechas en este archivo:
    {fechas_unicas}

  Píxeles únicos:
    {n_pixeles:,}

  Tiempo total:
    {t_total:.1f} minutos

Próximo paso:
  Puedes correr el mismo script con otro .csv.gz, por ejemplo:

  python Script_ImputacionTemporal.py "D:\\salida_sentinel\\tablas\\2023_S1_2_pixeles_con_SCL.csv.gz"
""")