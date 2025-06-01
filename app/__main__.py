import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSplitter, QTextEdit, QPushButton, QMainWindow, QHBoxLayout, QMessageBox
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt, Signal
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
        self.setGeometry(100, 100, 1600, 800)  # Increased width to accommodate 4 panes

        # Initialize error recovery manager
        self.error_recovery = ErrorRecoveryManager(self)
        self.error_recovery.networkErrorOccurred.connect(self._handle_network_error)
        self.error_recovery.paneErrorOccurred.connect(self._handle_pane_error)
        self.error_recovery.recoveryAttempted.connect(self._handle_recovery_attempt)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panes
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

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
        splitter.addWidget(self.chatgpt_pane)
        splitter.addWidget(self.grok_pane)
        splitter.addWidget(self.gemini_pane)
        splitter.addWidget(self.claude_pane)

        # Set initial sizes (4 equal panes)
        splitter.setSizes([400, 400, 400, 400])

        # Connect signals with error handling
        try:
            self._connect_pane_signals(self.chatgpt_pane)
            self._connect_pane_signals(self.grok_pane)
            self._connect_pane_signals(self.gemini_pane)
            self._connect_pane_signals(self.claude_pane)
            logger.info("All pane signals connected successfully")
        except Exception as e:
            logger.error(f"Error connecting pane signals: {str(e)}", exc_info=True)

    def _connect_pane_signals(self, pane):
        """Connect all signals for a pane."""
        try:
            pane.promptSubmitted.connect(self.on_prompt_submitted)
            pane.errorOccurred.connect(self.on_error_occurred)
            pane.answerReady.connect(self.on_answer_received)
            pane.userInputDetectedInPane.connect(self.on_pane_user_input)
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
        logger.debug(f"User input detected in {originating_pane.__class__.__name__}: {len(text)} characters")
        
        try:
            for pane in [self.chatgpt_pane, self.gemini_pane, self.grok_pane, self.claude_pane]:
                if pane is not originating_pane:  # Don't update the pane that sourced the text
                    pane.setExternalText(text)
        except Exception as e:
            logger.error(f"Error distributing user input: {str(e)}", exc_info=True)

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
        app = QApplication(sys.argv)
        logger.info("QApplication created")
        
        win = MainWindow()
        win.show()
        logger.info("Main window shown")
        
        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}", exc_info=True)
        sys.exit(1) 