#!/bin/bash
# Optimized Deployment Script for DigitalOcean

set -e

echo "🚀 Deploying Optimized TikTok Monitor to DigitalOcean..."

# Update system
echo "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
    rm get-docker.sh
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "🐙 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Clone repository if not present
if [ ! -d "tiktok-viral-monitor" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/jamesweston55/tiktok-viral-monitor.git
fi

cd tiktok-viral-monitor

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cat > .env << EOL
# Telegram Settings
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# SadCaptcha Settings
SADCAPTCHA_API_KEY=your_api_key_here

# Droplet Mode (enables optimizations)
DROPLET_MODE=true

# Database Settings
DB_PASSWORD=your_secure_database_password
EOL
    echo "📝 Please edit .env file with your actual credentials!"
fi

# Install psutil for resource monitoring
echo "📊 Installing resource monitoring dependencies..."
pip3 install psutil

# Set up system monitoring
echo "🔍 Setting up resource monitoring..."
cat > /etc/systemd/system/tiktok-resource-monitor.service << EOL
[Unit]
Description=TikTok Monitor Resource Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/tiktok-viral-monitor
ExecStart=/usr/bin/python3 monitor_resources.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOL

# Build and start optimized containers
echo "🏗️ Building optimized Docker image..."
docker-compose -f docker-compose.optimized.yml build

echo "🚀 Starting optimized TikTok Monitor..."
docker-compose -f docker-compose.optimized.yml up -d

# Start resource monitoring
systemctl daemon-reload
systemctl enable tiktok-resource-monitor
systemctl start tiktok-resource-monitor

echo "✅ Optimized deployment completed!"
echo ""
echo "📊 Container Status:"
docker-compose -f docker-compose.optimized.yml ps

echo ""
echo "🔍 Resource Monitoring:"
systemctl status tiktok-resource-monitor --no-pager

echo ""
echo "📝 Useful Commands:"
echo "  View logs: docker-compose -f docker-compose.optimized.yml logs -f"
echo "  Stop monitor: docker-compose -f docker-compose.optimized.yml down"
echo "  Restart monitor: docker-compose -f docker-compose.optimized.yml restart"
echo "  View resources: python3 monitor_resources.py"
echo "  System status: systemctl status tiktok-resource-monitor"
