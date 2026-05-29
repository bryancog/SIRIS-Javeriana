param(
  [string]$ProjectRoot = "D:\SIRIS",
  [string]$BaseUrl = "http://127.0.0.1:3000",
  [string]$CancelDateFrom = "2016-01-01",
  [string]$CancelDateTo = "2026-05-01",
  [string]$RecoveryDateFrom = "2016-01-01",
  [string]$RecoveryDateTo = "2016-02-01",
  [int]$CancelDelaySeconds = 4,
  [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$scriptPath = Join-Path $ProjectRoot "scripts_tests\run_cancel_recovery_test.py"
$evidenceDir = Join-Path $ProjectRoot "tests_evidence\cancel_recovery"
$logPath = Join-Path $evidenceDir "cancel_recovery_$timestamp.log"
$pythonExe = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

if (-not (Test-Path $pythonExe)) {
  throw "No se encontró Python del entorno virtual: $pythonExe"
}

if (-not (Test-Path $scriptPath)) {
  throw "No se encontró el script de prueba: $scriptPath"
}

Write-Host "==================================================="
Write-Host "SIRIS - Cancelación y recuperación v0.8"
Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "BaseUrl:     $BaseUrl"
Write-Host "Log:         $logPath"
Write-Host "==================================================="

Set-Location $ProjectRoot

& $pythonExe -m pip install requests 2>&1 | Tee-Object -FilePath $logPath

& $pythonExe $scriptPath `
  --base-url $BaseUrl `
  --project-root $ProjectRoot `
  --evidence-dir $evidenceDir `
  --cancel-date-from $CancelDateFrom `
  --cancel-date-to $CancelDateTo `
  --recovery-date-from $RecoveryDateFrom `
  --recovery-date-to $RecoveryDateTo `
  --cancel-delay-seconds $CancelDelaySeconds `
  --timeout-seconds $TimeoutSeconds 2>&1 | Tee-Object -FilePath $logPath -Append

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Resultado: FALLIDO. Revisa el log: $logPath"
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Resultado: APROBADO."
Write-Host "Evidencia guardada en: $logPath"
