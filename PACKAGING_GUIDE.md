# Multi-AI Desktop - Packaging Guide

This guide provides comprehensive instructions for packaging the Multi-AI Desktop Chat application for Windows and macOS distribution.

> **Note**: OCR functionality has been removed from the packaged builds to simplify dependencies and reduce build complexity. The distributed applications will focus on the core multi-AI chat functionality.

## 🎯 Quick Start

### Windows (PowerShell)
```powershell
# Basic build
.\build_windows.ps1

# Clean build with debug info
.\build_windows.ps1 -Clean -Debug

# Build with code signing
.\build_windows.ps1 -SignCert "path\to\certificate.p12" -SignPassword "password"
```

### macOS (Terminal)
```bash
# Make script executable (first time only)
chmod +x build_macos.sh

# Basic build
./build_macos.sh

# Clean build with signing and notarization
./build_macos.sh --clean --sign --notarize
```

## 📋 Prerequisites

### Common Requirements
- Python 3.8 or later
- Git
- Virtual environment (recommended)

### Windows-Specific
- **Python**: Download from [python.org](https://python.org)
- **Visual Studio Build Tools**: For native extensions
- **Windows SDK**: For code signing (optional)
- **Inno Setup**: For creating installers (optional)

### macOS-Specific  
- **Xcode Command Line Tools**: `xcode-select --install`
- **Apple Developer Account**: For code signing and notarization
- **Homebrew**: Recommended package manager

## 🔧 Installation & Setup

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd multi-ai-desktop

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install packaging dependencies (OCR-free for distribution)
pip install -r requirements_packaging.txt
```

### 2. Platform-Specific Setup

#### Windows Setup

1. **Install PyInstaller**:
   ```powershell
   pip install pyinstaller
   ```

2. **Install Inno Setup** (Optional, for installers):
   - Download from: https://jrsoftware.org/isinfo.php
   - Install to default location: `C:\Program Files (x86)\Inno Setup 6\`

3. **Setup Code Signing** (Optional):
   - Obtain a code signing certificate (.p12 or .pfx file)
   - Install Windows SDK for `signtool.exe`

#### macOS Setup

1. **Install py2app**:
   ```bash
   pip install py2app
   ```

2. **Setup Code Signing** (Optional):
   ```bash
   # Check available signing identities
   security find-identity -v -p codesigning
   
   # Example output:
   # 1) ABC123... "Developer ID Application: Your Name (TEAMID)"
   ```

3. **Setup Notarization** (Optional):
   ```bash
   # Create app-specific password at appleid.apple.com
   # Store credentials for notarization
   xcrun notarytool store-credentials "YourProfileName" \
     --apple-id "your@apple.id" \
     --team-id "YOURTEAMID" \
     --password "app-specific-password"
   ```

## 🏗️ Building Applications

### Windows Build Process

#### Basic Build
```powershell
# Clean build (recommended for releases)
.\build_windows.ps1 -Clean

# Debug build (for troubleshooting)
.\build_windows.ps1 -Debug
```

#### Advanced Build with Signing
```powershell
# With code signing certificate
.\build_windows.ps1 -Clean -SignCert "cert.p12" -SignPassword "password"

# With PFX certificate (no password)
.\build_windows.ps1 -Clean -SignCert "cert.pfx"
```

#### Build Outputs
- **Executable**: `dist\MultiAI-Desktop\MultiAI-Desktop.exe`
- **Installer**: `dist\MultiAI-Desktop-Setup-1.0.0.exe` (if Inno Setup available)

### macOS Build Process

#### Basic Build
```bash
# Clean build
./build_macos.sh --clean

# Debug build
./build_macos.sh --debug
```

#### Advanced Build with Signing
```bash
# First, configure signing identity in build_macos.sh:
# SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)"
# NOTARIZATION_PROFILE="YourProfileName"

# Build with signing and notarization
./build_macos.sh --clean --sign --notarize
```

#### Build Outputs
- **Application**: `dist/Multi-AI Desktop Chat.app`
- **DMG**: `dist/MultiAI-Desktop-1.0.0.dmg`

## 🎛️ Configuration Options

### PyInstaller Spec File (`multi_ai_desktop.spec`)

Key configuration options:

```python
# Console vs. Windowed mode
console=False,  # Set to True for debugging

# Include additional data files
datas=[
    ('app/js/*.js', 'app/js/'),
    ('app/styles/*.css', 'app/styles/'),
],

# Hidden imports (modules not auto-detected)
hiddenimports=[
    'PySide6.QtWebEngineCore',
    'app.panes.base_pane',
    # ... more modules
],

# Exclude unnecessary modules
excludes=[
    'matplotlib',
    'tkinter',
    'unittest',
],
```

### py2app Setup (`setup_macos.py`)

Key configuration options:

```python
OPTIONS = {
    'py2app': {
        'iconfile': 'app/assets/icon.icns',
        'plist': PLIST,  # App metadata
        'packages': ['PySide6', 'app'],
        'arch': 'universal2',  # Intel + Apple Silicon
        'strip': True,  # Reduce size
        'optimize': 2,  # Python optimization level
    }
}
```

## 🔒 Code Signing & Security

### Windows Code Signing

1. **Obtain Certificate**:
   - Purchase from Certificate Authority (DigiCert, Sectigo, etc.)
   - Or use self-signed for testing

2. **Sign Executable**:
   ```powershell
   # Automatic via build script
   .\build_windows.ps1 -SignCert "cert.p12" -SignPassword "password"
   
   # Manual signing
   signtool sign /f cert.p12 /p password /t http://timestamp.digicert.com MultiAI-Desktop.exe
   ```

3. **Verify Signature**:
   ```powershell
   signtool verify /pa MultiAI-Desktop.exe
   ```

### macOS Code Signing & Notarization

1. **Prerequisites**:
   - Apple Developer Account ($99/year)
   - Developer ID Application certificate
   - App-specific password

2. **Sign Application**:
   ```bash
   # Automatic via build script
   ./build_macos.sh --sign
   
   # Manual signing
   codesign --force --verify --verbose --sign "Developer ID Application: Your Name" --options runtime "Multi-AI Desktop Chat.app"
   ```

3. **Notarize Application**:
   ```bash
   # Automatic via build script
   ./build_macos.sh --notarize
   
   # Manual notarization
   xcrun notarytool submit app.dmg --keychain-profile "ProfileName" --wait
   xcrun stapler staple app.dmg
   ```

## 📦 Distribution

### Creating Installers

#### Windows Installer (Inno Setup)
The build script automatically generates an Inno Setup script:

```ini
[Setup]
AppName=Multi-AI Desktop Chat
AppVersion=1.0.0
DefaultDirName={pf}\Multi-AI Desktop Chat
OutputBaseFilename=MultiAI-Desktop-Setup-1.0.0
```

#### macOS DMG
The build script creates a DMG with:
- Application bundle
- Applications folder symlink
- Custom volume name

### Alternative Packaging

#### Windows Portable
Create a portable version:
```powershell
# Build with PyInstaller onedir mode (default)
pyinstaller multi_ai_desktop.spec

# Package as ZIP
Compress-Archive -Path "dist\MultiAI-Desktop" -DestinationPath "MultiAI-Desktop-Portable.zip"
```

#### macOS PKG Installer
```bash
# Create PKG installer
pkgbuild --root "dist/Multi-AI Desktop Chat.app" \
         --identifier "com.multiai.desktop" \
         --version "1.0.0" \
         --install-location "/Applications" \
         "MultiAI-Desktop-1.0.0.pkg"
```

## 🧪 Testing

### Pre-Distribution Testing

#### Windows Testing
1. **Clean VM Testing**:
   - Test on Windows 10 and 11
   - Test on system without Python/Qt installed
   - Verify all features work correctly

2. **Dependency Check**:
   ```powershell
   # Check DLL dependencies
   dumpbin /dependents MultiAI-Desktop.exe
   ```

#### macOS Testing
1. **Multiple macOS Versions**:
   - Test on macOS 10.14+ (minimum supported)
   - Test on both Intel and Apple Silicon Macs

2. **Gatekeeper Testing**:
   ```bash
   # Check signing and notarization
   spctl -a -t exec -vv "Multi-AI Desktop Chat.app"
   ```

### Performance Optimization

#### Reducing Bundle Size
1. **Exclude Unnecessary Modules**:
   ```python
   excludes=[
       'matplotlib', 'scipy', 'pandas',
       'unittest', 'test', 'tests',
   ]
   ```

2. **Strip Debug Symbols**:
   ```python
   # PyInstaller
   strip=True,
   
   # py2app
   'strip': True,
   ```

3. **Optimize Python Bytecode**:
   ```python
   # py2app
   'optimize': 2,
   ```

## 🚀 CI/CD Automation

### GitHub Actions Example

```yaml
name: Build and Release

on:
  push:
    tags: ['v*']

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Build Windows App
        run: .\build_windows.ps1 -Clean
      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: windows-build
          path: dist/

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Build macOS App
        run: ./build_macos.sh --clean
      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: macos-build
          path: dist/
```

## 🐛 Troubleshooting

### Common Issues

#### Windows Issues
1. **Missing DLLs**:
   ```
   Error: api-ms-win-crt-runtime-l1-1-0.dll missing
   ```
   **Solution**: Install Visual C++ Redistributable

2. **Qt Platform Plugin Error**:
   ```
   Error: This application failed to start because no Qt platform plugin could be initialized
   ```
   **Solution**: Ensure `platforms/qwindows.dll` is included

3. **WebEngine Issues**:
   ```
   Error: Qt WebEngine process didn't start
   ```
   **Solution**: Include WebEngine resources and run with `--no-sandbox`

#### macOS Issues
1. **App Won't Open**:
   ```
   Error: "App" is damaged and can't be opened
   ```
   **Solution**: Sign and notarize the application

2. **Missing Qt Frameworks**:
   ```
   Error: Library not loaded: @rpath/QtCore.framework/Versions/6/QtCore
   ```
   **Solution**: Ensure Qt frameworks are bundled correctly

3. **Permission Errors**:
   ```
   Error: Operation not permitted
   ```
   **Solution**: Add appropriate permissions to Info.plist

### Debug Mode

#### Windows Debug Build
```powershell
# Build with debug console
.\build_windows.ps1 -Debug

# Run with debug output
$env:QT_DEBUG_PLUGINS=1
.\dist\MultiAI-Desktop\MultiAI-Desktop.exe
```

#### macOS Debug Build
```bash
# Build with debug symbols
./build_macos.sh --debug

# Run with debug output
QT_DEBUG_PLUGINS=1 "./dist/Multi-AI Desktop Chat.app/Contents/MacOS/Multi-AI Desktop Chat"
```

## 📚 Additional Resources

### Documentation
- [PyInstaller Manual](https://pyinstaller.readthedocs.io/)
- [py2app Documentation](https://py2app.readthedocs.io/)
- [Qt Application Deployment](https://doc.qt.io/qt-6/deployment.html)

### Tools
- [Inno Setup](https://jrsoftware.org/isinfo.php) - Windows installer creation
- [Advanced Installer](https://www.advancedinstaller.com/) - Professional Windows installer
- [DMG Canvas](https://www.araelium.com/dmgcanvas) - macOS DMG creation
- [Packages](http://s.sudre.free.fr/Software/Packages/about.html) - macOS PKG installer creation

### Certificates & Signing
- [DigiCert Code Signing](https://www.digicert.com/code-signing/)
- [Apple Developer Program](https://developer.apple.com/programs/)
- [Windows Code Signing Guide](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools)

---

## 📞 Support

If you encounter issues during packaging:

1. Check the troubleshooting section above
2. Review build logs for specific error messages
3. Test on a clean virtual machine
4. Create an issue on the project repository with:
   - Platform and version
   - Complete error messages
   - Build configuration used

**Happy packaging! 🚀** 