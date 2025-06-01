(function() { 
    var bridgeInitialized = false;
    var attachAttempts = 0;
    const maxAttachAttempts = 15;
    const attachInterval = 300;

    function tryAttachListener() {
        attachAttempts++;
        var currentSelector = window.paneConfig.inputSelector;
        var inputElement = document.querySelector(currentSelector);

        if (inputElement) {
            console.log(`JS (${window.paneConfig.paneName}): Input listener attached to element:`, inputElement, `using selector: ` + currentSelector);
            inputElement.addEventListener('input', function(event) {
                if (inputElement._isProgrammaticUpdate) {
                    return; 
                }
                if (window.pyBridge && window.pyBridge.onUserInput) {
                    let text = '';
                    if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {
                        text = inputElement.value;
                    } else if (inputElement.hasAttribute('contenteditable')) {
                        text = inputElement.innerText;
                    }
                    window.pyBridge.onUserInput(text);
                } else {
                    console.warn(`JS (${window.paneConfig.paneName}): pyBridge or onUserInput not available when input event fired.`);
                }
            });
        } else {
            if (attachAttempts < maxAttachAttempts) {
                setTimeout(tryAttachListener, attachInterval);
            } else {
                console.error(`JS (${window.paneConfig.paneName}): Failed to find input element after ${maxAttachAttempts} attempts. Selector: ` + currentSelector);
            }
        }
    }

    function initWebChannelAndListeners() {
        if (typeof QWebChannel === 'undefined' || typeof QWebChannel.constructor !== 'function') {
            console.error(`JS (${window.paneConfig.paneName}): QWebChannel is not defined. Cannot establish pyBridge. Input listener WILL NOT WORK.`);
            return;
        }
        try {
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.pyBridge = channel.objects.pyBridge;
                bridgeInitialized = true;
                console.log(`JS (${window.paneConfig.paneName}): pyBridge initialized successfully via QWebChannel.`);
                tryAttachListener();
            });
        } catch (e) {
            console.error(`JS (${window.paneConfig.paneName}): Error initializing QWebChannel:`, e, '. Input listener WILL NOT WORK.');
        }
    }
    
    // Check if pyBridge is already available
    if (window.pyBridge && window.pyBridge.onUserInput) {
        console.log(`JS (${window.paneConfig.paneName}): pyBridge already available. Proceeding to attach listener.`);
        bridgeInitialized = true;
        tryAttachListener();
    } else if (typeof qt !== 'undefined' && qt.webChannelTransport) {
        initWebChannelAndListeners();
    } else {
        console.warn(`JS (${window.paneConfig.paneName}): qt.webChannelTransport not immediately available. Will retry QWebChannel init and listener attachment.`);
        let channelInitAttempts = 0;
        const maxChannelInitAttempts = 5;
        const channelInitInterval = 500;
        function retryInitWebChannel() {
            if (typeof qt !== 'undefined' && qt.webChannelTransport) {
                initWebChannelAndListeners();
            } else {
                channelInitAttempts++;
                if (channelInitAttempts < maxChannelInitAttempts) {
                    setTimeout(retryInitWebChannel, channelInitInterval);
                } else {
                    console.error(`JS (${window.paneConfig.paneName}): Failed to initialize QWebChannel after multiple attempts. qt.webChannelTransport not found.`);
                }
            }
        }
        retryInitWebChannel();
    }
})(); 