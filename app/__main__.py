import sys
import os
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QSplitter, 
                               QTextEdit, QPushButton, QMainWindow, QHBoxLayout, 
                               QMessageBox)
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWebEngineCore import QWebEngineSettings
from app.panes.base_pane import BasePane
from app.panes.chatgpt import ChatGPTPane
from app.panes.gemini import GeminiPane
from app.panes.grok import GrokPane
from app.panes.claude_pane import ClaudePane
from app.utils.logging_config import setup_logging, get_logger
from app.utils.error_recovery import ErrorRecoveryManager

# Initialize logging system
setup_logging(log_level="INFO", log_to_file=True, log_to_console=True)
logger = get_logger(__name__)

class PromptInput(QTextEdit):
    """A QTextEdit that emits a signal when Enter is pressed (without Shift)."""
    returnPressedSignal = Signal() # Custom signal

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if not (event.modifiers() & Qt.ShiftModifier): # If Shift is NOT pressed
                self.returnPressedSignal.emit()
                event.accept() # Consume the event, don't insert newline
                return
        super().keyPressEvent(event) # Default behavior for other keys or Shift+Enter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing Multi-AI Desktop application")
        
        self.setWindowTitle("Multi-AI Chat - ChatGPT | Grok | Gemini | Claude")
        self.setGeometry(100, 100, 1600, 800)  # Adjusted width since no OCR panel

        # Initialize error recovery manager
        self.error_recovery = ErrorRecoveryManager(self)
        self.error_recovery.networkErrorOccurred.connect(self._handle_network_error)
        self.error_recovery.paneErrorOccurred.connect(self._handle_pane_error)
        self.error_recovery.recoveryAttempted.connect(self._handle_recovery_attempt)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for maximum space
        main_layout.setSpacing(0)  # Remove spacing between panes

        # Create main splitter for AI panes
        self.ai_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.ai_splitter.setHandleWidth(1)  # Minimal splitter handle width
        
        # Create panes with error handling
        try:
            self.chatgpt_pane = ChatGPTPane()
            self.gemini_pane = GeminiPane()
            self.grok_pane = GrokPane()
            self.claude_pane = ClaudePane()
            logger.info("All AI panes created successfully")
        except Exception as e:
            logger.error(f"Error creating AI panes: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Initialization Error", 
                               f"Failed to initialize AI panes: {str(e)}")
            return

        # Add panes to splitter
        self.ai_splitter.addWidget(self.chatgpt_pane)
        self.ai_splitter.addWidget(self.grok_pane)
        self.ai_splitter.addWidget(self.gemini_pane)
        self.ai_splitter.addWidget(self.claude_pane)

        # Set initial sizes (4 equal panes)
        self.ai_splitter.setSizes([400, 400, 400, 400])

        # Add the AI splitter directly to main layout (no OCR panel)
        main_layout.addWidget(self.ai_splitter)

        # Connect signals with error handling
        try:
            self._connect_pane_signals(self.chatgpt_pane)
            self._connect_pane_signals(self.grok_pane)
            self._connect_pane_signals(self.gemini_pane)
            self._connect_pane_signals(self.claude_pane)
            logger.info("All pane signals connected successfully")
        except Exception as e:
            logger.error(f"Error connecting pane signals: {str(e)}", exc_info=True)
        
        # Test bridge connections after a delay to ensure everything is initialized
        QTimer.singleShot(3000, self._test_all_bridges)  # Test after 3 seconds

    def _connect_pane_signals(self, pane):
        """Connect all signals for a pane."""
        try:
            pane.promptSubmitted.connect(self.on_prompt_submitted)
            pane.errorOccurred.connect(self.on_error_occurred)
            pane.answerReady.connect(self.on_answer_received)
            pane.userInputDetectedInPane.connect(self.on_pane_user_input)
            
            # Also connect the new inputDetected signal if it exists
            if hasattr(pane, 'inputDetected'):
                pane.inputDetected.connect(self.on_input_detected)
            
            logger.debug(f"Connected signals for {pane.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error connecting signals for {pane.__class__.__name__}: {str(e)}")

    def on_prompt_submitted(self, prompt):
        """Handle prompt submission from any pane."""
        sender = self.sender()
        logger.info(f"Prompt submitted from {sender.__class__.__name__}: {len(prompt)} characters")
        
        try:
            # Forward to other panes
            if sender != self.chatgpt_pane:
                self.chatgpt_pane.send_prompt(prompt, programmatic=True)
            if sender != self.gemini_pane:
                self.gemini_pane.send_prompt(prompt, programmatic=True)
            if sender != self.grok_pane:
                self.grok_pane.send_prompt(prompt, programmatic=True)
            if sender != self.claude_pane:
                self.claude_pane.send_prompt(prompt, programmatic=True)
        except Exception as e:
            logger.error(f"Error forwarding prompt: {str(e)}", exc_info=True)

    def on_error_occurred(self, error_message):
        """Handle errors from any pane."""
        sender = self.sender()
        logger.error(f"Error in {sender.__class__.__name__}: {error_message}")
        
        # Use error recovery manager for better handling
        self.error_recovery.handle_pane_load_error(
            sender.__class__.__name__, 
            getattr(sender, 'URL', 'unknown'), 
            Exception(error_message)
        )

    def on_answer_received(self, answer):
        """Handle answers from any pane."""
        sender = self.sender()
        logger.info(f"{sender.__class__.__name__} response received: {len(answer)} characters")

    def on_pane_user_input(self, text, originating_pane):
        """Handle user input from any pane and distribute to others."""
        logger.info(f"🔥 USER INPUT DETECTED! Pane: {originating_pane.__class__.__name__}, Text: '{text}' ({len(text)} chars)")
        
        try:
            distributed_to = []
            for pane in [self.chatgpt_pane, self.gemini_pane, self.grok_pane, self.claude_pane]:
                if pane is not originating_pane:  # Don't update the pane that sourced the text
                    # Use the new sync_input_to_pane method for better compatibility
                    pane.sync_input_to_pane(text)
                    distributed_to.append(pane.__class__.__name__)
            
            logger.info(f"✅ Text distributed to: {', '.join(distributed_to)}")
        except Exception as e:
            logger.error(f"❌ Error distributing user input: {str(e)}", exc_info=True)

    def on_input_detected(self, pane_name, text):
        """Handle input detected from polling system."""
        logger.info(f"🔥 INPUT DETECTED VIA POLLING! Pane: {pane_name}, Text: '{text}' ({len(text)} chars)")
        
        # Find the originating pane
        originating_pane = None
        for pane in [self.chatgpt_pane, self.gemini_pane, self.grok_pane, self.claude_pane]:
            if pane.__class__.__name__ == pane_name:
                originating_pane = pane
                break
        
        if originating_pane:
            # Use the same distribution logic
            self.on_pane_user_input(text, originating_pane)
        else:
            logger.error(f"Could not find originating pane for {pane_name}")

    def _handle_network_error(self, url: str, error_message: str):
        """Handle network error signals from error recovery manager."""
        logger.warning(f"Network error handled: {url} - {error_message}")

    def _handle_pane_error(self, pane_name: str, error_message: str):
        """Handle pane error signals from error recovery manager."""
        logger.warning(f"Pane error handled: {pane_name} - {error_message}")

    def _handle_recovery_attempt(self, operation: str, success: bool):
        """Handle recovery attempt signals from error recovery manager."""
        if success:
            logger.info(f"Recovery successful for: {operation}")
        else:
            logger.warning(f"Recovery failed for: {operation}")

    def _test_all_bridges(self):
        """Test all bridge connections."""
        logger.info("Testing all bridge connections...")
        try:
            self.chatgpt_pane.test_bridge_connection()
            self.grok_pane.test_bridge_connection() 
            self.gemini_pane.test_bridge_connection()
            self.claude_pane.test_bridge_connection()
        except Exception as e:
            logger.error(f"Error testing bridges: {str(e)}", exc_info=True)

    def closeEvent(self, event):
        """Handle application close event."""
        logger.info("Application closing")
        try:
            # Clean up resources
            if hasattr(self, 'error_recovery'):
                # Stop any pending recovery timers
                for timer in self.error_recovery.recovery_timers.values():
                    timer.stop()
            
            # Accept the close event
            event.accept()
        except Exception as e:
            logger.error(f"Error during application shutdown: {str(e)}", exc_info=True)
            event.accept()  # Still close the application

if __name__ == "__main__":
    try:
        # Set Chrome flags for running as root in Docker
        # Note: Removed --disable-gpu to allow WebGL for Grok compatibility
        os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', 
                              '--no-sandbox --disable-dev-shm-usage')
        
        app = QApplication(sys.argv)
        logger.info("QApplication created")
        
        # Additional WebEngine settings for Docker
        try:
            from PySide6.QtWebEngineCore import QWebEngineSettings
            QWebEngineSettings.globalSettings().setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            QWebEngineSettings.globalSettings().setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            logger.info("WebEngine settings configured for Docker")
        except Exception as e:
            logger.warning(f"Could not configure WebEngine settings: {str(e)}")
        
        win = MainWindow()
        win.show()
        logger.info("Main window shown")
        
        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}", exc_info=True)
        sys.exit(1) 