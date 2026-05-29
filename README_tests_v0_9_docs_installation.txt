# SIRIS tests v0.9 - Documentación / instalación

Esta prueba verifica la consistencia final del repositorio, documentación y ambiente.

## Instalar

Copiar el contenido del ZIP en `D:\SIRIS`.

Debe quedar:

```txt
D:\SIRIS\scripts_tests\run_docs_installation_check.py
D:\SIRIS\scripts_tests\run_docs_installation_check.ps1
D:\SIRIS\docs\installation_check\CHECKLIST_CIERRE_DOCUMENTAL_v0_9.md
D:\SIRIS\docs\plan_pruebas_snippets\latex_resultados_v0_9_docs_installation.tex
```

## Ejecutar

Con el backend activo en `http://127.0.0.1:3000`:

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_docs_installation_check.ps1 `
  -BaseUrl "http://127.0.0.1:3000"
```

## Si el backend no está activo

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_docs_installation_check.ps1 `
  -SkipLiveCheck
```

## Evidencias

Se generan en:

```txt
D:\SIRIS\tests_evidence\documentation\
```

Archivos esperados:

```txt
documentation_installation_check_<timestamp>.log
documentation_installation_check_<timestamp>.json
```

Tomar captura cuando aparezca:

```txt
Resultado: APROBADO.
```

## Validaciones

```txt
DOC-01 Estructura principal del proyecto existe.
DOC-02 README actualizado.
DOC-03 .gitignore actualizado.
DOC-04 Scripts de pruebas disponibles.
DOC-05 Carpetas de evidencias existen.
DOC-06 Snippets/documentos auxiliares disponibles.
DOC-07 package.json consistente.
DOC-08 requirements.txt consistente.
DOC-09 frontend/dist generado.
DOC-10 Python venv y npm disponibles.
DOC-11 Scripts Python compilan.
DOC-12 Backend/endpoints base responden.
DOC-13 Checklist UAT disponible.
DOC-14 Flujo asíncrono presente en código.
```
