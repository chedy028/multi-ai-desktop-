"""
JavaScript file loader and manager for Multi-AI Desktop application.
"""
import os
from pathlib import Path
from typing import Dict, Optional
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class JSLoader:
    """Manages loading and caching of JavaScript files."""
    
    _instance = None
    _js_cache: Dict[str, str] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.js_dir = Path(__file__).parent.parent / "js"
        if not self.js_dir.exists():
            logger.warning(f"JavaScript directory not found: {self.js_dir}")
    
    def load_js_file(self, filename: str) -> Optional[str]:
        """
        Load a JavaScript file and return its content.
        
        Args:
            filename: Name of the JavaScript file (with or without .js extension)
            
        Returns:
            JavaScript content as string, or None if file not found
        """
        if not filename.endswith('.js'):
            filename += '.js'
        
        # Check cache first
        if filename in self._js_cache:
            logger.debug(f"Loading {filename} from cache")
            return self._js_cache[filename]
        
        js_file_path = self.js_dir / filename
        
        try:
            with open(js_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._js_cache[filename] = content
                logger.debug(f"Loaded JavaScript file: {filename}")
                return content
        except FileNotFoundError:
            logger.error(f"JavaScript file not found: {js_file_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading JavaScript file {filename}: {str(e)}")
            return None
    
    def get_input_listener_js(self, pane_name: str, input_selector: str) -> str:
        """
        Get the input listener JavaScript with configuration.
        
        Args:
            pane_name: Name of the pane
            input_selector: CSS selector for the input element
            
        Returns:
            Configured JavaScript code
        """
        js_content = self.load_js_file('input_listener.js')
        if js_content is None:
            logger.error("Failed to load input_listener.js")
            return ""
        
        # Inject configuration
        config_js = f"""
        window.paneConfig = {{
            paneName: "{pane_name}",
            inputSelector: {repr(input_selector)}
        }};
        """
        
        return config_js + js_content
    
    def get_multi_selector_listener_js(self, pane_name: str, input_selectors: list, enable_dom_inspection: bool = False) -> str:
        """
        Get the multi-selector input listener JavaScript with configuration.
        
        Args:
            pane_name: Name of the pane
            input_selectors: List of CSS selectors to try
            enable_dom_inspection: Whether to enable DOM inspection logging
            
        Returns:
            Configured JavaScript code
        """
        js_content = self.load_js_file('multi_selector_listener.js')
        if js_content is None:
            logger.error("Failed to load multi_selector_listener.js")
            return ""
        
        # Inject configuration
        config_js = f"""
        window.paneConfig = {{
            paneName: "{pane_name}",
            inputSelectors: {repr(input_selectors)},
            enableDOMInspection: {str(enable_dom_inspection).lower()}
        }};
        """
        
        return config_js + js_content
    
    def get_set_external_text_js(self, pane_name: str, input_selector: str, text: str) -> str:
        """
        Get the setExternalText JavaScript with configuration.
        
        Args:
            pane_name: Name of the pane
            input_selector: CSS selector for the input element
            text: Text to set
            
        Returns:
            Configured JavaScript code
        """
        js_content = self.load_js_file('set_external_text.js')
        if js_content is None:
            logger.error("Failed to load set_external_text.js")
            return ""
        
        # Inject configuration
        config_js = f"""
        window.paneConfig = {{
            paneName: "{pane_name}",
            inputSelector: {repr(input_selector)},
            textToSet: {repr(text)}
        }};
        """
        
        return config_js + js_content
    
    def clear_cache(self):
        """Clear the JavaScript file cache."""
        self._js_cache.clear()
        logger.info("JavaScript cache cleared")

# Singleton instance
js_loader = JSLoader() 