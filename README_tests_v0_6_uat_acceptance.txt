# SIRIS tests v0.6 - UAT / Aceptación de usuario

Esta prueba es manual. Valida que un usuario final pueda completar el flujo principal del sistema.

## Instalar

Copiar el contenido del ZIP en `D:\SIRIS`.

Debe quedar:

```txt
D:\SIRIS\docs\uat\UAT_SIRIS_v0_6_checklist.md
D:\SIRIS\docs\uat\UAT_SIRIS_v0_6_checklist.txt
D:\SIRIS\scripts_tests\prepare_uat_evidence.ps1
D:\SIRIS\docs\plan_pruebas_snippets\latex_resultados_v0_6_uat.tex
```

## Crear carpeta de evidencias y checklist de ejecución

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\prepare_uat_evidence.ps1
```

## Ejecutar manualmente

Abrir la aplicación en modo local o Cloudflare y realizar:

```txt
UAT-01 Acceso a la aplicación
UAT-02 Registro de usuario
UAT-03 Inicio de sesión
UAT-04 Visualización de dashboard
UAT-05 Selección de fechas
UAT-06 Dibujo de polígono
UAT-07 Inicio de exportación asíncrona
UAT-08 Seguimiento del estado
UAT-09 Visualización de video
UAT-10 Descarga de ZIP
UAT-11 Validación de usabilidad
UAT-12 Cierre de sesión
```

## Evidencias

Guardar en:

```txt
D:\SIRIS\tests_evidence\uat\
```

Capturas sugeridas:

```txt
EV_UAT_01_LOGIN.png
EV_UAT_02_REGISTRO.png
EV_UAT_03_DASHBOARD.png
EV_UAT_04_FECHAS_POLIGONO.png
EV_UAT_05_EXPORTACION_EN_PROCESO.png
EV_UAT_06_EXPORTACION_FINALIZADA.png
EV_UAT_07_VIDEO_RESULTADO.png
EV_UAT_08_ZIP_DESCARGADO.png
EV_UAT_09_LOGOUT.png
```

## Resultado esperado

El resultado global puede ser:

```txt
Aprobado
Aprobado con observaciones
Fallido
```
