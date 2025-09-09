#!/usr/bin/env python3
"""
Resource Monitoring Script
=========================

Monitors system resources and provides alerts when usage is high.
"""

import psutil
import time
import logging
import requests
import os
from datetime import datetime

# Configuration
MEMORY_THRESHOLD = 80  # Alert if memory usage > 80%
CPU_THRESHOLD = 90     # Alert if CPU usage > 90%
DISK_THRESHOLD = 85    # Alert if disk usage > 85%

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_system_stats():
    """Get current system statistics."""
    return {
        'memory_percent': psutil.virtual_memory().percent,
        'memory_used': psutil.virtual_memory().used / 1024 / 1024 / 1024,  # GB
        'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
        'cpu_percent': psutil.cpu_percent(interval=1),
        'disk_percent': psutil.disk_usage('/').percent,
        'disk_free': psutil.disk_usage('/').free / 1024 / 1024 / 1024,  # GB
        'load_avg': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
    }

def send_alert(message):
    """Send alert via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"ALERT: {message}")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': f"🚨 RESOURCE ALERT\n\n{message}",
            'parse_mode': 'HTML'
        }
        requests.post(url, data=data, timeout=10)
        print(f"📱 Alert sent: {message}")
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")

def check_resources():
    """Check system resources and send alerts if needed."""
    stats = get_system_stats()
    
    alerts = []
    
    # Memory check
    if stats['memory_percent'] > MEMORY_THRESHOLD:
        alerts.append(f"💾 High Memory Usage: {stats['memory_percent']:.1f}% ({stats['memory_used']:.1f}GB/{stats['memory_total']:.1f}GB)")
    
    # CPU check
    if stats['cpu_percent'] > CPU_THRESHOLD:
        alerts.append(f"🖥️ High CPU Usage: {stats['cpu_percent']:.1f}%")
    
    # Disk check
    if stats['disk_percent'] > DISK_THRESHOLD:
        alerts.append(f"💿 High Disk Usage: {stats['disk_percent']:.1f}% (Free: {stats['disk_free']:.1f}GB)")
    
    # Load average check (if available)
    if stats['load_avg'] > 2.0:
        alerts.append(f"⚡ High Load Average: {stats['load_avg']:.2f}")
    
    if alerts:
        message = f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" + "\n".join(alerts)
        send_alert(message)
    
    return len(alerts) == 0

def main():
    """Main monitoring loop."""
    print("🔍 Starting resource monitoring...")
    
    while True:
        try:
            is_healthy = check_resources()
            if is_healthy:
                print(f"✅ System healthy - {datetime.now().strftime('%H:%M:%S')}")
            
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            print("👋 Resource monitoring stopped")
            break
        except Exception as e:
            print(f"❌ Error in resource monitoring: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
