import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app.panes.base_pane import BasePane

class TestPane(BasePane):
    """Test pane that inherits from BasePane for OCR testing."""
    URL = "https://chat.openai.com"  # Using ChatGPT as a test site
    JS_INPUT = "textarea"  # ChatGPT's input selector

def main():
    app = QApplication(sys.argv)
    
    # Create test pane
    pane = TestPane()
    pane.resize(800, 600)
    pane.show()
    
    # Wait for the page to load
    def test_ocr():
        print("Testing OCR functionality...")
        
        # Try to find the input box
        location = pane.find_input_location()
        if location:
            x, y, w, h = location
            print(f"Found input box at: x={x}, y={y}, width={w}, height={h}")
            
            # Try to click it
            if pane.find_and_click_input():
                print("Successfully clicked the input box!")
            else:
                print("Failed to click the input box")
        else:
            print("Could not find the input box")
    
    # Wait 5 seconds for the page to load before testing
    QTimer.singleShot(5000, test_ocr)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 