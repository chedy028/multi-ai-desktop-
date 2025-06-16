# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get the app directory path
app_path = os.path.join(os.getcwd(), 'app')

# Collect all Qt WebEngine resources
qt_webengine_data = collect_data_files('PySide6.QtWebEngineCore')
qt_webengine_widgets_data = collect_data_files('PySide6.QtWebEngineWidgets')

# Collect JavaScript files
js_files = []
js_dir = os.path.join(app_path, 'js')
if os.path.exists(js_dir):
    for root, dirs, files in os.walk(js_dir):
        for file in files:
            if file.endswith('.js'):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, app_path)
                js_files.append((src_path, os.path.join('app', rel_path)))

# Collect CSS files
css_files = []
styles_dir = os.path.join(app_path, 'styles')
if os.path.exists(styles_dir):
    for root, dirs, files in os.walk(styles_dir):
        for file in files:
            if file.endswith('.css'):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, app_path)
                css_files.append((src_path, os.path.join('app', rel_path)))

# OCR functionality removed for packaging simplification
tesseract_data = []

a = Analysis(
    ['app/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Qt WebEngine files
        *qt_webengine_data,
        *qt_webengine_widgets_data,
        # App-specific files
        *js_files,
        *css_files,
        *tesseract_data,
        # Requirements and configs
        ('requirements.txt', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
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
        'app',
        'app.panes',
        'app.panes.base_pane',
        'app.panes.chatgpt',
        'app.panes.claude_pane',
        'app.panes.gemini',
        'app.panes.grok',
        'app.utils',
        'app.utils.js_loader',
        'app.utils.logging_config',
        'app.utils.error_recovery',
        'app.utils.ocr_utils',
        'app.widgets',
        'app.styles',
        # Third-party modules
        'requests',
        'difflib',
        'io',
        'base64',
        'time',
        'logging',
        'threading',
        'json',
        'os',
        'sys',
        # Standard library modules needed by dependencies
        'xml',
        'xml.etree',
        'xml.etree.ElementTree',
        'xml.parsers',
        'xml.parsers.expat',
        'pkg_resources',
        'setuptools',
        # Additional runtime dependencies
        'importlib',
        'importlib.machinery',
        'importlib.util',
        'zipimport',
        'zipfile',
        'struct',
        'pyimod01_archive',
        'pyimod02_importers',
        'pyimod03_ctypes',
        'pyimod04_pywin32',
        # Shiboken support dependencies
        'argparse',
        'shibokensupport',
        'shibokensupport.signature',
        'shibokensupport.signature.lib',
        'shibokensupport.signature.typing',
        'shibokensupport.signature.mapping',
        'shibokensupport.signature.bootstrap',
        'shibokensupport.signature.loader',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        'hooks/rthook.py',  # Custom runtime hook
    ],
    excludes=[
        'matplotlib',
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'test',
        'tests',
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MultiAI-Desktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/assets/icon.ico' if os.path.exists('app/assets/icon.ico') else None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MultiAI-Desktop',
) 