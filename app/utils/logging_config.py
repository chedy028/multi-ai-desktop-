"""
Centralized logging configuration for Multi-AI Desktop application.
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

class MultiAILogger:
    """Centralized logger configuration for the Multi-AI Desktop application."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.setup_logging()
            MultiAILogger._initialized = True
    
    def setup_logging(self, 
                     log_level: str = "INFO",
                     log_to_file: bool = True,
                     log_to_console: bool = True,
                     max_file_size: int = 10 * 1024 * 1024,  # 10MB
                     backup_count: int = 5):
        """
        Setup centralized logging configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Whether to log to file
            log_to_console: Whether to log to console
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
        """
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if log_to_file:
            log_file = log_dir / "multi_ai_desktop.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Create specific loggers for different components
        self._setup_component_loggers()
        
        logging.info("Multi-AI Desktop logging system initialized")
    
    def _setup_component_loggers(self):
        """Setup specific loggers for different application components."""
        # Base pane logger
        base_pane_logger = logging.getLogger('app.panes.base_pane')
        
        # Individual pane loggers
        chatgpt_logger = logging.getLogger('app.panes.chatgpt')
        gemini_logger = logging.getLogger('app.panes.gemini')
        grok_logger = logging.getLogger('app.panes.grok')
        claude_logger = logging.getLogger('app.panes.claude')
        
        # Utility loggers
        ocr_logger = logging.getLogger('app.utils.ocr_utils')
        
        # Main application logger
        main_logger = logging.getLogger('app.main')
        
        # JavaScript bridge logger
        js_bridge_logger = logging.getLogger('app.js_bridge')
        
        # Network/connectivity logger
        network_logger = logging.getLogger('app.network')
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get a logger instance for the specified name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Logger instance
        """
        return logging.getLogger(name)
    
    @staticmethod
    def log_exception(logger: logging.Logger, message: str, exc_info: bool = True):
        """
        Log an exception with full traceback.
        
        Args:
            logger: Logger instance
            message: Error message
            exc_info: Whether to include exception info
        """
        logger.error(message, exc_info=exc_info)
    
    @staticmethod
    def log_network_error(logger: logging.Logger, url: str, error: Exception):
        """
        Log network-related errors with context.
        
        Args:
            logger: Logger instance
            url: URL that failed
            error: Exception that occurred
        """
        logger.error(f"Network error accessing {url}: {str(error)}", exc_info=True)
    
    @staticmethod
    def log_js_bridge_event(logger: logging.Logger, pane_name: str, event: str, details: str = ""):
        """
        Log JavaScript bridge events.
        
        Args:
            logger: Logger instance
            pane_name: Name of the pane
            event: Event type
            details: Additional details
        """
        logger.debug(f"JS Bridge [{pane_name}] - {event}: {details}")

# Convenience function for easy import
def setup_logging(**kwargs):
    """Setup logging with optional parameters."""
    MultiAILogger().setup_logging(**kwargs)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return MultiAILogger.get_logger(name) 