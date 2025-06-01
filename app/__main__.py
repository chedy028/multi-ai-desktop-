import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QSplitter, 
                               QTextEdit, QPushButton, QMainWindow, QHBoxLayout, 
                               QMessageBox, QDockWidget, QTabWidget)
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt, Signal
from app.panes.base_pane import BasePane
from app.panes.chatgpt import ChatGPTPane
from app.panes.gemini import GeminiPane
from app.panes.grok import GrokPane
from app.panes.claude_pane import ClaudePane
from app.widgets.ocr_control import OCRControlWidget
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
        self.setGeometry(100, 100, 1800, 800)  # Increased width for OCR panel

        # Initialize error recovery manager
        self.error_recovery = ErrorRecoveryManager(self)
        self.error_recovery.networkErrorOccurred.connect(self._handle_network_error)
        self.error_recovery.paneErrorOccurred.connect(self._handle_pane_error)
        self.error_recovery.recoveryAttempted.connect(self._handle_recovery_attempt)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create main splitter for AI panes
        self.ai_splitter = QSplitter(Qt.Orientation.Horizontal)
        
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

        # Create OCR control panel
        self.setup_ocr_panel()

        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.ai_splitter)
        main_splitter.addWidget(self.ocr_dock_widget)
        
        # Set sizes: 80% for AI panes, 20% for OCR panel
        main_splitter.setSizes([1440, 360])
        main_layout.addWidget(main_splitter)

        # Connect signals with error handling
        try:
            self._connect_pane_signals(self.chatgpt_pane)
            self._connect_pane_signals(self.grok_pane)
            self._connect_pane_signals(self.gemini_pane)
            self._connect_pane_signals(self.claude_pane)
            logger.info("All pane signals connected successfully")
        except Exception as e:
            logger.error(f"Error connecting pane signals: {str(e)}", exc_info=True)

        # Set initial OCR target to first pane
        self.current_pane = self.chatgpt_pane
        self.ocr_control.set_target_widget(self.current_pane)

    def setup_ocr_panel(self):
        """Set up the OCR control panel."""
        try:
            # Create OCR control widget
            self.ocr_control = OCRControlWidget()
            
            # Create a dock widget for the OCR controls
            self.ocr_dock_widget = QWidget()
            ocr_layout = QVBoxLayout(self.ocr_dock_widget)
            
            # Add pane selection buttons
            pane_selection_widget = QWidget()
            pane_layout = QVBoxLayout(pane_selection_widget)
            
            # Title for pane selection
            from PySide6.QtWidgets import QLabel
            from PySide6.QtGui import QFont
            pane_title = QLabel("Select Target Pane")
            pane_title_font = QFont()
            pane_title_font.setBold(True)
            pane_title.setFont(pane_title_font)
            pane_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pane_layout.addWidget(pane_title)
            
            # Pane selection buttons
            self.chatgpt_button = QPushButton("ChatGPT")
            self.chatgpt_button.setCheckable(True)
            self.chatgpt_button.setChecked(True)  # Default selection
            self.chatgpt_button.clicked.connect(lambda: self.select_pane(self.chatgpt_pane, self.chatgpt_button))
            pane_layout.addWidget(self.chatgpt_button)
            
            self.grok_button = QPushButton("Grok")
            self.grok_button.setCheckable(True)
            self.grok_button.clicked.connect(lambda: self.select_pane(self.grok_pane, self.grok_button))
            pane_layout.addWidget(self.grok_button)
            
            self.gemini_button = QPushButton("Gemini")
            self.gemini_button.setCheckable(True)
            self.gemini_button.clicked.connect(lambda: self.select_pane(self.gemini_pane, self.gemini_button))
            pane_layout.addWidget(self.gemini_button)
            
            self.claude_button = QPushButton("Claude")
            self.claude_button.setCheckable(True)
            self.claude_button.clicked.connect(lambda: self.select_pane(self.claude_pane, self.claude_button))
            pane_layout.addWidget(self.claude_button)
            
            # Store buttons for easy access
            self.pane_buttons = [self.chatgpt_button, self.grok_button, self.gemini_button, self.claude_button]
            
            ocr_layout.addWidget(pane_selection_widget)
            
            # Add separator
            from PySide6.QtWidgets import QFrame
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            ocr_layout.addWidget(separator)
            
            # Add OCR control widget
            ocr_layout.addWidget(self.ocr_control)
            
            # Add stretch to push everything to top
            ocr_layout.addStretch()
            
            logger.info("OCR control panel created successfully")
            
        except Exception as e:
            logger.error(f"Error creating OCR panel: {str(e)}", exc_info=True)
            # Create a simple fallback widget
            self.ocr_dock_widget = QWidget()
            fallback_layout = QVBoxLayout(self.ocr_dock_widget)
            fallback_layout.addWidget(QLabel(f"OCR Panel Error: {str(e)}"))

    def select_pane(self, pane, button):
        """Select a pane as the OCR target."""
        try:
            # Update button states
            for btn in self.pane_buttons:
                btn.setChecked(False)
            button.setChecked(True)
            
            # Set the target pane
            self.current_pane = pane
            self.ocr_control.set_target_widget(pane)
            
            logger.info(f"OCR target set to: {pane.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Error selecting pane: {str(e)}", exc_info=True)

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