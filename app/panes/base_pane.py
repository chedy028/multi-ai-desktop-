import os # For path joining
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtCore import Signal, QUrl, Slot, QStandardPaths
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

class BasePane(QWebEngineView):
    """Base class for AI model panes in the Multi-AI Desk."""
    
    answerReady = Signal(str)  # Signal emitted when an answer is received
    
    URL: str = ""
    JS_INPUT: str = ""
    JS_SEND_BUTTON: str = ""
    JS_LAST_REPLY: str = ""

    # Class variable to store unique profile names
    _profile_name_counters = {}

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        if not self.URL: 
            raise NotImplementedError("Subclasses must define a URL and it cannot be empty.")

        # Create or get a unique profile for this pane instance or type
        # This helps keep session data separate for each AI service if they were to conflict
        # or if you want to manage data for each pane type distinctly.
        pane_type_name = self.__class__.__name__
        if pane_type_name not in BasePane._profile_name_counters:
            BasePane._profile_name_counters[pane_type_name] = 0
        BasePane._profile_name_counters[pane_type_name] += 1
        profile_name = f"{pane_type_name}_Profile_{BasePane._profile_name_counters[pane_type_name]}"

        # Use a standard location for persistent data
        data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        if not data_path:
            # Fallback if AppLocalDataLocation isn't available (should be rare)
            data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
        
        profile_storage_path = os.path.join(data_path, "MultiAIDesk", profile_name)
        
        # Ensure the directory exists
        os.makedirs(profile_storage_path, exist_ok=True)

        # Get the profile. If it exists with the name, it's loaded; otherwise, created.
        # However, QWebEngineProfile instances are managed by Qt and are not singletons by name in the same way
        # as defaultProfile(). We need to manage them if we want truly separate named profiles beyond default.
        # For simplicity and robustness, let's use named profiles based on the class name but still manage storage path.

        # If a profile with this name already exists, it might be reused by Qt under the hood
        # if not offTheRecord. For true persistence, we need to point it to a storage path.
        self.profile = QWebEngineProfile(profile_name, self) # Give it a name, parent it to self
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskCache)
        self.profile.setPersistentStoragePath(profile_storage_path)
        
        # Create a QWebEnginePage with this profile
        page = QWebEnginePage(self.profile, self)
        self.setPage(page)
        
        self.load(QUrl(self.URL))

    def setup_ui(self):
        """Set up the UI for displaying the answer."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0) # Panes are tight in a splitter
        self.answer_display = QTextEdit()
        self.answer_display.setReadOnly(True)
        self.answer_display.setPlaceholderText(f"{self.__class__.__name__} response will appear here.")
        layout.addWidget(self.answer_display)

    @Slot(str)
    def send_prompt(self, text: str):
        """Send a prompt to the AI and get a response. To be implemented by subclasses."""
        # Ensure text is properly escaped for JavaScript template literal 
        # and to prevent XSS if text were directly embedded in HTML (though here it's in a JS string value)
        escaped_text = text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

        # Validate selectors are defined
        if not self.JS_INPUT:
            self.answerReady.emit(f"{self.__class__.__name__} Error: JS_INPUT selector is not defined.")
            return
        if not self.JS_SEND_BUTTON:
            self.answerReady.emit(f"{self.__class__.__name__} Error: JS_SEND_BUTTON selector is not defined.")
            return
        if not self.JS_LAST_REPLY:
            self.answerReady.emit(f"{self.__class__.__name__} Error: JS_LAST_REPLY selector is not defined.")
            return

        js = f"""
        (async () => {{
           const box = document.querySelector("{self.JS_INPUT}");
           const btn = document.querySelector("{self.JS_SEND_BUTTON}");

           if (!box) {{
               return Promise.reject(`Element not found with selector (JS_INPUT): {self.JS_INPUT}`);
           }}
           if (!btn) {{
               return Promise.reject(`Element not found with selector (JS_SEND_BUTTON): {self.JS_SEND_BUTTON}`);
           }}

           box.value = `{escaped_text}`;
           // Dispatch events to make sure the site's JS framework (React, Vue, etc.) recognizes the change
           box.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));
           box.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
           // Some sites might need a slight delay or focus for the value to register properly before click
           // box.focus();
           // await new Promise(resolve => setTimeout(resolve, 50)); 

           btn.click();

           const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
           let prevText = '', stableCount = 0, currentText = '';
           const STABILITY_CHECKS = 4; 
           const CHECK_INTERVAL_MS = 500;
           let totalWaitTime = 0;
           const MAX_WAIT_TIME_MS = 60000; // Max 60 seconds

           console.log(`{self.__class__.__name__}: Waiting for reply stabilization...`);

           while (stableCount < STABILITY_CHECKS && totalWaitTime < MAX_WAIT_TIME_MS) {{
              await sleep(CHECK_INTERVAL_MS);
              totalWaitTime += CHECK_INTERVAL_MS;
              
              const replyElements = Array.from(document.querySelectorAll("{self.JS_LAST_REPLY}"));
              const lastElement = replyElements.length > 0 ? replyElements[replyElements.length - 1] : null;
              
              if (!lastElement) {{
                  // console.log(`{self.__class__.__name__}: JS_LAST_REPLY ('{self.JS_LAST_REPLY}') not found yet.`);
                  stableCount = 0; // Reset stability if element disappears
                  prevText = '';   // and reset previous text
                  continue;
              }}
              
              currentText = (lastElement.innerText || lastElement.textContent || "").trim();
              // console.log(`{self.__class__.__name__}: Check - Prev: '${'{prevText.substring(0,20)}'}...', Curr: '${'{currentText.substring(0,20)}'}...'`);

              if (currentText === prevText && currentText !== '') {{
                  stableCount++;
                  // console.log(`{self.__class__.__name__}: Stable count: ${'{stableCount}'}`);
              }} else {{
                  prevText = currentText;
                  stableCount = 0;
                  // console.log(`{self.__class__.__name__}: Text changed or empty. Resetting stable count.`);
              }}
           }}

           if (stableCount < STABILITY_CHECKS) {{
               const errorMessage = `Response did not stabilize for {self.__class__.__name__} within ${'{MAX_WAIT_TIME_MS / 1000}'}s. Last text: '${'{prevText.substring(0, 100)}'}...'`;
               console.error(errorMessage);
               return Promise.reject(errorMessage);
           }}
           console.log(`{self.__class__.__name__}: Reply stabilized: '${'{prevText.substring(0,100)}'}...'`);
           return prevText;
        }})()
        """

        def js_callback(result_or_error):
            if self.page().url().toString() == "about:blank": # Page might have been destroyed
                print(f"{self.__class__.__name__}: Page was destroyed, cannot emit result.")
                return

            if isinstance(result_or_error, str):
                self.answerReady.emit(result_or_error)
            else: # It's likely a JavaScript error (None, bool, number, or dict if parsing failed before reject)
                error_message = f"{self.__class__.__name__} JS Error: {str(result_or_error)}"
                print(error_message)
                self.answerReady.emit(error_message)

        self.page().runJavaScript(js, 0, js_callback) # Added worldId = 0 for isolated world

    def clear_response(self):
        """Clear the displayed response."""
        self.answer_display.clear()
       