param(
  [Parameter(Mandatory=$true)]
  [string]$BaseUrl,

  [string]$ProjectRoot = "D:\SIRIS",
  [string]$DateFrom = "2016-01-01",
  [string]$DateTo = "2016-02-01",
  [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$scriptDir = Join-Path $ProjectRoot "scripts_tests"
$scriptPath = Join-Path $scriptDir "run_cloudflare_async_smoke.py"
$evidenceDir = Join-Path $ProjectRoot "tests_evidence\cloudflare"
$logPath = Join-Path $evidenceDir "cloudflare_async_smoke_$timestamp.log"
$pythonExe = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

if (-not (Test-Path $pythonExe)) {
  throw "No se encontró Python del entorno virtual: $pythonExe"
}

if (-not (Test-Path $scriptPath)) {
  throw "No se encontró el script de prueba: $scriptPath"
}

Write-Host "==============================================="
Write-Host "SIRIS - Smoke Cloudflare + exportación asíncrona"
Write-Host "Base URL: $BaseUrl"
Write-Host "Fechas:   $DateFrom a $DateTo"
Write-Host "Log:      $logPath"
Write-Host "==============================================="

Set-Location $ProjectRoot

& $pythonExe -m pip install requests | Tee-Object -FilePath $logPath

& $pythonExe $scriptPath `
  --base-url $BaseUrl `
  --date-from $DateFrom `
  --date-to $DateTo `
  --timeout-seconds $TimeoutSeconds `
  --project-root $ProjectRoot `
  --evidence-dir $evidenceDir 2>&1 | Tee-Object -FilePath $logPath -Append

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Resultado: FALLIDO. Revisa el log: $logPath"
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Resultado: APROBADO."
Write-Host "Evidencia guardada en: $logPath"
