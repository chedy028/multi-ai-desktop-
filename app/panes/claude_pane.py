from app.panes.base_pane import BasePane

class ClaudePane(BasePane):
    """Pane for interacting with Anthropic's Claude using QWebEngineView."""
    
    URL = "https://claude.ai/chats"
    # Multiple fallback selectors for Claude input field - updated for current Claude.ai structure
    JS_INPUT_SELECTORS = [
        # Most common Claude selectors (based on current Claude.ai structure)
        'div[contenteditable="true"][data-testid="chat-input"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][aria-label*="message"]',
        'div[contenteditable="true"][aria-label*="Message"]',
        'div[contenteditable="true"][aria-label*="input"]',
        'div[contenteditable="true"][aria-label*="Input"]',
        'div[contenteditable="true"][placeholder*="Message"]',
        'div[contenteditable="true"][placeholder*="Ask"]',
        'div[contenteditable="true"][placeholder*="Type"]',
        # ProseMirror editor (commonly used by Claude)
        'div.ProseMirror[contenteditable="true"]',
        'div[data-testid="composer"] div[contenteditable="true"]',
        'div[data-testid="chat-input"] div[contenteditable="true"]',
        # Form-based selectors
        'form div[contenteditable="true"]',
        'form textarea',
        # Generic contenteditable selectors
        'div[contenteditable="true"]',
        '[contenteditable="true"]',
        # Textarea fallbacks
        'textarea[placeholder*="Message"]',
        'textarea[placeholder*="Ask"]',
        'textarea[data-testid*="input"]',
        'textarea[aria-label*="input"]',
        'textarea',
        # Final fallbacks
        'input[type="text"]'
    ]
    
    # Use the first selector as default for compatibility
    JS_INPUT = JS_INPUT_SELECTORS[0]
    JS_SEND_BUTTON = "button[aria-label*='Send'], button[data-testid*='send'], button[type='submit'], button[title*='Send']"
    JS_LAST_REPLY = "div[data-testid*='message'] .prose, div.message-content, .assistant-message, div[data-testid*='claude'] div"

    def __init__(self, parent=None):
        super().__init__(parent)
        # Note: User must manually log in to Claude within the pane

    def _inject_input_listener_js(self, ok):
        """Override to try multiple selectors for Claude."""
        if not ok:
            print(f"PY ({self.__class__.__name__}): Page load failed.")
            return

        if BasePane._qwebchannel_js_content is None:
            print(f"PY ({self.__class__.__name__}): qwebchannel.js content is not loaded. Cannot inject JS.")
            return

        # Create JavaScript that tries multiple selectors
        selectors_js = str(self.JS_INPUT_SELECTORS)
        
        script = f"""
            (function() {{ 
                var bridgeInitialized = false;
                var attachAttempts = 0;
                var currentSelectorIndex = 0;
                const maxAttachAttempts = 20; // Increased for Claude
                const attachInterval = 500; // Longer interval for Claude
                const selectors = {selectors_js};

                function tryAttachListener() {{
                    attachAttempts++;
                    
                    // Try each selector until we find one that works
                    for (let i = 0; i < selectors.length; i++) {{
                        var currentSelector = selectors[i];
                        console.log(`JS (Claude): Trying selector ${{i+1}}/${{selectors.length}}: ${{currentSelector}}`);
                        var inputElement = document.querySelector(currentSelector);

                        if (inputElement) {{
                            console.log(`JS (Claude): SUCCESS! Input listener attached to element using selector ${{i+1}}: ${{currentSelector}}`, inputElement);
                            
                            // Add multiple event listeners for better coverage
                            ['input', 'keyup', 'paste'].forEach(eventType => {{
                                inputElement.addEventListener(eventType, function(event) {{
                                    if (inputElement._isProgrammaticUpdate) {{
                                        return; 
                                    }}
                                    if (window.pyBridge && window.pyBridge.onUserInput) {{
                                        let text = '';
                                        if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {{
                                            text = inputElement.value;
                                        }} else if (inputElement.hasAttribute('contenteditable')) {{
                                            text = inputElement.innerText || inputElement.textContent || '';
                                        }}
                                        console.log(`JS (Claude): Sending text to Python via ${{eventType}}: "${{text}}"`);
                                        window.pyBridge.onUserInput(text);
                                    }} else {{
                                        console.warn('JS (Claude): pyBridge or onUserInput not available when ${{eventType}} event fired.');
                                    }}
                                }});
                            }});
                            
                            // Store the working selector for setExternalText
                            window.claudeWorkingSelector = currentSelector;
                            return; // Success, exit function
                        }}
                    }}
                    
                    // If we get here, none of the selectors worked
                    if (attachAttempts < maxAttachAttempts) {{
                        console.warn(`JS (Claude): No input element found with any selector (Attempt ${{attachAttempts}}/${{maxAttachAttempts}}). Retrying in ${{attachInterval}}ms.`);
                        setTimeout(tryAttachListener, attachInterval);
                    }} else {{
                        console.error(`JS (Claude): Failed to find input element after ${{maxAttachAttempts}} attempts with all selectors.`);
                        // Log available elements for debugging
                        console.log('JS (Claude): Available textareas:', document.querySelectorAll('textarea'));
                        console.log('JS (Claude): Available inputs:', document.querySelectorAll('input'));
                        console.log('JS (Claude): Available contenteditable elements:', document.querySelectorAll('[contenteditable="true"]'));
                        console.log('JS (Claude): Available ProseMirror elements:', document.querySelectorAll('.ProseMirror'));
                        console.log('JS (Claude): Available form elements:', document.querySelectorAll('form'));
                    }}
                }}

                function initWebChannelAndListeners() {{
                    if (typeof QWebChannel === 'undefined' || typeof QWebChannel.constructor !== 'function') {{
                        console.error('JS (Claude): QWebChannel is not defined. Cannot establish pyBridge. Input listener WILL NOT WORK.');
                        return;
                    }}
                    try {{
                        new QWebChannel(qt.webChannelTransport, function(channel) {{
                            window.pyBridge = channel.objects.pyBridge;
                            bridgeInitialized = true;
                            console.log('JS (Claude): pyBridge initialized successfully via QWebChannel.');
                            tryAttachListener();
                        }});
                    }} catch (e) {{
                        console.error('JS (Claude): Error initializing QWebChannel:', e, '. Input listener WILL NOT WORK.');
                    }}
                }}
                
                if (window.pyBridge && window.pyBridge.onUserInput) {{
                    console.log('JS (Claude): pyBridge already available. Proceeding to attach listener.');
                    bridgeInitialized = true;
                    tryAttachListener();
                }} else if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                    initWebChannelAndListeners();
                }} else {{
                    console.warn('JS (Claude): qt.webChannelTransport not immediately available. Will retry QWebChannel init.');
                    let channelInitAttempts = 0;
                    const maxChannelInitAttempts = 10; // Increased for Claude
                    const channelInitInterval = 1000; // Longer interval
                    function retryInitWebChannel() {{
                        if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                            initWebChannelAndListeners();
                        }} else {{
                            channelInitAttempts++;
                            if (channelInitAttempts < maxChannelInitAttempts) {{
                                setTimeout(retryInitWebChannel, channelInitInterval);
                            }} else {{
                                console.error('JS (Claude): Failed to initialize QWebChannel after multiple attempts. qt.webChannelTransport not found.');
                            }}
                        }}
                    }}
                    retryInitWebChannel();
                }}
            }})();
        """
        self.page.runJavaScript(BasePane._qwebchannel_js_content)
        self.page.runJavaScript(script)

    def setExternalText(self, text: str, selector: str = None):
        """Override to use the working selector found during initialization."""
        import json
        
        js_text_escaped = json.dumps(text)
        
        script = f"""
            (function() {{
                var selectors = {str(self.__class__.JS_INPUT_SELECTORS)};
                var workingSelector = window.claudeWorkingSelector;
                var inputElement = null;
                
                // First try the working selector if we have one
                if (workingSelector) {{
                    inputElement = document.querySelector(workingSelector);
                    if (inputElement) {{
                        console.log(`JS (Claude setExternalText): Using stored working selector: ${{workingSelector}}`);
                    }}
                }}
                
                // If that didn't work, try all selectors again
                if (!inputElement) {{
                    for (let i = 0; i < selectors.length; i++) {{
                        var currentSelector = selectors[i];
                        inputElement = document.querySelector(currentSelector);
                        if (inputElement) {{
                            console.log(`JS (Claude setExternalText): Found element with selector ${{i+1}}: ${{currentSelector}}`);
                            window.claudeWorkingSelector = currentSelector; // Update working selector
                            break;
                        }}
                    }}
                }}
                
                if (inputElement) {{
                    inputElement._isProgrammaticUpdate = true;
                    var scrollTop = inputElement.scrollTop;

                    if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {{
                        inputElement.focus();
                        inputElement.value = {js_text_escaped};
                        // Trigger multiple events for better compatibility
                        ['input', 'change', 'keyup'].forEach(eventType => {{
                            var event = new Event(eventType, {{ bubbles: true, cancelable: true }});
                            inputElement.dispatchEvent(event);
                        }});
                    }} else if (inputElement.isContentEditable || inputElement.hasAttribute('contenteditable')) {{
                        inputElement.focus();
                        
                        // For contenteditable elements, try multiple approaches
                        if (inputElement.innerText !== undefined) {{
                            inputElement.innerText = {js_text_escaped};
                        }} else {{
                            inputElement.textContent = {js_text_escaped};
                        }}
                        
                        // Trigger events for contenteditable
                        ['input', 'change', 'keyup'].forEach(eventType => {{
                            var event = new Event(eventType, {{ bubbles: true, cancelable: true }});
                            inputElement.dispatchEvent(event);
                        }});
                        
                        // Special handling for ProseMirror if detected
                        if (inputElement.classList.contains('ProseMirror')) {{
                            console.log('JS (Claude setExternalText): Detected ProseMirror editor, using special handling');
                            // ProseMirror might need special event handling
                            var keydownEvent = new KeyboardEvent('keydown', {{ bubbles: true, cancelable: true }});
                            inputElement.dispatchEvent(keydownEvent);
                        }}
                    }} else {{
                        inputElement.textContent = {js_text_escaped};
                    }}
                    
                    inputElement.scrollTop = scrollTop;
                    
                    // Clear the flag after a short delay to ensure all events are processed
                    setTimeout(() => {{
                        delete inputElement._isProgrammaticUpdate;
                    }}, 100);
                    
                    console.log(`JS (Claude setExternalText): Successfully set text: "{js_text_escaped}"`);
                }} else {{
                    console.warn(`JS (Claude setExternalText): Could not find input element with any selector`);
                    console.log('JS (Claude setExternalText): Available textareas:', document.querySelectorAll('textarea'));
                    console.log('JS (Claude setExternalText): Available inputs:', document.querySelectorAll('input'));
                    console.log('JS (Claude setExternalText): Available contenteditable elements:', document.querySelectorAll('[contenteditable="true"]'));
                }}
            }})();
        """
        if self.page:
            self.page.runJavaScript(script)

print(f"CLAUDE_PANE.PY MODULE LOADED. ClaudePane.JS_INPUT = '{ClaudePane.JS_INPUT}'")
