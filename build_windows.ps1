# Multi-AI Desktop - Windows Build Script
# Run this script in PowerShell to build the Windows executable

param(
    [switch]$Clean,
    [switch]$Debug,
    [string]$SignCert = "",
    [string]$SignPassword = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Multi-AI Desktop - Windows Build Script" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Check if we're in a virtual environment (including conda)
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
    
    # Create virtual environment if it doesn't exist
    if (-not (Test-Path "venv")) {
        python -m venv venv
    }
    
    # Activate virtual environment
    & "venv\Scripts\Activate.ps1"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to activate virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "Virtual environment active: $env:VIRTUAL_ENV" -ForegroundColor Green
}

# Clean previous builds if requested
if ($Clean) {
    Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
    Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "*.egg-info" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Cleaned previous builds" -ForegroundColor Green
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

$pyinstallerArgs = @(
    "--clean"
    "--noconfirm"
)

# Don't add windowed/console options when using a spec file - they're defined in the spec
if ($Debug) {
    $pyinstallerArgs += "--debug=all"
}

$pyinstallerArgs += "multi_ai_desktop.spec"

Write-Host "Running: pyinstaller $($pyinstallerArgs -join ' ')" -ForegroundColor Gray
& pyinstaller @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller build failed" -ForegroundColor Red
    exit 1
}

Write-Host "PyInstaller build completed" -ForegroundColor Green

# Sign the executable if certificate provided
if ([string]::IsNullOrEmpty($SignCert) -eq $false) {
    Write-Host "Signing executable..." -ForegroundColor Yellow
    
    $signToolPath = "${env:ProgramFiles(x86)}\Windows Kits\10\bin\x64\signtool.exe"
    if (-not (Test-Path $signToolPath)) {
        $signToolPath = "${env:ProgramFiles}\Windows Kits\10\bin\x64\signtool.exe"
    }
    
    if (Test-Path $signToolPath) {
        if ([string]::IsNullOrEmpty($SignPassword) -eq $false) {
            & $signToolPath sign /f $SignCert /p $SignPassword /t http://timestamp.digicert.com "dist\MultiAI-Desktop\MultiAI-Desktop.exe"
        } else {
            & $signToolPath sign /f $SignCert /t http://timestamp.digicert.com "dist\MultiAI-Desktop\MultiAI-Desktop.exe"
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Executable signed successfully" -ForegroundColor Green
        } else {
            Write-Host "Warning: Failed to sign executable" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Warning: SignTool not found, skipping code signing" -ForegroundColor Yellow
    }
}

# Create installer with Inno Setup (if available)
$innoSetupPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (Test-Path $innoSetupPath) {
    Write-Host "Creating installer with Inno Setup..." -ForegroundColor Yellow
    
    # Create Inno Setup script
    Write-Host "Creating Inno Setup script..." -ForegroundColor Gray
    $innoScript = @"
[Setup]
AppName=Multi-AI Desktop Chat
AppVersion=1.0.0
AppId={{F4A3B2C1-D6E5-4F7A-8B9C-1E2F3A4B5C6D}}
AppPublisher=Multi-AI Desktop Team
AppPublisherURL=https://github.com/your-username/multi-ai-desktop
AppSupportURL=https://github.com/your-username/multi-ai-desktop/issues
AppUpdatesURL=https://github.com/your-username/multi-ai-desktop/releases
DefaultDirName={autopf}\Multi-AI Desktop Chat
DefaultGroupName=Multi-AI Desktop Chat  
AllowNoIcons=yes
LicenseFile=
OutputDir=dist
OutputBaseFilename=MultiAI-Desktop-Setup-1.0.0
SetupIconFile=
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\MultiAI-Desktop.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
Source: "dist\MultiAI-Desktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Multi-AI Desktop Chat"; Filename: "{app}\MultiAI-Desktop.exe"
Name: "{group}\{cm:UninstallProgram,Multi-AI Desktop Chat}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Multi-AI Desktop Chat"; Filename: "{app}\MultiAI-Desktop.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Multi-AI Desktop Chat"; Filename: "{app}\MultiAI-Desktop.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\MultiAI-Desktop.exe"; Description: "{cm:LaunchProgram,Multi-AI Desktop Chat}"; Flags: nowait postinstall skipifsilent
"@

    $innoScript | Out-File -FilePath "installer.iss" -Encoding UTF8
    
    & $innoSetupPath "installer.iss"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installer created successfully" -ForegroundColor Green
    } else {
        Write-Host "Warning: Failed to create installer" -ForegroundColor Yellow
    }
} else {
    Write-Host "Inno Setup not found, skipping installer creation" -ForegroundColor Yellow
    Write-Host "Download from: https://jrsoftware.org/isinfo.php" -ForegroundColor Gray
}

# Display results
Write-Host ""
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "===============" -ForegroundColor Green

if (Test-Path "dist\MultiAI-Desktop\MultiAI-Desktop.exe") {
    $fileItem = Get-Item "dist\MultiAI-Desktop\MultiAI-Desktop.exe"
    $fileSize = [math]::Round($fileItem.Length / 1MB, 1)
    Write-Host "Executable: dist\MultiAI-Desktop\MultiAI-Desktop.exe ($fileSize MB)" -ForegroundColor Cyan
}

if (Test-Path "dist\MultiAI-Desktop-Setup-1.0.0.exe") {
    $installerItem = Get-Item "dist\MultiAI-Desktop-Setup-1.0.0.exe"
    $installerSize = [math]::Round($installerItem.Length / 1MB, 1)
    Write-Host "Installer: dist\MultiAI-Desktop-Setup-1.0.0.exe ($installerSize MB)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Test the build on a clean Windows VM before distribution!" -ForegroundColor Yellow
Write-Host "Packaging guide: https://pyinstaller.readthedocs.io/" -ForegroundColor Gray 