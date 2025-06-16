# Multi-AI Chat - Docker Web Deployment

This deployment runs your Qt desktop application inside a Docker container and makes it accessible via web browser using VNC and noVNC.

## How It Works

1. **Docker Container**: Runs Ubuntu with your Qt application
2. **Virtual Display**: Uses Xvfb to create a virtual X11 display
3. **VNC Server**: Captures the desktop and makes it accessible via VNC
4. **noVNC**: Web-based VNC client that runs in your browser
5. **Web Access**: Users can access your Qt app via HTTP in any web browser

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Your Qt application code in the `app/` directory

### Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

### Access the Application

1. Open your web browser
2. Navigate to: `http://localhost:6080`
3. Click "Connect" 
4. Enter password: `multi-ai` (or leave blank if no password)
5. Your Qt application will appear in the browser!

## Deployment Options

### Local Development
```bash
docker-compose up
```

### Production Deployment
```bash
# Build for production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Cloud Deployment
You can deploy this to any cloud provider that supports Docker:

- **AWS**: Use ECS, EKS, or EC2
- **Google Cloud**: Use Cloud Run, GKE, or Compute Engine  
- **Azure**: Use Container Instances, AKS, or VMs
- **Digital Ocean**: Use App Platform or Droplets
- **Railway**: Direct Docker deployment
- **Render**: Docker-based web services

## Configuration

### Security
- Change the VNC password in `Dockerfile`:
  ```dockerfile
  RUN mkdir -p ~/.vnc && x11vnc -storepasswd YOUR_PASSWORD ~/.vnc/passwd
  ```

### Screen Resolution
- Modify in `docker/supervisord.conf`:
  ```ini
  command=Xvfb :0 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset
  ```

### Ports
- Web interface: `6080` (HTTP)
- VNC direct: `5900` (optional)

## Advantages

✅ **Real Qt Application**: Your actual desktop app, not a web recreation
✅ **No Iframe Restrictions**: Bypasses all browser security limitations  
✅ **Cross-Platform**: Works on any device with a web browser
✅ **Easy Deployment**: Single Docker container
✅ **Scalable**: Can run multiple instances
✅ **Secure**: Containerized environment

## Performance Notes

- Network latency affects responsiveness
- Best for applications that don't require real-time interaction
- Suitable for tools, dashboards, and productivity applications
- Consider running closer to users (CDN/edge deployment)

## Troubleshooting

### Application Won't Start
```bash
# Check logs
docker-compose logs multi-ai-desktop

# Access container shell
docker-compose exec multi-ai-desktop bash
```

### Connection Issues
- Ensure port 6080 is accessible
- Check firewall settings
- Verify Docker is running

### Performance Issues
- Increase container resources
- Use faster internet connection
- Deploy closer to users geographically 