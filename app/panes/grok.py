from app.panes.base_pane import BasePane

class GrokPane(BasePane):
    """Pane for interacting with xAI's Grok using QWebEngineView."""
    
    URL = "https://grok.x.ai"
    JS_INPUT = "div[contenteditable='true'][role='textbox']"
    JS_SEND_BUTTON = "button[aria-label='Send message'], button[aria-label='Submit']"
    JS_LAST_REPLY = "div.message-content"

    def __init__(self, parent=None):
        super().__init__(parent)
        # Note: User must manually log in to X (Twitter) within the pane 