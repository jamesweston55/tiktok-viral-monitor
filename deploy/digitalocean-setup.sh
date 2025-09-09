#!/bin/bash
# TikTok Viral Monitor - DigitalOcean Setup Script
# Automated setup for Ubuntu 22.04 LTS

set -e

echo "🚀 Setting up TikTok Viral Monitor on DigitalOcean..."

# Update system
echo "🔄 Updating system packages..."
apt update && apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker root
rm get-docker.sh

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /opt/tiktok-monitor
cd /opt/tiktok-monitor

# Create necessary files
echo "📝 Creating configuration files..."

# Create Dockerfile
cat > Dockerfile << 'DOCKERFILE'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates procps curl \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright
RUN pip install --no-cache-dir playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create user
RUN useradd -m -u 1000 monitor && chown -R monitor:monitor /app
USER monitor

# Create data directory
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import os; exit(0 if os.path.exists('/app/data/simple_multi_monitor.db') else 1)"

CMD ["python3", "simple_multi_monitor.py"]
DOCKERFILE

# Create docker-compose.yml
cat > docker-compose.yml << 'COMPOSE'
version: '3.8'

services:
  tiktok-monitor:
    build: .
    container_name: tiktok-viral-monitor
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - SADCAPTCHA_API_KEY=${SADCAPTCHA_API_KEY}
    volumes:
      - ./data:/app/data
      - ./accounts.csv:/app/accounts.csv
      - ./logs:/app/logs
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.8'
        reservations:
          memory: 256M
          cpus: '0.2'
COMPOSE

# Create .env file
cat > .env << 'ENV'
# TikTok Viral Monitor Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
SADCAPTCHA_API_KEY=your_sadcaptcha_api_key_here

# Monitoring Settings
MONITORING_INTERVAL=5400
VIRAL_THRESHOLD=1000
MAX_CONCURRENT_SCRAPES=10
ENV

# Create requirements.txt
cat > requirements.txt << 'REQUIREMENTS'
playwright>=1.40.0
requests>=2.31.0
git+https://github.com/gbiz123/tiktok-captcha-solver.git
REQUIREMENTS

# Create accounts.csv
cat > accounts.csv << 'ACCOUNTS'
username
barbieglow8
angelbby5340
princessx_5y
pixieboo487
glamiebabe
softiekiss0
gl0wbarbie8
babygirlluv66
rosypixie4
cherryxoxo3467r
ACCOUNTS

# Create necessary directories
mkdir -p data logs

# Set permissions
chmod 755 /opt/tiktok-monitor
chmod 644 /opt/tiktok-monitor/.env

# Create systemd service
cat > /etc/systemd/system/tiktok-monitor.service << 'SERVICE'
[Unit]
Description=TikTok Viral Monitor
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/tiktok-monitor
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE

# Enable service
systemctl daemon-reload
systemctl enable tiktok-monitor

# Create management scripts
cat > /opt/tiktok-monitor/start.sh << 'START'
#!/bin/bash
cd /opt/tiktok-monitor
docker-compose up -d
echo "TikTok Monitor started at $(date)"
START

cat > /opt/tiktok-monitor/stop.sh << 'STOP'
#!/bin/bash
cd /opt/tiktok-monitor
docker-compose down
echo "TikTok Monitor stopped at $(date)"
STOP

cat > /opt/tiktok-monitor/logs.sh << 'LOGS'
#!/bin/bash
cd /opt/tiktok-monitor
docker-compose logs -f
LOGS

cat > /opt/tiktok-monitor/update.sh << 'UPDATE'
#!/bin/bash
cd /opt/tiktok-monitor
git pull 2>/dev/null || echo "No git repo, skipping pull"
docker-compose down
docker-compose up -d --build
echo "TikTok Monitor updated at $(date)"
UPDATE

# Make scripts executable
chmod +x /opt/tiktok-monitor/*.sh

# Create backup script
cat > /opt/backup-monitor.sh << 'BACKUP'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p /opt/backups
cp /opt/tiktok-monitor/data/simple_multi_monitor.db /opt/backups/monitor_$DATE.db
find /opt/backups -name "monitor_*.db" -mtime +7 -delete
echo "Backup created: monitor_$DATE.db"
BACKUP

chmod +x /opt/backup-monitor.sh

# Schedule daily backups
echo "0 2 * * * /opt/backup-monitor.sh" | crontab -

# Configure firewall
echo "🔒 Configuring firewall..."
ufw allow ssh
ufw allow 80
ufw allow 443
ufw --force enable

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /opt/tiktok-monitor/.env with your API keys:"
echo "   nano /opt/tiktok-monitor/.env"
echo ""
echo "2. Start the monitor:"
echo "   /opt/tiktok-monitor/start.sh"
echo ""
echo "3. Check status:"
echo "   /opt/tiktok-monitor/logs.sh"
echo ""
echo "🔧 Management commands:"
echo "  Start:   /opt/tiktok-monitor/start.sh"
echo "  Stop:    /opt/tiktok-monitor/stop.sh"
echo "  Logs:    /opt/tiktok-monitor/logs.sh"
echo "  Update:  /opt/tiktok-monitor/update.sh"
echo "  Backup:  /opt/backup-monitor.sh"
echo ""
echo "🎯 Your TikTok monitor is ready to deploy!"
