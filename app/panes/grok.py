from app.panes.base_pane import BasePane

class GrokPane(BasePane):
    """Pane for interacting with xAI's Grok using QWebEngineView."""
    
    URL = "https://grok.x.ai"
    JS_INPUT = ('body > div.flex.w-full.h-full > div > main > '
                'div.flex.flex-col.items-center.w-full.h-full.p-2.mx-auto.justify-center' 
                '.\\@sm\\:p-4.\\@sm\\:gap-9.\\@xl\\:w-4\\/5.isolate > div > ' 
                'div.absolute.bottom-0.mx-auto.inset-x-0.max-w-\\[51rem\\]' 
                '.\\@sm\\:relative.flex.flex-col.items-center.w-full.gap-1' 
                '.\\@sm\\:gap-5.\\@sm\\:bottom-auto.\\@sm\\:inset-x-auto.\\@sm\\:max-w-full > div > ' 
                'form > div > div > div.relative.z-10 > textarea')
    JS_SEND_BUTTON = "button[type='submit']"
    JS_LAST_REPLY = "div.message-content"

    def __init__(self, parent=None):
        super().__init__(parent)
        # Note: User must manually log in to X (Twitter) within the pane 

print(f"GROK.PY MODULE LOADED. GrokPane.JS_INPUT = '{GrokPane.JS_INPUT}'") # Debug print