param(
  [string]$ProjectRoot = "D:\SIRIS"
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$uatDir = Join-Path $ProjectRoot "tests_evidence\uat"
$template = Join-Path $ProjectRoot "docs\uat\UAT_SIRIS_v0_6_checklist.md"
$output = Join-Path $uatDir "UAT_SIRIS_v0_6_checklist_$timestamp.md"

New-Item -ItemType Directory -Force -Path $uatDir | Out-Null

if (-not (Test-Path $template)) {
  throw "No se encontró la plantilla UAT: $template"
}

Copy-Item $template $output -Force

Write-Host "==================================================="
Write-Host "SIRIS - Preparación UAT v0.6"
Write-Host "Carpeta de evidencias: $uatDir"
Write-Host "Checklist creado: $output"
Write-Host "==================================================="
Write-Host ""
Write-Host "Capturas sugeridas:"
Write-Host "  EV_UAT_01_LOGIN.png"
Write-Host "  EV_UAT_02_REGISTRO.png"
Write-Host "  EV_UAT_03_DASHBOARD.png"
Write-Host "  EV_UAT_04_FECHAS_POLIGONO.png"
Write-Host "  EV_UAT_05_EXPORTACION_EN_PROCESO.png"
Write-Host "  EV_UAT_06_EXPORTACION_FINALIZADA.png"
Write-Host "  EV_UAT_07_VIDEO_RESULTADO.png"
Write-Host "  EV_UAT_08_ZIP_DESCARGADO.png"
Write-Host "  EV_UAT_09_LOGOUT.png"
