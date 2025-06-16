from app.panes.base_pane import BasePane
from PySide6.QtCore import QTimer, QRect
from app.utils.logging_config import get_logger
import io
try:
    from PIL import Image
    import pytesseract
except ImportError:
    # Optional computer vision dependencies
    Image = None
    pytesseract = None

logger = get_logger(__name__)

class GrokPane(BasePane):
    """Pane for interacting with xAI's Grok using QWebEngineView."""
    
    URL = "https://grok.x.ai"
    JS_INPUT_SELECTORS = [
        'textarea[placeholder*="Ask"]',
        'textarea[placeholder*="Message"]',
        'textarea[placeholder*="Type"]',
        'textarea[placeholder*="What"]',
        'div[contenteditable="true"][placeholder*="Ask"]',
        'div[contenteditable="true"][placeholder*="Message"]',
        'div[contenteditable="true"][placeholder*="Type"]',
        'div[contenteditable="true"][placeholder*="What"]',
        'textarea[data-testid*="input"]',
        'textarea[data-testid*="prompt"]',
        'textarea[data-testid*="message"]',
        'textarea[data-testid*="composer"]',
        'div[contenteditable="true"][data-testid*="input"]',
        'div[contenteditable="true"][data-testid*="prompt"]',
        'div[contenteditable="true"][data-testid*="message"]',
        'div[contenteditable="true"][data-testid*="composer"]',
        'form textarea',
        'form div[contenteditable="true"]',
        'form input[type="text"]',
        'textarea:not([style*="display: none"]):not([style*="visibility: hidden"])',
        'div[contenteditable="true"]:not([style*="display: none"]):not([style*="visibility: hidden"])',
        'input[type="text"]:not([style*="display: none"]):not([style*="visibility: hidden"])',
        'textarea',
        'div[contenteditable="true"]',
        '[contenteditable="true"]',
        'input[type="text"]'
    ]
    JS_INPUT = JS_INPUT_SELECTORS[0]
    JS_SEND_BUTTON = "button[type='submit'], button[aria-label*='Send'], button[data-testid*='send']"
    JS_LAST_REPLY = "div.message-content, div[data-testid*='message'], div[data-testid*='response']"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        # Initialize computer vision properties
        self.cv_enabled = False
        self.js_detection_failed = False
        self.last_ocr_text = ""
        self.cv_check_interval = 1000  # 1 second
        self.input_area_rect = None
        
        # Initialize computer vision timer
        from PySide6.QtCore import QTimer
        self.cv_timer = QTimer()
        self.cv_timer.timeout.connect(self._check_input_with_cv)
        
        # Set custom JS detection callback on the existing bridge
        self.bridge.onJSDetectionStatus = self._on_js_detection_status
        
        logger.info("Initialized GrokPane with computer vision fallback capability.")

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
            
        # Check if computer vision dependencies are available
        if Image is None or pytesseract is None:
            print("PY (GrokPane): Computer vision dependencies not available (PIL/pytesseract)")
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

    def fix_grok_input_focus(self):
        """Fix Grok input field focus and placeholder clearing issues."""
        script = """
            (function() {
                console.log('JS (Grok): Attempting to fix input focus and placeholder issues...');
                
                // Find all possible input elements
                var inputElements = [];
                var selectors = [
                    'textarea[placeholder*="What"]',
                    'textarea[placeholder*="know"]',
                    'div[contenteditable="true"]',
                    'textarea',
                    '[contenteditable="true"]'
                ];
                
                selectors.forEach(function(selector) {
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {
                        var rect = el.getBoundingClientRect();
                        var isVisible = rect.width > 0 && rect.height > 0 && 
                                       window.getComputedStyle(el).display !== 'none' &&
                                       window.getComputedStyle(el).visibility !== 'hidden';
                        if (isVisible) {
                            inputElements.push(el);
                        }
                    });
                });
                
                console.log('JS (Grok): Found', inputElements.length, 'visible input elements');
                
                inputElements.forEach(function(el, index) {
                    console.log('JS (Grok): Input element', index, ':', el.tagName, el.placeholder || 'no placeholder');
                    
                    // Force focus and clear placeholder behavior
                    try {
                        // Focus the element
                        el.focus();
                        
                        // Clear placeholder styling if it exists
                        if (el.placeholder) {
                            console.log('JS (Grok): Clearing placeholder for element', index);
                            
                            // Force placeholder to hide by simulating input
                            var event = new Event('input', { bubbles: true });
                            el.dispatchEvent(event);
                            
                            // Also try focus event
                            var focusEvent = new Event('focus', { bubbles: true });
                            el.dispatchEvent(focusEvent);
                            
                            // Set a temporary value to force placeholder to disappear
                            if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
                                var originalValue = el.value;
                                el.value = ' '; // Temporary space
                                setTimeout(function() {
                                    el.value = originalValue; // Restore original value
                                }, 100);
                            } else if (el.contentEditable === 'true') {
                                var originalText = el.innerText;
                                el.innerText = ' '; // Temporary space
                                setTimeout(function() {
                                    el.innerText = originalText; // Restore original text
                                }, 100);
                            }
                        }
                        
                        // Force a style update
                        el.style.opacity = '0.99';
                        setTimeout(function() {
                            el.style.opacity = '1';
                        }, 50);
                        
                    } catch (e) {
                        console.log('JS (Grok): Error fixing element', index, ':', e);
                    }
                });
                
                return inputElements.length;
            })();
        """
        
        try:
            self.page.runJavaScript(script, lambda result: 
                print(f"PY (GrokPane): Fixed {result} input elements"))
        except Exception as e:
            print(f"PY (GrokPane): Error running fix script: {e}")

    def setExternalText(self, text: str, selector: str = None):
        """Override to fix Grok input issues and use the working selector found during initialization."""
        import json
        
        # First, try to fix any focus/placeholder issues
        self.fix_grok_input_focus()
        
        js_text_escaped = json.dumps(text)
        
        script = f"""
            (function() {{
                var selectors = {str(self.__class__.JS_INPUT_SELECTORS)};
                var workingSelector = window.grokWorkingSelector;
                var inputElement = null;
                
                console.log('JS (Grok setExternalText): Setting text:', {js_text_escaped});
                
                // Try working selector first
                if (workingSelector) {{
                    inputElement = document.querySelector(workingSelector);
                    if (inputElement) {{
                        console.log('JS (Grok setExternalText): Using working selector:', workingSelector);
                    }}
                }}
                
                // If that failed, try all selectors
                if (!inputElement) {{
                    for (let i = 0; i < selectors.length; i++) {{
                        var elements = document.querySelectorAll(selectors[i]);
                        for (let j = 0; j < elements.length; j++) {{
                            var el = elements[j];
                            var rect = el.getBoundingClientRect();
                            var isVisible = rect.width > 0 && rect.height > 0 && 
                                           window.getComputedStyle(el).display !== 'none' &&
                                           window.getComputedStyle(el).visibility !== 'hidden';
                            if (isVisible) {{
                                console.log('JS (Grok setExternalText): Found with selector', i+1, ':', selectors[i]);
                                inputElement = el;
                                window.grokWorkingSelector = selectors[i];
                                break;
                            }}
                        }}
                        if (inputElement) break;
                    }}
                }}
                
                if (inputElement) {{
                    inputElement._isProgrammaticUpdate = true;
                    
                    try {{
                        // Force focus first
                        inputElement.focus();
                        
                        // Clear any existing content and placeholder
                        if (inputElement.tagName === 'TEXTAREA' || inputElement.tagName === 'INPUT') {{
                            inputElement.value = '';
                            inputElement.placeholder = ''; // Clear placeholder temporarily
                            
                            // Set the new text
                            inputElement.value = {js_text_escaped};
                            
                            // Trigger events to ensure the UI updates
                            ['input', 'change', 'keyup'].forEach(function(eventType) {{
                                var event = new Event(eventType, {{ bubbles: true }});
                                inputElement.dispatchEvent(event);
                            }});
                            
                        }} else if (inputElement.contentEditable === 'true') {{
                            inputElement.innerText = '';
                            inputElement.textContent = '';
                            
                            // Set the new text
                            inputElement.innerText = {js_text_escaped};
                            
                            // Trigger events
                            ['input', 'change'].forEach(function(eventType) {{
                                var event = new Event(eventType, {{ bubbles: true }});
                                inputElement.dispatchEvent(event);
                            }});
                        }}
                        
                        // Force a visual update
                        inputElement.style.opacity = '0.99';
                        setTimeout(function() {{
                            inputElement.style.opacity = '1';
                            inputElement._isProgrammaticUpdate = false;
                        }}, 100);
                        
                        console.log('JS (Grok setExternalText): Text set successfully');
                        return true;
                        
                    }} catch (e) {{
                        console.log('JS (Grok setExternalText): Error setting text:', e);
                        inputElement._isProgrammaticUpdate = false;
                        return false;
                    }}
                }} else {{
                    console.log('JS (Grok setExternalText): No input element found');
                    return false;
                }}
            }})();
        """
        
        try:
            self.page.runJavaScript(script, lambda result: 
                print(f"PY (GrokPane): setExternalText result: {result}"))
        except Exception as e:
            print(f"PY (GrokPane): Error in setExternalText: {e}")

    def sync_text_from_other_pane(self, text: str) -> bool:
        """
        Synchronize text from another pane to Grok using OCR-based approach.
        This method finds the input box with OCR, clicks it, then sets text.
        
        Args:
            text: Text to set in the input box
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Syncing text to Grok from other pane: '{text[:50]}...'")
            
            # First, try to find the input box with OCR
            target_texts = [
                "What can I help with?", "What do you want to know?", "what do you want to know", "Ask anything",
                "Message", "Type a message", "help", "with", "ask", "know"
            ]
            
            # Find input box location
            input_location = self.ocr_finder.find_input_box(self, target_texts)
            
            if input_location:
                x, y, w, h = input_location
                logger.info(f"Found Grok input box at ({x}, {y}) size {w}x{h}")
                
                # Click the input box to focus it
                from PySide6.QtCore import QPoint
                from PySide6.QtGui import QMouseEvent
                from PySide6.QtCore import Qt
                
                # Calculate click position (center of found area)
                click_x = x + w // 2
                click_y = y + h // 2
                
                # Create and send mouse click event
                click_pos = QPoint(click_x, click_y)
                
                # Send mouse press and release events
                press_event = QMouseEvent(
                    QMouseEvent.Type.MouseButtonPress,
                    click_pos,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
                
                release_event = QMouseEvent(
                    QMouseEvent.Type.MouseButtonRelease,
                    click_pos,
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier
                )
                
                # Send the events to the web view
                self.web_view.mousePressEvent(press_event)
                self.web_view.mouseReleaseEvent(release_event)
                
                logger.info(f"Clicked Grok input box at ({click_x}, {click_y})")
                
                # Wait a moment for the click to register
                from PySide6.QtCore import QTimer
                QTimer.singleShot(200, lambda: self._set_text_after_click(text))
                
                return True
            else:
                logger.warning("Could not find Grok input box with OCR, falling back to JavaScript")
                # Fall back to the original JavaScript method
                self.setExternalText(text)
                return False
                
        except Exception as e:
            logger.error(f"Error in sync_text_from_other_pane: {str(e)}", exc_info=True)
            # Fall back to original method
            self.setExternalText(text)
            return False
    
    def _set_text_after_click(self, text: str):
        """Set text after clicking the input box."""
        try:
            logger.info("Setting text after click")
            
            # Use a more aggressive text setting approach
            import json
            js_text_escaped = json.dumps(text)
            
            script = f"""
                (function() {{
                    console.log('JS (Grok): Setting text after click:', {js_text_escaped});
                    
                    // Find the currently focused element
                    var focusedElement = document.activeElement;
                    console.log('JS (Grok): Focused element:', focusedElement);
                    
                    if (focusedElement && (
                        focusedElement.tagName === 'TEXTAREA' || 
                        focusedElement.tagName === 'INPUT' ||
                        focusedElement.contentEditable === 'true'
                    )) {{
                        console.log('JS (Grok): Using focused element');
                        
                        // Clear the element completely
                        if (focusedElement.tagName === 'TEXTAREA' || focusedElement.tagName === 'INPUT') {{
                            focusedElement.value = '';
                            focusedElement.placeholder = '';
                            
                            // Set new text
                            focusedElement.value = {js_text_escaped};
                            
                            // Trigger events
                            ['focus', 'input', 'change', 'keyup'].forEach(function(eventType) {{
                                var event = new Event(eventType, {{ bubbles: true }});
                                focusedElement.dispatchEvent(event);
                            }});
                            
                        }} else if (focusedElement.contentEditable === 'true') {{
                            focusedElement.innerHTML = '';
                            focusedElement.innerText = '';
                            focusedElement.textContent = '';
                            
                            // Set new text
                            focusedElement.innerText = {js_text_escaped};
                            
                            // Trigger events
                            ['focus', 'input', 'change'].forEach(function(eventType) {{
                                var event = new Event(eventType, {{ bubbles: true }});
                                focusedElement.dispatchEvent(event);
                            }});
                        }}
                        
                        console.log('JS (Grok): Text set successfully on focused element');
                        return true;
                    }} else {{
                        console.log('JS (Grok): No suitable focused element, trying selectors');
                        
                        // Fall back to selector-based approach
                        var selectors = {str(self.__class__.JS_INPUT_SELECTORS)};
                        
                        for (let i = 0; i < selectors.length; i++) {{
                            var elements = document.querySelectorAll(selectors[i]);
                            for (let j = 0; j < elements.length; j++) {{
                                var el = elements[j];
                                var rect = el.getBoundingClientRect();
                                var isVisible = rect.width > 0 && rect.height > 0;
                                
                                if (isVisible) {{
                                    console.log('JS (Grok): Found visible element with selector:', selectors[i]);
                                    
                                    // Focus and clear
                                    el.focus();
                                    
                                    if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {{
                                        el.value = '';
                                        el.value = {js_text_escaped};
                                    }} else if (el.contentEditable === 'true') {{
                                        el.innerText = '';
                                        el.innerText = {js_text_escaped};
                                    }}
                                    
                                    // Trigger events
                                    ['focus', 'input', 'change'].forEach(function(eventType) {{
                                        var event = new Event(eventType, {{ bubbles: true }});
                                        el.dispatchEvent(event);
                                    }});
                                    
                                    return true;
                                }}
                            }}
                        }}
                        
                        console.log('JS (Grok): No suitable element found');
                        return false;
                    }}
                }})();
            """
            
            self.page.runJavaScript(script, lambda result: 
                logger.info(f"Text setting after click result: {result}"))
                
        except Exception as e:
            logger.error(f"Error setting text after click: {str(e)}", exc_info=True)

print(f"GROK.PY MODULE LOADED. GrokPane.JS_INPUT = '{GrokPane.JS_INPUT}'")