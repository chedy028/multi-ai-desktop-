# Rebuild script for Multi-AI Desktop
$ErrorActionPreference = "Stop"

Write-Host "Rebuilding Multi-AI Desktop..." -ForegroundColor Cyan

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cleaned previous builds" -ForegroundColor Green

# Create hooks directory if it doesn't exist
if (-not (Test-Path "hooks")) {
    New-Item -ItemType Directory -Path "hooks"
}

# Install/upgrade dependencies
Write-Host "Installing/upgrading dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install --upgrade pyinstaller
pip install -r requirements_packaging.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "Dependencies installed" -ForegroundColor Green

# Run PyInstaller
Write-Host "Building with PyInstaller..." -ForegroundColor Yellow
pyinstaller --clean --noconfirm multi_ai_desktop.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "`nTo test the application:" -ForegroundColor Cyan
Write-Host "1. Navigate to dist/MultiAI-Desktop" -ForegroundColor Yellow
Write-Host "2. Run MultiAI-Desktop.exe" -ForegroundColor Yellow
Write-Host "`nIf you see any error messages, please share them for further debugging." -ForegroundColor Cyan 