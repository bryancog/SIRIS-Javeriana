# SIRIS tests v0.5 - Prueba de carga moderada

Esta prueba valida el comportamiento del backend ante concurrencia moderada.

No ejecuta exportaciones pesadas. Evalúa endpoints livianos y funcionales:

```txt
GET /
GET /api/session
GET /api/study-area
GET /api/area/geotiff-status
POST /api/register
POST /api/login
```

## Instalar

Copiar el contenido del ZIP en `D:\SIRIS`.

Debe quedar:

```txt
D:\SIRIS\scripts_tests\run_moderate_load_test.py
D:\SIRIS\scripts_tests\run_moderate_load_test.ps1
D:\SIRIS\docs\plan_pruebas_snippets\latex_resultados_v0_5_moderate_load.tex
```

## Requisitos

Tener el backend activo en:

```txt
http://127.0.0.1:3000
```

## Ejecutar local

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_moderate_load_test.ps1 `
  -BaseUrl "http://127.0.0.1:3000" `
  -Users 10 `
  -RequestsPerUser 20
```

## Ejecutar con carga un poco mayor

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_moderate_load_test.ps1 `
  -BaseUrl "http://127.0.0.1:3000" `
  -Users 20 `
  -RequestsPerUser 25
```

## Evidencias

Se generan en:

```txt
D:\SIRIS\tests_evidence\load\
```

Archivos esperados:

```txt
moderate_load_<timestamp>.log
moderate_load_<timestamp>.json
moderate_load_<timestamp>.csv
```

Tomar captura cuando aparezca:

```txt
Resultado: APROBADO.
```

## Criterios de aceptación

```txt
Tasa de éxito >= 95%
Latencia p95 <= 2000 ms
Solicitudes funcionales fallidas = 0
```
