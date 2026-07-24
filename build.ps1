$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$outputDirectory = Join-Path $projectRoot "dist\PrintersMonitoring"
$databasePath = Join-Path $outputDirectory "data\printers.db"
$databaseBackup = $null

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

if (Test-Path $databasePath) {
    $databaseBackup = [System.IO.Path]::GetTempFileName()
    Copy-Item -LiteralPath $databasePath -Destination $databaseBackup
    Write-Host "Preserving existing database..."
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --name PrintersMonitoring `
    --onedir `
    --add-data "app\templates;app\templates" `
    --add-data "app\static;app\static" `
    run.py

if ($LASTEXITCODE -ne 0) {
    if ($databaseBackup) {
        Remove-Item -LiteralPath $databaseBackup -Force
    }
    throw "Build failed."
}

New-Item -ItemType Directory -Force -Path (Join-Path $outputDirectory "data") | Out-Null
if ($databaseBackup) {
    Copy-Item -LiteralPath $databaseBackup -Destination $databasePath
    Remove-Item -LiteralPath $databaseBackup -Force
    Write-Host "Existing database restored."
}

Write-Host ""
Write-Host "Build completed:"
Write-Host (Join-Path $outputDirectory "PrintersMonitoring.exe")
