#!/bin/bash

# Start supervisor to manage all services
echo "Starting Multi-AI Chat Desktop App via Web..."
echo "Web interface will be available at: http://localhost:6080"
echo "Click 'Connect' and use password: multi-ai"
echo ""

# Start all services via supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf 