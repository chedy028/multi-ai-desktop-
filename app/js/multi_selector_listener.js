(function() { 
    var bridgeInitialized = false;
    var attachAttempts = 0;
    var currentSelectorIndex = 0;
    const maxAttachAttempts = 20;
    const attachInterval = 500;
    const selectors = window.paneConfig.inputSelectors;

    function logDOMState() {
        console.log(`=== ${window.paneConfig.paneName} DOM INSPECTION ===`);
        console.log(`URL: ${window.location.href}`);
        console.log(`Title: "${document.title}"`);
        
        var allInputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        console.log(`Total input elements found: ${allInputs.length}`);
        
        allInputs.forEach((el, idx) => {
            var rect = el.getBoundingClientRect();
            var isVisible = rect.width > 0 && rect.height > 0 && 
                           window.getComputedStyle(el).display !== 'none' &&
                           window.getComputedStyle(el).visibility !== 'hidden';
            
            console.log(`[${idx}] ${el.tagName} - Visible: ${isVisible}`);
            console.log(`    Placeholder: "${el.placeholder || ''}"`);
            console.log(`    DataTestId: "${el.getAttribute('data-testid') || ''}"`);
            console.log(`    Classes: "${el.className || ''}"`);
            console.log(`    ID: "${el.id || ''}"`);
            console.log(`    ContentEditable: ${el.contentEditable}`);
            console.log(`    Size: ${rect.width}x${rect.height} at (${rect.x}, ${rect.y})`);
            
            if (el.parentElement) {
                console.log(`    Parent: ${el.parentElement.tagName} - "${el.parentElement.className || ''}"`);
            }
            console.log('    ---');
        });
        
        var forms = document.querySelectorAll('form');
        console.log(`Forms found: ${forms.length}`);
        forms.forEach((form, idx) => {
            var formInputs = form.querySelectorAll('input, textarea, [contenteditable="true"]');
            console.log(`Form ${idx}: ${formInputs.length} inputs`);
        });
        
        console.log('=== END INSPECTION ===');
    }

    function tryAttachListener() {
        attachAttempts++;
        
        if (window.paneConfig.enableDOMInspection) {
            logDOMState();
        }
        
        for (let i = 0; i < selectors.length; i++) {
            var currentSelector = selectors[i];
            console.log(`JS (${window.paneConfig.paneName}): Trying selector ${i+1}/${selectors.length}: ${currentSelector}`);
            var inputElement = document.querySelector(currentSelector);

            if (inputElement) {
                console.log(`JS (${window.paneConfig.paneName}): SUCCESS! Input listener attached to element using selector ${i+1}: ${currentSelector}`, inputElement);
                
                ['input', 'keyup', 'paste'].forEach(eventType => {
                    inputElement.addEventListener(eventType, function(event) {
                        if (inputElement._isProgrammaticUpdate) {
                            return; 
                        }
                        if (window.pyBridge && window.pyBridge.onUserInput) {
                            let text = '';
                            if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {
                                text = inputElement.value;
                            } else if (inputElement.hasAttribute('contenteditable')) {
                                text = inputElement.innerText || inputElement.textContent || '';
                            }
                            console.log(`JS (${window.paneConfig.paneName}): Sending text to Python via ${eventType}: "${text}"`);
                            window.pyBridge.onUserInput(text);
                        } else {
                            console.warn(`JS (${window.paneConfig.paneName}): pyBridge or onUserInput not available when ${eventType} event fired.`);
                        }
                    });
                });
                
                window[window.paneConfig.paneName.toLowerCase() + 'WorkingSelector'] = currentSelector;
                return;
            }
        }
        
        if (attachAttempts < maxAttachAttempts) {
            console.warn(`JS (${window.paneConfig.paneName}): No input element found with any selector (Attempt ${attachAttempts}/${maxAttachAttempts}). Retrying in ${attachInterval}ms.`);
            setTimeout(tryAttachListener, attachInterval);
        } else {
            console.error(`JS (${window.paneConfig.paneName}): Failed to find input element after ${maxAttachAttempts} attempts with all selectors.`);
            console.log(`JS (${window.paneConfig.paneName}): Available textareas:`, document.querySelectorAll('textarea'));
            console.log(`JS (${window.paneConfig.paneName}): Available inputs:`, document.querySelectorAll('input'));
            console.log(`JS (${window.paneConfig.paneName}): Available contenteditable elements:`, document.querySelectorAll('[contenteditable="true"]'));
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
    
    if (window.pyBridge && window.pyBridge.onUserInput) {
        console.log(`JS (${window.paneConfig.paneName}): pyBridge already available. Proceeding to attach listener.`);
        bridgeInitialized = true;
        tryAttachListener();
    } else if (typeof qt !== 'undefined' && qt.webChannelTransport) {
        initWebChannelAndListeners();
    } else {
        console.warn(`JS (${window.paneConfig.paneName}): qt.webChannelTransport not immediately available. Will retry QWebChannel init.`);
        let channelInitAttempts = 0;
        const maxChannelInitAttempts = 10;
        const channelInitInterval = 1000;
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