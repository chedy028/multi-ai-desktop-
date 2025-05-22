from app.utils.ocr_utils import OCRFinder
from PySide6.QtWidgets import QApplication, QMainWindow, QLineEdit, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt
import sys
import cv2
import numpy as np

def create_test_window():
    # Create the main window
    window = QMainWindow()
    window.setWindowTitle("OCR Test Window")
    window.setGeometry(100, 100, 400, 200)
    
    # Create central widget and layout
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Create a label with the target text
    label = QLabel("Ask anything")
    label.setStyleSheet("font-size: 16px; font-weight: bold;")
    layout.addWidget(label)
    
    # Create input box
    input_box = QLineEdit()
    input_box.setPlaceholderText("Type here...")
    input_box.setMinimumHeight(30)
    layout.addWidget(input_box)
    
    return window

def main():
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create test window
    window = create_test_window()
    window.show()
    
    # Create OCR finder instance
    ocr = OCRFinder()
    
    # Wait a moment for the window to be fully rendered
    app.processEvents()
    
    # Capture the window for debugging
    img = ocr.capture_widget(window.centralWidget())
    cv2.imwrite("debug_capture.png", img)
    print("Saved debug capture to debug_capture.png")
    
    # Try to find the input box
    print("\nSearching for 'Ask anything' text...")
    bbox = ocr.find_input_box(window.centralWidget())
    
    if bbox:
        x, y, w, h = bbox
        print(f"Found text at position: x={x}, y={y}, width={w}, height={h}")
        
        # Draw rectangle on debug image
        debug_img = img.copy()
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imwrite("debug_detection.png", debug_img)
        print("Saved debug detection to debug_detection.png")
        
        # Try to click the input box
        print("\nAttempting to click the input box...")
        if ocr.click_input_box(window.centralWidget()):
            print("Successfully clicked the input box!")
        else:
            print("Failed to click the input box")
    else:
        print("Could not find the text")
    
    # Keep the window open for a moment to see the results
    app.exec()

if __name__ == "__main__":
    main() 