(function() {
    var maxAttempts = 5;
    var attemptDelay = 500; // 500ms between attempts
    var currentAttempt = 0;
    
    function trySetExternalText() {
        currentAttempt++;
        
        var currentSelector = window.paneConfig.inputSelector;
        var inputElement = document.querySelector(currentSelector);
        
        if (inputElement) {
            console.log(`JS (setExternalText in ${window.paneConfig.paneName}): Found input element on attempt ${currentAttempt}, setting text`);
            
            inputElement._isProgrammaticUpdate = true;
            var scrollTop = inputElement.scrollTop;

            if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {
                inputElement.focus();
                inputElement.value = window.paneConfig.textToSet;
                
                // Dispatch events to trigger any UI updates
                var inputEvent = new Event('input', { bubbles: true, cancelable: true });
                inputElement.dispatchEvent(inputEvent);
                var changeEvent = new Event('change', { bubbles: true, cancelable: true });
                inputElement.dispatchEvent(changeEvent);
                
                // Attempt to dispatch keydown/keyup for Space to further nudge UI
                var kdEvent = new KeyboardEvent('keydown', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
                inputElement.dispatchEvent(kdEvent);
                var kuEvent = new KeyboardEvent('keyup', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
                inputElement.dispatchEvent(kuEvent);
                
            } else if (inputElement.isContentEditable || inputElement.hasAttribute('contenteditable')) {
                inputElement.focus();
                inputElement.innerText = window.paneConfig.textToSet;
                
                // Dispatch events
                var inputEvent = new Event('input', { bubbles: true, cancelable: true });
                inputElement.dispatchEvent(inputEvent);
                var kdEvent = new KeyboardEvent('keydown', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
                inputElement.dispatchEvent(kdEvent);
                var kuEvent = new KeyboardEvent('keyup', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
                inputElement.dispatchEvent(kuEvent);
                
            } else {
                // Fallback for other element types
                inputElement.textContent = window.paneConfig.textToSet;
            }
            
            // Restore scroll position
            if (scrollTop !== undefined) {
                inputElement.scrollTop = scrollTop;
            }
            
            // Clean up programmatic update flag after a short delay
            setTimeout(function() {
                delete inputElement._isProgrammaticUpdate;
            }, 100);
            
            console.log(`JS (setExternalText in ${window.paneConfig.paneName}): Successfully set text: "${window.paneConfig.textToSet}"`);
            
        } else if (currentAttempt < maxAttempts) {
            console.warn(`JS (setExternalText in ${window.paneConfig.paneName}): Could not find input element on attempt ${currentAttempt}/${maxAttempts}, retrying in ${attemptDelay}ms`);
            setTimeout(trySetExternalText, attemptDelay);
        } else {
            console.error(`JS (setExternalText in ${window.paneConfig.paneName}): Failed to find input element after ${maxAttempts} attempts with selector: ${currentSelector}`);
            // Log available input elements for debugging
            console.log(`JS (setExternalText in ${window.paneConfig.paneName}): Available textareas:`, document.querySelectorAll('textarea'));
            console.log(`JS (setExternalText in ${window.paneConfig.paneName}): Available inputs:`, document.querySelectorAll('input'));
            console.log(`JS (setExternalText in ${window.paneConfig.paneName}): Available contenteditable elements:`, document.querySelectorAll('[contenteditable="true"]'));
        }
    }
    
    // Start the attempt process
    trySetExternalText();
})(); 