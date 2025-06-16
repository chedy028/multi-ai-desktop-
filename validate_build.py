#!/usr/bin/env python3
"""
Multi-AI Desktop - Build Environment Validation Script

This script validates that your environment is properly configured
for building the Multi-AI Desktop application on Windows and macOS.
"""

import os
import sys
import subprocess
import platform
import importlib
from pathlib import Path

def print_header(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(item, status, details=""):
    """Print a status line with consistent formatting."""
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {item:<30} {details}")
    return status

def check_python_version():
    """Check Python version compatibility."""
    version = sys.version_info
    required = (3, 8)
    
    if version >= required:
        return print_status("Python Version", True, f"{version.major}.{version.minor}.{version.micro}")
    else:
        return print_status("Python Version", False, f"{version.major}.{version.minor}.{version.micro} (requires 3.8+)")

def check_module(module_name, required=True):
    """Check if a Python module is available."""
    try:
        importlib.import_module(module_name)
        return print_status(f"Module: {module_name}", True, "Available")
    except ImportError:
        status_text = "Required" if required else "Optional"
        return print_status(f"Module: {module_name}", not required, f"Missing ({status_text})")

def check_command(command, required=True):
    """Check if a command-line tool is available."""
    try:
        result = subprocess.run([command, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            return print_status(f"Command: {command}", True, version)
        else:
            raise subprocess.CalledProcessError(result.returncode, command)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        status_text = "Required" if required else "Optional"
        return print_status(f"Command: {command}", not required, f"Missing ({status_text})")

def check_file_exists(filepath, description, required=True):
    """Check if a file exists."""
    path = Path(filepath)
    if path.exists():
        size = path.stat().st_size
        return print_status(description, True, f"Found ({size} bytes)")
    else:
        status_text = "Required" if required else "Optional"
        return print_status(description, not required, f"Missing ({status_text})")

def check_virtual_environment():
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    venv_path = os.environ.get('VIRTUAL_ENV', 'Not detected')
    
    if in_venv:
        return print_status("Virtual Environment", True, venv_path)
    else:
        return print_status("Virtual Environment", False, "Not active (recommended)")

def validate_windows_build_env():
    """Validate Windows-specific build environment."""
    print_header("Windows Build Environment")
    
    issues = []
    
    # Check packaging tools
    if not check_module("PyInstaller", required=False):
        issues.append("Install PyInstaller: pip install pyinstaller")
    
    # Check for Inno Setup
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe"
    ]
    
    inno_found = any(Path(p).exists() for p in inno_paths)
    if not print_status("Inno Setup", inno_found, "For creating installers"):
        issues.append("Download Inno Setup from: https://jrsoftware.org/isinfo.php")
    
    # Check for Windows SDK (signtool for code signing)
    sdk_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin",
        r"C:\Program Files\Windows Kits\10\bin"
    ]
    
    signtool_found = False
    for sdk_path in sdk_paths:
        if Path(sdk_path).exists():
            for arch in ["x64", "x86"]:
                signtool_path = Path(sdk_path) / arch / "signtool.exe"
                if signtool_path.exists():
                    signtool_found = True
                    break
    
    if not print_status("Windows SDK (signtool)", signtool_found, "For code signing"):
        issues.append("Install Windows SDK for code signing support")
    
    return issues

def validate_macos_build_env():
    """Validate macOS-specific build environment."""
    print_header("macOS Build Environment")
    
    issues = []
    
    # Check packaging tools
    if not check_module("py2app", required=False):
        issues.append("Install py2app: pip install py2app")
    
    # Check for Xcode command line tools
    if not check_command("xcodebuild", required=False):
        issues.append("Install Xcode command line tools: xcode-select --install")
    
    # Check for codesign (part of Xcode tools)
    if not check_command("codesign", required=False):
        issues.append("Code signing tools not available")
    
    # Check for notarization tools
    if not check_command("xcrun", required=False):
        issues.append("Xcode command line tools required for notarization")
    
    # Check for DMG creation tools
    if not check_command("hdiutil", required=False):
        issues.append("DMG creation tools not available")
    
    return issues

def validate_common_environment():
    """Validate common build environment requirements."""
    print_header("Common Requirements")
    
    issues = []
    
    # Python version
    if not check_python_version():
        issues.append("Upgrade Python to 3.8 or later")
    
    # Virtual environment
    if not check_virtual_environment():
        issues.append("Consider using a virtual environment")
    
    # Core Python modules (OCR dependencies removed for packaging)
    core_modules = [
        "PySide6",
        "requests",
    ]
    
    for module in core_modules:
        if not check_module(module):
            issues.append(f"Install {module}: see requirements.txt")
    
    # Optional modules
    optional_modules = [
        ("matplotlib", "For advanced plotting"),
        ("scipy", "For scientific computing"),
        ("PIL", "OCR functionality (excluded from packaging)"),
        ("cv2", "OCR functionality (excluded from packaging)"),
        ("pytesseract", "OCR functionality (excluded from packaging)"),
    ]
    
    for module, description in optional_modules:
        check_module(module, required=False)
    
    return issues

def validate_project_structure():
    """Validate project file structure."""
    print_header("Project Structure")
    
    issues = []
    
    # Required files
    required_files = [
        ("requirements_packaging.txt", "Packaging dependencies (OCR-free)"),
        ("app/__main__.py", "Main application entry point"),
        ("app/panes/base_pane.py", "Base pane class"),
        ("app/utils/js_loader.py", "JavaScript loader"),
        ("multi_ai_desktop.spec", "PyInstaller specification"),
        ("setup_macos.py", "py2app setup script"),
    ]
    
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            issues.append(f"Missing required file: {filepath}")
    
    # Optional files
    optional_files = [
        ("build_windows.ps1", "Windows build script"),
        ("build_macos.sh", "macOS build script"),
        ("app/assets/icon.ico", "Windows application icon"),
        ("app/assets/icon.icns", "macOS application icon"),
    ]
    
    for filepath, description in optional_files:
        check_file_exists(filepath, description, required=False)
    
    # Check JavaScript files
    js_dir = Path("app/js")
    if js_dir.exists():
        js_files = list(js_dir.glob("*.js"))
        print_status("JavaScript Files", len(js_files) > 0, f"Found {len(js_files)} files")
    else:
        issues.append("JavaScript directory not found: app/js")
    
    return issues

def main():
    """Main validation function."""
    print("🔍 Multi-AI Desktop - Build Environment Validation")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    
    all_issues = []
    
    # Common validation
    all_issues.extend(validate_common_environment())
    all_issues.extend(validate_project_structure())
    
    # Platform-specific validation
    if platform.system() == "Windows":
        all_issues.extend(validate_windows_build_env())
    elif platform.system() == "Darwin":
        all_issues.extend(validate_macos_build_env())
    else:
        print_header("Platform Support")
        print_status("Platform", False, f"Unsupported platform: {platform.system()}")
        all_issues.append("Only Windows and macOS are currently supported")
    
    # Summary
    print_header("Validation Summary")
    
    if not all_issues:
        print("🎉 All checks passed! Your environment is ready for building.")
        print("\nNext steps:")
        if platform.system() == "Windows":
            print("  • Run: .\\build_windows.ps1")
        elif platform.system() == "Darwin":
            print("  • Run: ./build_macos.sh")
        print("  • Check PACKAGING_GUIDE.md for detailed instructions")
        return 0
    else:
        print(f"⚠️  Found {len(all_issues)} issue(s) that should be addressed:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n📚 For detailed setup instructions, see PACKAGING_GUIDE.md")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 