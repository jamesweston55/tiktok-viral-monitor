#!/usr/bin/env python3
"""
Simple Multi-Account TikTok Viral Monitor
========================================

Simplified viral monitoring system for multiple TikTok accounts with:
- Simple username-only CSV file
- Uniform monitoring intervals
- Efficient batch processing
- Telegram alerts for viral videos

Features:
- Monitor all accounts every 5 minutes
- 100+ view increase threshold for viral detection
- Staggered scraping to avoid rate limits
- Comprehensive logging
- Telegram alerts with video links

Usage:
    python3 simple_multi_monitor.py

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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

# Import our existing scraper
from main import get_latest_videos

# Import configuration
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    MONITORING_INTERVAL, VIRAL_THRESHOLD, ACCOUNTS_FILE, DATABASE_FILE,
    MAX_CONCURRENT_SCRAPES, SCRAPE_DELAY_SECONDS, BATCH_DELAY_SECONDS,
    MAX_VIDEOS_TO_CHECK, LOG_FILE, LOG_LEVEL, LOG_FORMAT
)

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class SimpleMultiMonitor:
    def __init__(self):
        self.db_file = DATABASE_FILE
        self.accounts = self.load_accounts()
        self.init_database()
        self.running = True
        
    def load_accounts(self) -> List[str]:
        """Load usernames from CSV file."""
        usernames = []
        try:
            with open(ACCOUNTS_FILE, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    username = row['username'].strip()
                    if username:
                        usernames.append(username)
            
            logging.info(f"📊 Loaded {len(usernames)} accounts for monitoring")
            logging.info(f"⏰ Monitoring interval: {MONITORING_INTERVAL // 60} minutes")
            logging.info(f"🎯 Viral threshold: {VIRAL_THRESHOLD} views")
            
            return usernames
            
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
            
            # Create table for storing video data
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
                    avg_views INTEGER DEFAULT 0
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_username_scraped ON video_data(username, scraped_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON video_data(id)')
            
            conn.commit()
            conn.close()
            logging.info(f"✅ Database initialized: {self.db_file}")
            
        except Exception as e:
            logging.error(f"❌ Error initializing database: {e}")
            raise
    
    def save_video_data(self, username: str, videos: List[Dict]):
        """Save scraped video data to database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            current_time = datetime.now()
            
            for video in videos:
                cursor.execute('''
                    INSERT OR REPLACE INTO video_data 
                    (id, username, description, views, likes, comments, shares, created_date, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video['id'], username, video['desc'], video['views'],
                    video['likes'], video['comments'], video['shares'],
                    video['created'], current_time
                ))
            
            # Update monitoring statistics
            cursor.execute('''
                INSERT OR REPLACE INTO monitoring_stats 
                (username, total_scrapes, total_videos_found, last_scrape_time)
                VALUES (?, 
                    COALESCE((SELECT total_scrapes FROM monitoring_stats WHERE username = ?), 0) + 1,
                    COALESCE((SELECT total_videos_found FROM monitoring_stats WHERE username = ?), 0) + ?,
                    ?)
            ''', (username, username, username, len(videos), current_time))
            
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
    
    async def scrape_account(self, username: str) -> Tuple[str, bool, List[Dict]]:
        """Scrape a single account."""
        try:
            logging.info(f"🔍 Scraping @{username}")
            
            # Add delay to avoid overwhelming the system
            await asyncio.sleep(SCRAPE_DELAY_SECONDS)
            
            videos = await get_latest_videos(username, limit=MAX_VIDEOS_TO_CHECK)
            
            if videos:
                self.save_video_data(username, videos)
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
                logging.info(f"  • Accounts: {stats[0]}/{len(self.accounts)}")
                logging.info(f"  • Total scrapes: {stats[1] or 0}")
                logging.info(f"  • Videos found: {stats[2] or 0}")
                logging.info(f"  • Viral alerts: {stats[3] or 0}")
            
            # Show recent viral alerts
            cursor.execute('''
                SELECT username, total_viral_alerts, last_viral_alert
                FROM monitoring_stats 
                WHERE total_viral_alerts > 0
                ORDER BY last_viral_alert DESC
                LIMIT 5
            ''')
            
            recent_alerts = cursor.fetchall()
            if recent_alerts:
                logging.info("🔥 RECENT VIRAL ACCOUNTS:")
                for username, alerts, last_alert in recent_alerts:
                    if last_alert:
                        last_time = datetime.fromisoformat(last_alert).strftime('%H:%M')
                        logging.info(f"  • @{username}: {alerts} alerts (last: {last_time})")
            
            conn.close()
            
        except Exception as e:
            logging.error(f"❌ Error getting status: {e}")
    
    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle."""
        logging.info(f"🔄 Starting scrape cycle: {len(self.accounts)} accounts")
        
        # Process accounts in batches to respect rate limits
        batch_size = MAX_CONCURRENT_SCRAPES
        total_viral = 0
        
        for i in range(0, len(self.accounts), batch_size):
            batch = self.accounts[i:i + batch_size]
            
            # Create tasks for concurrent execution
            tasks = [self.scrape_account(username) for username in batch]
            
            # Execute batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count viral videos
            for result in results:
                if isinstance(result, tuple) and len(result) == 3:
                    _, success, viral_videos = result
                    if success:
                        total_viral += len(viral_videos)
            
            # Add delay between batches
            if i + batch_size < len(self.accounts):
                await asyncio.sleep(BATCH_DELAY_SECONDS)
        
        logging.info(f"✅ Scrape cycle completed - {total_viral} viral videos detected")
    
    async def run(self):
        """Main monitoring loop."""
        logging.info("🚀 Simple Multi-Account TikTok Viral Monitor Started!")
        logging.info(f"📋 Monitoring {len(self.accounts)} accounts every {MONITORING_INTERVAL//60} minutes")
        
        # Send startup notification
        try:
            startup_message = f"""🤖 **Multi-Account Monitor Started**

📊 **Configuration**:
• Accounts: {len(self.accounts)}
• Monitoring: Every {MONITORING_INTERVAL//60} minutes
• Viral Threshold: {VIRAL_THRESHOLD} views
• Max Concurrent: {MAX_CONCURRENT_SCRAPES}

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
                start_time = datetime.now()
                
                # Run monitoring cycle
                await self.run_monitoring_cycle()
                
                # Print status every 5 cycles
                if cycle_count % 5 == 0:
                    self.print_status()
                
                # Calculate how long to wait
                cycle_duration = (datetime.now() - start_time).total_seconds()
                wait_time = max(0, MONITORING_INTERVAL - cycle_duration)
                
                if wait_time > 0:
                    next_run = datetime.now() + timedelta(seconds=wait_time)
                    logging.info(f"💤 Next cycle at: {next_run.strftime('%H:%M:%S')} (in {int(wait_time/60)} min)")
                    await asyncio.sleep(wait_time)
                else:
                    logging.warning(f"⚠️  Cycle took {int(cycle_duration)} seconds (longer than {MONITORING_INTERVAL} sec interval)")
                
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
        monitor = SimpleMultiMonitor()
        monitor.print_status()
        return
    
    # Start monitoring
    monitor = SimpleMultiMonitor()
    await monitor.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Simple Multi-Monitor stopped")
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1) 