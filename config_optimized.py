#!/usr/bin/env python3
"""
TikTok Viral Monitor Configuration - OPTIMIZED FOR MEMORY
========================================================

Centralized configuration file for all monitoring settings.
Optimized for better memory management and droplet deployment.
"""

import os

# =============================================================================
# TELEGRAM SETTINGS
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8400102574:AAFUN6vR6bsBdTHLt_6clxMlxYV-7IMG7fE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "2021266274")

# =============================================================================
# MONITORING INTERVALS (in seconds)
# =============================================================================
MONITORING_INTERVAL = 90 * 60  # 90 minutes
SCRAPE_DELAY_SECONDS = 10      # Increased from 5 to 10 for better stability
BATCH_DELAY_SECONDS = 60       # Increased from 30 to 60 for better stability

# =============================================================================
# VIRAL DETECTION SETTINGS
# =============================================================================
VIRAL_THRESHOLD = 100  # 1000 views
MAX_VIDEOS_TO_CHECK = 5                # Number of latest videos to monitor per account

# =============================================================================
# PERFORMANCE SETTINGS - OPTIMIZED FOR MEMORY
# =============================================================================
MAX_CONCURRENT_SCRAPES = 3  # Reduced from 10 to 3 for better memory management
BROWSER_HEADLESS = True                # Set to False to see browser (for debugging)
PAGE_TIMEOUT = 30000                   # Page load timeout in milliseconds

# =============================================================================
# MEMORY MANAGEMENT SETTINGS
# =============================================================================
BROWSER_MEMORY_LIMIT = "512MB"         # Memory limit per browser instance
MAX_BROWSER_INSTANCES = 3              # Maximum number of browser instances
BROWSER_CLEANUP_INTERVAL = 5           # Clean up browsers every 5 scrapes
ENABLE_BROWSER_REUSE = True            # Reuse browser instances when possible
BROWSER_IDLE_TIMEOUT = 300             # Close idle browsers after 5 minutes

# =============================================================================
# DROPLET OPTIMIZATION SETTINGS
# =============================================================================
DROPLET_MODE = os.getenv("DROPLET_MODE", "false").lower() == "true"
if DROPLET_MODE:
    # Optimized settings for DigitalOcean droplets (1GB RAM)
    MAX_CONCURRENT_SCRAPES = 2         # Very conservative for 1GB RAM
    SCRAPE_DELAY_SECONDS = 15          # Longer delays to reduce load
    BATCH_DELAY_SECONDS = 90           # Longer batch delays
    BROWSER_MEMORY_LIMIT = "256MB"     # Lower memory per browser
    MAX_BROWSER_INSTANCES = 2          # Only 2 browsers max
    BROWSER_IDLE_TIMEOUT = 180         # Close idle browsers after 3 minutes
    PAGE_TIMEOUT = 45000               # Longer timeout for slower connections

# =============================================================================
# FILE LOCATIONS
# =============================================================================
ACCOUNTS_FILE = "accounts.csv"
DATABASE_FILE = "simple_multi_monitor.db"
LOG_FILE = "simple_multi_monitor.log"

# =============================================================================
# CAPTCHA & ANTI-BOT SETTINGS
# =============================================================================
SADCAPTCHA_API_KEY = os.getenv("SADCAPTCHA_API_KEY", "a5afce8d13f3b809256269cb5d71d46a")
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# =============================================================================
# LOGGING SETTINGS
# =============================================================================
LOG_LEVEL = "INFO"                     # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'

# =============================================================================
# QUICK PRESETS - Uncomment one to use
# =============================================================================

# # AGGRESSIVE MONITORING (Fast detection, higher resource usage)
# MONITORING_INTERVAL = 2 * 60          # 2 minutes
# SCRAPE_DELAY_SECONDS = 5              # 5 seconds
# VIRAL_THRESHOLD = 50                  # 50 views
# MAX_CONCURRENT_SCRAPES = 5            # 5 concurrent

# # CONSERVATIVE MONITORING (Slower detection, lower resource usage)
# MONITORING_INTERVAL = 15 * 60         # 15 minutes
# SCRAPE_DELAY_SECONDS = 20             # 20 seconds
# VIRAL_THRESHOLD = 500                 # 500 views
# MAX_CONCURRENT_SCRAPES = 2            # 2 concurrent

# # HIGH VOLUME MONITORING (For many accounts)
# MONITORING_INTERVAL = 10 * 60         # 10 minutes
# SCRAPE_DELAY_SECONDS = 5              # 5 seconds
# VIRAL_THRESHOLD = 200                 # 200 views
# MAX_CONCURRENT_SCRAPES = 6            # 6 concurrent

# =============================================================================
# VALIDATION
# =============================================================================
def validate_config():
    """Validate configuration settings."""
    errors = []
    
    if MONITORING_INTERVAL < 60:
        errors.append("MONITORING_INTERVAL should be at least 60 seconds to avoid rate limits")
    
    if SCRAPE_DELAY_SECONDS < 1:
        errors.append("SCRAPE_DELAY_SECONDS should be at least 1 second")
    
    if VIRAL_THRESHOLD < 1:
        errors.append("VIRAL_THRESHOLD should be at least 1")
    
    if MAX_CONCURRENT_SCRAPES < 1:
        errors.append("MAX_CONCURRENT_SCRAPES should be at least 1")
    
    if MAX_CONCURRENT_SCRAPES > 10:
        errors.append("MAX_CONCURRENT_SCRAPES should not exceed 10 to avoid overwhelming TikTok")
    
    if errors:
        print("⚠️  Configuration Warnings:")
        for error in errors:
            print(f"  • {error}")
        print()
    
    return len(errors) == 0

if __name__ == "__main__":
    print("🔧 TikTok Viral Monitor Configuration - OPTIMIZED")
    print("=" * 60)
    print(f"📊 Monitoring Interval: {MONITORING_INTERVAL // 60} minutes")
    print(f"🎯 Viral Threshold: {VIRAL_THRESHOLD} views")
    print(f"⚡ Scrape Delay: {SCRAPE_DELAY_SECONDS} seconds")
    print(f"🔄 Max Concurrent: {MAX_CONCURRENT_SCRAPES} accounts")
    print(f"💾 Browser Memory Limit: {BROWSER_MEMORY_LIMIT}")
    print(f"🖥️  Max Browser Instances: {MAX_BROWSER_INSTANCES}")
    print(f"🌐 Droplet Mode: {'ON' if DROPLET_MODE else 'OFF'}")
    print(f"📁 Accounts File: {ACCOUNTS_FILE}")
    print(f"💾 Database File: {DATABASE_FILE}")
    print("=" * 60)
    
    if validate_config():
        print("✅ Configuration is valid!")
    else:
        print("❌ Please fix configuration issues above")
