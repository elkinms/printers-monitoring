$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Virtual environment not found. Create .venv and install requirements first."
}

$pyInstallerAvailable = Test-Path (Join-Path $projectRoot ".venv\Lib\site-packages\PyInstaller")
if (-not $pyInstallerAvailable) {
    Write-Host "Installing PyInstaller..."
    & $python -m pip install "pyinstaller>=6.0,<7.0"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install PyInstaller."
    }
}

Write-Host "Building PrintersMonitoring..."
& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --name PrintersMonitoring `
    --onedir `
    --add-data "app\templates;app\templates" `
    --add-data "app\static;app\static" `
    run.py

if ($LASTEXITCODE -ne 0) {
    throw "Build failed."
}

$outputDirectory = Join-Path $projectRoot "dist\PrintersMonitoring"
New-Item -ItemType Directory -Force -Path (Join-Path $outputDirectory "data") | Out-Null

Write-Host ""
Write-Host "Build completed:"
Write-Host (Join-Path $outputDirectory "PrintersMonitoring.exe")
