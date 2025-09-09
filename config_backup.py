#!/usr/bin/env python3
"""
TikTok Viral Monitor Configuration
=================================

Centralized configuration file for all monitoring settings.
Edit these values to customize your monitoring behavior.
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
SCRAPE_DELAY_SECONDS = 5  # high_volume preset
BATCH_DELAY_SECONDS = 30               # 30 seconds - delay between batches

# =============================================================================
# VIRAL DETECTION SETTINGS
# =============================================================================
VIRAL_THRESHOLD = 1000  # 1000 views
MAX_VIDEOS_TO_CHECK = 5                # Number of latest videos to monitor per account

# =============================================================================
# PERFORMANCE SETTINGS
# =============================================================================
MAX_CONCURRENT_SCRAPES = 10  # 10 concurrent
BROWSER_HEADLESS = True                # Set to False to see browser (for debugging)
PAGE_TIMEOUT = 30000                   # Page load timeout in milliseconds

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
    print("🔧 TikTok Viral Monitor Configuration")
    print("=" * 50)
    print(f"📊 Monitoring Interval: {MONITORING_INTERVAL // 60} minutes")
    print(f"🎯 Viral Threshold: {VIRAL_THRESHOLD} views")
    print(f"⚡ Scrape Delay: {SCRAPE_DELAY_SECONDS} seconds")
    print(f"🔄 Max Concurrent: {MAX_CONCURRENT_SCRAPES} accounts")
    print(f"📁 Accounts File: {ACCOUNTS_FILE}")
    print(f"💾 Database File: {DATABASE_FILE}")
    print("=" * 50)
    
    if validate_config():
        print("✅ Configuration is valid!")
    else:
        print("❌ Please fix configuration issues above") 