# SIRIS tests v0.7.1 - Fix SEC-14

Corrige la evaluación de SEC-14.

Motivo:
La versión v0.7 podía marcar como fallido un caso donde la ruta con `../` era normalizada y la SPA respondía con `index.html` HTTP 200. Eso no necesariamente expone archivos sensibles.

Corrección:
- No usa `urljoin`, para evitar normalización previa.
- Usa intentos codificados de path traversal.
- SEC-14 falla solo si se expone contenido sensible o un archivo descargable.
- HTTP 200 con HTML de la SPA se considera seguro si no contiene contenido SQLite ni attachment.

## Instalar

Copiar en `D:\SIRIS`:

```txt
scripts_tests/run_security_extended_test.py
scripts_tests/run_security_extended_test.ps1
```

## Ejecutar

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_security_extended_test.ps1 `
  -BaseUrl "http://127.0.0.1:3000"
```
