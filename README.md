# Multi-AI Desktop

A desktop application that allows you to interact with multiple AI models (ChatGPT, Gemini, and Grok) in a unified interface.

## Features

- Multiple AI model support (ChatGPT, Gemini, Grok)
- Modern Qt-based user interface
- Tabbed interface for managing multiple conversations
- Direct login support for each service
- Resource management and conversation history

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/multi-ai-desktop.git
cd multi-ai-desktop
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Development Setup

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

## Usage

Run the application:
```bash
python -m app
```

## Configuration

Create a `.env` file in the project root with your login credentials:
```
CHATGPT_USERNAME=your_chatgpt_username
CHATGPT_PASSWORD=your_chatgpt_password
GEMINI_USERNAME=your_gemini_username
GEMINI_PASSWORD=your_gemini_password
GROK_USERNAME=your_grok_username
GROK_PASSWORD=your_grok_password
```

## License

MIT License 