from app.panes.base_pane import BasePane

class GeminiPane(BasePane):
    """Pane for interacting with Google's Gemini using QWebEngineView."""
    
    URL = "https://gemini.google.com/app"
    JS_INPUT = "div.input-area rich-textarea > div[contenteditable='true']"
    JS_SEND_BUTTON = "button[aria-label='Send message'], button[aria-label='Submit']"
    JS_LAST_REPLY = "div.model-response-text"

    def __init__(self, parent=None):
        super().__init__(parent)
        # Note: User must manually log in to Google within the pane 