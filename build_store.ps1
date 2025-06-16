# Multi-AI Desktop - Windows Store Build Script
# Run this script in PowerShell to build the Windows Store package

param(
    [string]$PublisherName = "YourPublisherName",
    [string]$SignCert = "",
    [string]$SignPassword = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Multi-AI Desktop - Windows Store Build Script" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# Check if we're in a virtual environment
$inVirtualEnv = $false
if ($env:VIRTUAL_ENV -or $env:CONDA_DEFAULT_ENV) {
    $inVirtualEnv = $true
    if ($env:CONDA_DEFAULT_ENV) {
        Write-Host "Conda environment active: $env:CONDA_DEFAULT_ENV" -ForegroundColor Green
    } else {
        Write-Host "Virtual environment active: $env:VIRTUAL_ENV" -ForegroundColor Green
    }
}

if (-not $inVirtualEnv) {
    Write-Host "Warning: Not in a virtual environment!" -ForegroundColor Yellow
    Write-Host "Creating and activating virtual environment..." -ForegroundColor Yellow
    
    if (-not (Test-Path "venv")) {
        python -m venv venv
    }
    
    & "venv\Scripts\Activate.ps1"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to activate virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "Virtual environment active: $env:VIRTUAL_ENV" -ForegroundColor Green
}

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "*.egg-info" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cleaned previous builds" -ForegroundColor Green

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

# Build with PyInstaller
Write-Host "Building with PyInstaller..." -ForegroundColor Yellow
pyinstaller --clean --noconfirm multi_ai_desktop.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller build failed" -ForegroundColor Red
    exit 1
}

Write-Host "PyInstaller build completed" -ForegroundColor Green

# Create Assets directory if it doesn't exist
if (-not (Test-Path "Assets")) {
    New-Item -ItemType Directory -Path "Assets"
}

# Create placeholder images if they don't exist
$imageSizes = @{
    "StoreLogo.png" = "50x50"
    "Square150x150Logo.png" = "150x150"
    "Square44x44Logo.png" = "44x44"
    "Wide310x150Logo.png" = "310x150"
}

# Create a simple placeholder icon using PowerShell
foreach ($image in $imageSizes.GetEnumerator()) {
    if (-not (Test-Path "Assets\$($image.Key)")) {
        Write-Host "Creating placeholder for $($image.Key)..." -ForegroundColor Yellow
        
        # Create a simple colored square as placeholder
        $size = $image.Value.Split('x')[0]
        $bitmap = New-Object System.Drawing.Bitmap $size, $size
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear([System.Drawing.Color]::FromArgb(255, 0, 120, 215))  # Windows blue color
        $bitmap.Save("Assets\$($image.Key)", [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

# Update manifest with publisher name
$manifestContent = Get-Content "Package.appxmanifest" -Raw
$manifestContent = $manifestContent -replace "CN=YourPublisherName", "CN=$PublisherName"
$manifestContent | Set-Content "Package.appxmanifest"

# Create MSIX package
Write-Host "Creating MSIX package..." -ForegroundColor Yellow

# Check if MakeAppx is available
$makeAppxPath = "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.0.19041.0\x64\makeappx.exe"
if (-not (Test-Path $makeAppxPath)) {
    $makeAppxPath = "${env:ProgramFiles}\Windows Kits\10\bin\10.0.19041.0\x64\makeappx.exe"
}

if (Test-Path $makeAppxPath) {
    # Create package directory
    $packageDir = "AppPackages"
    if (-not (Test-Path $packageDir)) {
        New-Item -ItemType Directory -Path $packageDir
    }

    # Copy files to package directory
    $packageContentDir = "$packageDir\MultiAIDesktop"
    if (Test-Path $packageContentDir) {
        Remove-Item -Path $packageContentDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $packageContentDir

    # Copy application files
    Copy-Item "dist\MultiAI-Desktop\*" -Destination $packageContentDir -Recurse
    Copy-Item "Package.appxmanifest" -Destination $packageContentDir
    Copy-Item "Assets" -Destination $packageContentDir -Recurse

    # Create MSIX package
    & $makeAppxPath pack /d $packageContentDir /p "$packageDir\MultiAIDesktop.msix"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "MSIX package created successfully" -ForegroundColor Green
    } else {
        Write-Host "Failed to create MSIX package" -ForegroundColor Red
        exit 1
    }

    # Sign the package if certificate provided
    if ([string]::IsNullOrEmpty($SignCert) -eq $false) {
        Write-Host "Signing MSIX package..." -ForegroundColor Yellow
        
        $signToolPath = "${env:ProgramFiles(x86)}\Windows Kits\10\bin\x64\signtool.exe"
        if (-not (Test-Path $signToolPath)) {
            $signToolPath = "${env:ProgramFiles}\Windows Kits\10\bin\x64\signtool.exe"
        }
        
        if (Test-Path $signToolPath) {
            if ([string]::IsNullOrEmpty($SignPassword) -eq $false) {
                & $signToolPath sign /f $SignCert /p $SignPassword /fd sha256 /a "$packageDir\MultiAIDesktop.msix"
            } else {
                & $signToolPath sign /f $SignCert /fd sha256 /a "$packageDir\MultiAIDesktop.msix"
            }
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "MSIX package signed successfully" -ForegroundColor Green
            } else {
                Write-Host "Warning: Failed to sign MSIX package" -ForegroundColor Yellow
            }
        } else {
            Write-Host "Warning: SignTool not found, skipping code signing" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "Error: MakeAppx not found. Please install the Windows SDK." -ForegroundColor Red
    exit 1
}

# Display results
Write-Host ""
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "===============" -ForegroundColor Green

if (Test-Path "$packageDir\MultiAIDesktop.msix") {
    $fileItem = Get-Item "$packageDir\MultiAIDesktop.msix"
    $fileSize = [math]::Round($fileItem.Length / 1MB, 1)
    Write-Host "MSIX Package: $packageDir\MultiAIDesktop.msix ($fileSize MB)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test the MSIX package on a clean Windows VM" -ForegroundColor Yellow
Write-Host "2. Submit the package to the Microsoft Store" -ForegroundColor Yellow
Write-Host "3. Complete the store listing and certification process" -ForegroundColor Yellow 