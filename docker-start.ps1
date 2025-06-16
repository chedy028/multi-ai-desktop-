Write-Host "🐳 Multi-AI Desktop - Docker Startup Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check if Docker is running
Write-Host "🔍 Checking Docker status..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✅ Docker is running!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop manually." -ForegroundColor Red
    Write-Host "Once Docker Desktop is running, run this script again." -ForegroundColor Yellow
    exit 1
}

# Build the Docker image
Write-Host "🏗️ Building Docker image..." -ForegroundColor Yellow
docker-compose build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image built successfully!" -ForegroundColor Green
}
else {
    Write-Host "❌ Failed to build Docker image." -ForegroundColor Red
    exit 1
}

# Start the application
Write-Host "🚀 Starting Multi-AI Desktop application..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Application started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📱 Access your application at: http://localhost:6080" -ForegroundColor Cyan
    Write-Host "🔐 VNC Password: multi-ai (or leave blank)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📝 To view logs: docker-compose logs -f" -ForegroundColor Yellow
    Write-Host "🛑 To stop: docker-compose down" -ForegroundColor Yellow
}
else {
    Write-Host "❌ Failed to start application." -ForegroundColor Red
    exit 1
} 