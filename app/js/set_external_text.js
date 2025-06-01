(function() {
    var currentSelector = window.paneConfig.inputSelector;
    var inputElement = document.querySelector(currentSelector);
    if (inputElement) {
        inputElement._isProgrammaticUpdate = true;

        var scrollTop = inputElement.scrollTop;

        if (inputElement.tagName === 'TEXTAREA' || (inputElement.tagName === 'INPUT' && (inputElement.type === 'text' || inputElement.type === 'search'))) {
            inputElement.focus();
            inputElement.value = window.paneConfig.textToSet;
            var inputEvent = new Event('input', { bubbles: true, cancelable: true });
            inputElement.dispatchEvent(inputEvent);
            var changeEvent = new Event('change', { bubbles: true, cancelable: true });
            inputElement.dispatchEvent(changeEvent);
            // Attempt to dispatch keydown/keyup for Space to further nudge UI
            var kdEvent = new KeyboardEvent('keydown', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
            inputElement.dispatchEvent(kdEvent);
            var kuEvent = new KeyboardEvent('keyup', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
            inputElement.dispatchEvent(kuEvent);
        } else if (inputElement.isContentEditable) {
            inputElement.focus();
            inputElement.innerText = window.paneConfig.textToSet;
            var inputEvent = new Event('input', { bubbles: true, cancelable: true });
            inputElement.dispatchEvent(inputEvent);
            var kdEvent = new KeyboardEvent('keydown', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
            inputElement.dispatchEvent(kdEvent);
            var kuEvent = new KeyboardEvent('keyup', { 'key': ' ', 'code': 'Space', 'keyCode': 32, 'which': 32, 'bubbles': true, 'cancelable': true });
            inputElement.dispatchEvent(kuEvent);
        } else {
            inputElement.textContent = window.paneConfig.textToSet;
        }
        
        inputElement.scrollTop = scrollTop;
        delete inputElement._isProgrammaticUpdate;

    } else {
        console.warn(`JS (setExternalText in ${window.paneConfig.paneName}): Could not find input element with selector: ${currentSelector}`);
    }
})(); 