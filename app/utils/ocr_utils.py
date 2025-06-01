"""
Enhanced OCR utilities for Multi-AI Desktop application.
"""
import pytesseract
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QRect, QPoint
import pyautogui
import time
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class OCRFinder:
    def __init__(self):
        """Initialize the OCR finder with default settings."""
        self.tesseract_available = False
        self.last_capture_path = "debug_capture.png"
        self.last_processed_path = "debug_processed.png"
        
        # Configure pytesseract path and test
        try:
            version = pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info(f"Tesseract OCR initialized successfully. Version: {version}")
        except Exception as e:
            logger.error(f"Error configuring Tesseract: {str(e)}")
            logger.error("Please make sure Tesseract is installed and the path is correctly set")
            self.tesseract_available = False

    def is_available(self) -> bool:
        """Check if OCR is available and working."""
        return self.tesseract_available

    def test_ocr(self, text: str = "Test OCR") -> bool:
        """
        Test if OCR is working by creating a simple image with text and trying to read it.
        
        Args:
            text: The text to test OCR with
            
        Returns:
            bool: True if OCR is working correctly, False otherwise
        """
        if not self.tesseract_available:
            logger.error("Tesseract is not available for testing")
            return False
            
        try:
            # Create a blank image with white background
            img = np.ones((100, 400), dtype=np.uint8) * 255
            
            # Add text to the image with good contrast
            cv2.putText(img, text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            # Save test image for debugging
            cv2.imwrite("ocr_test.png", img)
            
            # Try to read the text
            result = pytesseract.image_to_string(img, config='--psm 8')
            
            # Check if the text was read correctly
            if text.lower() in result.lower():
                logger.info(f"OCR test successful! Detected text: '{result.strip()}'")
                return True
            else:
                logger.warning(f"OCR test failed. Expected '{text}', got '{result.strip()}'")
                return False
                
        except Exception as e:
            logger.error(f"Error during OCR test: {str(e)}", exc_info=True)
            return False

    def capture_widget(self, widget: QWidget) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the given widget and save it for inspection.
        
        Args:
            widget: The QWidget to capture
            
        Returns:
            numpy array of the captured image in BGR format, or None if failed
        """
        try:
            # Get widget's global position and size
            global_pos = widget.mapToGlobal(QPoint(0, 0))
            size = widget.size()
            
            logger.debug(f"Capturing widget at ({global_pos.x()}, {global_pos.y()}) size {size.width()}x{size.height()}")
            
            # Capture screen region
            screenshot = pyautogui.screenshot(region=(
                global_pos.x(), global_pos.y(), size.width(), size.height()
            ))
            
            # Convert to numpy array and BGR format for OpenCV
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Save for inspection
            cv2.imwrite(self.last_capture_path, img_bgr)
            logger.debug(f"Saved widget capture to {self.last_capture_path}")
            
            return img_bgr
            
        except Exception as e:
            logger.error(f"Error capturing widget: {str(e)}", exc_info=True)
            return None

    def preprocess_for_ocr(self, img_bgr: np.ndarray, save_debug: bool = True) -> List[np.ndarray]:
        """
        Preprocess the image for better OCR accuracy using multiple strategies.
        
        Args:
            img_bgr: The input image in BGR format (numpy array)
            save_debug: Whether to save debug images
            
        Returns:
            List of preprocessed images to try with OCR
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            
            processed_images = []
            
            # Strategy 1: Simple threshold
            _, thresh1 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            processed_images.append(thresh1)
            
            # Strategy 2: Adaptive threshold
            thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            processed_images.append(thresh2)
            
            # Strategy 3: OTSU threshold
            _, thresh3 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(thresh3)
            
            # Strategy 4: Enhanced contrast + OTSU
            enhanced = cv2.equalizeHist(gray)
            _, thresh4 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(thresh4)
            
            # Strategy 5: Inverted (for dark backgrounds)
            _, thresh5 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            processed_images.append(thresh5)
            
            if save_debug:
                # Save the best looking one for debugging
                cv2.imwrite(self.last_processed_path, thresh3)
                logger.debug(f"Saved processed image to {self.last_processed_path}")
            
            return processed_images
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}", exc_info=True)
            return [img_bgr]  # Return original if preprocessing fails

    def find_text_in_image(self, img: np.ndarray, target_texts: List[str]) -> Optional[Tuple[int, int, int, int, str]]:
        """
        Find any of the target texts in the image using OCR.
        
        Args:
            img: Preprocessed image
            target_texts: List of texts to search for
            
        Returns:
            Tuple of (x, y, width, height, found_text) if found, None otherwise
        """
        try:
            # Try different PSM modes for better detection
            psm_modes = [6, 8, 7, 3, 4]  # Different page segmentation modes
            
            for psm in psm_modes:
                try:
                    config = f'--psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=config)
                    
                    # Check each detected text block
                    for i, detected_text in enumerate(data['text']):
                        if detected_text.strip():  # Skip empty detections
                            confidence = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
                            
                            # Check if any target text matches
                            for target_text in target_texts:
                                if self._text_matches(detected_text, target_text, confidence):
                                    logger.info(f"Found text '{detected_text}' (target: '{target_text}') with confidence {confidence}% using PSM {psm}")
                                    return (
                                        data['left'][i],
                                        data['top'][i],
                                        data['width'][i],
                                        data['height'][i],
                                        detected_text
                                    )
                except Exception as e:
                    logger.debug(f"PSM {psm} failed: {str(e)}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error in OCR text detection: {str(e)}", exc_info=True)
            return None

    def _text_matches(self, detected_text: str, target_text: str, confidence: int) -> bool:
        """
        Check if detected text matches target text with fuzzy matching.
        
        Args:
            detected_text: Text detected by OCR
            target_text: Target text to match
            confidence: OCR confidence level
            
        Returns:
            True if texts match
        """
        if confidence < 30:  # Skip very low confidence detections
            return False
            
        detected_lower = detected_text.lower().strip()
        target_lower = target_text.lower().strip()
        
        # Exact match
        if target_lower in detected_lower:
            return True
            
        # Fuzzy match for common OCR errors
        # Remove common OCR misreads
        detected_clean = detected_lower.replace('0', 'o').replace('1', 'l').replace('5', 's')
        target_clean = target_lower.replace('0', 'o').replace('1', 'l').replace('5', 's')
        
        if target_clean in detected_clean:
            return True
            
        # Check if most characters match (for partial matches)
        if len(target_lower) > 3:
            matches = sum(1 for a, b in zip(detected_lower, target_lower) if a == b)
            match_ratio = matches / max(len(detected_lower), len(target_lower))
            if match_ratio > 0.7:  # 70% character match
                return True
        
        return False

    def find_input_box(self, widget: QWidget, target_texts: List[str] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        Find the input box in the widget using OCR.
        
        Args:
            widget: The QWidget to search in
            target_texts: List of texts to look for (default: common input placeholders)
            
        Returns:
            Tuple of (x, y, width, height) if found, None otherwise
        """
        if not self.tesseract_available:
            logger.error("Tesseract is not available")
            return None
            
        if target_texts is None:
            target_texts = [
                "Ask anything", "Message", "Type a message", "Enter your message",
                "What can I help", "How can I help", "Ask me anything",
                "Type here", "Enter text", "Search", "Chat"
            ]
        
        logger.info(f"Searching for input box with texts: {target_texts}")
        
        # Capture the widget
        img = self.capture_widget(widget)
        if img is None:
            return None
        
        # Try multiple preprocessing strategies
        processed_images = self.preprocess_for_ocr(img)
        
        for i, processed_img in enumerate(processed_images):
            logger.debug(f"Trying preprocessing strategy {i+1}/{len(processed_images)}")
            result = self.find_text_in_image(processed_img, target_texts)
            if result:
                x, y, w, h, found_text = result
                logger.info(f"Found input box with text '{found_text}' at ({x}, {y}) size {w}x{h}")
                return (x, y, w, h)
        
        logger.warning("No input box found with OCR")
        return None

    def click_input_box(self, widget: QWidget, target_texts: List[str] = None) -> bool:
        """
        Find and click the input box in the widget.
        
        Args:
            widget: The QWidget to search in
            target_texts: List of texts to look for
            
        Returns:
            True if successful, False otherwise
        """
        bbox = self.find_input_box(widget, target_texts)
        if bbox:
            x, y, w, h = bbox
            
            # Calculate center point
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Get widget's global position
            global_pos = widget.mapToGlobal(QPoint(0, 0))
            
            # Calculate absolute click position
            click_x = global_pos.x() + center_x
            click_y = global_pos.y() + center_y
            
            logger.info(f"Clicking input box at ({click_x}, {click_y})")
            
            try:
                # Click at the center of the input box
                pyautogui.click(click_x, click_y)
                time.sleep(0.5)  # Give time for the click to register
                return True
            except Exception as e:
                logger.error(f"Error clicking input box: {str(e)}", exc_info=True)
                return False
        else:
            logger.warning("Could not find input box to click")
            return False

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the OCR system."""
        return {
            "tesseract_available": self.tesseract_available,
            "last_capture_path": self.last_capture_path,
            "last_processed_path": self.last_processed_path,
            "tesseract_version": pytesseract.get_tesseract_version() if self.tesseract_available else "Not available"
        } 