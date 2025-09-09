#!/usr/bin/env python3
"""
Multi-Account TikTok Viral Monitor
==================================

Advanced viral monitoring system for multiple TikTok accounts with:
- CSV-based account management
- Priority-based scheduling
- Efficient resource management
- Parallel processing
- Advanced analytics and reporting

Features:
- Monitor 50+ accounts efficiently
- Priority-based monitoring (high/medium/low)
- Staggered scraping to avoid rate limits
- Comprehensive logging and analytics
- Telegram alerts with account details
- Database optimization for large datasets

Usage:
    python3 multi_account_monitor.py

Author: Created for jamesweston55
Date: September 7, 2024
"""

import asyncio
import csv
import json
import logging
import os
import sqlite3
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import queue

import requests

# Import our existing scraper
from main import get_latest_videos

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8400102574:AAFUN6vR6bsBdTHLt_6clxMlxYV-7IMG7fE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "2021266274")

# Monitoring intervals based on priority
PRIORITY_INTERVALS = {
    'high': 5 * 60,      # 5 minutes for high priority accounts
    'medium': 15 * 60,    # 15 minutes for medium priority
    'low': 30 * 60        # 30 minutes for low priority
}

VIRAL_THRESHOLD = 100  # View increase threshold for viral detection
ACCOUNTS_FILE = "accounts.csv"
DATABASE_FILE = "multi_account_monitor.db"
MAX_CONCURRENT_SCRAPES = 3  # Limit concurrent scraping to avoid rate limits
SCRAPE_DELAY_SECONDS = 10   # Delay between individual scrapes

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('multi_account_monitor.log'),
        logging.StreamHandler()
    ]
)

class MultiAccountMonitor:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.accounts = self.load_accounts()
        self.init_database()
        self.scrape_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.running = True
        
    def load_accounts(self) -> List[Dict]:
        """Load accounts from CSV file."""
        accounts = []
        try:
            with open(ACCOUNTS_FILE, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['status'].lower() == 'active':
                        accounts.append({
                            'username': row['username'].strip(),
                            'priority': row['priority'].lower().strip(),
                            'last_scraped': None,
                            'next_scrape': datetime.now()
                        })
            
            logging.info(f"📊 Loaded {len(accounts)} active accounts")
            
            # Log priority distribution
            priority_counts = {}
            for account in accounts:
                priority = account['priority']
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            for priority, count in priority_counts.items():
                interval_min = PRIORITY_INTERVALS[priority] // 60
                logging.info(f"  • {priority.upper()}: {count} accounts (every {interval_min} min)")
                
            return accounts
            
        except FileNotFoundError:
            logging.error(f"❌ Accounts file not found: {ACCOUNTS_FILE}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"❌ Error loading accounts: {e}")
            sys.exit(1)
    
    def init_database(self):
        """Initialize SQLite database for storing video data."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create table for storing video data with account info
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_data (
                    id TEXT,
                    username TEXT,
                    description TEXT,
                    views INTEGER,
                    likes INTEGER,
                    comments INTEGER,
                    shares INTEGER,
                    created_date TEXT,
                    scraped_at TIMESTAMP,
                    priority TEXT,
                    PRIMARY KEY (id, username, scraped_at)
                )
            ''')
            
            # Create table for monitoring statistics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitoring_stats (
                    username TEXT PRIMARY KEY,
                    total_scrapes INTEGER DEFAULT 0,
                    total_videos_found INTEGER DEFAULT 0,
                    total_viral_alerts INTEGER DEFAULT 0,
                    last_scrape_time TIMESTAMP,
                    last_viral_alert TIMESTAMP,
                    avg_views INTEGER DEFAULT 0,
                    priority TEXT
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_username_scraped ON video_data(username, scraped_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON video_data(id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_priority ON video_data(priority)')
            
            conn.commit()
            conn.close()
            logging.info(f"✅ Database initialized: {self.db_file}")
            
        except Exception as e:
            logging.error(f"❌ Error initializing database: {e}")
            raise
    
    def save_video_data(self, username: str, videos: List[Dict], priority: str):
        """Save scraped video data to database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            current_time = datetime.now()
            
            for video in videos:
                cursor.execute('''
                    INSERT OR REPLACE INTO video_data 
                    (id, username, description, views, likes, comments, shares, created_date, scraped_at, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video['id'], username, video['desc'], video['views'],
                    video['likes'], video['comments'], video['shares'],
                    video['created'], current_time, priority
                ))
            
            # Update monitoring statistics
            cursor.execute('''
                INSERT OR REPLACE INTO monitoring_stats 
                (username, total_scrapes, total_videos_found, last_scrape_time, priority)
                VALUES (?, 
                    COALESCE((SELECT total_scrapes FROM monitoring_stats WHERE username = ?), 0) + 1,
                    COALESCE((SELECT total_videos_found FROM monitoring_stats WHERE username = ?), 0) + ?,
                    ?, ?)
            ''', (username, username, username, len(videos), current_time, priority))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"❌ Error saving data for {username}: {e}")
    
    def get_previous_video_data(self, username: str) -> Dict[str, int]:
        """Get previous video view counts for comparison."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get the most recent data for this username (excluding current scrape)
            cursor.execute('''
                SELECT id, views FROM video_data 
                WHERE username = ? AND scraped_at < (
                    SELECT MAX(scraped_at) FROM video_data WHERE username = ?
                )
                ORDER BY scraped_at DESC
                LIMIT 5
            ''', (username, username))
            
            previous_data = {}
            for row in cursor.fetchall():
                previous_data[row[0]] = row[1]
            
            conn.close()
            return previous_data
            
        except Exception as e:
            logging.error(f"❌ Error getting previous data for {username}: {e}")
            return {}
    
    def check_viral_videos(self, username: str, current_videos: List[Dict]) -> List[Dict]:
        """Check for viral videos and return alerts."""
        previous_data = self.get_previous_video_data(username)
        viral_videos = []
        
        for video in current_videos:
            video_id = video['id']
            current_views = video['views']
            
            if video_id in previous_data:
                previous_views = previous_data[video_id]
                view_increase = current_views - previous_views
                
                if view_increase >= VIRAL_THRESHOLD:
                    viral_info = {
                        'username': username,
                        'video_id': video_id,
                        'description': video['desc'][:100] + "..." if len(video['desc']) > 100 else video['desc'],
                        'current_views': current_views,
                        'previous_views': previous_views,
                        'view_increase': view_increase,
                        'likes': video['likes'],
                        'comments': video['comments'],
                        'shares': video['shares']
                    }
                    viral_videos.append(viral_info)
        
        return viral_videos
    
    def send_viral_alert(self, viral_videos: List[Dict]):
        """Send Telegram alert for viral videos."""
        if not viral_videos:
            return
        
        try:
            for viral_video in viral_videos:
                # Create TikTok URL
                tiktok_url = f"https://www.tiktok.com/@{viral_video['username']}/video/{viral_video['video_id']}"
                
                message = f"""🚨 **VIRAL ALERT!** 🚨

👤 **Account**: @{viral_video['username']}
📹 **Video**: {viral_video['description']}

📊 **Performance**:
• Views: {viral_video['current_views']:,} (+{viral_video['view_increase']:,})
• Likes: {viral_video['likes']:,}
• Comments: {viral_video['comments']:,}
• Shares: {viral_video['shares']:,}

🔗 **Link**: {tiktok_url}

⏰ **Detected**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                data = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                }
                
                response = requests.post(url, data=data, timeout=10)
                
                if response.status_code == 200:
                    logging.info(f"🔥 VIRAL ALERT sent for @{viral_video['username']} (+{viral_video['view_increase']:,} views)")
                    
                    # Update viral alert count in database
                    self.update_viral_alert_count(viral_video['username'])
                else:
                    logging.error(f"❌ Failed to send Telegram alert: {response.status_code}")
                
                # Small delay between messages to avoid rate limiting
                time.sleep(1)
                
        except Exception as e:
            logging.error(f"❌ Error sending viral alert: {e}")
    
    def update_viral_alert_count(self, username: str):
        """Update viral alert count in database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE monitoring_stats 
                SET total_viral_alerts = total_viral_alerts + 1,
                    last_viral_alert = ?
                WHERE username = ?
            ''', (datetime.now(), username))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"❌ Error updating viral alert count for {username}: {e}")
    
    async def scrape_account(self, account: Dict) -> Tuple[str, bool, List[Dict]]:
        """Scrape a single account."""
        username = account['username']
        priority = account['priority']
        
        try:
            logging.info(f"🔍 Scraping @{username} (priority: {priority})")
            
            # Add delay to avoid overwhelming the system
            await asyncio.sleep(SCRAPE_DELAY_SECONDS)
            
            videos = await get_latest_videos(username, limit=5)
            
            if videos:
                self.save_video_data(username, videos, priority)
                viral_videos = self.check_viral_videos(username, videos)
                
                if viral_videos:
                    self.send_viral_alert(viral_videos)
                
                logging.info(f"✅ @{username}: {len(videos)} videos, {len(viral_videos)} viral")
                return username, True, viral_videos
            else:
                logging.warning(f"⚠️  @{username}: No videos found")
                return username, False, []
                
        except Exception as e:
            logging.error(f"❌ Error scraping @{username}: {e}")
            return username, False, []
    
    def get_accounts_to_scrape(self) -> List[Dict]:
        """Get accounts that are due for scraping based on priority."""
        current_time = datetime.now()
        accounts_to_scrape = []
        
        for account in self.accounts:
            if current_time >= account['next_scrape']:
                accounts_to_scrape.append(account)
        
        # Sort by priority (high first)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        accounts_to_scrape.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return accounts_to_scrape
    
    def update_next_scrape_time(self, account: Dict):
        """Update the next scrape time for an account."""
        interval = PRIORITY_INTERVALS.get(account['priority'], PRIORITY_INTERVALS['low'])
        account['last_scraped'] = datetime.now()
        account['next_scrape'] = datetime.now() + timedelta(seconds=interval)
    
    def print_status(self):
        """Print current monitoring status."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get overall statistics
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT username) as total_accounts,
                    SUM(total_scrapes) as total_scrapes,
                    SUM(total_videos_found) as total_videos,
                    SUM(total_viral_alerts) as total_alerts
                FROM monitoring_stats
            ''')
            
            stats = cursor.fetchone()
            if stats:
                logging.info(f"📊 MONITORING STATUS:")
                logging.info(f"  • Accounts: {stats[0]}")
                logging.info(f"  • Total scrapes: {stats[1] or 0}")
                logging.info(f"  • Videos found: {stats[2] or 0}")
                logging.info(f"  • Viral alerts: {stats[3] or 0}")
            
            # Show next scrape times
            current_time = datetime.now()
            next_scrapes = []
            for account in self.accounts:
                time_until = (account['next_scrape'] - current_time).total_seconds()
                if time_until <= 300:  # Show accounts due within 5 minutes
                    next_scrapes.append(f"@{account['username']} ({account['priority']}) in {int(time_until)}s")
            
            if next_scrapes:
                logging.info(f"⏰ NEXT SCRAPES: {', '.join(next_scrapes[:5])}")
            
            conn.close()
            
        except Exception as e:
            logging.error(f"❌ Error getting status: {e}")
    
    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle."""
        accounts_to_scrape = self.get_accounts_to_scrape()
        
        if not accounts_to_scrape:
            return
        
        logging.info(f"🔄 Starting scrape cycle: {len(accounts_to_scrape)} accounts")
        
        # Process accounts in batches to respect rate limits
        batch_size = MAX_CONCURRENT_SCRAPES
        for i in range(0, len(accounts_to_scrape), batch_size):
            batch = accounts_to_scrape[i:i + batch_size]
            
            # Create tasks for concurrent execution
            tasks = [self.scrape_account(account) for account in batch]
            
            # Execute batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update next scrape times
            for account in batch:
                self.update_next_scrape_time(account)
            
            # Add delay between batches
            if i + batch_size < len(accounts_to_scrape):
                await asyncio.sleep(30)  # 30 seconds between batches
        
        logging.info(f"✅ Scrape cycle completed")
    
    async def run(self):
        """Main monitoring loop."""
        logging.info("🚀 Multi-Account TikTok Viral Monitor Started!")
        logging.info(f"📋 Monitoring {len(self.accounts)} accounts")
        
        # Send startup notification
        try:
            startup_message = f"""🤖 **Multi-Account Monitor Started**

📊 **Configuration**:
• Accounts: {len(self.accounts)}
• High Priority: Every {PRIORITY_INTERVALS['high']//60} min
• Medium Priority: Every {PRIORITY_INTERVALS['medium']//60} min  
• Low Priority: Every {PRIORITY_INTERVALS['low']//60} min
• Viral Threshold: {VIRAL_THRESHOLD} views

🟢 **Status**: Running
⏰ **Started**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": startup_message,
                "parse_mode": "Markdown"
            }
            requests.post(url, data=data, timeout=10)
        except:
            pass
        
        cycle_count = 0
        while self.running:
            try:
                cycle_count += 1
                
                # Run monitoring cycle
                await self.run_monitoring_cycle()
                
                # Print status every 10 cycles
                if cycle_count % 10 == 0:
                    self.print_status()
                
                # Wait before next check (check every 30 seconds for due accounts)
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                logging.info("⏹️  Monitoring stopped by user")
                self.running = False
            except Exception as e:
                logging.error(f"❌ Error in monitoring loop: {e}")
                logging.error(traceback.format_exc())
                await asyncio.sleep(60)  # Wait 1 minute before retrying

async def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        # Just show status and exit
        monitor = MultiAccountMonitor()
        monitor.print_status()
        return
    
    # Start monitoring
    monitor = MultiAccountMonitor()
    await monitor.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Multi-Account Monitor stopped")
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1) 