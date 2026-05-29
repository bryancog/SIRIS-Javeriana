# SIRIS tests v0.8 - Cancelación y recuperación

Esta prueba valida el flujo asíncrono:

```txt
Iniciar exportación larga
Cancelar exportación activa
Confirmar estado cancelled
Confirmar limpieza del producto cancelado
Iniciar nueva exportación
Esperar stage done
Validar video y ZIP
```

## Instalar

Copiar el contenido del ZIP en `D:\SIRIS`.

Debe quedar:

```txt
D:\SIRIS\scripts_tests\run_cancel_recovery_test.py
D:\SIRIS\scripts_tests\run_cancel_recovery_test.ps1
D:\SIRIS\docs\plan_pruebas_snippets\latex_resultados_v0_8_cancel_recovery.tex
```

## Ejecutar

Con el backend activo en `http://127.0.0.1:3000`:

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_cancel_recovery_test.ps1 `
  -BaseUrl "http://127.0.0.1:3000"
```

## Parámetros por defecto

La exportación que se cancela usa rango largo:

```txt
2016-01-01 a 2026-05-01
```

La exportación de recuperación usa rango corto:

```txt
2016-01-01 a 2016-02-01
```

## Evidencias

Se generan en:

```txt
D:\SIRIS\tests_evidence\cancel_recovery\
```

Archivos esperados:

```txt
cancel_recovery_<timestamp>.log
cancel_recovery_<timestamp>.json
```

Tomar captura cuando aparezca:

```txt
Resultado: APROBADO.
```
