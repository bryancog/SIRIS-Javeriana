# SIRIS tests v0.2 - Cloudflare + exportación asíncrona

Esta prueba valida el despliegue público mediante Cloudflare Tunnel y el flujo de exportación asíncrona.

## Requisitos

1. Backend activo en `http://127.0.0.1:3000`.
2. Frontend compilado con `npm.cmd run build`.
3. Cloudflare Tunnel activo:
   ```powershell
   cloudflared tunnel --url http://localhost:3000
   ```
4. URL pública `https://....trycloudflare.com`.

## Instalar

Copiar estos archivos en la raíz de `D:\SIRIS`:

```txt
scripts_tests/run_cloudflare_async_smoke.py
scripts_tests/run_cloudflare_async_smoke.ps1
docs/plan_pruebas_snippets/latex_resultados_v0_2_cloudflare_async.tex
```

## Ejecutar

Reemplazar la URL por la que entregue Cloudflare:

```powershell
cd D:\SIRIS

powershell -ExecutionPolicy Bypass -File .\scripts_tests\run_cloudflare_async_smoke.ps1 `
  -BaseUrl "https://TU-URL.trycloudflare.com" `
  -DateFrom "2016-01-01" `
  -DateTo "2016-02-01" `
  -TimeoutSeconds 1800
```

Si el rango corto no contiene datos suficientes, ampliar la fecha final:

```powershell
-DateTo "2016-06-01"
```

## Evidencia

Se genera en:

```txt
D:\SIRIS\tests_evidence\cloudflare\
```

Archivos esperados:

```txt
cloudflare_async_smoke_<timestamp>.log
cloudflare_async_smoke_<timestamp>.json
```

Tomar captura de la terminal cuando aparezca `Resultado: APROBADO.`
