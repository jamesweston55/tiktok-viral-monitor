#!/usr/bin/env python3
"""
Viral Monitor Setup Script
==========================

Sets up and configures the TikTok viral monitoring system.
Handles Telegram bot configuration and service management.

Usage:
    python3 setup_viral_monitor.py

Author: Created for jamesweston55
Date: September 7, 2024
"""

import os
import subprocess
import sys
from pathlib import Path

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    🚨 VIRAL MONITOR SETUP 🚨                  ║
║                                                              ║
║  Automatically detect viral TikTok videos and get instant   ║
║  Telegram alerts when your videos explode in popularity!    ║
╚══════════════════════════════════════════════════════════════╝
""")

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    try:
        import requests
        print("✅ requests - OK")
    except ImportError:
        print("❌ requests not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    
    # Check if main.py exists
    if not Path("main.py").exists():
        print("❌ main.py not found. Please ensure your TikTok scraper is in the same directory.")
        return False
    
    print("✅ TikTok scraper found")
    return True

def setup_telegram_bot():
    """Interactive Telegram bot setup."""
    print("\n🤖 TELEGRAM BOT SETUP")
    print("=" * 50)
    
    print("""
To receive viral alerts on Telegram, you need to:

1. Create a Telegram Bot:
   • Open Telegram and message @BotFather
   • Send: /newbot
   • Choose a name and username for your bot
   • Copy the bot token that BotFather gives you

2. Get your Chat ID:
   • Send any message to your new bot
   • Visit this URL in your browser (replace YOUR_BOT_TOKEN):
     https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   • Look for "chat":{"id": YOUR_CHAT_ID
""")
    
    bot_token = input("\n🔑 Enter your Telegram Bot Token: ").strip()
    if not bot_token:
        print("⚠️  Skipping Telegram setup. You can configure it later.")
        return None, None
    
    chat_id = input("💬 Enter your Chat ID: ").strip()
    if not chat_id:
        print("⚠️  Skipping Telegram setup. You can configure it later.")
        return None, None
    
    # Test the bot
    print("🧪 Testing Telegram bot...")
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': '🚨 TikTok Viral Monitor Setup Complete! 🚨\n\nYour viral detection system is now active. You\'ll receive alerts when videos gain 1200+ views in 90 minutes!'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Telegram bot test successful! Check your Telegram for a test message.")
            return bot_token, chat_id
        else:
            print(f"❌ Telegram bot test failed: {response.status_code}")
            print("Please check your bot token and chat ID.")
            return None, None
            
    except Exception as e:
        print(f"❌ Error testing bot: {e}")
        return None, None

def create_env_file(bot_token, chat_id):
    """Create environment file for configuration."""
    if bot_token and chat_id:
        env_content = f"""# TikTok Viral Monitor Configuration
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_CHAT_ID={chat_id}
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ Configuration saved to .env file")
        return True
    return False

def create_start_script(username):
    """Create a start script for easy launching."""
    script_content = f"""#!/bin/bash
# TikTok Viral Monitor Launcher
# Usage: ./start_monitor.sh

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

echo "🚀 Starting TikTok Viral Monitor for @{username}"
echo "⏰ Monitoring every 90 minutes"
echo "📈 Viral threshold: 1200+ view increase"
echo "💬 Telegram alerts: {'Enabled' if Path('.env').exists() else 'Disabled'}"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

python3 viral_monitor.py {username}
"""
    
    with open('start_monitor.sh', 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod('start_monitor.sh', 0o755)
    print(f"✅ Created start_monitor.sh launcher script")

def create_systemd_service(username):
    """Create systemd service file for automatic startup."""
    current_dir = Path.cwd().absolute()
    
    service_content = f"""[Unit]
Description=TikTok Viral Monitor for @{username}
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'user')}
WorkingDirectory={current_dir}
Environment=PATH={current_dir}
EnvironmentFile={current_dir}/.env
ExecStart=/usr/bin/python3 {current_dir}/viral_monitor.py {username}
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
"""
    
    service_file = f"tiktok-viral-monitor-{username}.service"
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    print(f"✅ Created systemd service file: {service_file}")
    print(f"""
🔧 To install as a system service (optional):
   sudo cp {service_file} /etc/systemd/system/
   sudo systemctl enable {service_file}
   sudo systemctl start {service_file}
""")

def main():
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Setup failed. Please install dependencies and try again.")
        return
    
    # Get username
    print("\n📱 TikTok Configuration")
    print("=" * 50)
    username = input("Enter TikTok username to monitor (without @): ").strip()
    if not username:
        print("❌ Username is required.")
        return
    
    # Set up Telegram
    bot_token, chat_id = setup_telegram_bot()
    
    # Create configuration
    create_env_file(bot_token, chat_id)
    
    # Create scripts
    create_start_script(username)
    create_systemd_service(username)
    
    print("\n🎉 SETUP COMPLETE!")
    print("=" * 50)
    print(f"✅ Monitoring configured for: @{username}")
    print(f"✅ Viral threshold: 1200+ views in 90 minutes")
    print(f"✅ Telegram alerts: {'Enabled' if bot_token else 'Disabled'}")
    print(f"✅ Database: viral_monitor.db")
    print(f"✅ Logs: viral_monitor.log")
    
    print("\n🚀 HOW TO START MONITORING:")
    print("Option 1 (Recommended): ./start_monitor.sh")
    print(f"Option 2: python3 viral_monitor.py {username}")
    print(f"Option 3: python3 viral_monitor.py {username} --once  (single check)")
    
    print(f"\n📊 Monitor will check @{username} every 90 minutes")
    print("💬 You'll get Telegram alerts when videos go viral!")
    
    # Ask if they want to start now
    start_now = input("\n🚀 Start monitoring now? (y/n): ").strip().lower()
    if start_now == 'y':
        print(f"\n🎬 Starting viral monitor for @{username}...")
        try:
            subprocess.run([sys.executable, "viral_monitor.py", username])
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped. You can restart anytime with ./start_monitor.sh")

if __name__ == "__main__":
    main() 