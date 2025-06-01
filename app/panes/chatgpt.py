from app.panes.base_pane import BasePane

class ChatGPTPane(BasePane):
    """Pane for interacting with ChatGPT using QWebEngineView."""
    URL = "https://chat.openai.com"
    JS_INPUT = "#prompt-textarea"
    JS_SEND_BUTTON = "button[data-testid='send-button']"
    JS_LAST_REPLY = "div[data-message-author-role='assistant'] .markdown"

    def __init__(self, parent=None):
        super().__init__(parent)
        # All functionality is inherited from BasePane 