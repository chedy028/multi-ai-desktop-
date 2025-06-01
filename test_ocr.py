#!/usr/bin/env python3
"""
Test script for OCR Control Widget
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from app.widgets.ocr_control import OCRControlWidget
from app.utils.logging_config import setup_logging

def main():
    # Initialize logging
    setup_logging(log_level="INFO", log_to_console=True)
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("OCR Control Widget Test")
    window.setGeometry(100, 100, 400, 600)
    
    # Create central widget
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Add title
    title = QLabel("OCR Control Widget Test")
    title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
    layout.addWidget(title)
    
    # Add OCR control widget
    ocr_control = OCRControlWidget()
    layout.addWidget(ocr_control)
    
    # Show window
    window.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 