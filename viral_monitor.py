#!/usr/bin/env python3
"""
TikTok Viral Monitor
===================

Monitors TikTok profiles every 5 minutes and sends Telegram alerts when videos go viral.
Detects when view count increases by 100+ views within a 5-minute window.

Features:
- Automated scraping every 5 minutes
- View comparison and viral detection
- Telegram bot notifications with video links
- Persistent data storage
- Error handling and logging

Usage:
    python3 viral_monitor.py <username>

Example:
    python3 viral_monitor.py tiktok

Author: Created for jamesweston55
Date: September 7, 2024
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

# Import our existing scraper
from main import get_latest_videos

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8400102574:AAFUN6vR6bsBdTHLt_6clxMlxYV-7IMG7fE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "2021266274")
MONITORING_INTERVAL = 5 * 60  # 5 minutes in seconds
VIRAL_THRESHOLD = 100  # View increase threshold for viral detection
DATABASE_FILE = "viral_monitor.db"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('viral_monitor.log'),
        logging.StreamHandler()
    ]
)

class ViralMonitor:
    def __init__(self, username: str):
        self.username = username
        self.db_file = DATABASE_FILE
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for storing video data."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create table for storing video data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_data (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    description TEXT,
                    views INTEGER,
                    likes INTEGER,
                    comments INTEGER,
                    shares INTEGER,
                    created_date TEXT,
                    scraped_at TIMESTAMP,
                    UNIQUE(id, scraped_at)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_username_scraped ON video_data(username, scraped_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON video_data(id)')
            
            conn.commit()
            conn.close()
            logging.info(f"Database initialized: {self.db_file}")
            
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise
    
    def save_video_data(self, videos: List[Dict]):
        """Save scraped video data to database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            scraped_at = datetime.now()
            
            for video in videos:
                cursor.execute('''
                    INSERT OR REPLACE INTO video_data 
                    (id, username, description, views, likes, comments, shares, created_date, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video['id'],
                    self.username,
                    video['desc'],
                    video['views'],
                    video['likes'],
                    video['comments'],
                    video['shares'],
                    video['created'],
                    scraped_at
                ))
            
            conn.commit()
            conn.close()
            logging.info(f"Saved {len(videos)} videos to database")
            
        except Exception as e:
            logging.error(f"Error saving video data: {e}")
            raise
    
    def get_previous_data(self, time_window_minutes: int = 90) -> Dict[str, Dict]:
        """Get video data from the previous scrape within the time window."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get data from 90 minutes ago (with some tolerance)
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes + 10)
            
            cursor.execute('''
                SELECT id, views, likes, comments, shares, scraped_at
                FROM video_data 
                WHERE username = ? AND scraped_at >= ?
                ORDER BY scraped_at DESC
            ''', (self.username, cutoff_time))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Group by video ID and get the most recent entry for each
            previous_data = {}
            for row in rows:
                video_id, views, likes, comments, shares, scraped_at = row
                if video_id not in previous_data:
                    previous_data[video_id] = {
                        'views': views,
                        'likes': likes,
                        'comments': comments,
                        'shares': shares,
                        'scraped_at': scraped_at
                    }
            
            logging.info(f"Retrieved previous data for {len(previous_data)} videos")
            return previous_data
            
        except Exception as e:
            logging.error(f"Error retrieving previous data: {e}")
            return {}
    
    def detect_viral_videos(self, current_videos: List[Dict], previous_data: Dict[str, Dict]) -> List[Dict]:
        """Detect videos that have gone viral based on view increase."""
        viral_videos = []
        
        for video in current_videos:
            video_id = video['id']
            current_views = video['views']
            
            if video_id in previous_data:
                previous_views = previous_data[video_id]['views']
                view_increase = current_views - previous_views
                
                logging.info(f"Video {video_id}: {previous_views} -> {current_views} (+{view_increase} views)")
                
                if view_increase >= VIRAL_THRESHOLD:
                    viral_video = video.copy()
                    viral_video['view_increase'] = view_increase
                    viral_video['previous_views'] = previous_views
                    viral_videos.append(viral_video)
                    
                    logging.warning(f"🚨 VIRAL VIDEO DETECTED! {video_id} gained {view_increase} views!")
            else:
                logging.info(f"New video detected: {video_id} with {current_views} views")
        
        return viral_videos
    
    def send_telegram_message(self, message: str):
        """Send a message via Telegram bot."""
        if TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
            logging.warning("Telegram bot token not configured. Skipping notification.")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logging.info("Telegram notification sent successfully")
                return True
            else:
                logging.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")
            return False
    
    def format_viral_alert(self, viral_video: Dict) -> str:
        """Format viral video alert message for Telegram."""
        video_url = f"https://www.tiktok.com/@{self.username}/video/{viral_video['id']}"
        
        message = f"""🚨 <b>VIRAL VIDEO ALERT!</b> 🚨

📱 <b>TikTok Profile:</b> @{self.username}
🎬 <b>Video:</b> {viral_video['desc'][:100]}{'...' if len(viral_video['desc']) > 100 else ''}

📈 <b>VIEW EXPLOSION:</b>
• Previous: {viral_video['previous_views']:,} views
• Current: {viral_video['views']:,} views
• <b>Increase: +{viral_video['view_increase']:,} views in 90 minutes!</b>

💫 <b>Current Stats:</b>
❤️ {viral_video['likes']:,} likes
💬 {viral_video['comments']:,} comments
🔄 {viral_video['shares']:,} shares

🔗 <b>Watch here:</b> {video_url}

⏰ Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return message
    
    async def run_single_check(self):
        """Run a single monitoring check."""
        try:
            logging.info(f"Starting viral check for @{self.username}")
            
            # Scrape current video data
            current_videos = await get_latest_videos(self.username, limit=5)
            
            if not current_videos:
                logging.warning("No videos found in current scrape")
                return
            
            logging.info(f"Successfully scraped {len(current_videos)} videos")
            
            # Get previous data for comparison
            previous_data = self.get_previous_data()
            
            # Detect viral videos
            viral_videos = self.detect_viral_videos(current_videos, previous_data)
            
            # Send notifications for viral videos
            for viral_video in viral_videos:
                message = self.format_viral_alert(viral_video)
                self.send_telegram_message(message)
                
                # Also save to file for backup
                alert_filename = f"viral_alert_{viral_video['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(alert_filename, 'w') as f:
                    json.dump(viral_video, f, indent=2)
                logging.info(f"Viral alert saved to {alert_filename}")
            
            # Save current data to database
            self.save_video_data(current_videos)
            
            if viral_videos:
                logging.info(f"🚨 Found {len(viral_videos)} viral videos!")
            else:
                logging.info("✅ No viral videos detected this round")
                
        except Exception as e:
            logging.error(f"Error in viral check: {e}")
            logging.error(traceback.format_exc())
    
    async def run_continuous_monitoring(self):
        """Run continuous monitoring every 90 minutes."""
        logging.info(f"🚀 Starting continuous viral monitoring for @{self.username}")
        logging.info(f"⏰ Checking every {MONITORING_INTERVAL // 60} minutes")
        logging.info(f"📈 Viral threshold: {VIRAL_THRESHOLD}+ view increase")
        
        while True:
            try:
                await self.run_single_check()
                
                # Wait for next check
                next_check = datetime.now() + timedelta(seconds=MONITORING_INTERVAL)
                logging.info(f"💤 Next check scheduled for: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                
                await asyncio.sleep(MONITORING_INTERVAL)
                
            except KeyboardInterrupt:
                logging.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logging.error(f"Error in continuous monitoring: {e}")
                logging.info("⏳ Waiting 5 minutes before retry...")
                await asyncio.sleep(300)  # Wait 5 minutes before retry


def setup_telegram_bot():
    """Instructions for setting up Telegram bot."""
    print("""
🤖 TELEGRAM BOT SETUP INSTRUCTIONS:

1. Create a Telegram Bot:
   • Message @BotFather on Telegram
   • Send: /newbot
   • Choose a name and username for your bot
   • Save the bot token

2. Get Your Chat ID:
   • Message your bot something
   • Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   • Find your chat ID in the response

3. Set Environment Variables:
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_CHAT_ID="your_chat_id_here"

4. Or edit this script and replace the placeholder values

📱 Your bot will send viral alerts to your Telegram!
""")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 viral_monitor.py <username> [--setup]")
        print("Example: python3 viral_monitor.py tiktok")
        print("Setup: python3 viral_monitor.py --setup")
        sys.exit(1)
    
    if sys.argv[1] == "--setup":
        setup_telegram_bot()
        return
    
    username = sys.argv[1]
    
    # Check if Telegram is configured
    if TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("⚠️  Telegram bot not configured. Run with --setup for instructions.")
        print("You can still run monitoring, but alerts will only be logged.")
        
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Initialize monitor
    monitor = ViralMonitor(username)
    
    # Check if this is a one-time check or continuous monitoring
    if len(sys.argv) > 2 and sys.argv[2] == "--once":
        logging.info("Running single viral check...")
        await monitor.run_single_check()
    else:
        logging.info("Starting continuous monitoring...")
        await monitor.run_continuous_monitoring()


if __name__ == "__main__":
    asyncio.run(main()) 