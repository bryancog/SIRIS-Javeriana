# SIRIS tests v0.3 - Validación geoespacial local

Esta prueba valida técnicamente los productos generados por SIRIS después de una exportación.

No genera una exportación nueva. Usa la exportación más reciente ubicada en:

```txt
D:\SIRIS\backend\data\area_exports\
```

También permite validar una exportación específica con `-OutName`.

## Archivos

Copiar en la raíz de `D:\SIRIS`:

```txt
scripts_tests/run_geospatial_validation.py
scripts_tests/run_geospatial_validation.ps1
docs/plan_pruebas_snippets/latex_resultados_v0_3_geospatial_validation.tex
```

## Ejecutar usando la exportación más reciente

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_geospatial_validation.ps1
```

## Ejecutar usando una exportación específica

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_geospatial_validation.ps1 `
  -OutName "area_178007220795"
```

## Evidencia

Se genera en:

```txt
D:\SIRIS\tests_evidence\geospatial\
```

Archivos esperados:

```txt
geospatial_validation_<timestamp>.log
geospatial_validation_<timestamp>.json
```

Tomar captura de la terminal cuando aparezca:

```txt
Resultado: APROBADO.
```

Guardar como:

```txt
EV_GEOSPATIAL_VALIDATION_V03_TERMINAL.png
```

## Validaciones

```txt
GEO-00 Directorio general de exportaciones disponible.
GEO-01 Directorio específico de exportación disponible.
GEO-02 polygon.json existente y con vértices válidos.
GEO-03 Video MP4 existente y no vacío.
GEO-04 ZIP GeoTIFF/CSV existente, legible y con archivos esperados.
GEO-05 Directorio geotiff existente.
GEO-06 Existencia de archivos GeoTIFF.
GEO-07 Apertura de GeoTIFF con rasterio y metadatos válidos.
GEO-08 CSV existente, legible y con columnas esperadas.
```
