import os # For path joining
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal, QUrl, Slot, QStandardPaths, QObject, QTimer, QFile, QIODevice, QTextStream
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from app.utils.ocr_utils import OCRFinder
from app.utils.logging_config import get_logger
from app.utils.js_loader import js_loader
from app.utils.error_recovery import retry_on_failure, NetworkError, JSBridgeError
from typing import List, Optional, Tuple

logger = get_logger(__name__)

class JsBridge(QObject):
    """Bridge class to handle communication between JavaScript and Python."""
    textEnteredInWebView = Signal(str, str)  # text, pane_identifier

    def __init__(self, pane_identifier, parent=None):
        super().__init__(parent)
        self.pane_identifier = pane_identifier

    @Slot(str)
    def onUserInput(self, text):
        logger.debug(f"JsBridge.onUserInput called with text: {text}")
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
        logger.info(f"Initializing {pane_name} pane")

        # Load qwebchannel.js content if not already loaded (happens once across all instances)
        if BasePane._qwebchannel_js_content is None:
            logger.debug(f"Loading qwebchannel.js content for {pane_name}")
            # Try the alternative resource path
            qfile_path = ":/qtwebchannel/qwebchannel.js"
            qfile = QFile(qfile_path)
            if qfile.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
                stream = QTextStream(qfile)
                BasePane._qwebchannel_js_content = stream.readAll()
                qfile.close()
                if BasePane._qwebchannel_js_content and BasePane._qwebchannel_js_content.strip() != "":
                    logger.info(f"qwebchannel.js loaded successfully. Length: {len(BasePane._qwebchannel_js_content)}")
                else:
                    logger.warning(f"qwebchannel.js loaded but is empty")
                    BasePane._qwebchannel_js_content = ""
            else:
                logger.error(f"Could not load qwebchannel.js from {qfile_path}: {qfile.errorString()}")
                BasePane._qwebchannel_js_content = ""
        else:
            logger.debug(f"qwebchannel.js already loaded. Length: {len(BasePane._qwebchannel_js_content) if BasePane._qwebchannel_js_content else 0}")

        # Initialize OCR finder
        self.ocr_finder = OCRFinder()

        # Set up the layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create web view
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)

        # Set up profile with error handling
        try:
            self._setup_web_profile()
        except Exception as e:
            logger.error(f"Error setting up web profile for {pane_name}: {str(e)}", exc_info=True)
            raise

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

        # Load the URL with error handling
        try:
            logger.info(f"Loading URL for {pane_name}: {self.URL}")
            self.web_view.load(QUrl(self.URL))
        except Exception as e:
            logger.error(f"Error loading URL {self.URL} for {pane_name}: {str(e)}", exc_info=True)
            self.errorOccurred.emit(f"Failed to load URL: {str(e)}")

    def _setup_web_profile(self):
        """Set up the web engine profile with proper error handling."""
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
        
        logger.debug(f"Web profile set up for {self.__class__.__name__} at {profile_storage_path}")

    @retry_on_failure(max_retries=2, delay=1.0, exceptions=(JSBridgeError,))
    @Slot(bool)
    def _inject_input_listener_js(self, ok): # Slot for loadFinished signal
        if not ok:
            logger.error(f"Page load failed for {self.__class__.__name__}")
            self.errorOccurred.emit("Page load failed")
            return

        if BasePane._qwebchannel_js_content is None:
            logger.error(f"qwebchannel.js content is not loaded. Cannot inject JS for {self.__class__.__name__}")
            raise JSBridgeError("qwebchannel.js content not available")

        js_input_selector = getattr(self.__class__, 'JS_INPUT', None)
        if not js_input_selector:
            logger.debug(f"No JS_INPUT selector defined for {self.__class__.__name__}. Skipping input listener injection.")
            return

        logger.debug(f"Injecting input listener JS for {self.__class__.__name__} with selector: {js_input_selector}")

        try:
            # Use the new JavaScript loader
            script = js_loader.get_input_listener_js(self.__class__.__name__, js_input_selector)
            if not script:
                raise JSBridgeError("Failed to load input listener JavaScript")
            
            # Inject qwebchannel.js first, then our script
            self.page.runJavaScript(BasePane._qwebchannel_js_content)
            self.page.runJavaScript(script)
            
            logger.info(f"Successfully injected input listener JS for {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error injecting JavaScript for {self.__class__.__name__}: {str(e)}", exc_info=True)
            raise JSBridgeError(f"JavaScript injection failed: {str(e)}")

    @retry_on_failure(max_retries=2, delay=0.5, exceptions=(Exception,))
    def setExternalText(self, text: str, selector: str = None):
        # Determine the correct selector
        js_selector = selector if selector else getattr(self.__class__, 'JS_INPUT', None)
        if not js_selector:
            logger.warning(f"No JS_INPUT selector defined for setExternalText in {self.__class__.__name__}")
            return

        logger.debug(f"Setting external text for {self.__class__.__name__}: {len(text)} characters")

        try:
            # Use the new JavaScript loader
            script = js_loader.get_set_external_text_js(self.__class__.__name__, js_selector, text)
            if not script:
                logger.error(f"Failed to load setExternalText JavaScript for {self.__class__.__name__}")
                return
            
            if self.page:
                self.page.runJavaScript(script)
                logger.debug(f"Successfully set external text for {self.__class__.__name__}")
            else:
                logger.error(f"Page not available for JS execution in setExternalText for {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error setting external text for {self.__class__.__name__}: {str(e)}", exc_info=True)

    def _handle_text_from_webview(self, text: str):
        logger.debug(f"BasePane._handle_text_from_webview called for {self.__class__.__name__} with text: {len(text)} characters")
        if self._is_programmatic_update and text == self._last_programmatically_set_text:
            logger.debug(f"Ignoring programmatic update for {self.__class__.__name__}")
            return
        logger.debug(f"Emitting userInputDetectedInPane for {self.__class__.__name__}")
        self.userInputDetectedInPane.emit(text, self)

    def ensure_input_focused(self):
        """Focus the input box using JavaScript to make the placeholder visible for OCR."""
        if not self.JS_INPUT:
            logger.error(f"JS_INPUT selector not defined for ensure_input_focused in {self.__class__.__name__}")
            return
        js = f'''
        (function() {{
            var inp = document.querySelector(`{self.JS_INPUT}`);
            if (inp) {{ inp.focus(); }}
        }})();
        '''
        try:
            self.page.runJavaScript(js)
            logger.debug(f"Focused input box for {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error focusing input box for {self.__class__.__name__}: {str(e)}")

    def find_and_click_input(self, target_texts: List[str] = None) -> bool:
        """
        Find and click the input box using OCR.
        
        Args:
            target_texts: List of texts to look for (default: common input placeholders)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure input is focused first
            self.ensure_input_focused()
            
            # Use default target texts if none provided
            if target_texts is None:
                target_texts = [
                    "Ask anything", "Message", "Type a message", "Enter your message",
                    "What can I help", "How can I help", "Ask me anything",
                    "Type here", "Enter text", "Search", "Chat"
                ]
            
            logger.info(f"Attempting OCR input click for {self.__class__.__name__} with texts: {target_texts}")
            result = self.ocr_finder.click_input_box(self, target_texts)
            
            if result:
                logger.info(f"OCR input click successful for {self.__class__.__name__}")
            else:
                logger.warning(f"OCR input click failed for {self.__class__.__name__}")
                
            return result
        except Exception as e:
            logger.error(f"Error in find_and_click_input for {self.__class__.__name__}: {str(e)}", exc_info=True)
            return False

    def find_input_location(self, target_texts: List[str] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the location of the input box using OCR.
        
        Args:
            target_texts: List of texts to look for (default: common input placeholders)
            
        Returns:
            Tuple of (x, y, width, height) if found, None otherwise
        """
        try:
            # Ensure input is focused first
            self.ensure_input_focused()
            
            # Use default target texts if none provided
            if target_texts is None:
                target_texts = [
                    "Ask anything", "Message", "Type a message", "Enter your message",
                    "What can I help", "How can I help", "Ask me anything",
                    "Type here", "Enter text", "Search", "Chat"
                ]
            
            logger.info(f"Attempting OCR input location for {self.__class__.__name__} with texts: {target_texts}")
            result = self.ocr_finder.find_input_box(self, target_texts)
            
            if result:
                logger.info(f"OCR input location found for {self.__class__.__name__}: {result}")
            else:
                logger.warning(f"OCR input location not found for {self.__class__.__name__}")
                
            return result
        except Exception as e:
            logger.error(f"Error in find_input_location for {self.__class__.__name__}: {str(e)}", exc_info=True)
            return None

    def test_ocr_system(self) -> bool:
        """
        Test the OCR system for this pane.
        
        Returns:
            True if OCR is working, False otherwise
        """
        try:
            if not self.ocr_finder.is_available():
                logger.error(f"OCR system not available for {self.__class__.__name__}")
                return False
                
            # Test basic OCR functionality
            if not self.ocr_finder.test_ocr():
                logger.error(f"OCR test failed for {self.__class__.__name__}")
                return False
                
            logger.info(f"OCR system test passed for {self.__class__.__name__}")
            return True
        except Exception as e:
            logger.error(f"Error testing OCR system for {self.__class__.__name__}: {str(e)}", exc_info=True)
            return False

    def __del__(self):
        """Clean up resources when the pane is destroyed."""
        try:
            logger.debug(f"Cleaning up resources for {self.__class__.__name__}")
            # Disconnect signals
            if hasattr(self, 'web_view') and self.web_view:
                self.web_view.loadFinished.disconnect()
            if hasattr(self, 'bridge') and self.bridge:
                self.bridge.textEnteredInWebView.disconnect()
            
            # Clear page
            if hasattr(self, 'web_view') and self.web_view:
                self.web_view.setPage(None)
            if hasattr(self, 'page') and self.page:
                self.page.deleteLater()
            
            # Remove profile reference
            if hasattr(self, 'profile'):
                profile_name = self.profile.name()
                if profile_name in BasePane._profile_name_counters:
                    del BasePane._profile_name_counters[profile_name]
        except Exception as e:
            logger.error(f"Error during cleanup for {self.__class__.__name__}: {str(e)}")
            pass