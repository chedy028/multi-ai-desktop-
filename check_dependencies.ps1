# Check and install required dependencies
$ErrorActionPreference = "Stop"

Write-Host "Checking dependencies..." -ForegroundColor Cyan

# Check Visual C++ Redistributable
$vcRedistPath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Community\VC\Redist\MSVC\14.29.30133\vcredist_x64.exe"
$vcRedistPath2022 = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Community\VC\Redist\MSVC\14.38.33130\vcredist_x64.exe"

if (-not (Test-Path $vcRedistPath) -and -not (Test-Path $vcRedistPath2022)) {
    Write-Host "Visual C++ Redistributable not found. Downloading..." -ForegroundColor Yellow
    $url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    $output = "vc_redist.x64.exe"
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $output
        Write-Host "Installing Visual C++ Redistributable..." -ForegroundColor Yellow
        Start-Process -FilePath $output -ArgumentList "/install", "/quiet", "/norestart" -Wait
        Remove-Item $output
        Write-Host "Visual C++ Redistributable installed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to download or install Visual C++ Redistributable" -ForegroundColor Red
        Write-Host "Please download and install it manually from: https://aka.ms/vs/17/release/vc_redist.x64.exe" -ForegroundColor Yellow
    }
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Warning: Script is not running as administrator" -ForegroundColor Yellow
    Write-Host "Some operations may require elevated privileges" -ForegroundColor Yellow
}

# Check Windows version
$osInfo = Get-WmiObject -Class Win32_OperatingSystem
Write-Host "Windows Version: $($osInfo.Caption) $($osInfo.Version)" -ForegroundColor Cyan

# Check if .NET Framework is installed
$dotNetVersion = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction SilentlyContinue
if ($dotNetVersion) {
    Write-Host ".NET Framework Version: $($dotNetVersion.Version)" -ForegroundColor Green
} else {
    Write-Host ".NET Framework not found" -ForegroundColor Yellow
}

# Check system architecture
$is64Bit = [Environment]::Is64BitOperatingSystem
Write-Host "System Architecture: $(if ($is64Bit) { '64-bit' } else { '32-bit' })" -ForegroundColor Cyan

Write-Host "`nDependency check complete!" -ForegroundColor Green
Write-Host "If the application still doesn't start, try running it from the command line to see error messages:" -ForegroundColor Yellow
Write-Host "1. Open Command Prompt as Administrator" -ForegroundColor Yellow
Write-Host "2. Navigate to the application directory" -ForegroundColor Yellow
Write-Host "3. Run: MultiAI-Desktop.exe" -ForegroundColor Yellow 