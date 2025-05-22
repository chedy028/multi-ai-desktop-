import os # For path joining
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal, QUrl, Slot, QStandardPaths, QObject, QTimer, QFile, QIODevice, QTextStream
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from app.utils.ocr_utils import OCRFinder
import logging

class JsBridge(QObject):
    """Bridge class to handle communication between JavaScript and Python."""
    textEnteredInWebView = Signal(str, str)  # text, pane_identifier

    def __init__(self, pane_identifier, parent=None):
        super().__init__(parent)
        self.pane_identifier = pane_identifier

    @Slot(str)
    def onUserInput(self, text):
        print(f"JsBridge.onUserInput called with text: {text}")  # Debug print
        self.textEnteredInWebView.emit(text, self.pane_identifier)

class BasePane(QWidget):
    """Base class for AI model panes in the Multi-AI Desk."""
    
    answerReady = Signal(str)  # Signal emitted when an answer is received
    promptSubmitted = Signal(str)  # Signal for prompt submissions
    errorOccurred = Signal(str)  # Signal for error reporting
    userInputDetectedInPane = Signal(str, object)  # text, self (originating pane instance)
    
    URL: str = ""
    JS_INPUT: str = ""
    JS_SEND_BUTTON: str = ""
    JS_LAST_REPLY: str = ""

    # Class variable to store unique profile names
    _profile_name_counters = {}
    _qwebchannel_js_content = None # Class variable to hold qwebchannel.js content

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        if not self.URL: 
            raise NotImplementedError("Subclasses must define a URL and it cannot be empty.")

        pane_name = self.__class__.__name__
        print(f"DEBUG PY ({pane_name}): Initializing. Checking _qwebchannel_js_content. Is None? {BasePane._qwebchannel_js_content is None}")

        # Load qwebchannel.js content if not already loaded (happens once across all instances)
        if BasePane._qwebchannel_js_content is None:
            print(f"DEBUG PY ({pane_name}): _qwebchannel_js_content is None. Attempting to load.")
            # Try the alternative resource path
            qfile_path = ":/qtwebchannel/qwebchannel.js"
            qfile = QFile(qfile_path)
            if qfile.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
                stream = QTextStream(qfile)
                BasePane._qwebchannel_js_content = stream.readAll()
                qfile.close()
                if BasePane._qwebchannel_js_content and BasePane._qwebchannel_js_content.strip() != "":
                    print(f"DEBUG PY ({pane_name}): qwebchannel.js loaded successfully from qrc path '{qfile_path}'. Length: {len(BasePane._qwebchannel_js_content)}")
                else:
                    print(f"DEBUG PY ({pane_name}): qwebchannel.js loaded from qrc path '{qfile_path}' but is empty or whitespace.")
                    BasePane._qwebchannel_js_content = "" # Ensure it's an empty string
            else:
                print(f"DEBUG PY ({pane_name}): Error: Could not load qwebchannel.js from qrc path '{qfile_path}'. Error: {qfile.errorString()}")
                BasePane._qwebchannel_js_content = "" # Ensure it's an empty string on failure
        else:
            print(f"DEBUG PY ({pane_name}): _qwebchannel_js_content already processed/loaded. Current content length: {len(BasePane._qwebchannel_js_content) if BasePane._qwebchannel_js_content is not None else 'None'}")

        print(f"DEBUG PY ({pane_name}): Final _qwebchannel_js_content status before JS injection. Is String? {isinstance(BasePane._qwebchannel_js_content, str)}. Length: {len(BasePane._qwebchannel_js_content) if BasePane._qwebchannel_js_content else '0 or None'}")

        # Initialize OCR finder
        self.ocr_finder = OCRFinder()

        # Set up the layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create web view
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

        # Set up profile
        pane_type_name = self.__class__.__name__
        if pane_type_name not in BasePane._profile_name_counters:
            BasePane._profile_name_counters[pane_type_name] = 0
        BasePane._profile_name_counters[pane_type_name] += 1
        profile_name = f"{pane_type_name}_Profile_{BasePane._profile_name_counters[pane_type_name]}"

        data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        if not data_path:
            data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
        
        profile_storage_path = os.path.join(data_path, "MultiAIDesk", profile_name)
        os.makedirs(profile_storage_path, exist_ok=True)

        self.profile = QWebEngineProfile(profile_name, self)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentStoragePath(profile_storage_path)
        
        self.page = QWebEnginePage(self.profile, self)
        self.web_view.setPage(self.page)
        
        # Setup QWebChannel
        self.pane_identifier = self.__class__.__name__
        self.bridge = JsBridge(self.pane_identifier)
        self.channel = QWebChannel(self.page)
        self.page.setWebChannel(self.channel)
        self.channel.registerObject("pyBridge", self.bridge)

        # Connect signals
        self.bridge.textEnteredInWebView.connect(self._handle_text_from_webview)
        self.web_view.loadFinished.connect(self._inject_input_listener_js)
        
        self._is_programmatic_update = False
        self._last_programmatically_set_text = ""

        # Load the URL
        self.web_view.load(QUrl(self.URL))

    @Slot(bool)
    def _inject_input_listener_js(self, ok): # Slot for loadFinished signal
        if not ok:
            logging.error(f"PY ({self.__class__.__name__}): Page load failed.")
            return

        if BasePane._qwebchannel_js_content is None:
            logging.error(f"PY ({self.__class__.__name__}): qwebchannel.js content is not loaded. Cannot inject JS.")
            return

        js_input_selector = getattr(self.__class__, 'JS_INPUT', None)
        if not js_input_selector:
            logging.debug(f"PY ({self.__class__.__name__}): No JS_INPUT selector defined. Skipping input listener injection.")
            return

        # Escape the selector for safe inclusion in the JS string template
        # and then json.dumps for direct use as a JS string literal in querySelector
        js_input_selector_escaped_for_script = json.dumps(js_input_selector)

        # Debugging instance vs class attribute for JS_INPUT
        instance_js_input = self.__dict__.get('JS_INPUT', 'Not in instance __dict__')
        logging.debug(f"DEBUG PY ({self.__class__.__name__} instance in _inject_input_listener_js): Instance id={id(self)}, Class object id={id(self.__class__)}")
        logging.debug(f"DEBUG PY ({self.__class__.__name__} instance in _inject_input_listener_js): JS_INPUT (from self.__class__.JS_INPUT)='{self.__class__.JS_INPUT}'")
        logging.debug(f"DEBUG PY ({self.__class__.__name__} instance in _inject_input_listener_js): self.JS_INPUT (from instance dict if present)='{instance_js_input}'")

        logging.debug(f"PY ({self.__class__.__name__}): Preparing to inject JS. self.JS_INPUT = '{js_input_selector}'")

        script = f"""
            (function() {{ 
                var bridgeInitialized = false;
                var attachAttempts = 0;
                const maxAttachAttempts = 15; // Increased attempts
                const attachInterval = 300; // Slightly increased interval

                function tryAttachListener() {{
                    attachAttempts++;
                    var currentSelector = {js_input_selector_escaped_for_script};
                    // console.log(`JS ({self.__class__.__name__}): Attempting to find input element (Attempt ${{attachAttempts}}/${{maxAttachAttempts}}). Selector: ` + currentSelector);
                    var inputElement = document.querySelector(currentSelector);

                    if (inputElement) {{
                        console.log(`JS ({self.__class__.__name__}): Input listener attached to element:`, inputElement, `using selector: ` + currentSelector);
                        inputElement.addEventListener('input', function(event) {{
                            if (inputElement._isProgrammaticUpdate) {{ // Check for the flag
                                // console.log(`JS ({self.__class__.__name__}): Ignoring programmatic input event on`, inputElement);
                                return; 
                            }}
                            if (window.pyBridge && window.pyBridge.onUserInput) {{
                                let text = '';
                                if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {{
                                    text = inputElement.value;
                                }} else if (inputElement.hasAttribute('contenteditable')) {{
                                    text = inputElement.innerText;
                                }}
                                window.pyBridge.onUserInput(text);
                            }} else {{
                                console.warn('JS ({self.__class__.__name__}): pyBridge or onUserInput not available when input event fired.');
                            }}
                        }});
                        // Add focus/blur for diagnostics if needed in future
                        // inputElement.addEventListener('focus', function() {{ console.log(`JS ({self.__class__.__name__}): Element focused: ` + currentSelector); }});
                        // inputElement.addEventListener('blur', function() {{ console.log(`JS ({self.__class__.__name__}): Element blurred: ` + currentSelector); }});
                    }} else {{
                        if (attachAttempts < maxAttachAttempts) {{
                            // console.warn(`JS ({self.__class__.__name__}): Could not find input element (Attempt ${{attachAttempts}}/${{maxAttachAttempts}}). Retrying in ${{attachInterval}}ms. Selector: ` + currentSelector);
                            setTimeout(tryAttachListener, attachInterval);
                        }} else {{
                            console.error(`JS ({self.__class__.__name__}): Failed to find input element after ${{maxAttachAttempts}} attempts. Selector: ` + currentSelector);
                        }}
                    }}
                }}

                function initWebChannelAndListeners() {{
                    if (typeof QWebChannel === 'undefined' || typeof QWebChannel.constructor !== 'function') {{
                        console.error('JS ({self.__class__.__name__}): QWebChannel is not defined. Cannot establish pyBridge. Input listener WILL NOT WORK.');
                        return; // Stop if QWebChannel is missing
                    }}
                    try {{
                        new QWebChannel(qt.webChannelTransport, function(channel) {{
                            window.pyBridge = channel.objects.pyBridge;
                            bridgeInitialized = true;
                            console.log('JS ({self.__class__.__name__}): pyBridge initialized successfully via QWebChannel.');
                            tryAttachListener(); // Now attempt to attach the input listener
                        }});
                    }} catch (e) {{
                        console.error('JS ({self.__class__.__name__}): Error initializing QWebChannel:', e, '. Input listener WILL NOT WORK.');
                        // If QWebChannel fails, pyBridge won't be set up, so listeners depending on it are moot.
                    }}
                }}
                
                // Check if pyBridge is already available (e.g. from a previous injection or persistent context)
                if (window.pyBridge && window.pyBridge.onUserInput) {{
                    console.log('JS ({self.__class__.__name__}): pyBridge already available. Proceeding to attach listener.');
                    bridgeInitialized = true;
                    tryAttachListener();
                }} else if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                    // console.log('JS ({self.__class__.__name__}): qt.webChannelTransport available. Attempting to initialize QWebChannel.');
                    initWebChannelAndListeners();
                }} else {{
                    // Fallback: try to set up listeners after a delay, hoping transport becomes available
                    // This is less reliable and indicates a potential issue with QWebChannel setup timing.
                    console.warn('JS ({self.__class__.__name__}): qt.webChannelTransport not immediately available. Will retry QWebChannel init and listener attachment. This might indicate a setup issue.');
                    let channelInitAttempts = 0;
                    const maxChannelInitAttempts = 5;
                    const channelInitInterval = 500; // ms
                    function retryInitWebChannel() {{
                        if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                            initWebChannelAndListeners();
                        }} else {{
                            channelInitAttempts++;
                            if (channelInitAttempts < maxChannelInitAttempts) {{
                                // console.warn(`JS ({self.__class__.__name__}): Retrying QWebChannel init (Attempt ${{channelInitAttempts}}/${{maxChannelInitAttempts}})...`);
                                setTimeout(retryInitWebChannel, channelInitInterval);
                            }} else {{
                                console.error('JS ({self.__class__.__name__}): Failed to initialize QWebChannel after multiple attempts. qt.webChannelTransport not found.');
                            }}
                        }}
                    }}
                    retryInitWebChannel();
                }}
            }})();
        """
        self.page.runJavaScript(BasePane._qwebchannel_js_content) # Ensure qwebchannel.js is loaded first
        self.page.runJavaScript(script) # Then run our script that uses it

    def setExternalText(self, text: str, selector: str = None):
        # Determine the correct selector
        js_selector = selector if selector else getattr(self.__class__, 'JS_INPUT', None)
        if not js_selector:
            logging.warning(f"PY ({self.__class__.__name__}): No JS_INPUT selector defined for setExternalText.")
            return

        js_selector_escaped = json.dumps(js_selector)
        js_text_escaped = json.dumps(text)

        script = f"""
            (function() {{
                var currentSelector = {js_selector_escaped};
                var inputElement = document.querySelector(currentSelector);
                if (inputElement) {{
                    // console.log(`JS (setExternalText in {self.__class__.__name__}): Found element:`, inputElement, `for selector: ` + currentSelector + `. Setting text to: {js_text_escaped}`);
                    
                    inputElement._isProgrammaticUpdate = true; // Set flag before changing value

                    var scrollTop = inputElement.scrollTop; // Store scroll position

                    if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {{
                        // console.log(`JS (setExternalText in {self.__class__.__name__}): Handling as TEXTAREA/INPUT for selector: ` + currentSelector);
                        inputElement.focus(); // Focus before setting value
                        inputElement.value = {js_text_escaped};
                        var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                        inputElement.dispatchEvent(inputEvent);
                        var changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                        inputElement.dispatchEvent(changeEvent);
                        // Attempt to dispatch keydown/keyup for Space to further nudge UI
                        var kdEvent = new KeyboardEvent('keydown', {{ 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true }});
                        inputElement.dispatchEvent(kdEvent);
                        var kuEvent = new KeyboardEvent('keyup', {{ 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true }});
                        inputElement.dispatchEvent(kuEvent);
                        // inputElement.blur(); // Keep commented out for now
                    }} else if (inputElement.isContentEditable) {{
                        // console.log(`JS (setExternalText in {self.__class__.__name__}): Handling as contenteditable for selector: ` + currentSelector);
                        inputElement.focus(); // Also ensure focus for contenteditable
                        inputElement.innerText = {js_text_escaped};
                        var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                        inputElement.dispatchEvent(inputEvent);
                        // Also try keydown/keyup for contenteditable
                        var kdEvent = new KeyboardEvent('keydown', {{ 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true }});
                        inputElement.dispatchEvent(kdEvent);
                        var kuEvent = new KeyboardEvent('keyup', {{ 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true }});
                        inputElement.dispatchEvent(kuEvent);
                    }} else {{
                        // Fallback for other types, though less common for our inputs
                        // console.log(`JS (setExternalText in {self.__class__.__name__}): Handling as other (e.g. div, span) for selector: ` + currentSelector);
                        inputElement.textContent = {js_text_escaped};
                    }}
                    
                    inputElement.scrollTop = scrollTop; // Restore scroll position

                    delete inputElement._isProgrammaticUpdate; // Clear flag after dispatching

                }} else {{
                    console.warn(`JS (setExternalText in {self.__class__.__name__}): Could not find input element with selector: ${{currentSelector}}`);
                }}
            }})();
        """
        if self.page:
            self.page.runJavaScript(script)
        else:
            logging.error(f"PY ({self.__class__.__name__}): Page not available for JS execution in setExternalText.")

    def _handle_text_from_webview(self, text: str):
        print(f"BasePane._handle_text_from_webview called with text: {text}")  # Debug print
        if self._is_programmatic_update and text == self._last_programmatically_set_text:
            print("Ignoring programmatic update")  # Debug print
            return
        print(f"Emitting userInputDetectedInPane with text: {text}")  # Debug print
        self.userInputDetectedInPane.emit(text, self)

    def ensure_input_focused(self):
        """Focus the input box using JavaScript to make the placeholder visible for OCR."""
        if not self.JS_INPUT:
            print(f"{self.__class__.__name__} Error: JS_INPUT selector not defined for ensure_input_focused.")
            return
        js = f'''
        (function() {{
            var inp = document.querySelector(`{self.JS_INPUT}`);
            if (inp) {{ inp.focus(); }}
        }})();
        '''
        self.page.runJavaScript(js)
        print("[DEBUG] Ran JS to focus input box.")

    def find_and_click_input(self, target_text: str = "Ask anything") -> bool:
        """
        Find and click the input box using OCR.
        
        Args:
            target_text: The text to look for (default: "Ask anything")
            
        Returns:
            True if successful, False otherwise
        """
        self.ensure_input_focused()
        return self.ocr_finder.click_input_box(self, target_text)

    def find_input_location(self, target_text: str = "Ask anything"):
        """
        Find the location of the input box using OCR.
        
        Args:
            target_text: The text to look for (default: "Ask anything")
            
        Returns:
            Tuple of (x, y, width, height) if found, None otherwise
        """
        self.ensure_input_focused()
        return self.ocr_finder.find_input_box(self, target_text)

    def __del__(self):
        """Clean up resources when the pane is destroyed."""
        try:
            # Disconnect signals
            self.web_view.loadFinished.disconnect()
            self.bridge.textEnteredInWebView.disconnect()
            
            # Clear page
            self.web_view.setPage(None)
            self.page.deleteLater()
            
            # Remove profile reference
            if hasattr(self, 'profile'):
                profile_name = self.profile.name()
                if profile_name in BasePane._profile_name_counters:
                    del BasePane._profile_name_counters[profile_name]
        except:
            pass