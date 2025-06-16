import os # For path joining
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Signal, QUrl, Slot, QStandardPaths, QObject, QTimer, QFile, QIODevice, QTextStream, Qt
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from app.utils.logging_config import get_logger
from app.utils.js_loader import js_loader, JSLoader
from app.utils.error_recovery import retry_on_failure, NetworkError, JSBridgeError, ErrorRecoveryManager
from typing import List, Optional, Tuple

logger = get_logger(__name__)

class JsBridge(QObject):
    """Bridge class to handle communication between JavaScript and Python."""
    textEnteredInWebView = Signal(str, str)  # text, pane_identifier

    def __init__(self, pane_identifier, parent=None):
        super().__init__(parent)
        self.pane_identifier = pane_identifier
        self.parent_pane = parent  # Reference to the parent pane

    @Slot(str)
    def onUserInput(self, text):
        logger.debug(f"JsBridge.onUserInput called with text: {text}")
        # Emit the legacy signal for compatibility
        self.textEnteredInWebView.emit(text, self.pane_identifier)
        
        # Also emit the userInputDetectedInPane signal directly from the parent pane
        if self.parent_pane and hasattr(self.parent_pane, 'userInputDetectedInPane'):
            logger.debug(f"Emitting userInputDetectedInPane signal from {self.pane_identifier}")
            self.parent_pane.userInputDetectedInPane.emit(text, self.parent_pane)

class BasePane(QWidget):
    """Base class for all AI chat panes."""
    
    # Signals for synchronization
    userInputDetectedInPane = Signal(str, object)  # text, pane
    promptSubmitted = Signal(str)  # For compatibility with main window
    errorOccurred = Signal(str)    # For compatibility with main window  
    answerReady = Signal(str)      # For compatibility with main window
    
    # Signals for cross-pane communication
    inputDetected = Signal(str, str)  # pane_name, text
    
    URL: str = ""
    JS_INPUT: str = ""
    JS_SEND_BUTTON: str = ""
    JS_LAST_REPLY: str = ""

    # Class variable to store unique profile names
    _profile_name_counters = {}
    _qwebchannel_js_content = None # Class variable to hold qwebchannel.js content

    def __init__(self, name: str = None, parent=None):
        super().__init__(parent)
        self.name = name or self.__class__.__name__
        self.js_loader = JSLoader()
        self.error_recovery = ErrorRecoveryManager(self)
        
        # Initialize current URL tracking
        self._current_url = None
        self._last_input_text = ""  # Track last input text for polling
        self._is_syncing = False  # Flag to prevent polling during sync
        
        # Initialize JS injection timer
        self._js_injection_timer = QTimer()
        self._js_injection_timer.setSingleShot(True)
        self._js_injection_timer.timeout.connect(self._delayed_js_injection)
        
        # Input polling timer for synchronization
        self._input_poll_timer = QTimer()
        self._input_poll_timer.timeout.connect(self._poll_for_input_changes)
        self._input_poll_timer.start(1000)  # Poll every 1000ms (reduced frequency)
        
        # Load qwebchannel.js content if not already loaded
        self._load_qwebchannel_js()
        
        # Create JavaScript bridge for communication
        self.bridge = JsBridge(self.__class__.__name__, self)
        self.bridge.textEnteredInWebView.connect(self._handle_text_from_webview)
        
        self.setup_ui()
        self._setup_web_profile()
        
        # Set up web channel after profile is created
        self._setup_web_channel()
        
        # Load the URL if defined in the subclass
        if hasattr(self.__class__, 'URL') and self.__class__.URL:
            self.load_url(self.__class__.URL)
            logger.info(f"Loading URL for {self.__class__.__name__}: {self.__class__.URL}")
        
    def setup_ui(self):
        """Setup the user interface."""
        # Main layout with no margins for maximum space utilization
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)  # Remove spacing
        self.setLayout(layout)
        
        # Web view takes up all available space
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # Compact status bar (only visible when needed)
        self.status_widget = QWidget()
        self.status_widget.setMaximumHeight(25)  # Compact height
        self.status_widget.setVisible(False)  # Hidden by default
        status_layout = QHBoxLayout(self.status_widget)
        status_layout.setContentsMargins(5, 2, 5, 2)  # Minimal margins
        layout.addWidget(self.status_widget)
        
        # Compact status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 11px;")  # Smaller font
        status_layout.addWidget(self.status_label)
        
        # Compact error recovery button
        self.recovery_button = QPushButton("Recover")
        self.recovery_button.setMaximumWidth(60)  # Smaller button
        self.recovery_button.setMaximumHeight(20)
        self.recovery_button.setStyleSheet("font-size: 10px; padding: 2px;")
        self.recovery_button.setVisible(False)
        status_layout.addWidget(self.recovery_button)
        
        # Connect signals
        self.recovery_button.clicked.connect(self.recover_from_error)
        
    def load_url(self, url: str):
        """Load a URL in the web view."""
        from PySide6.QtCore import QUrl
        if isinstance(url, str):
            qurl = QUrl(url)
        else:
            qurl = url
        self.web_view.setUrl(qurl)
        logger.debug(f"Loading URL in {self.__class__.__name__}: {url}")
        
    def inject_js(self, js_code: str):
        """Inject JavaScript code into the web view."""
        self.web_view.page().runJavaScript(js_code)
        
    def recover_from_error(self):
        """Attempt to recover from an error state."""
        # Reload the current page to recover from errors
        if self.web_view and self.web_view.page():
            self.web_view.reload()
            self.clear_error()
        
    def show_error(self, message: str):
        """Show an error message in the compact status bar."""
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("color: red; font-size: 11px;")
        self.recovery_button.setVisible(True)
        self.status_widget.setVisible(True)  # Show the status widget
        
    def clear_error(self):
        """Clear any error message and hide status bar."""
        self.status_label.setText("")
        self.status_label.setStyleSheet("font-size: 11px;")
        self.recovery_button.setVisible(False)
        self.status_widget.setVisible(False)  # Hide the status widget

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
        
        # Connect page signals for JavaScript injection
        self.page.loadFinished.connect(self._inject_input_listener_js)
        self.page.loadStarted.connect(self._on_load_started)
        self.page.urlChanged.connect(self._on_url_changed)
        
        logger.debug(f"Web profile set up for {self.__class__.__name__} at {profile_storage_path}")

    @retry_on_failure(max_retries=2, delay=1.0, exceptions=(JSBridgeError,))
    @Slot(bool)
    def _inject_input_listener_js(self, ok): # Slot for loadFinished signal
        if not ok:
            logger.error(f"Page load failed for {self.__class__.__name__}")
            self.show_error("Page load failed")
            return

        # The JavaScript bridge is optional - polling works without it
        # Try to inject the bridge, but don't fail if qwebchannel.js is not available
        try:
            if BasePane._qwebchannel_js_content is None:
                logger.warning(f"qwebchannel.js content is not loaded for {self.__class__.__name__}. Bridge injection skipped, but polling will still work.")
                return

            js_input_selector = getattr(self.__class__, 'JS_INPUT', None)
            if not js_input_selector:
                logger.debug(f"No JS_INPUT selector defined for {self.__class__.__name__}. Skipping input listener injection.")
                return

            logger.debug(f"Injecting input listener JS for {self.__class__.__name__} with selector: {js_input_selector}")

            # Use the new JavaScript loader
            script = js_loader.get_input_listener_js(self.__class__.__name__, js_input_selector)
            if not script:
                logger.warning(f"Failed to load input listener JavaScript for {self.__class__.__name__}. Polling will still work.")
                return
            
            # Inject qwebchannel.js first, then our script
            self.page.runJavaScript(BasePane._qwebchannel_js_content)
            self.page.runJavaScript(script)
            
            logger.info(f"Successfully injected input listener JS for {self.__class__.__name__}")
        except Exception as e:
            logger.warning(f"JavaScript bridge injection failed for {self.__class__.__name__}: {str(e)}. Polling will still work.")
            # Don't raise an exception - polling will handle synchronization

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
        logger.debug(f"Emitting userInputDetectedInPane for {self.__class__.__name__}")
        self.userInputDetectedInPane.emit(text, self)

    @Slot()
    def _on_load_started(self):
        """Handle page load start - prepare for potential JS re-injection."""
        logger.debug(f"Page load started for {self.__class__.__name__}")
        # Cancel any pending delayed injection
        if self._js_injection_timer.isActive():
            self._js_injection_timer.stop()

    @Slot()
    def _on_url_changed(self, url):
        """Handle URL changes - indicates navigation to new chat or page."""
        url_str = url.toString()
        logger.debug(f"URL changed for {self.__class__.__name__}: {url_str}")
        
        # Check if this is a significant URL change (not just fragment changes)
        if self._current_url and self._is_significant_url_change(self._current_url, url_str):
            logger.info(f"Significant URL change detected in {self.__class__.__name__}: {self._current_url} -> {url_str}")
            # Schedule delayed JS injection to allow page to fully load
            # Use a shorter delay for better responsiveness
            self._js_injection_timer.start(1500)  # 1.5 second delay
        
        self._current_url = url_str

    def _is_significant_url_change(self, old_url: str, new_url: str) -> bool:
        """
        Determine if a URL change is significant enough to require JS re-injection.
        
        Args:
            old_url: Previous URL
            new_url: New URL
            
        Returns:
            True if the change is significant (different path/query), False for minor changes
        """
        try:
            from urllib.parse import urlparse
            
            old_parsed = urlparse(old_url)
            new_parsed = urlparse(new_url)
            
            # Consider it significant if the path changed or if query parameters changed
            # (indicating navigation to a new chat/conversation)
            path_changed = old_parsed.path != new_parsed.path
            query_changed = old_parsed.query != new_parsed.query
            
            # For ChatGPT, also consider fragment changes significant as they often indicate new chats
            if "chatgpt" in new_url.lower() or "openai" in new_url.lower():
                fragment_changed = old_parsed.fragment != new_parsed.fragment
                return path_changed or query_changed or fragment_changed
            
            return path_changed or query_changed
        except Exception as e:
            logger.error(f"Error comparing URLs in {self.__class__.__name__}: {str(e)}")
            return True  # Err on the side of caution

    @Slot()
    def _delayed_js_injection(self):
        """Perform delayed JavaScript injection after URL change."""
        logger.info(f"Performing delayed JS injection for {self.__class__.__name__} after URL change")
        try:
            # Inject JS as if the page just finished loading
            # This is optional - if it fails, polling will still work
            self._inject_input_listener_js(True)
        except Exception as e:
            logger.warning(f"Delayed JS injection failed for {self.__class__.__name__}: {str(e)}. Polling will continue to work.")
            # Don't propagate the exception - the app should continue working
        
        # Ensure polling is still active after page change
        if not self._input_poll_timer.isActive():
            logger.info(f"Restarting input polling for {self.__class__.__name__} after page change")
            self._input_poll_timer.start(1000)

    def __del__(self):
        """Clean up resources when the pane is destroyed."""
        try:
            logger.debug(f"Cleaning up resources for {self.__class__.__name__}")
            # Stop any active timers
            if hasattr(self, '_js_injection_timer') and self._js_injection_timer:
                self._js_injection_timer.stop()
            
            # Disconnect signals
            if hasattr(self, 'web_view') and self.web_view:
                self.web_view.loadFinished.disconnect()
            if hasattr(self, 'bridge') and self.bridge:
                self.bridge.textEnteredInWebView.disconnect()
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.urlChanged.disconnect()
                    self.page.loadStarted.disconnect()
                except:
                    pass  # Ignore if already disconnected
            
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

    @classmethod
    def _load_qwebchannel_js(cls):
        """Load qwebchannel.js content if not already loaded."""
        if cls._qwebchannel_js_content is None:
            try:
                # For PySide6, qwebchannel.js is built into the WebEngine
                # We need to provide the actual qwebchannel.js content
                cls._qwebchannel_js_content = """
                /****************************************************************************
                **
                ** Copyright (C) 2016 The Qt Company Ltd.
                ** Copyright (C) 2016 basysKom GmbH, author Bernd Lamecker <bernd.lamecker@basyskom.com>
                ** SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
                **
                ****************************************************************************/

                ;(function() {
                "use strict";

                var QWebChannelMessageTypes = {
                    signal: 1,
                    propertyUpdate: 2,
                    init: 3,
                    idle: 4,
                    debug: 5,
                    invokeMethod: 6,
                    connectToSignal: 7,
                    disconnectFromSignal: 8,
                    setProperty: 9,
                    response: 10,
                };

                var QWebChannel = function(transport, initCallback)
                {
                    if (typeof transport !== "object" || typeof transport.send !== "function") {
                        console.error("The QWebChannel expects a transport object with a send function and onmessage callback property." +
                                     " Given is: transport: " + typeof(transport) + ", transport.send: " + typeof(transport.send));
                        return;
                    }

                    var channel = this;
                    this.transport = transport;

                    this.send = function(data)
                    {
                        if (typeof(data) !== "string") {
                            data = JSON.stringify(data);
                        }
                        channel.transport.send(data);
                    }

                    this.transport.onmessage = function(message)
                    {
                        var data = message.data;
                        if (typeof data === "string") {
                            data = JSON.parse(data);
                        }
                        switch (data.type) {
                        case QWebChannelMessageTypes.signal:
                            channel.handleSignal(data);
                            break;
                        case QWebChannelMessageTypes.response:
                            channel.handleResponse(data);
                            break;
                        case QWebChannelMessageTypes.propertyUpdate:
                            channel.handlePropertyUpdate(data);
                            break;
                        default:
                            console.error("invalid message received:", message.data);
                            break;
                        }
                    }

                    this.execCallbacks = {};
                    this.execId = 0;
                    this.exec = function(data, callback)
                    {
                        if (!callback) {
                            // if no callback is given, send directly
                            channel.send(data);
                            return;
                        }
                        if (channel.execId === Number.MAX_VALUE) {
                            // wrap
                            channel.execId = Number.MIN_VALUE;
                        }
                        if (data.hasOwnProperty("id")) {
                            console.error("Cannot exec message with property id: " + JSON.stringify(data));
                            return;
                        }
                        data.id = channel.execId++;
                        channel.execCallbacks[data.id] = callback;
                        channel.send(data);
                    };

                    this.objects = {};

                    this.handleSignal = function(message)
                    {
                        var object = channel.objects[message.object];
                        if (object) {
                            object.signalEmitted(message.signal, message.args);
                        } else {
                            console.warn("Unhandled signal: " + message.object + "::" + message.signal);
                        }
                    };

                    this.handleResponse = function(message)
                    {
                        if (!message.hasOwnProperty("id")) {
                            console.error("Invalid response message received: ", JSON.stringify(message));
                            return;
                        }
                        channel.execCallbacks[message.id](message.data);
                        delete channel.execCallbacks[message.id];
                    };

                    this.handlePropertyUpdate = function(message)
                    {
                        for (var i in message.data) {
                            var data = message.data[i];
                            var object = channel.objects[data.object];
                            if (object) {
                                object.propertyUpdate(data.signals, data.properties);
                            } else {
                                console.warn("Unhandled property update: " + data.object + " :: " + JSON.stringify(data));
                            }
                        }
                        channel.exec({type: QWebChannelMessageTypes.idle});
                    };

                    this.debug = function(message)
                    {
                        channel.send({type: QWebChannelMessageTypes.debug, data: message});
                    };

                    channel.exec({type: QWebChannelMessageTypes.init}, function(data) {
                        for (var objectName in data) {
                            var object = new QObject(objectName, data[objectName], channel);
                        }
                        // now unwrap properties, which might reference other registered objects
                        for (var objectName in channel.objects) {
                            channel.objects[objectName].unwrapProperties();
                        }
                        if (initCallback) {
                            initCallback(channel);
                        }
                        channel.exec({type: QWebChannelMessageTypes.idle});
                    });
                };

                function QObject(name, data, webChannel)
                {
                    this.__id__ = name;
                    webChannel.objects[name] = this;

                    // List of callbacks that get invoked upon signal emission
                    this.__objectSignals__ = {};

                    // Cache of all properties, updated when a notify signal is emitted
                    this.__propertyCache__ = {};

                    var object = this;

                    // ----------------------------------------------------------------------

                    this.unwrapQObject = function(response)
                    {
                        if (response instanceof Array) {
                            // support list of objects
                            var ret = new Array(response.length);
                            for (var i = 0; i < response.length; ++i) {
                                ret[i] = object.unwrapQObject(response[i]);
                            }
                            return ret;
                        }
                        if (!response
                            || !response["__QObject*__"]
                            || response.id === undefined) {
                            return response;
                        }

                        var objectId = response.id;
                        if (webChannel.objects[objectId])
                            return webChannel.objects[objectId];

                        if (!response.data) {
                            console.error("Cannot unwrap unknown QObject " + objectId + " without data.");
                            return;
                        }

                        var qObject = new QObject( objectId, response.data, webChannel );
                        qObject.destroyed.connect(function() {
                            if (webChannel.objects[objectId] === qObject) {
                                delete webChannel.objects[objectId];
                                // reset the now deleted QObject to an empty {} object
                                // just assigning {} though would not have the desired effect, but the
                                // below also ensures all external references will see the empty map
                                // NOTE: this detour is necessary to workaround QTBUG-40021
                                var propertyNames = [];
                                for (var propertyName in qObject) {
                                    propertyNames.push(propertyName);
                                }
                                for (var idx in propertyNames) {
                                    delete qObject[propertyNames[idx]];
                                }
                            }
                        });
                        // here we are already initialized, and thus must directly unwrap the properties
                        qObject.unwrapProperties();
                        return qObject;
                    }

                    this.unwrapProperties = function()
                    {
                        for (var propertyIdx in object.__propertyCache__) {
                            object.__propertyCache__[propertyIdx] = object.unwrapQObject(object.__propertyCache__[propertyIdx]);
                        }
                    }

                    function addSignal(signalData, isPropertyNotifySignal)
                    {
                        var signalName = signalData[0];
                        var signalIndex = signalData[1];
                        object[signalName] = {
                            connect: function(callback) {
                                if (typeof(callback) !== "function") {
                                    console.error("Bad callback given to connect to signal " + signalName);
                                    return;
                                }

                                object.__objectSignals__[signalIndex] = object.__objectSignals__[signalIndex] || [];
                                object.__objectSignals__[signalIndex].push(callback);

                                if (!isPropertyNotifySignal && signalName !== "destroyed") {
                                    // only required for "pure" signals, handled separately for properties in propertyUpdate
                                    // also note that we always get notified about the destroyed signal
                                    webChannel.exec({
                                        type: QWebChannelMessageTypes.connectToSignal,
                                        object: object.__id__,
                                        signal: signalIndex
                                    });
                                }
                            },
                            disconnect: function(callback) {
                                if (typeof(callback) !== "function") {
                                    console.error("Bad callback given to disconnect from signal " + signalName);
                                    return;
                                }
                                object.__objectSignals__[signalIndex] = object.__objectSignals__[signalIndex] || [];
                                var idx = object.__objectSignals__[signalIndex].indexOf(callback);
                                if (idx === -1) {
                                    console.error("Cannot find connection of signal " + signalName + " to " + callback.name);
                                    return;
                                }
                                object.__objectSignals__[signalIndex].splice(idx, 1);
                                if (!isPropertyNotifySignal && object.__objectSignals__[signalIndex].length === 0) {
                                    // only required for "pure" signals, handled separately for properties in propertyUpdate
                                    webChannel.exec({
                                        type: QWebChannelMessageTypes.disconnectFromSignal,
                                        object: object.__id__,
                                        signal: signalIndex
                                    });
                                }
                            }
                        };
                    }

                    /**
                     * Invokes all callbacks for the given signalname. Also works for property notify callbacks.
                     */
                    function invokeSignalCallbacks(signalName, signalArgs)
                    {
                        var connections = object.__objectSignals__[signalName];
                        if (connections) {
                            connections.forEach(function(callback) {
                                callback.apply(callback, signalArgs);
                            });
                        }
                    }

                    this.propertyUpdate = function(signals, propertyMap)
                    {
                        // update property cache
                        for (var propertyIndex in propertyMap) {
                            var propertyValue = propertyMap[propertyIndex];
                            object.__propertyCache__[propertyIndex] = propertyValue;
                        }

                        for (var signalName in signals) {
                            // Invoke all callbacks, as signalEmitted() does not. This ensures the
                            // property cache is updated before the callbacks are invoked.
                            invokeSignalCallbacks(signalName, signals[signalName]);
                        }
                    }

                    this.signalEmitted = function(signalName, signalArgs)
                    {
                        invokeSignalCallbacks(signalName, signalArgs);
                    }

                    function addMethod(methodData)
                    {
                        var methodName = methodData[0];
                        var methodIdx = methodData[1];
                        object[methodName] = function() {
                            var args = [];
                            var callback;
                            for (var i = 0; i < arguments.length; ++i) {
                                if (typeof arguments[i] === "function")
                                    callback = arguments[i];
                                else
                                    args.push(arguments[i]);
                            }

                            webChannel.exec({
                                "type": QWebChannelMessageTypes.invokeMethod,
                                "object": object.__id__,
                                "method": methodIdx,
                                "args": args
                            }, function(response) {
                                if (response !== undefined) {
                                    var result = object.unwrapQObject(response);
                                    if (callback) {
                                        (callback)(result);
                                    }
                                }
                            });
                        };
                    }

                    function bindGetterSetter(propertyInfo)
                    {
                        var propertyIndex = propertyInfo[0];
                        var propertyName = propertyInfo[1];
                        var notifySignalData = propertyInfo[2];
                        // initialize property cache with current value
                        // NOTE: if this is an object, it is not directly unwrapped as it might
                        // reference other QObject that we do not know yet
                        object.__propertyCache__[propertyIndex] = propertyInfo[3];

                        if (notifySignalData) {
                            if (notifySignalData[0] === 1) {
                                // signal name is optimized away, reconstruct the actual name
                                notifySignalData[0] = propertyName + "Changed";
                            }
                            addSignal(notifySignalData, true);
                        }

                        Object.defineProperty(object, propertyName, {
                            configurable: true,
                            get: function () {
                                var propertyValue = object.__propertyCache__[propertyIndex];
                                if (propertyValue === undefined) {
                                    // This shouldn't happen
                                    console.warn("Undefined value in property cache for property \"" + propertyName + "\" in object " + object.__id__);
                                }

                                return propertyValue;
                            },
                            set: function(value) {
                                if (value === undefined) {
                                    console.warn("Property setter for " + propertyName + " called with undefined value!");
                                    return;
                                }
                                object.__propertyCache__[propertyIndex] = value;
                                webChannel.exec({
                                    "type": QWebChannelMessageTypes.setProperty,
                                    "object": object.__id__,
                                    "property": propertyIndex,
                                    "value": value
                                });
                            }
                        });

                    }

                    // ----------------------------------------------------------------------

                    data.methods.forEach(addMethod);

                    data.properties.forEach(bindGetterSetter);

                    data.signals.forEach(function(signal) { addSignal(signal, false); });

                    for (var name in data.enums) {
                        object[name] = data.enums[name];
                    }
                }

                //required for use with nodejs
                if (typeof module === 'object') {
                    module.exports = {
                        QWebChannel: QWebChannel
                    };
                }

                if (typeof window !== "undefined") {
                    window.QWebChannel = QWebChannel;
                }

                })();
                """
                logger.info("QWebChannel JS content loaded successfully")
            except Exception as e:
                logger.error(f"Error loading QWebChannel JS content: {str(e)}")
                # Set a fallback that won't break the injection
                cls._qwebchannel_js_content = "// QWebChannel fallback"
    
    def _setup_web_channel(self):
        """Set up the web channel for JavaScript communication."""
        try:
            # Create web channel
            self.channel = QWebChannel()
            
            # Create and register the bridge
            if hasattr(self, 'bridge'):
                self.channel.registerObject('pyBridge', self.bridge)
            
            # Set web channel on the page
            if hasattr(self, 'page') and self.page:
                self.page.setWebChannel(self.channel)
                logger.debug(f"Web channel set up for {self.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Error setting up web channel for {self.__class__.__name__}: {str(e)}", exc_info=True)

    def test_bridge_connection(self):
        """Test method to verify bridge is working."""
        logger.info(f"Testing bridge connection for {self.__class__.__name__}")
        if hasattr(self, 'bridge') and self.bridge:
            logger.info(f"Bridge exists for {self.__class__.__name__}")
            # Simulate a test signal
            self.bridge.onUserInput("Bridge test message")
        else:
            logger.error(f"No bridge found for {self.__class__.__name__}")

    def send_prompt(self, prompt: str, programmatic: bool = False):
        """Send a prompt to this pane (to be implemented by subclasses)."""
        logger.debug(f"send_prompt called for {self.__class__.__name__} with prompt: {len(prompt)} chars, programmatic: {programmatic}")
        # Default implementation: set the text using JavaScript
        if programmatic:
            self.setExternalText(prompt)
        else:
            # Emit signal for synchronization
            self.promptSubmitted.emit(prompt)
    
    def sync_text_from_other_pane(self, text: str):
        """Sync text from another pane (fallback to setExternalText)."""
        logger.debug(f"sync_text_from_other_pane called for {self.__class__.__name__} with text: {len(text)} chars")
        self.setExternalText(text)

    def _poll_for_input_changes(self):
        """Poll for input changes by directly checking common input elements"""
        if not hasattr(self, 'web_view') or not self.web_view or self._is_syncing:
            return
            
        # JavaScript to check for input in common AI chat interfaces
        js_code = """
        (function() {
            var inputSelectors = [
                // ChatGPT selectors
                '#prompt-textarea',
                'textarea[data-testid="textbox"]',
                'textarea[placeholder*="Message"]',
                '[data-testid="gizmo-composer-input"]',
                // Grok selectors (enhanced for actual chat interface)
                'textarea[placeholder*="Ask Grok"]',
                'textarea[placeholder*="Message Grok"]',
                'textarea[data-testid="grok-input"]',
                'div[data-testid="chat-input"]',
                'div[data-testid="composer-input"]',
                'div[contenteditable="true"][data-testid*="input"]',
                'textarea[placeholder*="Ask"]',
                'textarea[placeholder*="What"]',
                'div[contenteditable="true"][placeholder*="Ask"]',
                'div[contenteditable="true"][placeholder*="What"]',
                // Additional Grok chat interface selectors
                'textarea[class*="composer"]',
                'textarea[class*="input"]',
                'div[contenteditable="true"][role="textbox"]',
                // Gemini selectors
                'div.input-area rich-textarea > div[contenteditable="true"]',
                'rich-textarea div[contenteditable="true"]',
                // Claude selectors
                'div[contenteditable="true"][data-testid="chat-input"]',
                'div.ProseMirror[contenteditable="true"]',
                // Generic selectors
                'textarea[placeholder*="message"]',
                'textarea[placeholder*="Chat"]',
                'textarea[placeholder*="Type"]',
                'textarea[name="prompt"]',
                'textarea[role="textbox"]',
                'div[contenteditable="true"]',
                'div[role="textbox"]',
                'input[type="text"]',
                '.ProseMirror'
            ];
            
            var currentText = "";
            var foundElement = null;
            
            // Add debugging for Grok specifically
            var isGrok = window.location.href.includes('grok.com') || window.location.href.includes('x.ai');
            if (isGrok) {
                console.log('GROK DEBUG: Current URL:', window.location.href);
                console.log('GROK DEBUG: All textareas:', document.querySelectorAll('textarea'));
                console.log('GROK DEBUG: All contenteditable divs:', document.querySelectorAll('div[contenteditable="true"]'));
                console.log('GROK DEBUG: All inputs:', document.querySelectorAll('input'));
                console.log('GROK DEBUG: Elements with placeholder containing "Ask":', document.querySelectorAll('[placeholder*="Ask"]'));
                console.log('GROK DEBUG: Elements with data-testid:', document.querySelectorAll('[data-testid]'));
            }
            
            for (var i = 0; i < inputSelectors.length; i++) {
                var elements = document.querySelectorAll(inputSelectors[i]);
                for (var j = 0; j < elements.length; j++) {
                    var element = elements[j];
                    var text = element.value || element.textContent || element.innerText || "";
                    if (text.trim().length > 0) {
                        currentText = text.trim();
                        foundElement = element;
                        if (isGrok) {
                            console.log('GROK DEBUG: Found text in element:', inputSelectors[i], 'text:', text);
                        }
                        break;
                    }
                }
                if (currentText) break;
            }
            
            // If no text found but we're on Grok, let's try to find any visible input element
            if (!currentText && isGrok) {
                var allInputs = document.querySelectorAll('textarea, input[type="text"], div[contenteditable="true"]');
                for (var k = 0; k < allInputs.length; k++) {
                    var input = allInputs[k];
                    var rect = input.getBoundingClientRect();
                    var isVisible = rect.width > 0 && rect.height > 0 && input.offsetParent !== null;
                    if (isVisible) {
                        var text = input.value || input.textContent || input.innerText || "";
                        if (text.trim().length > 0) {
                            currentText = text.trim();
                            console.log('GROK DEBUG: Found text in visible element:', input.tagName, input.className, input.placeholder, 'text:', text);
                            break;
                        }
                    }
                }
            }
            
            return currentText;
        })();
        """
        
        try:
            self.web_view.page().runJavaScript(js_code, self._handle_polled_input)
        except Exception as e:
            logger.debug(f"Error polling for input in {self.name}: {e}")
    
    def _handle_polled_input(self, result):
        """Handle the result from input polling"""
        current_text = result if isinstance(result, str) else ""
        current_text = current_text.strip()
        
        # Check if text has changed
        if current_text != self._last_input_text:
            # Handle text addition (meaningful text added)
            if len(current_text) > 3 and len(current_text) > len(self._last_input_text):
                self._last_input_text = current_text
                logger.info(f"🔥 Input detected via polling in {self.name}: {current_text[:50]}...")
                self.userInputDetectedInPane.emit(current_text, self)
            
            # Handle text deletion/clearing (text became shorter or empty)
            elif len(current_text) < len(self._last_input_text) and len(self._last_input_text) > 3:
                self._last_input_text = current_text
                logger.info(f"🗑️ Text deletion detected via polling in {self.name}: '{current_text}' (was: '{self._last_input_text[:30]}...')")
                self.userInputDetectedInPane.emit(current_text, self)
            
            # Handle complete clearing (text becomes empty)
            elif current_text == "" and self._last_input_text != "":
                self._last_input_text = current_text
                logger.info(f"🗑️ Text cleared via polling in {self.name}")
                self.userInputDetectedInPane.emit("", self)

    def sync_input_to_pane(self, text: str):
        """Sync input text to this pane's input field using site-specific selectors"""
        if not hasattr(self, 'web_view') or not self.web_view:
            return
        
        # Get the specific selectors for this pane type
        site_name = self.__class__.__name__
        
        # Site-specific JavaScript for setting text
        if site_name == "ChatGPTPane":
            js_code = f"""
            (function() {{
                var text = {repr(text)};
                var selectors = [
                    '#prompt-textarea',
                    'textarea[data-testid="textbox"]',
                    'textarea[placeholder*="Message"]',
                    'textarea[placeholder*="ChatGPT"]',
                    'div[contenteditable="true"][data-testid="textbox"]',
                    'textarea'
                ];
                
                console.log('ChatGPT: Trying to set text:', text);
                
                for (var i = 0; i < selectors.length; i++) {{
                    var selector = selectors[i];
                    var element = document.querySelector(selector);
                    console.log('ChatGPT: Trying selector', selector, 'found:', !!element);
                    
                    if (element && element.offsetParent !== null) {{
                        console.log('ChatGPT: Element details:', element.tagName, element.placeholder, element.getAttribute('data-testid'));
                        
                        // Focus first
                        element.focus();
                        
                        // Clear existing text and set new text
                        if (element.tagName === 'TEXTAREA') {{
                            element.value = text;
                        }} else {{
                            element.textContent = text;
                        }}
                        
                        // Trigger events
                        element.dispatchEvent(new Event('focus', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        element.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, key: 'a' }}));
                        element.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, key: 'a' }}));
                        
                        console.log('ChatGPT: Successfully set text to', selector, 'new value:', element.value || element.textContent);
                        return true;
                    }}
                }}
                
                // Debug: log all textarea and contenteditable elements
                console.log('ChatGPT: All textareas:', document.querySelectorAll('textarea'));
                console.log('ChatGPT: All contenteditable:', document.querySelectorAll('[contenteditable="true"]'));
                console.log('ChatGPT: All with data-testid:', document.querySelectorAll('[data-testid]'));
                
                return false;
            }})();
            """
        elif site_name == "GeminiPane":
            js_code = f"""
            (function() {{
                var text = {repr(text)};
                var selectors = [
                    'div.input-area rich-textarea > div[contenteditable="true"]',
                    'rich-textarea div[contenteditable="true"]',
                    'div[contenteditable="true"][data-testid="textbox"]',
                    'div[contenteditable="true"]',
                    'textarea'
                ];
                
                console.log('Gemini: Trying to set text:', text);
                
                for (var i = 0; i < selectors.length; i++) {{
                    var selector = selectors[i];
                    var element = document.querySelector(selector);
                    console.log('Gemini: Trying selector', selector, 'found:', !!element);
                    
                    if (element && element.offsetParent !== null) {{
                        console.log('Gemini: Element details:', element.tagName, element.getAttribute('contenteditable'));
                        
                        element.focus();
                        element.textContent = text;
                        
                        // Trigger events
                        element.dispatchEvent(new Event('focus', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        console.log('Gemini: Successfully set text to', selector, 'new value:', element.textContent);
                        return true;
                    }}
                }}
                
                console.log('Gemini: No suitable element found. All contenteditable:', document.querySelectorAll('[contenteditable="true"]'));
                return false;
            }})();
            """
        elif site_name == "GrokPane":
            js_code = f"""
            (function() {{
                var text = {repr(text)};
                var selectors = [
                    // Enhanced Grok selectors for actual chat interface
                    'textarea[placeholder*="Ask Grok"]',
                    'textarea[placeholder*="Message Grok"]',
                    'textarea[data-testid="grok-input"]',
                    'div[data-testid="chat-input"]',
                    'div[data-testid="composer-input"]',
                    'div[contenteditable="true"][data-testid*="input"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'textarea[placeholder*="Ask"]',
                    'textarea[placeholder*="What"]',
                    'textarea[placeholder*="Message"]',
                    'div[contenteditable="true"][placeholder*="Ask"]',
                    'div[contenteditable="true"][placeholder*="What"]',
                    // Class-based selectors for chat interface
                    'textarea[class*="composer"]',
                    'textarea[class*="input"]',
                    'textarea[class*="chat"]',
                    // Generic fallbacks
                    'div[contenteditable="true"]',
                    'textarea',
                    'input[type="text"]'
                ];
                
                console.log('Grok: Trying to set text:', text);
                console.log('Grok: Current URL:', window.location.href);
                
                // Enhanced debugging - show all possible input elements first
                console.log('Grok: DEBUG - All textareas:', document.querySelectorAll('textarea'));
                console.log('Grok: DEBUG - All contenteditable:', document.querySelectorAll('[contenteditable="true"]'));
                console.log('Grok: DEBUG - All inputs:', document.querySelectorAll('input'));
                console.log('Grok: DEBUG - All with data-testid:', document.querySelectorAll('[data-testid]'));
                console.log('Grok: DEBUG - All with placeholder:', document.querySelectorAll('[placeholder]'));
                
                var foundElement = null;
                
                for (var i = 0; i < selectors.length; i++) {{
                    var selector = selectors[i];
                    var element = document.querySelector(selector);
                    console.log('Grok: Trying selector', selector, 'found:', !!element);
                    
                    if (element) {{
                        var isVisible = element.offsetParent !== null && 
                                       window.getComputedStyle(element).display !== 'none' &&
                                       window.getComputedStyle(element).visibility !== 'hidden';
                        console.log('Grok: Element visible:', isVisible);
                        console.log('Grok: Element details:', element.tagName, element.className, element.placeholder, element.getAttribute('data-testid'));
                        
                        if (isVisible) {{
                            foundElement = element;
                            break;
                        }}
                    }}
                }}
                
                // If no element found with selectors, try to find any visible input in bottom half of page
                if (!foundElement) {{
                    console.log('Grok: No element found with selectors, searching for visible inputs...');
                    var allInputs = document.querySelectorAll('textarea, input[type="text"], div[contenteditable="true"]');
                    for (var j = 0; j < allInputs.length; j++) {{
                        var input = allInputs[j];
                        var rect = input.getBoundingClientRect();
                        var isVisible = rect.width > 0 && rect.height > 0 && input.offsetParent !== null &&
                                       rect.bottom > window.innerHeight * 0.3; // Bottom 70% of page
                        if (isVisible) {{
                            console.log('Grok: Found visible input:', input.tagName, input.className, input.placeholder);
                            foundElement = input;
                            break;
                        }}
                    }}
                }}
                
                if (foundElement) {{
                    console.log('Grok: Using element:', foundElement.tagName, foundElement.className, foundElement.placeholder);
                    
                    // Focus first
                    foundElement.focus();
                    
                    // Clear and set text
                    if (foundElement.tagName === 'TEXTAREA' || foundElement.tagName === 'INPUT') {{
                        foundElement.value = text;
                        console.log('Grok: Set textarea/input value:', foundElement.value);
                    }} else {{
                        foundElement.innerHTML = '';
                        foundElement.textContent = text;
                        console.log('Grok: Set contenteditable text:', foundElement.textContent);
                    }}
                    
                    // Trigger comprehensive events
                    foundElement.dispatchEvent(new Event('focus', {{ bubbles: true }}));
                    foundElement.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    foundElement.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    foundElement.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, key: 'a' }}));
                    foundElement.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, key: 'a' }}));
                    foundElement.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    foundElement.dispatchEvent(new Event('focusout', {{ bubbles: true }}));
                    
                    console.log('Grok: Successfully set text');
                    return true;
                }} else {{
                    console.log('Grok: No suitable input element found');
                    // Log all elements that might be inputs for debugging
                    var allElements = document.querySelectorAll('*');
                    var potentialInputs = [];
                    for (var k = 0; k < allElements.length; k++) {{
                        var el = allElements[k];
                        if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' || 
                            el.contentEditable === 'true' || el.getAttribute('role') === 'textbox') {{
                            potentialInputs.push({{
                                tag: el.tagName,
                                className: el.className,
                                placeholder: el.placeholder,
                                id: el.id,
                                dataTestId: el.getAttribute('data-testid'),
                                visible: el.offsetParent !== null
                            }});
                        }}
                    }}
                    console.log('Grok: All potential input elements:', potentialInputs);
                    return false;
                }}
            }})();
            """
        elif site_name == "ClaudePane":
            js_code = f"""
            (function() {{
                var text = {repr(text)};
                var selectors = [
                    'div[contenteditable="true"][data-testid="chat-input"]',
                    'div.ProseMirror[contenteditable="true"]',
                    'div[contenteditable="true"]'
                ];
                
                for (var selector of selectors) {{
                    var element = document.querySelector(selector);
                    if (element && element.offsetParent !== null) {{
                        element.textContent = text;
                        element.focus();
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        console.log('Claude: Set text to', selector);
                        return true;
                    }}
                }}
                return false;
            }})();
            """
        else:
            # Generic fallback
            js_code = f"""
            (function() {{
                var text = {repr(text)};
                var selectors = [
                    'textarea[placeholder*="message"]',
                    'textarea[placeholder*="Ask"]',
                    'textarea[data-testid="textbox"]',
                    'div[contenteditable="true"]',
                    'textarea'
                ];
                
                for (var selector of selectors) {{
                    var element = document.querySelector(selector);
                    if (element && element.offsetParent !== null) {{
                        if (element.tagName === 'TEXTAREA') {{
                            element.value = text;
                        }} else {{
                            element.textContent = text;
                        }}
                        element.focus();
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        console.log('Generic: Set text to', selector);
                        return true;
                    }}
                }}
                return false;
            }})();
            """
        
        try:
            # Set sync flag to prevent polling interference
            self._is_syncing = True
            
            def handle_sync_result(success):
                self._is_syncing = False
                if success:
                    logger.info(f"✅ Text sync to {site_name}: SUCCESS - {text[:30]}...")
                    # Update last text to prevent re-detection
                    self._last_input_text = text
                else:
                    logger.warning(f"⚠️ Text sync to {site_name}: FAILED - {text[:30]}...")
                    
            self.web_view.page().runJavaScript(js_code, handle_sync_result)
        except Exception as e:
            self._is_syncing = False
            logger.error(f"❌ Error syncing text to {site_name}: {e}")