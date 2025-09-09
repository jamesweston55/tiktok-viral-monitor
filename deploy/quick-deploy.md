# 🚀 Quick DigitalOcean Deployment

## Option 1: One-Command Setup (Recommended)

1. **Create DigitalOcean Droplet:**
   - Go to [digitalocean.com](https://digitalocean.com)
   - Create → Droplets
   - Ubuntu 22.04 LTS, $6/month (1GB RAM)
   - Add SSH key or password
   - Create droplet

2. **Connect and Deploy:**
   ```bash
   # Connect to your server
   ssh root@YOUR_SERVER_IP
   
   # Run one-command setup
   curl -sSL https://raw.githubusercontent.com/your-repo/tiktokscraper/main/deploy/digitalocean-setup.sh | bash
   ```

3. **Configure:**
   ```bash
   # Edit configuration
   nano /opt/tiktok-monitor/.env
   
   # Add your API keys:
   TELEGRAM_BOT_TOKEN=8400102574:AAFUN6vR6bsBdTHLt_6clxMlxYV-7IMG7fE
   TELEGRAM_CHAT_ID=2021266274
   SADCAPTCHA_API_KEY=a5afce8d13f3b809256269cb5d71d46a
   ```

4. **Start Monitoring:**
   ```bash
   /opt/tiktok-monitor/start.sh
   ```

## Option 2: Manual Setup

1. **Create Droplet** (same as above)

2. **Connect and Install:**
   ```bash
   ssh root@YOUR_SERVER_IP
   
   # Update system
   apt update && apt upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com | sh
   
   # Install Docker Compose
   curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   chmod +x /usr/local/bin/docker-compose
   ```

3. **Deploy Application:**
   ```bash
   # Create directory
   mkdir -p /opt/tiktok-monitor
   cd /opt/tiktok-monitor
   
   # Copy your files (use scp or git)
   # Then run:
   docker-compose up -d
   ```

## Management Commands

```bash
# Start monitor
/opt/tiktok-monitor/start.sh

# Stop monitor  
/opt/tiktok-monitor/stop.sh

# View logs
/opt/tiktok-monitor/logs.sh

# Update code
/opt/tiktok-monitor/update.sh

# Check status
docker ps
```

## Expected Results

- ✅ Monitor runs 24/7
- ✅ Checks accounts every 90 minutes
- ✅ Alerts when videos gain 1000+ views
- ✅ Sends Telegram notifications
- ✅ Automatic restarts on failure
- ✅ Daily backups

## Cost: ~$6-8/month

---

**🎯 Ready to deploy? Follow Option 1 for the fastest setup!**
