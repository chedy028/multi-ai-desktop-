"""
py2app setup script for Multi-AI Desktop Chat
Build for macOS with: python setup_macos.py py2app
"""

import os
import sys
from setuptools import setup
import plistlib

# App metadata
APP_NAME = "Multi-AI Desktop Chat"
APP_VERSION = "1.0.0"
APP_IDENTIFIER = "com.multiai.desktop"

# Main script
APP_SCRIPT = 'app/__main__.py'

# Collect JavaScript files
def collect_js_files():
    js_files = []
    js_dir = 'app/js'
    if os.path.exists(js_dir):
        for root, dirs, files in os.walk(js_dir):
            for file in files:
                if file.endswith('.js'):
                    js_files.append(os.path.join(root, file))
    return js_files

# Collect CSS files  
def collect_css_files():
    css_files = []
    styles_dir = 'app/styles'
    if os.path.exists(styles_dir):
        for root, dirs, files in os.walk(styles_dir):
            for file in files:
                if file.endswith('.css'):
                    css_files.append(os.path.join(root, file))
    return css_files

# Data files to include
DATA_FILES = [
    'requirements.txt',
    'README.md',
    *collect_js_files(),
    *collect_css_files(),
]

# Additional Qt frameworks that might be needed
QT_FRAMEWORKS = [
    'QtCore',
    'QtGui', 
    'QtWidgets',
    'QtWebEngineCore',
    'QtWebEngineWidgets',
    'QtNetwork',
    'QtPrintSupport',
    'QtQml',
    'QtQuick',
    'QtSql',
    'QtWebKit',
    'QtWebKitWidgets',
]

# App bundle settings
PLIST = {
    'CFBundleName': APP_NAME,
    'CFBundleDisplayName': APP_NAME,
    'CFBundleGetInfoString': f"{APP_NAME} {APP_VERSION}",
    'CFBundleIdentifier': APP_IDENTIFIER,
    'CFBundleVersion': APP_VERSION,
    'CFBundleShortVersionString': APP_VERSION,
    'NSHumanReadableCopyright': '© 2024 Multi-AI Desktop. All rights reserved.',
    'CFBundleDocumentTypes': [],
    'LSMinimumSystemVersion': '10.14',  # macOS Mojave minimum
    'LSApplicationCategoryType': 'public.app-category.productivity',
    'NSHighResolutionCapable': True,
    'NSSupportsAutomaticGraphicsSwitching': True,
    'NSRequiresAquaSystemAppearance': False,
    'LSUIElement': False,  # Show in Dock
    'NSAppTransportSecurity': {
        'NSAllowsArbitraryLoads': True,  # Allow web content
        'NSAllowsLocalNetworking': True,
    },
    # Camera permission removed since OCR functionality is disabled
    'NSMicrophoneUsageDescription': 'This app may access microphone for AI interactions.',
    # Camera security removed since OCR functionality is disabled
    'com.apple.security.device.microphone': True,
    'com.apple.security.network.client': True,
    'com.apple.security.network.server': True,
}

# py2app options
OPTIONS = {
    'py2app': {
        'argv_emulation': False,
        'no_chdir': True,
        'iconfile': 'app/assets/icon.icns' if os.path.exists('app/assets/icon.icns') else None,
        'plist': PLIST,
        'resources': DATA_FILES,
        'packages': [
            'PySide6',
            'app',
            'requests',
        ],
        'includes': [
            # Qt modules
            'PySide6.QtCore',
            'PySide6.QtGui', 
            'PySide6.QtWidgets',
            'PySide6.QtWebEngineCore',
            'PySide6.QtWebEngineWidgets',
            'PySide6.QtWebEngineView',
            'PySide6.QtNetwork',
            'PySide6.QtPrintSupport',
            'PySide6.QtQml',
            'PySide6.QtQuick',
            'PySide6.QtSql',
            # App modules
            'app.panes.base_pane',
            'app.panes.chatgpt',
            'app.panes.claude_pane',
            'app.panes.gemini',
            'app.panes.grok',
            'app.utils.js_loader',
            'app.utils.logging_config',
            'app.utils.error_recovery',
            'app.utils.ocr_utils',
            # Third-party modules
            'difflib',
            'io',
            'base64',
            'time',
            'logging',
            'threading',
            'json',
        ],
        'excludes': [
            'matplotlib',
            'tkinter',
            'unittest',
            'xml',
            'xmlrpc',
            'pydoc',
            'doctest',
            'argparse',
            'test',
            'tests',
            'pygame',
            'scipy',
            'IPython',
            'notebook',
            # OCR-related modules (removed for packaging)
            'cv2',
            'opencv',
            'pytesseract',
            'tesseract',
            'PIL',
            'Pillow',
            'numpy',
            'pyautogui',
        ],
        'qt_plugins': [
            'platforms',
            'imageformats',
            'iconengines',
            'mediaservice',
            'printsupport',
        ],
        'strip': True,
        'optimize': 2,
        'site_packages': True,
        'alias': False,  # Set to True for development builds
        'semi_standalone': False,
        'debug_modulegraph': False,
        'debug_skip_macholib': False,
        'arch': 'universal2',  # Build for both Intel and Apple Silicon
    }
}

if __name__ == '__main__':
    setup(
        name=APP_NAME,
        version=APP_VERSION,
        description="Multi-AI Desktop Chat Application",
        author="Multi-AI Desktop Team",
        author_email="contact@multiai-desktop.com",
        url="https://github.com/your-username/multi-ai-desktop",
        app=[APP_SCRIPT],
        data_files=DATA_FILES,
        options=OPTIONS,
        setup_requires=['py2app'],
        install_requires=[
            'PySide6>=6.4.0',
            'requests>=2.28.0',
        ],
    ) 