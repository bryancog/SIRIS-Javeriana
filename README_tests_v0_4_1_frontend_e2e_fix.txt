# SIRIS tests v0.4.1 - Fix frontend/E2E Playwright

Corrige el fallo de Playwright strict mode en E2E-07.

Motivo:
Playwright encontró tres textos visibles que coincidían con `/Haz clic en el mapa|Dibujo activo/i`.
La prueba fallaba no por la aplicación, sino porque el selector era ambiguo.

Corrección:
- Se valida `.results-hint` para el texto "Haz clic en el mapa".
- Se valida `.status-card` para el texto "Dibujo activo: 1 punto".
- El script PowerShell ejecuta Playwright desde `D:\SIRIS\frontend` y usa `.\playwright.config.js`.

## Instalar

Copiar estos archivos en `D:\SIRIS`:

```txt
frontend/e2e/siris_frontend_e2e.spec.js
scripts_tests/run_frontend_e2e.ps1
```

## Ejecutar

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_frontend_e2e.ps1 `
  -BaseUrl "http://127.0.0.1:3000" `
  -SkipInstall
```
