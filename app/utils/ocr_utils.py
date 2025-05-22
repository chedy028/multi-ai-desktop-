import pytesseract
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QRect
import pyautogui

class OCRFinder:
    def __init__(self):
        """Initialize the OCR finder with default settings."""
        # Configure pytesseract path
        try:
            # Test if pytesseract is working
            pytesseract.get_tesseract_version()
            print("Tesseract is properly configured")
        except Exception as e:
            print(f"Error configuring Tesseract: {str(e)}")
            print("Please make sure Tesseract is installed and the path is correctly set")

    def test_ocr(self, text: str = "Test OCR") -> bool:
        """
        Test if OCR is working by creating a simple image with text and trying to read it.
        
        Args:
            text: The text to test OCR with
            
        Returns:
            bool: True if OCR is working correctly, False otherwise
        """
        try:
            # Create a blank image
            img = np.ones((100, 300), dtype=np.uint8) * 255
            
            # Add text to the image
            cv2.putText(img, text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            # Try to read the text
            result = pytesseract.image_to_string(img)
            
            # Check if the text was read correctly
            if text.lower() in result.lower():
                print(f"OCR test successful! Detected text: {result.strip()}")
                return True
            else:
                print(f"OCR test failed. Expected '{text}', got '{result.strip()}'")
                return False
                
        except Exception as e:
            print(f"Error during OCR test: {str(e)}")
            return False

    def capture_widget(self, widget: QWidget) -> np.ndarray:
        """
        Capture a screenshot of the given widget and save it for inspection.
        
        Args:
            widget: The QWidget to capture
            
        Returns:
            numpy array of the captured image in BGR format
        """
        # Get widget geometry
        rect = widget.geometry()
        # Capture screen region
        screenshot = pyautogui.screenshot(region=(
            rect.x(), rect.y(), rect.width(), rect.height()
        ))
        # Convert to numpy array and BGR format for OpenCV
        img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        # Save for inspection
        cv2.imwrite("debug_capture.png", img_bgr)
        print("[DEBUG] Saved widget capture to debug_capture.png")
        return img_bgr

    def preprocess_for_ocr(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Preprocess the image for better OCR accuracy: grayscale, contrast, thresholding.
        Args:
            img_bgr: The input image in BGR format (numpy array)
        Returns:
            Preprocessed image (numpy array)
        """
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def find_input_box(self, widget: QWidget, target_text: str = "Ask anything") -> Optional[Tuple[int, int, int, int]]:
        """
        Find the input box in the widget using OCR.
        
        Args:
            widget: The QWidget to search in
            target_text: The text to look for (default: "Ask anything")
            
        Returns:
            Tuple of (x, y, width, height) if found, None otherwise
        """
        # Capture the widget
        img = self.capture_widget(widget)
        # Preprocess for OCR
        img = self.preprocess_for_ocr(img)
        # Perform OCR
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        # Print all OCR blocks for debugging
        for i, txt in enumerate(data['text']):
            print(f"[OCR DEBUG] Block#{i}: '{txt}' @ ({data['left'][i]}, {data['top'][i]})")
        # Find the target text
        for i, txt in enumerate(data['text']):
            if target_text.lower() in txt.strip().lower():
                return (
                    data['left'][i],
                    data['top'][i],
                    data['width'][i],
                    data['height'][i]
                )
        return None

    def click_input_box(self, widget: QWidget, target_text: str = "Ask anything") -> bool:
        """
        Find and click the input box in the widget.
        
        Args:
            widget: The QWidget to search in
            target_text: The text to look for (default: "Ask anything")
            
        Returns:
            True if successful, False otherwise
        """
        bbox = self.find_input_box(widget, target_text)
        if bbox:
            x, y, w, h = bbox
            # Calculate center point
            center_x = x + w//2
            center_y = y + h//2
            
            # Get widget's global position
            global_pos = widget.mapToGlobal(widget.rect().topLeft())
            
            # Click at the center of the input box
            pyautogui.click(
                global_pos.x() + center_x,
                global_pos.y() + center_y
            )
            return True
        return False 