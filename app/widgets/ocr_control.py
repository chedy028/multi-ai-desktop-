"""
OCR Control Widget for Multi-AI Desktop application.
Provides user interface for OCR fallback system.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTextEdit, QGroupBox, QProgressBar, 
                               QComboBox, QCheckBox, QMessageBox, QFrame)
from PySide6.QtCore import Signal, QThread, QTimer, Qt
from PySide6.QtGui import QFont, QPixmap, QPalette
from typing import Optional, List
import os
from app.utils.ocr_utils import OCRFinder
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class OCRWorkerThread(QThread):
    """Worker thread for OCR operations to prevent UI blocking."""
    
    ocrCompleted = Signal(bool, str)  # success, message
    ocrProgress = Signal(str)  # progress message
    
    def __init__(self, ocr_finder: OCRFinder, widget: QWidget, target_texts: List[str]):
        super().__init__()
        self.ocr_finder = ocr_finder
        self.widget = widget
        self.target_texts = target_texts
        
    def run(self):
        """Run OCR operation in background thread."""
        try:
            self.ocrProgress.emit("Capturing widget screenshot...")
            
            # Skip the test during actual OCR operations - just check if Tesseract is available
            if not self.ocr_finder.is_available():
                self.ocrCompleted.emit(False, "OCR system not available. Please check Tesseract installation.")
                return
            
            self.ocrProgress.emit("Searching for input box...")
            
            # Try to find and click input box
            success = self.ocr_finder.click_input_box(self.widget, self.target_texts)
            
            if success:
                self.ocrCompleted.emit(True, "Successfully found and clicked input box!")
            else:
                self.ocrCompleted.emit(False, "Could not find input box with OCR. Check debug images for details.")
                
        except Exception as e:
            logger.error(f"Error in OCR worker thread: {str(e)}", exc_info=True)
            self.ocrCompleted.emit(False, f"OCR operation failed: {str(e)}")

class OCRControlWidget(QWidget):
    """Widget for controlling OCR fallback system."""
    
    ocrActivated = Signal(QWidget, list)  # widget, target_texts
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ocr_finder = OCRFinder()
        self.current_widget = None
        self.ocr_thread = None
        
        self.setup_ui()
        self.update_status()
        
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("OCR Fallback System")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Status section
        self.setup_status_section(layout)
        
        # Control section
        self.setup_control_section(layout)
        
        # Debug section
        self.setup_debug_section(layout)
        
        # Progress section
        self.setup_progress_section(layout)
        
    def setup_status_section(self, layout):
        """Set up the status section."""
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Checking OCR availability...")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        # Test OCR button
        self.test_button = QPushButton("Test OCR System")
        self.test_button.clicked.connect(self.test_ocr)
        status_layout.addWidget(self.test_button)
        
        layout.addWidget(status_group)
        
    def setup_control_section(self, layout):
        """Set up the control section."""
        control_group = QGroupBox("OCR Controls")
        control_layout = QVBoxLayout(control_group)
        
        # Target text selection
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Search for:"))
        
        self.text_combo = QComboBox()
        self.text_combo.setEditable(True)
        self.text_combo.addItems([
            "Ask anything",
            "what do you want to know",  # Grok pattern
            "Message",
            "Type a message", 
            "Enter your message",
            "What can I help",
            "How can I help",
            "Ask me anything",
            "Type here",
            "Enter text",
            "Search",
            "Chat",
            "Send a message",
            "Start typing",
            "Write something"
        ])
        text_layout.addWidget(self.text_combo)
        control_layout.addLayout(text_layout)
        
        # Options
        self.auto_mode_checkbox = QCheckBox("Auto-retry with different text patterns")
        self.auto_mode_checkbox.setChecked(True)
        control_layout.addWidget(self.auto_mode_checkbox)
        
        # Main OCR button
        self.ocr_button = QPushButton("🔍 Find Input Box with OCR")
        self.ocr_button.setMinimumHeight(40)
        self.ocr_button.clicked.connect(self.activate_ocr)
        control_layout.addWidget(self.ocr_button)
        
        layout.addWidget(control_group)
        
    def setup_debug_section(self, layout):
        """Set up the debug section."""
        debug_group = QGroupBox("Debug Information")
        debug_layout = QVBoxLayout(debug_group)
        
        # Debug info display
        self.debug_text = QTextEdit()
        self.debug_text.setMaximumHeight(100)
        self.debug_text.setReadOnly(True)
        debug_layout.addWidget(self.debug_text)
        
        # Debug buttons
        debug_buttons_layout = QHBoxLayout()
        
        self.refresh_debug_button = QPushButton("Refresh Debug Info")
        self.refresh_debug_button.clicked.connect(self.update_debug_info)
        debug_buttons_layout.addWidget(self.refresh_debug_button)
        
        self.view_images_button = QPushButton("View Debug Images")
        self.view_images_button.clicked.connect(self.view_debug_images)
        debug_buttons_layout.addWidget(self.view_images_button)
        
        debug_layout.addLayout(debug_buttons_layout)
        layout.addWidget(debug_group)
        
    def setup_progress_section(self, layout):
        """Set up the progress section."""
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
    def update_status(self):
        """Update the OCR system status."""
        if self.ocr_finder.is_available():
            debug_info = self.ocr_finder.get_debug_info()
            version = debug_info.get("tesseract_version", "Unknown")
            self.status_label.setText(f"✅ OCR System Ready\nTesseract Version: {version}")
            self.status_label.setStyleSheet("color: green;")
            self.ocr_button.setEnabled(True)
        else:
            self.status_label.setText("❌ OCR System Not Available\nPlease install Tesseract OCR")
            self.status_label.setStyleSheet("color: red;")
            self.ocr_button.setEnabled(False)
            
    def test_ocr(self):
        """Test the OCR system."""
        self.test_button.setEnabled(False)
        self.test_button.setText("Testing...")
        
        # Test OCR in a separate thread to avoid blocking UI
        QTimer.singleShot(100, self._run_ocr_test)
        
    def _run_ocr_test(self):
        """Run OCR test."""
        try:
            success = self.ocr_finder.test_ocr("Test OCR")
            if success:
                QMessageBox.information(self, "OCR Test", "✅ OCR test successful!\nThe system is working correctly.")
            else:
                QMessageBox.warning(self, "OCR Test", "❌ OCR test failed.\nPlease check your Tesseract installation.")
        except Exception as e:
            QMessageBox.critical(self, "OCR Test Error", f"Error during OCR test:\n{str(e)}")
        finally:
            self.test_button.setEnabled(True)
            self.test_button.setText("Test OCR System")
            
    def set_target_widget(self, widget: QWidget):
        """Set the widget to perform OCR on."""
        self.current_widget = widget
        logger.info(f"OCR target widget set to: {widget.__class__.__name__}")
        
    def activate_ocr(self):
        """Activate OCR to find input box."""
        if not self.current_widget:
            QMessageBox.warning(self, "No Target", "Please select a pane first.")
            return
            
        if not self.ocr_finder.is_available():
            QMessageBox.critical(self, "OCR Not Available", "OCR system is not available. Please install Tesseract.")
            return
            
        # Get target texts
        target_texts = []
        current_text = self.text_combo.currentText().strip()
        if current_text:
            target_texts.append(current_text)
            
        if self.auto_mode_checkbox.isChecked():
            # Add common variations
            default_texts = [
                "Ask anything", "what do you want to know", "Message", "Type a message", "Enter your message",
                "What can I help", "How can I help", "Ask me anything",
                "Type here", "Enter text", "Search", "Chat", "Send a message", "Start typing"
            ]
            for text in default_texts:
                if text not in target_texts:
                    target_texts.append(text)
        
        if not target_texts:
            target_texts = ["Ask anything"]  # Fallback
            
        logger.info(f"Starting OCR with target texts: {target_texts}")
        
        # Start OCR operation in background thread
        self.start_ocr_operation(target_texts)
        
    def start_ocr_operation(self, target_texts: List[str]):
        """Start OCR operation in background thread."""
        # Disable controls during operation
        self.ocr_button.setEnabled(False)
        self.ocr_button.setText("🔍 Searching...")
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_label.setVisible(True)
        self.progress_label.setText("Initializing OCR...")
        
        # Start worker thread
        self.ocr_thread = OCRWorkerThread(self.ocr_finder, self.current_widget, target_texts)
        self.ocr_thread.ocrCompleted.connect(self.on_ocr_completed)
        self.ocr_thread.ocrProgress.connect(self.on_ocr_progress)
        self.ocr_thread.start()
        
    def on_ocr_progress(self, message: str):
        """Handle OCR progress updates."""
        self.progress_label.setText(message)
        logger.debug(f"OCR Progress: {message}")
        
    def on_ocr_completed(self, success: bool, message: str):
        """Handle OCR completion."""
        # Hide progress
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        # Re-enable controls
        self.ocr_button.setEnabled(True)
        self.ocr_button.setText("🔍 Find Input Box with OCR")
        
        # Show result
        if success:
            QMessageBox.information(self, "OCR Success", f"✅ {message}")
            logger.info(f"OCR operation successful: {message}")
        else:
            QMessageBox.warning(self, "OCR Failed", f"❌ {message}")
            logger.warning(f"OCR operation failed: {message}")
            
        # Update debug info
        self.update_debug_info()
        
        # Clean up thread
        if self.ocr_thread:
            self.ocr_thread.deleteLater()
            self.ocr_thread = None
            
    def update_debug_info(self):
        """Update debug information display."""
        try:
            debug_info = self.ocr_finder.get_debug_info()
            debug_text = f"""Tesseract Available: {debug_info['tesseract_available']}
Version: {debug_info['tesseract_version']}
Last Capture: {debug_info['last_capture_path']}
Last Processed: {debug_info['last_processed_path']}
Target Widget: {self.current_widget.__class__.__name__ if self.current_widget else 'None'}"""
            self.debug_text.setPlainText(debug_text)
        except Exception as e:
            self.debug_text.setPlainText(f"Error getting debug info: {str(e)}")
            
    def view_debug_images(self):
        """Open debug images for inspection."""
        try:
            debug_info = self.ocr_finder.get_debug_info()
            
            # Check if debug images exist
            capture_path = debug_info['last_capture_path']
            processed_path = debug_info['last_processed_path']
            
            images_found = []
            if os.path.exists(capture_path):
                images_found.append(capture_path)
            if os.path.exists(processed_path):
                images_found.append(processed_path)
            if os.path.exists("ocr_test.png"):
                images_found.append("ocr_test.png")
                
            if images_found:
                message = f"Debug images found:\n" + "\n".join(images_found)
                message += "\n\nThese images are saved in the project directory for inspection."
                QMessageBox.information(self, "Debug Images", message)
                
                # Try to open the folder containing the images
                import subprocess
                import sys
                try:
                    if sys.platform == "win32":
                        subprocess.run(["explorer", "."], check=False)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", "."], check=False)
                    else:
                        subprocess.run(["xdg-open", "."], check=False)
                except:
                    pass  # Ignore if can't open folder
            else:
                QMessageBox.information(self, "Debug Images", "No debug images found. Run OCR operation first.")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error accessing debug images: {str(e)}")
            
    def closeEvent(self, event):
        """Handle widget close event."""
        # Clean up OCR thread if running
        if self.ocr_thread and self.ocr_thread.isRunning():
            self.ocr_thread.terminate()
            self.ocr_thread.wait(1000)  # Wait up to 1 second
        event.accept() 