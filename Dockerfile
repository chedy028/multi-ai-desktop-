# Use Ubuntu as base image
FROM ubuntu:22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-tk \
    python3-dev \
    xvfb \
    x11vnc \
    fluxbox \
    wget \
    curl \
    supervisor \
    net-tools \
    dos2unix \
    xauth \
    xxd \
    tesseract-ocr \
    tesseract-ocr-eng \
    # Qt and X11 dependencies for PySide6
    qt6-base-dev \
    libqt6gui6 \
    libqt6widgets6 \
    libqt6webenginewidgets6 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxkbcommon-x11-0 \
    libxcomposite1 \
    libxrandr2 \
    libasound2 \
    libxss1 \
    libgconf-2-4 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN wget -qO- https://github.com/novnc/noVNC/archive/v1.3.0.tar.gz | tar xz -C /opt/ \
    && mv /opt/noVNC-1.3.0 /opt/novnc \
    && wget -qO- https://github.com/novnc/websockify/archive/v0.10.0.tar.gz | tar xz -C /opt/ \
    && mv /opt/websockify-0.10.0 /opt/websockify

# Create index.html that redirects to vnc.html
RUN echo '<html><head><meta http-equiv="refresh" content="0; url=vnc.html"></head><body>Redirecting to VNC...</body></html>' > /opt/novnc/index.html

# Set display environment
ENV DISPLAY=:0
ENV VNC_PORT=5900
ENV NO_VNC_PORT=6080
ENV QT_QPA_PLATFORM=xcb
ENV QT_X11_NO_MITSHM=1

# Create app directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY *.py ./

# Create supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create VNC password (change this for security)
RUN mkdir -p ~/.vnc && x11vnc -storepasswd multi-ai ~/.vnc/passwd

# Expose ports
EXPOSE 6080 5900

# Create startup script and fix line endings
COPY docker/start.sh /start.sh
RUN dos2unix /start.sh && chmod +x /start.sh

CMD ["/start.sh"] 