param(
  [string]$ProjectRoot = "D:\SIRIS",
  [string]$BaseUrl = "http://127.0.0.1:3000",
  [int]$Users = 10,
  [int]$RequestsPerUser = 20,
  [int]$ThinkTimeMs = 100,
  [double]$MinSuccessRate = 0.95,
  [double]$MaxP95Ms = 2000
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$scriptPath = Join-Path $ProjectRoot "scripts_tests\run_moderate_load_test.py"
$evidenceDir = Join-Path $ProjectRoot "tests_evidence\load"
$logPath = Join-Path $evidenceDir "moderate_load_$timestamp.log"
$pythonExe = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

if (-not (Test-Path $pythonExe)) {
  throw "No se encontró Python del entorno virtual: $pythonExe"
}

if (-not (Test-Path $scriptPath)) {
  throw "No se encontró el script de prueba: $scriptPath"
}

Write-Host "==================================================="
Write-Host "SIRIS - Prueba de carga moderada v0.5"
Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "BaseUrl:     $BaseUrl"
Write-Host "Users:       $Users"
Write-Host "Requests/user: $RequestsPerUser"
Write-Host "Log:         $logPath"
Write-Host "==================================================="

Set-Location $ProjectRoot

& $pythonExe -m pip install requests 2>&1 | Tee-Object -FilePath $logPath

& $pythonExe $scriptPath `
  --base-url $BaseUrl `
  --users $Users `
  --requests-per-user $RequestsPerUser `
  --think-time-ms $ThinkTimeMs `
  --evidence-dir $evidenceDir `
  --min-success-rate $MinSuccessRate `
  --max-p95-ms $MaxP95Ms 2>&1 | Tee-Object -FilePath $logPath -Append

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Resultado: FALLIDO. Revisa el log: $logPath"
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Resultado: APROBADO."
Write-Host "Evidencia guardada en: $logPath"
