from PySide6.QtWebEngineCore import QWebEnginePage

print('QWebEnginePage signals:')
for attr in dir(QWebEnginePage):
    if 'signal' in attr.lower() or 'Signal' in attr:
        print(attr) 