"""
Error recovery and resilience utilities for Multi-AI Desktop application.
"""
import time
import functools
from typing import Callable, Any, Optional, Type, Tuple
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtWidgets import QMessageBox, QWidget
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class NetworkError(Exception):
    """Custom exception for network-related errors."""
    pass

class JSBridgeError(Exception):
    """Custom exception for JavaScript bridge errors."""
    pass

class PaneLoadError(Exception):
    """Custom exception for pane loading errors."""
    pass

def retry_on_failure(max_retries: int = 3, 
                    delay: float = 1.0, 
                    backoff_factor: float = 2.0,
                    exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    Decorator for retrying functions that may fail.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator

class ErrorRecoveryManager(QObject):
    """Manages error recovery and resilience for the application."""
    
    # Signals for error events
    networkErrorOccurred = Signal(str, str)  # url, error_message
    paneErrorOccurred = Signal(str, str)     # pane_name, error_message
    recoveryAttempted = Signal(str, bool)    # operation, success
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent_widget = parent
        self.recovery_timers = {}
        self.error_counts = {}
        self.max_error_threshold = 5
        self.recovery_delay = 5000  # 5 seconds
        
    def handle_network_error(self, url: str, error: Exception, pane_name: str = "Unknown"):
        """
        Handle network-related errors with automatic recovery attempts.
        
        Args:
            url: The URL that failed
            error: The exception that occurred
            pane_name: Name of the pane where error occurred
        """
        error_key = f"network_{pane_name}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        logger.error(f"Network error in {pane_name} accessing {url}: {str(error)}")
        self.networkErrorOccurred.emit(url, str(error))
        
        if self.error_counts[error_key] <= self.max_error_threshold:
            self._schedule_recovery(error_key, lambda: self._recover_network_connection(url, pane_name))
        else:
            self._show_persistent_error_dialog(
                f"Network Error - {pane_name}",
                f"Persistent network issues detected for {pane_name}.\n"
                f"URL: {url}\n"
                f"Error: {str(error)}\n\n"
                f"Please check your internet connection and try reloading the pane manually."
            )
    
    def handle_js_bridge_error(self, pane_name: str, error: Exception):
        """
        Handle JavaScript bridge errors.
        
        Args:
            pane_name: Name of the pane where error occurred
            error: The exception that occurred
        """
        error_key = f"js_bridge_{pane_name}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        logger.error(f"JS Bridge error in {pane_name}: {str(error)}")
        self.paneErrorOccurred.emit(pane_name, f"JavaScript bridge error: {str(error)}")
        
        if self.error_counts[error_key] <= self.max_error_threshold:
            self._schedule_recovery(error_key, lambda: self._recover_js_bridge(pane_name))
    
    def handle_pane_load_error(self, pane_name: str, url: str, error: Exception):
        """
        Handle pane loading errors.
        
        Args:
            pane_name: Name of the pane that failed to load
            url: URL that failed to load
            error: The exception that occurred
        """
        error_key = f"pane_load_{pane_name}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        logger.error(f"Pane load error for {pane_name} at {url}: {str(error)}")
        self.paneErrorOccurred.emit(pane_name, f"Failed to load: {str(error)}")
        
        if self.error_counts[error_key] <= self.max_error_threshold:
            self._schedule_recovery(error_key, lambda: self._recover_pane_load(pane_name, url))
    
    def _schedule_recovery(self, error_key: str, recovery_func: Callable):
        """Schedule a recovery attempt after a delay."""
        if error_key in self.recovery_timers:
            self.recovery_timers[error_key].stop()
        
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._attempt_recovery(error_key, recovery_func))
        timer.start(self.recovery_delay)
        self.recovery_timers[error_key] = timer
        
        logger.info(f"Scheduled recovery for {error_key} in {self.recovery_delay/1000}s")
    
    def _attempt_recovery(self, error_key: str, recovery_func: Callable):
        """Attempt to recover from an error."""
        try:
            logger.info(f"Attempting recovery for {error_key}")
            recovery_func()
            self.error_counts[error_key] = 0  # Reset error count on successful recovery
            self.recoveryAttempted.emit(error_key, True)
            logger.info(f"Recovery successful for {error_key}")
        except Exception as e:
            logger.error(f"Recovery failed for {error_key}: {str(e)}")
            self.recoveryAttempted.emit(error_key, False)
            # Don't schedule another recovery to avoid infinite loops
    
    def _recover_network_connection(self, url: str, pane_name: str):
        """Attempt to recover network connection by reloading the URL."""
        # This would be implemented by the calling pane
        logger.info(f"Attempting network recovery for {pane_name} at {url}")
        # The actual recovery would be handled by the pane itself
        # This is more of a notification/coordination mechanism
    
    def _recover_js_bridge(self, pane_name: str):
        """Attempt to recover JavaScript bridge connection."""
        logger.info(f"Attempting JS bridge recovery for {pane_name}")
        # The actual recovery would be handled by the pane itself
    
    def _recover_pane_load(self, pane_name: str, url: str):
        """Attempt to recover pane loading."""
        logger.info(f"Attempting pane load recovery for {pane_name} at {url}")
        # The actual recovery would be handled by the pane itself
    
    def _show_persistent_error_dialog(self, title: str, message: str):
        """Show an error dialog for persistent issues."""
        if self.parent_widget:
            QMessageBox.warning(
                self.parent_widget,
                title,
                message,
                QMessageBox.StandardButton.Ok
            )
        else:
            logger.critical(f"Persistent error - {title}: {message}")
    
    def reset_error_count(self, error_key: str):
        """Reset error count for a specific error type."""
        if error_key in self.error_counts:
            self.error_counts[error_key] = 0
            logger.info(f"Reset error count for {error_key}")
    
    def get_error_count(self, error_key: str) -> int:
        """Get current error count for a specific error type."""
        return self.error_counts.get(error_key, 0)

class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing cascading failures.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful function execution."""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed function execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

# Convenience functions
def handle_with_recovery(error_manager: ErrorRecoveryManager):
    """Decorator for handling errors with the recovery manager."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Determine error type and handle appropriately
                if "network" in str(e).lower() or "connection" in str(e).lower():
                    error_manager.handle_network_error("unknown", e)
                else:
                    logger.error(f"Unhandled error in {func.__name__}: {str(e)}", exc_info=True)
                raise e
        return wrapper
    return decorator 