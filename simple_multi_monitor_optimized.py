#!/usr/bin/env python3
"""
TikTok Viral Monitor - OPTIMIZED VERSION
========================================

Multi-account TikTok viral video monitoring system with optimized memory management.
Monitors multiple TikTok accounts for viral videos and sends alerts via Telegram.

Features:
- Memory-optimized browser management
- Droplet mode for cloud deployment
- Browser instance reuse and cleanup
- Resource monitoring and limits
"""

import asyncio
import sqlite3
import csv
import os
import sys
import time
import traceback
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
import queue
import gc
import psutil

# Import our scraper and config
from main import get_latest_videos
from config_optimized import *

# =============================================================================
# MEMORY MANAGEMENT
# =============================================================================

class BrowserManager:
    """Manages browser instances with memory optimization."""
    
    def __init__(self, max_instances=3, memory_limit="512MB", idle_timeout=300):
        self.max_instances = max_instances
        self.memory_limit = memory_limit
        self.idle_timeout = idle_timeout
        self.browsers = []
        self.last_used = {}
        self.lock = threading.Lock()
        
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def cleanup_idle_browsers(self):
        """Clean up idle browser instances."""
        with self.lock:
            current_time = time.time()
            browsers_to_close = []
            
            for i, browser in enumerate(self.browsers):
                if browser and current_time - self.last_used.get(i, 0) > self.idle_timeout:
                    browsers_to_close.append(i)
            
            for i in reversed(browsers_to_close):
                try:
                    asyncio.create_task(self.browsers[i].close())
                    self.browsers[i] = None
                    del self.last_used[i]
                    logging.info(f"🧹 Cleaned up idle browser instance {i}")
                except Exception as e:
                    logging.error(f"Error cleaning up browser {i}: {e}")
    
    def force_garbage_collection(self):
        """Force garbage collection to free memory."""
        gc.collect()
        memory_after = self.get_memory_usage()
        logging.info(f"🗑️  Garbage collection completed. Memory: {memory_after:.1f}MB")

# Global browser manager
browser_manager = BrowserManager(
    max_instances=MAX_BROWSER_INSTANCES,
    memory_limit=BROWSER_MEMORY_LIMIT,
    idle_timeout=BROWSER_IDLE_TIMEOUT
)

# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def init_database():
    """Initialize SQLite database with optimized settings."""
    conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")  # Better for concurrent access
    conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
    conn.execute("PRAGMA cache_size=1000")    # More cache
    conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
    
    # Video data table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS video_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            video_id TEXT NOT NULL,
            description TEXT,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            shares INTEGER,
            create_time TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, video_id)
        )
    ''')
    
    # Monitoring stats table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            last_scraped TIMESTAMP,
            videos_found INTEGER DEFAULT 0,
            viral_alerts_sent INTEGER DEFAULT 0,
            last_viral_alert TIMESTAMP,
            UNIQUE(username)
        )
    ''')
    
    # Create indexes for better performance
    conn.execute('CREATE INDEX IF NOT EXISTS idx_username_video ON video_data(username, video_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON video_data(scraped_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_username_stats ON monitoring_stats(username)')
    
    conn.commit()
    conn.close()
    logging.info("📊 Database initialized with optimizations")

def save_video_data(username, videos):
    """Save video data to database with batch insert."""
    if not videos:
        return
    
    conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
    try:
        # Prepare batch insert data
        video_data = []
        for video in videos:
            video_data.append((
                username,
                video.get('video_id', ''),
                video.get('description', '')[:500],  # Limit description length
                video.get('views', 0),
                video.get('likes', 0),
                video.get('comments', 0),
                video.get('shares', 0),
                video.get('create_time', ''),
                datetime.now()
            ))
        
        # Batch insert with conflict resolution
        conn.executemany('''
            INSERT OR REPLACE INTO video_data 
            (username, video_id, description, views, likes, comments, shares, create_time, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', video_data)
        
        conn.commit()
        logging.info(f"💾 Saved {len(videos)} videos for @{username}")
        
    except Exception as e:
        logging.error(f"❌ Error saving video data for @{username}: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_previous_video_data(username, limit=5):
    """Get previous video data for comparison."""
    conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
    try:
        cursor = conn.execute('''
            SELECT video_id, views, likes, comments, shares, create_time
            FROM video_data 
            WHERE username = ? 
            ORDER BY scraped_at DESC 
            LIMIT ?
        ''', (username, limit))
        
        videos = []
        for row in cursor.fetchall():
            videos.append({
                'video_id': row[0],
                'views': row[1],
                'likes': row[2],
                'comments': row[3],
                'shares': row[4],
                'create_time': row[5]
            })
        
        return videos
    except Exception as e:
        logging.error(f"❌ Error getting previous data for @{username}: {e}")
        return []
    finally:
        conn.close()

# =============================================================================
# VIRAL DETECTION
# =============================================================================

def check_viral_videos(username, current_videos, previous_videos):
    """Check for viral videos by comparing current and previous data."""
    viral_videos = []
    
    # Create lookup for previous videos
    prev_lookup = {v['video_id']: v for v in previous_videos}
    
    for current_video in current_videos:
        video_id = current_video.get('video_id')
        if not video_id:
            continue
            
        current_views = current_video.get('views', 0)
        previous_video = prev_lookup.get(video_id)
        
        if previous_video:
            previous_views = previous_video.get('views', 0)
            view_increase = current_views - previous_views
            
            if view_increase >= VIRAL_THRESHOLD:
                viral_videos.append({
                    'video_id': video_id,
                    'description': current_video.get('description', ''),
                    'current_views': current_views,
                    'previous_views': previous_views,
                    'view_increase': view_increase,
                    'likes': current_video.get('likes', 0),
                    'comments': current_video.get('comments', 0),
                    'shares': current_video.get('shares', 0),
                    'create_time': current_video.get('create_time', '')
                })
                logging.info(f"🔥 VIRAL DETECTED! @{username} video {video_id}: +{view_increase} views")
    
    return viral_videos

def send_viral_alert(username, viral_videos):
    """Send viral alert via Telegram."""
    if not viral_videos:
        return
    
    try:
        import requests
        
        message = f"🔥 VIRAL ALERT! @{username}\n\n"
        
        for i, video in enumerate(viral_videos[:3], 1):  # Limit to 3 videos
            message += f"📹 Video {i}:\n"
            message += f"📈 Views: {video['previous_views']:,} → {video['current_views']:,} (+{video['view_increase']:,})\n"
            message += f"❤️  Likes: {video['likes']:,}\n"
            message += f"💬 Comments: {video['comments']:,}\n"
            message += f"🔄 Shares: {video['shares']:,}\n"
            if video['description']:
                desc = video['description'][:100] + "..." if len(video['description']) > 100 else video['description']
                message += f"📝 Description: {desc}\n"
            message += f"⏰ Posted: {video['create_time']}\n\n"
        
        if len(viral_videos) > 3:
            message += f"... and {len(viral_videos) - 3} more viral videos!\n"
        
        message += f"🔗 https://www.tiktok.com/@{username}"
        
        # Send to Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logging.info(f"📱 Sent viral alert for @{username}")
            update_viral_alert_count(username)
        else:
            logging.error(f"❌ Failed to send alert for @{username}: {response.status_code}")
            
    except Exception as e:
        logging.error(f"❌ Error sending viral alert for @{username}: {e}")

def update_viral_alert_count(username):
    """Update viral alert count in database."""
    conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
    try:
        conn.execute('''
            INSERT OR REPLACE INTO monitoring_stats 
            (username, last_scraped, viral_alerts_sent, last_viral_alert)
            VALUES (?, COALESCE((SELECT last_scraped FROM monitoring_stats WHERE username = ?), CURRENT_TIMESTAMP), 
                   COALESCE((SELECT viral_alerts_sent FROM monitoring_stats WHERE username = ?), 0) + 1, 
                   CURRENT_TIMESTAMP)
        ''', (username, username, username))
        conn.commit()
    except Exception as e:
        logging.error(f"❌ Error updating alert count for @{username}: {e}")
    finally:
        conn.close()

# =============================================================================
# ACCOUNT MANAGEMENT
# =============================================================================

def load_accounts():
    """Load accounts from CSV file."""
    accounts = []
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                username = row.get('username', '').strip()
                if username and not username.startswith('#'):
                    accounts.append(username)
        
        logging.info(f"📋 Loaded {len(accounts)} accounts from {ACCOUNTS_FILE}")
        return accounts
    except FileNotFoundError:
        logging.error(f"❌ Accounts file {ACCOUNTS_FILE} not found!")
        return []
    except Exception as e:
        logging.error(f"❌ Error loading accounts: {e}")
        return []

# =============================================================================
# SCRAPING FUNCTIONS
# =============================================================================

async def scrape_account(username, scrape_count=0):
    """Scrape a single account with memory management."""
    try:
        # Clean up browsers periodically
        if scrape_count % BROWSER_CLEANUP_INTERVAL == 0:
            browser_manager.cleanup_idle_browsers()
            browser_manager.force_garbage_collection()
        
        # Check memory usage
        memory_usage = browser_manager.get_memory_usage()
        if memory_usage > 800:  # If using more than 800MB
            logging.warning(f"⚠️  High memory usage: {memory_usage:.1f}MB")
            browser_manager.force_garbage_collection()
        
        logging.info(f"🔍 Scraping @{username}...")
        
        # Get latest videos
        videos = await get_latest_videos(username, limit=MAX_VIDEOS_TO_CHECK)
        
        if not videos:
            logging.warning(f"⚠️  No videos found for @{username}")
            return
        
        # Save current data
        save_video_data(username, videos)
        
        # Get previous data for comparison
        previous_videos = get_previous_video_data(username, limit=MAX_VIDEOS_TO_CHECK)
        
        # Check for viral videos
        viral_videos = check_viral_videos(username, videos, previous_videos)
        
        if viral_videos:
            send_viral_alert(username, viral_videos)
        
        # Update monitoring stats
        conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
        try:
            conn.execute('''
                INSERT OR REPLACE INTO monitoring_stats 
                (username, last_scraped, videos_found)
                VALUES (?, CURRENT_TIMESTAMP, ?)
            ''', (username, len(videos)))
            conn.commit()
        finally:
            conn.close()
        
        logging.info(f"✅ Completed @{username}: {len(videos)} videos, {len(viral_videos)} viral")
        
    except Exception as e:
        logging.error(f"❌ Error scraping @{username}: {e}")
        logging.error(traceback.format_exc())

async def run_monitoring_cycle():
    """Run one complete monitoring cycle with optimized resource management."""
    accounts = load_accounts()
    if not accounts:
        logging.error("❌ No accounts to monitor!")
        return
    
    logging.info(f"🚀 Starting monitoring cycle for {len(accounts)} accounts")
    logging.info(f"💾 Memory usage: {browser_manager.get_memory_usage():.1f}MB")
    
    # Process accounts in smaller batches to manage memory
    batch_size = MAX_CONCURRENT_SCRAPES
    total_batches = (len(accounts) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(accounts))
        batch_accounts = accounts[start_idx:end_idx]
        
        logging.info(f"📦 Processing batch {batch_num + 1}/{total_batches}: {len(batch_accounts)} accounts")
        
        # Create tasks for this batch
        tasks = []
        for i, username in enumerate(batch_accounts):
            task = asyncio.create_task(scrape_account(username, start_idx + i))
            tasks.append(task)
        
        # Wait for batch to complete
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logging.error(f"❌ Error in batch {batch_num + 1}: {e}")
        
        # Clean up between batches
        browser_manager.cleanup_idle_browsers()
        
        # Wait between batches (except for the last one)
        if batch_num < total_batches - 1:
            logging.info(f"⏳ Waiting {BATCH_DELAY_SECONDS} seconds before next batch...")
            await asyncio.sleep(BATCH_DELAY_SECONDS)
    
    # Final cleanup
    browser_manager.force_garbage_collection()
    final_memory = browser_manager.get_memory_usage()
    logging.info(f"✅ Monitoring cycle completed. Final memory: {final_memory:.1f}MB")

# =============================================================================
# MAIN MONITORING LOOP
# =============================================================================

async def main():
    """Main monitoring loop with resource management."""
    # Setup logging with error handling
    log_handlers = [logging.StreamHandler(sys.stdout)]
    
    # Only add file handler if log file is not a directory
    if not os.path.isdir(LOG_FILE):
        try:
            log_handlers.append(logging.FileHandler(LOG_FILE))
        except Exception as e:
            print(f"Warning: Could not create log file {LOG_FILE}: {e}")
            print("Logging to console only.")
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=log_handlers
    )
    
    # Initialize database
    init_database()
    
    # Send startup notification
    try:
        import requests
        accounts = load_accounts()
        message = f"""🤖 Multi-Account Monitor Started (OPTIMIZED)

📊 Configuration:
• Accounts: {len(accounts)}
• Monitoring: Every {MONITORING_INTERVAL // 60} minutes
• Viral Threshold: {VIRAL_THRESHOLD} views
• Max Concurrent: {MAX_CONCURRENT_SCRAPES}
• Memory Limit: {BROWSER_MEMORY_LIMIT}
• Droplet Mode: {'ON' if DROPLET_MODE else 'OFF'}

🟢 Status: Running
⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        logging.error(f"❌ Failed to send startup notification: {e}")
    
    logging.info("🚀 TikTok Viral Monitor (OPTIMIZED) started")
    logging.info(f"💾 Initial memory usage: {browser_manager.get_memory_usage():.1f}MB")
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            logging.info(f"🔄 Starting monitoring cycle #{cycle_count}")
            
            start_time = time.time()
            await run_monitoring_cycle()
            cycle_duration = time.time() - start_time
            
            logging.info(f"⏱️  Cycle #{cycle_count} completed in {cycle_duration:.1f} seconds")
            logging.info(f"💾 Memory usage: {browser_manager.get_memory_usage():.1f}MB")
            
            # Wait for next cycle
            wait_time = MONITORING_INTERVAL - cycle_duration
            if wait_time > 0:
                logging.info(f"⏳ Waiting {wait_time:.0f} seconds until next cycle...")
                await asyncio.sleep(wait_time)
            else:
                logging.warning("⚠️  Cycle took longer than monitoring interval!")
                
    except KeyboardInterrupt:
        logging.info("👋 Simple Multi-Monitor stopped")
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        logging.error(traceback.format_exc())
    finally:
        # Final cleanup
        browser_manager.force_garbage_collection()
        logging.info(f"💾 Final memory usage: {browser_manager.get_memory_usage():.1f}MB")

if __name__ == "__main__":
    asyncio.run(main())
