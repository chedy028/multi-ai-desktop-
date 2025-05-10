from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Signal, Qt

class PromptInput(QTextEdit):
    """A text input widget that emits a signal when Enter is pressed without Shift."""
    
    promptReady = Signal(str)  # Signal emitted when Enter is pressed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type your message here... (Shift+Enter for new line)")
        self.setAcceptRichText(False)
        self.setMinimumHeight(50)
        
    def keyPressEvent(self, event):
        """Handle key press events to detect Enter without Shift."""
        if (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            text = self.toPlainText().strip()
            if text:  # Only emit if there's actual text
                self.promptReady.emit(text)
                self.clear()
            event.accept()
        else:
            super().keyPressEvent(event) 