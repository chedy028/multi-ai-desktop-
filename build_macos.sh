#!/bin/bash

# Multi-AI Desktop - macOS Build Script
# Run with: ./build_macos.sh [--clean] [--debug] [--sign] [--notarize]

set -e  # Exit on any error

# Configuration
APP_NAME="Multi-AI Desktop Chat"
APP_VERSION="1.0.0"
BUNDLE_ID="com.multiai.desktop"
DEVELOPER_ID=""  # Set your Apple Developer ID here
SIGNING_IDENTITY=""  # Set your signing identity here
NOTARIZATION_PROFILE=""  # Set your notarization profile here

# Parse command line arguments
CLEAN=false
DEBUG=false
SIGN=false
NOTARIZE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --sign)
            SIGN=true
            shift
            ;;
        --notarize)
            NOTARIZE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--clean] [--debug] [--sign] [--notarize]"
            exit 1
            ;;
    esac
done

echo "🚀 Multi-AI Desktop - macOS Build Script"
echo "========================================"

# Check for virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not in a virtual environment!"
    echo "Creating and activating virtual environment..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to activate virtual environment"
        exit 1
    fi
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"

# Clean previous builds if requested
if [[ "$CLEAN" == true ]]; then
    echo "🧹 Cleaning previous builds..."
    rm -rf build dist *.egg-info
    echo "✅ Cleaned previous builds"
fi

# Install/upgrade dependencies
echo "📦 Installing/upgrading dependencies..."
python -m pip install --upgrade pip
pip install --upgrade py2app
pip install -r requirements_packaging.txt

if [[ $? -ne 0 ]]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"

# Check for required tools
echo "🔍 Checking required tools..."

# Check if we have Xcode command line tools
if ! command -v xcodebuild &> /dev/null; then
    echo "❌ Xcode command line tools not found"
    echo "Install with: xcode-select --install"
    exit 1
fi

# Check for code signing tools if signing is requested
if [[ "$SIGN" == true ]]; then
    if [[ -z "$SIGNING_IDENTITY" ]]; then
        echo "❌ SIGNING_IDENTITY not set in script"
        echo "Set your Apple Developer ID certificate name"
        exit 1
    fi
    
    # Check if the signing identity exists
    if ! security find-identity -v -p codesigning | grep -q "$SIGNING_IDENTITY"; then
        echo "❌ Signing identity '$SIGNING_IDENTITY' not found"
        echo "Available identities:"
        security find-identity -v -p codesigning
        exit 1
    fi
fi

echo "✅ Required tools available"

# Build the application
echo "🔨 Building with py2app..."

PY2APP_ARGS="py2app"

if [[ "$DEBUG" == true ]]; then
    PY2APP_ARGS="$PY2APP_ARGS --debug-modulegraph"
fi

python setup_macos.py $PY2APP_ARGS

if [[ $? -ne 0 ]]; then
    echo "❌ py2app build failed"
    exit 1
fi

echo "✅ py2app build completed"

# Sign the application if requested
if [[ "$SIGN" == true ]]; then
    echo "🔏 Signing application..."
    
    APP_PATH="dist/$APP_NAME.app"
    
    # Sign all binaries and frameworks first
    echo "Signing frameworks and binaries..."
    find "$APP_PATH" -type f \( -name "*.dylib" -o -name "*.so" -o -perm +111 \) -exec codesign --force --verify --verbose --sign "$SIGNING_IDENTITY" {} \;
    
    # Sign the main app bundle
    echo "Signing main application bundle..."
    codesign --force --verify --verbose --sign "$SIGNING_IDENTITY" --options runtime "$APP_PATH"
    
    if [[ $? -eq 0 ]]; then
        echo "✅ Application signed successfully"
        
        # Verify the signature
        echo "🔍 Verifying signature..."
        codesign --verify --deep --strict --verbose=2 "$APP_PATH"
        
        if [[ $? -eq 0 ]]; then
            echo "✅ Signature verification passed"
        else
            echo "⚠️  Warning: Signature verification failed"
        fi
    else
        echo "❌ Failed to sign application"
        exit 1
    fi
fi

# Create DMG
echo "📦 Creating DMG..."

DMG_NAME="MultiAI-Desktop-$APP_VERSION"
DMG_PATH="dist/$DMG_NAME.dmg"

# Remove existing DMG
rm -f "$DMG_PATH"

# Create temporary directory for DMG contents
DMG_TEMP="dist/dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# Copy app to DMG temp directory
cp -R "dist/$APP_NAME.app" "$DMG_TEMP/"

# Create Applications symlink
ln -s /Applications "$DMG_TEMP/Applications"

# Create the DMG
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_TEMP" -ov -format UDZO "$DMG_PATH"

if [[ $? -eq 0 ]]; then
    echo "✅ DMG created successfully"
    
    # Sign the DMG if signing is enabled
    if [[ "$SIGN" == true ]]; then
        echo "🔏 Signing DMG..."
        codesign --force --sign "$SIGNING_IDENTITY" "$DMG_PATH"
        
        if [[ $? -eq 0 ]]; then
            echo "✅ DMG signed successfully"
        else
            echo "⚠️  Warning: Failed to sign DMG"
        fi
    fi
else
    echo "❌ Failed to create DMG"
    exit 1
fi

# Clean up temp directory
rm -rf "$DMG_TEMP"

# Notarize if requested
if [[ "$NOTARIZE" == true ]]; then
    if [[ -z "$NOTARIZATION_PROFILE" ]]; then
        echo "❌ NOTARIZATION_PROFILE not set in script"
        echo "Create a notarization profile with: xcrun notarytool store-credentials"
        exit 1
    fi
    
    echo "📋 Submitting for notarization..."
    echo "This may take several minutes..."
    
    # Submit for notarization
    xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARIZATION_PROFILE" --wait
    
    if [[ $? -eq 0 ]]; then
        echo "✅ Notarization successful"
        
        # Staple the notarization to the DMG
        echo "📎 Stapling notarization..."
        xcrun stapler staple "$DMG_PATH"
        
        if [[ $? -eq 0 ]]; then
            echo "✅ Notarization stapled successfully"
        else
            echo "⚠️  Warning: Failed to staple notarization"
        fi
    else
        echo "❌ Notarization failed"
        echo "Check the notarization log for details"
        exit 1
    fi
fi

# Display results
echo ""
echo "🎉 Build Complete!"
echo "=================="

if [[ -d "dist/$APP_NAME.app" ]]; then
    APP_SIZE=$(du -sh "dist/$APP_NAME.app" | cut -f1)
    echo "📁 Application: dist/$APP_NAME.app ($APP_SIZE)"
fi

if [[ -f "$DMG_PATH" ]]; then
    DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    echo "💿 DMG: $DMG_PATH ($DMG_SIZE)"
fi

echo ""
echo "🧪 Test the build on different macOS versions before distribution!"
echo "📚 Packaging guide: https://py2app.readthedocs.io/"

# Instructions for first-time setup
if [[ "$SIGN" == false ]]; then
    echo ""
    echo "📝 To enable code signing:"
    echo "1. Get an Apple Developer account"
    echo "2. Create a Developer ID certificate"
    echo "3. Set SIGNING_IDENTITY in this script"
    echo "4. Run with --sign flag"
fi

if [[ "$NOTARIZE" == false ]] && [[ "$SIGN" == true ]]; then
    echo ""
    echo "📝 To enable notarization:"
    echo "1. Create app-specific password: https://appleid.apple.com"
    echo "2. Store credentials: xcrun notarytool store-credentials"
    echo "3. Set NOTARIZATION_PROFILE in this script"
    echo "4. Run with --notarize flag"
fi 