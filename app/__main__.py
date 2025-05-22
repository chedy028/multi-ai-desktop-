import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSplitter, QTextEdit, QPushButton, QMainWindow, QHBoxLayout, QMessageBox
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt, Signal
from app.panes.base_pane import BasePane
from app.panes.chatgpt import ChatGPTPane
from app.panes.gemini import GeminiPane
from app.panes.grok import GrokPane

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
        self.setWindowTitle("Multi-AI Chat")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panes
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Create panes
        self.chatgpt_pane = ChatGPTPane()
        self.gemini_pane = GeminiPane()
        self.grok_pane = GrokPane()

        # Add panes to splitter
        splitter.addWidget(self.chatgpt_pane)
        splitter.addWidget(self.gemini_pane)
        splitter.addWidget(self.grok_pane)

        # Set initial sizes
        splitter.setSizes([400, 400, 400])

        # Connect signals
        self._connect_pane_signals(self.chatgpt_pane)
        self._connect_pane_signals(self.gemini_pane)
        self._connect_pane_signals(self.grok_pane)

    def _connect_pane_signals(self, pane):
        """Connect all signals for a pane."""
        pane.promptSubmitted.connect(self.on_prompt_submitted)
        pane.errorOccurred.connect(self.on_error_occurred)
        pane.answerReady.connect(self.on_answer_received)
        pane.userInputDetectedInPane.connect(self.on_pane_user_input)

    def on_prompt_submitted(self, prompt):
        """Handle prompt submission from any pane."""
        sender = self.sender()
        
        # Forward to other panes
        if sender != self.chatgpt_pane:
            self.chatgpt_pane.send_prompt(prompt, programmatic=True)
        if sender != self.gemini_pane:
            self.gemini_pane.send_prompt(prompt, programmatic=True)
        if sender != self.grok_pane:
            self.grok_pane.send_prompt(prompt, programmatic=True)

    def on_error_occurred(self, error_message):
        """Handle errors from any pane."""
        sender = self.sender()
        QMessageBox.warning(
            self,
            f"Error in {sender.__class__.__name__}",
            error_message,
            QMessageBox.StandardButton.Ok
        )

    def on_answer_received(self, answer):
        """Handle answers from any pane."""
        sender = self.sender()
        print(f"{sender.__class__.__name__} response received: {len(answer)} characters")

    def on_pane_user_input(self, text, originating_pane):
        """Handle user input from any pane and distribute to others."""
        for pane in [self.chatgpt_pane, self.gemini_pane, self.grok_pane]:
            if pane is not originating_pane:  # Don't update the pane that sourced the text
                pane.setExternalText(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec()) 