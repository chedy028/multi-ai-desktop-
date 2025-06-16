import os
import sys
import importlib.machinery
import importlib.util

def _setup_python_path():
    """Setup Python path for the embedded interpreter."""
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_dir = os.path.dirname(sys.executable)
        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        
        # Add the base directory to Python path
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        # Add _internal directory if it exists
        internal_dir = os.path.join(base_dir, '_internal')
        if os.path.exists(internal_dir) and internal_dir not in sys.path:
            sys.path.insert(0, internal_dir)

def _setup_import_hooks():
    """Setup import hooks for the embedded interpreter."""
    if getattr(sys, 'frozen', False):
        # Ensure PyInstaller's import hooks are properly initialized
        if not hasattr(sys, '_pyi_rth_utils'):
            import _pyi_rth_utils
            sys._pyi_rth_utils = _pyi_rth_utils

# Initialize the Python environment
_setup_python_path()
_setup_import_hooks() 