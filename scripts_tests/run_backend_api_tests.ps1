param(
  [string]$ProjectRoot = "D:\SIRIS"
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backendRoot = Join-Path $ProjectRoot "backend"
$evidenceDir = Join-Path $ProjectRoot "tests_evidence\backend_api"
$logPath = Join-Path $evidenceDir "backend_api_tests_$timestamp.log"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

Write-Host "==============================================="
Write-Host "SIRIS - Pruebas Backend/API v0.1"
Write-Host "Proyecto: $ProjectRoot"
Write-Host "Backend:  $backendRoot"
Write-Host "Log:      $logPath"
Write-Host "==============================================="

Set-Location $backendRoot

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
  throw "No se encontró .\venv\Scripts\python.exe. Crea el entorno virtual antes de ejecutar pruebas."
}

$env:SIRIS_NPY_ROOTS = "D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos;D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_sr_x4_lanczos_faltantes_web"
$env:SIRIS_MASK_ROOT = "D:\SIRIS_DATA\tesis_saits_v2_scl_mask\outputs_imputation_masks"
$env:SIRIS_GEOTIFF_WORKERS = "2"
$env:PYTHONPATH = $backendRoot

Write-Host "Instalando dependencias de prueba si hacen falta..."
.\venv\Scripts\python.exe -m pip install pytest httpx | Tee-Object -FilePath $logPath

Write-Host ""
Write-Host "Ejecutando pytest..."
.\venv\Scripts\python.exe -m pytest -v 2>&1 | Tee-Object -FilePath $logPath -Append

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Resultado: FALLIDO. Revisa el log: $logPath"
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Resultado: APROBADO."
Write-Host "Evidencia guardada en: $logPath"
