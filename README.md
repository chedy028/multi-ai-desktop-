# Multi-AI Desktop Chat

A powerful Qt-based desktop application that allows you to interact with multiple AI models (ChatGPT, Claude, Gemini, and Grok) simultaneously. Access it locally or via web through Docker with VNC.

## 🚀 Features

- **Multiple AI Models**: ChatGPT, Claude, Gemini, and Grok in one interface
- **Real-time Input Mirroring**: Type in one pane, see it reflected in others
- **OCR Capabilities**: Extract text from images and screenshots
- **Modern Qt Interface**: Beautiful, responsive desktop application
- **Web Access**: Run in Docker and access via web browser through VNC
- **Direct Login Support**: Login to each AI service within the app

## 🖥️ Local Installation

### Prerequisites
- Python 3.8+
- Qt6 libraries (for local running)

### Install and Run Locally

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd multi-ai-desktop
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python -m app
```

## 🐳 Docker Deployment (Web Access)

The best way to make the desktop app accessible via web browser:

### Quick Start

1. **Build and run with Docker:**
```bash
docker compose build
docker compose up
```

2. **Access via web browser:**
   - Open: http://localhost:6080
   - Click "Connect"
   - Password: `multi-ai`

### Background Mode
```bash
docker compose up -d  # Run in background
docker compose logs   # View logs
docker compose down   # Stop containers
```

## 🌐 Remote Access Setup

For production deployment on a VM/VPS:

1. **Deploy on your server:**
```bash
git clone <your-repo-url>
cd multi-ai-desktop
docker compose up -d
```

2. **Configure firewall:**
```bash
# Allow port 6080 for web access
sudo ufw allow 6080
```

3. **Access remotely:**
   - Open: http://your-server-ip:6080
   - Password: `multi-ai`

## 🔧 Configuration

### Security (Production)
Change the VNC password in `Dockerfile`:
```dockerfile
RUN mkdir -p ~/.vnc && x11vnc -storepasswd YOUR_PASSWORD ~/.vnc/passwd
```

### Display Settings
Modify display resolution in `docker/supervisord.conf`:
```ini
command=Xvfb :0 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset
```

## 📱 Usage

1. **Access the application** (locally or via web)
2. **Login to AI services** - Each pane will load the respective AI service
3. **Type in any pane** - Your input will be mirrored to all other panes
4. **Use OCR features** - Extract text from images when running locally

## 🛠️ Tech Stack

- **Frontend**: PySide6 (Qt for Python)
- **Web Embedding**: QWebEngineView
- **OCR**: Tesseract + OpenCV
- **Containerization**: Docker + Docker Compose
- **Remote Access**: VNC + noVNC

## 📊 Architecture

```
User Browser → noVNC (Port 6080) → VNC → X11/Qt Desktop App
```

## 🔍 Troubleshooting

### Container Issues
```bash
# View detailed logs
docker compose logs multi-ai-desktop

# Restart container
docker compose restart

# Rebuild if needed
docker compose build --no-cache
```

### Local Qt Issues
```bash
# Install Qt6 dependencies (Ubuntu/Debian)
sudo apt-get install qt6-base-dev libqt6webenginewidgets6

# Set environment variables
export QT_QPA_PLATFORM=xcb
export DISPLAY=:0
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test locally and in Docker
4. Submit a pull request

## 📄 License

MIT License

---

**Access your Multi-AI Desktop anywhere through the web! 🚀** 