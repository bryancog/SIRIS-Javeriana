param(
  [string]$ProjectRoot = "D:\SIRIS",
  [string]$OutName = "",
  [int]$MaxGeoTIFFs = 5
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$scriptPath = Join-Path $ProjectRoot "scripts_tests\run_geospatial_validation.py"
$evidenceDir = Join-Path $ProjectRoot "tests_evidence\geospatial"
$logPath = Join-Path $evidenceDir "geospatial_validation_$timestamp.log"
$pythonExe = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

if (-not (Test-Path $pythonExe)) {
  throw "No se encontró Python del entorno virtual: $pythonExe"
}

if (-not (Test-Path $scriptPath)) {
  throw "No se encontró el script de prueba: $scriptPath"
}

Write-Host "==================================================="
Write-Host "SIRIS - Validación geoespacial local v0.3.1"
Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "OutName:     $OutName"
Write-Host "Log:         $logPath"
Write-Host "==================================================="

Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($OutName)) {
  & $pythonExe $scriptPath `
    --project-root $ProjectRoot `
    --evidence-dir $evidenceDir `
    --max-geotiffs $MaxGeoTIFFs 2>&1 | Tee-Object -FilePath $logPath
} else {
  & $pythonExe $scriptPath `
    --project-root $ProjectRoot `
    --out-name $OutName `
    --evidence-dir $evidenceDir `
    --max-geotiffs $MaxGeoTIFFs 2>&1 | Tee-Object -FilePath $logPath
}

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Resultado: FALLIDO. Revisa el log: $logPath"
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Resultado: APROBADO."
Write-Host "Evidencia guardada en: $logPath"
