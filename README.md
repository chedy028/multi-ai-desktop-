# Multi-AI Desktop

A desktop application that allows you to interact with multiple AI models (ChatGPT, Gemini, and Grok) in a unified interface, featuring real-time input mirroring between panes.

## Features

- Multiple AI model support (ChatGPT, Gemini, Grok)
- Real-time input mirroring between active panes
- Modern Qt-based user interface
- Tabbed interface for managing multiple conversations (Note: Current implementation uses a QSplitter, not tabs)
- Direct login support for each service within its web view
- Resource management and conversation history (Placeholder for future development)

## Tech Stack

- Python 3.x
- PySide6 (Qt for Python)
- QWebEngineView (for embedding web content and interacting via JavaScript)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/chedy028/multi-ai-desktop-.git
cd multi-ai-desktop-
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package (or dependencies from pyproject.toml if not a full package yet):
```bash
# If pyproject.toml and a build system like Poetry/Flit is used:
# pip install .
# Or, install main dependencies directly (example):
pip install pyside6 python-dotenv
# For OCR features (if used, ensure Tesseract OCR is installed on your system):
# pip install pytesseract Pillow opencv-python pyautogui 
```

## Development Setup

1. Install development dependencies (if applicable, e.g., for linters, testers):
```bash
# pip install -e ".[dev]" # If defined in pyproject.toml
# pip install pytest flake8 black # Example dev tools
```

2. Run tests (if applicable):
```bash
# pytest
```

## Usage

Run the application from the project root directory:
```bash
python -m app
```

## Configuration

Currently, user login for each AI service (ChatGPT, Gemini, Grok) is handled manually within their respective web views after the application starts.

(Optional) For future development involving direct API interactions or automated logins, a `.env` file in the project root can be used for credentials. Ensure `.env` is listed in your `.gitignore` file.
Example `.env` structure:
```
CHATGPT_API_KEY=your_chatgpt_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
# etc.
```

## Known Issues & Limitations

- **Grok Pane UI with Mirrored Text:** When text is mirrored *to* the Grok pane from other panes (e.g., ChatGPT, Gemini), Grok's web UI may not fully update. This can result in the mirrored text overlapping with Grok's placeholder text, and the send button in Grok might not activate for this programmatically inserted text. Typing directly into the Grok pane works as expected and correctly mirrors to other panes.
- **Initial Pane Loading:** Panes load web content which might take a few moments depending on network speed and service availability. Ensure you have a stable internet connection.

## License

MIT License 