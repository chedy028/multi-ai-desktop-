from app.panes.base_pane import BasePane
from PySide6.QtCore import QTimer, QRect
from PySide6.QtGui import QPixmap
import pytesseract
from PIL import Image
import io

class GrokPane(BasePane):
    """Pane for interacting with xAI's Grok using QWebEngineView with computer vision fallback."""
    
    URL = "https://grok.x.ai"
    # Simplified but comprehensive selectors focusing on logged-in Grok interface
    JS_INPUT_SELECTORS = [
        # Most likely selectors for logged-in Grok (based on modern chat interfaces)
        'textarea[placeholder*="Ask"]',
        'textarea[placeholder*="Message"]',
        'textarea[placeholder*="Type"]',
        'textarea[placeholder*="What"]',
        'div[contenteditable="true"][placeholder*="Ask"]',
        'div[contenteditable="true"][placeholder*="Message"]',
        'div[contenteditable="true"][placeholder*="Type"]',
        'div[contenteditable="true"][placeholder*="What"]',
        # Data-testid patterns
        'textarea[data-testid*="input"]',
        'textarea[data-testid*="prompt"]',
        'textarea[data-testid*="message"]',
        'textarea[data-testid*="composer"]',
        'div[contenteditable="true"][data-testid*="input"]',
        'div[contenteditable="true"][data-testid*="prompt"]',
        'div[contenteditable="true"][data-testid*="message"]',
        'div[contenteditable="true"][data-testid*="composer"]',
        # Form-based (most common pattern)
        'form textarea',
        'form div[contenteditable="true"]',
        'form input[type="text"]',
        # Generic but visible elements
        'textarea:not([style*="display: none"]):not([style*="visibility: hidden"])',
        'div[contenteditable="true"]:not([style*="display: none"]):not([style*="visibility: hidden"])',
        'input[type="text"]:not([style*="display: none"]):not([style*="visibility: hidden"])',
        # Very generic fallbacks
        'textarea',
        'div[contenteditable="true"]',
        '[contenteditable="true"]',
        'input[type="text"]'
    ]
    
    # Use the first selector as default for compatibility
    JS_INPUT = JS_INPUT_SELECTORS[0]
    JS_SEND_BUTTON = "button[type='submit'], button[aria-label*='Send'], button[data-testid*='send']"
    JS_LAST_REPLY = "div.message-content, div[data-testid*='message'], div[data-testid*='response']"

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Computer vision fallback system
        self.cv_enabled = False
        self.cv_timer = QTimer()
        self.cv_timer.timeout.connect(self._check_input_with_cv)
        self.last_ocr_text = ""
        self.js_detection_failed = False
        self.cv_check_interval = 1000  # Check every 1 second
        self.input_area_rect = None  # Will be set based on page layout
        
        # Add callback for JS detection status to the existing bridge
        self.bridge.onJSDetectionStatus = self._on_js_detection_status
        
        print(f"PY (GrokPane): Initialized with computer vision fallback support")

    def _inject_input_listener_js(self, ok):
        """Override with immediate DOM inspection and computer vision fallback."""
        if not ok:
            print(f"PY ({self.__class__.__name__}): Page load failed.")
            return

        if BasePane._qwebchannel_js_content is None:
            print(f"PY ({self.__class__.__name__}): qwebchannel.js content is not loaded. Cannot inject JS.")
            return

        # Create JavaScript with immediate DOM inspection and simplified logic
        selectors_js = str(self.JS_INPUT_SELECTORS)
        
        script = f"""
            (function() {{ 
                var bridgeInitialized = false;
                var isListenerAttached = false;
                var workingSelector = null;
                var jsDetectionFailed = false;
                const selectors = {selectors_js};

                function logDOMState() {{
                    console.log('=== GROK DOM INSPECTION ===');
                    console.log(`URL: ${{window.location.href}}`);
                    console.log(`Title: "${{document.title}}"`);
                    
                    // Find ALL input-like elements
                    var allInputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
                    console.log(`Total input elements found: ${{allInputs.length}}`);
                    
                    allInputs.forEach((el, idx) => {{
                        var rect = el.getBoundingClientRect();
                        var isVisible = rect.width > 0 && rect.height > 0 && 
                                       window.getComputedStyle(el).display !== 'none' &&
                                       window.getComputedStyle(el).visibility !== 'hidden';
                        
                        console.log(`[${{idx}}] ${{el.tagName}} - Visible: ${{isVisible}}`);
                        console.log(`    Placeholder: "${{el.placeholder || ''}}"`);
                        console.log(`    DataTestId: "${{el.getAttribute('data-testid') || ''}}"`);
                        console.log(`    Classes: "${{el.className || ''}}"`);
                        console.log(`    ID: "${{el.id || ''}}"`);
                        console.log(`    ContentEditable: ${{el.contentEditable}}`);
                        console.log(`    Size: ${{rect.width}}x${{rect.height}} at (${{rect.x}}, ${{rect.y}})`);
                        
                        if (el.parentElement) {{
                            console.log(`    Parent: ${{el.parentElement.tagName}} - "${{el.parentElement.className || ''}}"`);
                        }}
                        console.log('    ---');
                    }});
                    
                    // Check forms
                    var forms = document.querySelectorAll('form');
                    console.log(`Forms found: ${{forms.length}}`);
                    forms.forEach((form, idx) => {{
                        var formInputs = form.querySelectorAll('input, textarea, [contenteditable="true"]');
                        console.log(`Form ${{idx}}: ${{formInputs.length}} inputs`);
                    }});
                    
                    console.log('=== END INSPECTION ===');
                }}

                function findAndAttachToInput() {{
                    if (isListenerAttached) {{
                        console.log('JS (Grok): Already attached, skipping');
                        return true;
                    }}
                    
                    console.log('JS (Grok): Starting input search...');
                    logDOMState();
                    
                    // Try each selector
                    for (let i = 0; i < selectors.length; i++) {{
                        var selector = selectors[i];
                        console.log(`JS (Grok): Testing selector ${{i+1}}/${{selectors.length}}: ${{selector}}`);
                        
                        try {{
                            var elements = document.querySelectorAll(selector);
                            console.log(`JS (Grok): Found ${{elements.length}} elements with this selector`);
                            
                            for (let j = 0; j < elements.length; j++) {{
                                var el = elements[j];
                                var rect = el.getBoundingClientRect();
                                var isVisible = rect.width > 0 && rect.height > 0 && 
                                               window.getComputedStyle(el).display !== 'none' &&
                                               window.getComputedStyle(el).visibility !== 'hidden';
                                
                                console.log(`JS (Grok): Element ${{j}}: Visible=${{isVisible}}, Size=${{rect.width}}x${{rect.height}}`);
                                
                                if (isVisible) {{
                                    console.log(`JS (Grok): SUCCESS! Attaching to visible element with selector: ${{selector}}`);
                                    console.log(`JS (Grok): Element details:`, el);
                                    
                                    // Attach event listeners
                                    ['input', 'keyup', 'paste', 'change'].forEach(eventType => {{
                                        el.addEventListener(eventType, function(event) {{
                                            if (el._isProgrammaticUpdate) {{
                                                return; 
                                            }}
                                            if (window.pyBridge && window.pyBridge.onUserInput) {{
                                                let text = '';
                                                if (el.tagName === 'TEXTAREA' || (el.tagName === 'INPUT' && el.type === 'text')) {{
                                                    text = el.value;
                                                }} else if (el.contentEditable === 'true') {{
                                                    text = el.innerText || el.textContent || '';
                                                }}
                                                console.log(`JS (Grok): User input detected via ${{eventType}}: "${{text}}"`);
                                                window.pyBridge.onUserInput(text);
                                            }}
                                        }});
                                    }});
                                    
                                    workingSelector = selector;
                                    window.grokWorkingSelector = selector;
                                    isListenerAttached = true;
                                    console.log(`JS (Grok): Listener attached successfully!`);
                                    
                                    // Notify Python that JS detection succeeded
                                    if (window.pyBridge && window.pyBridge.onJSDetectionStatus) {{
                                        window.pyBridge.onJSDetectionStatus(true);
                                    }}
                                    
                                    return true;
                                }}
                            }}
                        }} catch (e) {{
                            console.log(`JS (Grok): Error with selector ${{selector}}:`, e);
                        }}
                    }}
                    
                    console.log('JS (Grok): No suitable input element found - JS detection failed');
                    jsDetectionFailed = true;
                    
                    // Notify Python that JS detection failed, enable computer vision
                    if (window.pyBridge && window.pyBridge.onJSDetectionStatus) {{
                        window.pyBridge.onJSDetectionStatus(false);
                    }}
                    
                    return false;
                }}

                function retryAttachment() {{
                    console.log('JS (Grok): Retrying input attachment...');
                    if (!findAndAttachToInput()) {{
                        setTimeout(retryAttachment, 3000); // Longer retry interval
                    }}
                }}

                function initWebChannelAndStart() {{
                    if (typeof QWebChannel === 'undefined') {{
                        console.error('JS (Grok): QWebChannel not available');
                        return;
                    }}
                    
                    try {{
                        new QWebChannel(qt.webChannelTransport, function(channel) {{
                            window.pyBridge = channel.objects.pyBridge;
                            bridgeInitialized = true;
                            console.log('JS (Grok): Bridge initialized, starting input search');
                            
                            // Start immediately, then retry if needed
                            if (!findAndAttachToInput()) {{
                                setTimeout(retryAttachment, 3000);
                            }}
                        }});
                    }} catch (e) {{
                        console.error('JS (Grok): QWebChannel error:', e);
                    }}
                }}
                
                // Start the process
                if (window.pyBridge) {{
                    console.log('JS (Grok): Bridge already available');
                    bridgeInitialized = true;
                    findAndAttachToInput();
                }} else if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                    initWebChannelAndStart();
                }} else {{
                    console.log('JS (Grok): Waiting for qt.webChannelTransport...');
                    var attempts = 0;
                    function waitForQt() {{
                        if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                            initWebChannelAndStart();
                        }} else if (attempts < 10) {{
                            attempts++;
                            setTimeout(waitForQt, 1000);
                        }} else {{
                            console.error('JS (Grok): Failed to initialize - qt.webChannelTransport not found');
                            // Enable computer vision as fallback
                            if (window.pyBridge && window.pyBridge.onJSDetectionStatus) {{
                                window.pyBridge.onJSDetectionStatus(false);
                            }}
                        }}
                    }}
                    waitForQt();
                }}
            }})();
        """
        self.page.runJavaScript(BasePane._qwebchannel_js_content)
        self.page.runJavaScript(script)

    def _on_js_detection_status(self, success: bool):
        """Handle JS detection status and enable/disable computer vision."""
        print(f"PY (GrokPane): JS detection status: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            self.js_detection_failed = False
            if self.cv_enabled:
                print("PY (GrokPane): Disabling computer vision - JS detection working")
                self.cv_timer.stop()
                self.cv_enabled = False
        else:
            self.js_detection_failed = True
            if not self.cv_enabled:
                print("PY (GrokPane): Enabling computer vision fallback - JS detection failed")
                self._enable_computer_vision()

    def _enable_computer_vision(self):
        """Enable computer vision-based input detection."""
        self.cv_enabled = True
        
        # Set input area rectangle (bottom portion of the view where input is likely)
        view_rect = self.geometry()
        # Focus on bottom 20% of the view where input fields are typically located
        input_height = int(view_rect.height() * 0.2)
        self.input_area_rect = QRect(0, view_rect.height() - input_height, view_rect.width(), input_height)
        
        print(f"PY (GrokPane): Computer vision enabled - monitoring area: {self.input_area_rect}")
        print(f"PY (GrokPane): OCR check interval: {self.cv_check_interval}ms")
        
        # Start the timer
        self.cv_timer.start(self.cv_check_interval)

    def _check_input_with_cv(self):
        """Use computer vision to detect text changes in the input area."""
        if not self.cv_enabled:
            return
            
        try:
            # Take screenshot of the input area
            pixmap = self.grab(self.input_area_rect)
            
            # Convert to PIL Image
            buffer = io.BytesIO()
            pixmap.save(buffer, "PNG")
            buffer.seek(0)
            image = Image.open(buffer)
            
            # Use OCR to extract text
            ocr_text = pytesseract.image_to_string(image, config='--psm 6').strip()
            
            # Filter out noise and short text
            if len(ocr_text) > 2 and ocr_text != self.last_ocr_text:
                # Check if this looks like user input (not UI elements)
                if self._is_likely_user_input(ocr_text):
                    print(f"PY (GrokPane): Computer vision detected input: '{ocr_text}'")
                    self.last_ocr_text = ocr_text
                    
                    # Emit the signal to synchronize with other panes
                    self.userInputDetectedInPane.emit(ocr_text, self)
                else:
                    print(f"PY (GrokPane): OCR text filtered out (likely UI): '{ocr_text}'")
            
        except Exception as e:
            print(f"PY (GrokPane): Computer vision error: {e}")

    def _is_likely_user_input(self, text: str) -> bool:
        """Determine if OCR text is likely user input vs UI elements."""
        # Filter out common UI elements
        ui_elements = [
            "TRY GROK", "BUILD WITH GROK", "Grok", "SuperGrok",
            "Create Images", "Edit Image", "Latest News", "Personas",
            "Workspaces", "New", "Tools", "Send", "Submit"
        ]
        
        # Check if text is too similar to UI elements
        text_lower = text.lower()
        for ui_element in ui_elements:
            if ui_element.lower() in text_lower:
                return False
        
        # Check if text looks like a sentence or question
        if len(text) > 10 and (' ' in text or '?' in text):
            return True
            
        # Check if text is reasonable length for user input
        return 3 <= len(text) <= 500

    def setExternalText(self, text: str, selector: str = None):
        """Override to use the working selector found during initialization."""
        import json
        
        js_text_escaped = json.dumps(text)
        
        script = f"""
            (function() {{
                var selectors = {str(self.__class__.JS_INPUT_SELECTORS)};
                var workingSelector = window.grokWorkingSelector;
                var inputElement = null;
                
                console.log(`JS (Grok setExternalText): Setting text: "{js_text_escaped}"`);
                
                // Try working selector first
                if (workingSelector) {{
                    inputElement = document.querySelector(workingSelector);
                    if (inputElement) {{
                        console.log(`JS (Grok setExternalText): Using working selector: ${{workingSelector}}`);
                    }}
                }}
                
                // If that failed, try all selectors
                if (!inputElement) {{
                    for (let i = 0; i < selectors.length; i++) {{
                        inputElement = document.querySelector(selectors[i]);
                        if (inputElement) {{
                            var rect = inputElement.getBoundingClientRect();
                            var isVisible = rect.width > 0 && rect.height > 0;
                            if (isVisible) {{
                                console.log(`JS (Grok setExternalText): Found with selector ${{i+1}}: ${{selectors[i]}}`);
                                window.grokWorkingSelector = selectors[i];
                                break;
                            }}
                        }}
                    }}
                }}
                
                if (inputElement) {{
                    inputElement._isProgrammaticUpdate = true;
                    
                    if (inputElement.tagName === 'TEXTAREA' || inputElement.tagName === 'INPUT') {{
                        inputElement.focus();
                        inputElement.value = {js_text_escaped};
                        inputElement.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inputElement.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }} else if (inputElement.contentEditable === 'true') {{
                        inputElement.focus();
                        inputElement.innerText = {js_text_escaped};
                        inputElement.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                    
                    setTimeout(() => {{
                        delete inputElement._isProgrammaticUpdate;
                    }}, 100);
                    
                    console.log(`JS (Grok setExternalText): Text set successfully`);
                }} else {{
                    console.warn(`JS (Grok setExternalText): No input element found - relying on computer vision`);
                }}
            }})();
        """
        if self.page:
            self.page.runJavaScript(script)

print(f"GROK.PY MODULE LOADED. GrokPane.JS_INPUT = '{GrokPane.JS_INPUT}'")