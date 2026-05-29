param(
  [string]$ProjectRoot = "D:\SIRIS",
  [string]$BaseUrl = "http://127.0.0.1:3000",
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$frontendRoot = Join-Path $ProjectRoot "frontend"
$evidenceDir = Join-Path $ProjectRoot "tests_evidence\frontend_e2e"
$logPath = Join-Path $evidenceDir "frontend_e2e_$timestamp.log"

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

if (-not (Test-Path $frontendRoot)) {
  throw "No se encontró la carpeta frontend: $frontendRoot"
}

if (-not (Test-Path (Join-Path $frontendRoot "playwright.config.js"))) {
  throw "No se encontró playwright.config.js en: $frontendRoot"
}

if (-not (Test-Path (Join-Path $frontendRoot "e2e\siris_frontend_e2e.spec.js"))) {
  throw "No se encontró la prueba E2E: $frontendRoot\e2e\siris_frontend_e2e.spec.js"
}

Write-Host "==================================================="
Write-Host "SIRIS - Frontend E2E Playwright v0.4.1"
Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "BaseUrl:     $BaseUrl"
Write-Host "Log:         $logPath"
Write-Host "==================================================="

Set-Location $frontendRoot

if (-not $SkipInstall) {
  Write-Host ""
  Write-Host "Instalando dependencias de frontend y Playwright..."
  npm.cmd install 2>&1 | Tee-Object -FilePath $logPath

  npm.cmd install --save-dev @playwright/test 2>&1 | Tee-Object -FilePath $logPath -Append

  npx.cmd playwright install chromium 2>&1 | Tee-Object -FilePath $logPath -Append
}

$env:SIRIS_E2E_BASE_URL = $BaseUrl
$env:SIRIS_E2E_EVIDENCE_DIR = $evidenceDir

Write-Host ""
Write-Host "Ejecutando pruebas E2E..."
npx.cmd playwright test --config=.\playwright.config.js --project=chromium 2>&1 | Tee-Object -FilePath $logPath -Append

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Resultado: FALLIDO. Revisa el log: $logPath"
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Resultado: APROBADO."
Write-Host "Evidencia guardada en: $logPath"
Write-Host "Capturas guardadas en: $evidenceDir"
