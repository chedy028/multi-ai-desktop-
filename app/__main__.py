import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSplitter, QTextEdit, QPushButton
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt, Signal
from .panes.chatgpt import ChatGPTPane
# from .panes.gemini  import GeminiPane # This line will be removed
from app.panes.base_pane import BasePane

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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-AI Desk")

        # GeminiPane and GrokPane are defined locally in this file
        self.panes = [ChatGPTPane(), GeminiPane(), GrokPane()]
        splitter   = QSplitter(Qt.Horizontal)
        for p in self.panes: splitter.addWidget(p)

        lay = QVBoxLayout(self)
        lay.addWidget(splitter, 1)

        for pane in self.panes:
            pane.answerReady.connect(lambda text, p=pane: self.display(p, text))

    def display(self, pane, text):
        # Very simple: replace the prompt box with answer.  
        # In production you'd show each answer in the pane footer or a side widget.
        # For now, individual panes will update their own QTextEdit.
        # This function will just print as in the user's example.
        print(f"{pane.__class__.__name__} answered {len(text)} chars: {text[:100]}...")

class GrokPane(BasePane):
    """Pane for interacting with xAI's Grok using QWebEngineView."""
    URL = "https://grok.x.ai"
    JS_INPUT = "textarea[data-testid='tweetTextarea'][placeholder*='What'], textarea[data-testid='tweetTextarea'][placeholder*='Ask']"
    JS_SEND_BUTTON = "button[data-testid='tweetButton'], button[data-testid='sendButton']"
    JS_LAST_REPLY = "article[data-testid='tweet'] div[data-testid='tweetText']"

    def __init__(self, parent=None):
        super().__init__(parent)
        # Note: Grok requires X (Twitter) login, which will happen in the QWebEngineView.
        # Users will need to log in manually within the pane first.
        # The JS selectors might need to be very robust due to X's complex and changing UI.

class GeminiPane(BasePane):
    """Pane for interacting with Google's Gemini using QWebEngineView."""
    URL = "https://gemini.google.com/app"
    JS_INPUT = "div.input-area rich-textarea > div[contenteditable='true']"
    JS_SEND_BUTTON = "button[aria-label='Send message'], button[aria-label='Submit']"
    JS_LAST_REPLY = "message-content div.model-response-text"

    def __init__(self, parent=None):
        super().__init__(parent)
        # All other methods (like send_prompt) are inherited from BasePane.

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1600, 900)
    win.show()
    sys.exit(app.exec()) 