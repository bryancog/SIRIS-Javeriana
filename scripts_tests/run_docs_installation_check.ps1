param(
  [string]$ProjectRoot = "D:\SIRIS",
  [string]$BaseUrl = "http://127.0.0.1:3000",
  [switch]$SkipLiveCheck
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$scriptPath = Join-Path $ProjectRoot "scripts_tests\run_docs_installation_check.py"
$evidenceDir = Join-Path $ProjectRoot "tests_evidence\documentation"
$logPath = Join-Path $evidenceDir "documentation_installation_check_$timestamp.log"
$pythonExe = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

if (-not (Test-Path $pythonExe)) {
  throw "No se encontró Python del entorno virtual: $pythonExe"
}

if (-not (Test-Path $scriptPath)) {
  throw "No se encontró el script de prueba: $scriptPath"
}

Write-Host "==================================================="
Write-Host "SIRIS - Documentación / instalación v0.9"
Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "BaseUrl:     $BaseUrl"
Write-Host "Log:         $logPath"
Write-Host "==================================================="

Set-Location $ProjectRoot

& $pythonExe -m pip install requests 2>&1 | Tee-Object -FilePath $logPath

if ($SkipLiveCheck) {
  & $pythonExe $scriptPath `
    --project-root $ProjectRoot `
    --base-url $BaseUrl `
    --evidence-dir $evidenceDir `
    --skip-live-check 2>&1 | Tee-Object -FilePath $logPath -Append
} else {
  & $pythonExe $scriptPath `
    --project-root $ProjectRoot `
    --base-url $BaseUrl `
    --evidence-dir $evidenceDir 2>&1 | Tee-Object -FilePath $logPath -Append
}

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Resultado: FALLIDO. Revisa el log: $logPath"
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Resultado: APROBADO."
Write-Host "Evidencia guardada en: $logPath"
