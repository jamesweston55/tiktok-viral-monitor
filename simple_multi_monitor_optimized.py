#!/usr/bin/env python3
# Cache bust: 2025-09-10-05:28 - Force Docker rebuild
# TikTok Viral Monitor - Optimized Version with Emergency Debugging
# This script monitors TikTok accounts for viral videos and sends Telegram notifications
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
import json
import os
import sys
import time
import traceback
import logging
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import threading
import queue
import gc
import psutil
import random
from playwright.async_api import async_playwright
from main import solve_captcha

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
            # Get video_id from either 'video_id' or 'id' field
            video_id = video.get('video_id') or video.get('id', '')
            if not video_id:
                logging.warning(f"Skipping video with missing ID for {username}: {video}")
                continue
                
            video_data.append((
                username,
                str(video_id),  # Ensure it's a string
                video.get("desc", "")[:500],  # Limit description length
                video.get('views', 0),
                video.get('likes', 0),
                video.get('comments', 0),
                video.get('shares', 0),
                video.get("created", ""),
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


def get_previous_video_data_for_ids(username: str, video_ids: list[str]) -> dict[str, dict]:
    """Get the latest previous row per video_id for a username.
    Returns a mapping: video_id -> {views, likes, comments, shares, create_time}.
    """
    if not video_ids:
        return {}
    # Deduplicate and keep only valid ids
    unique_ids = [vid for vid in {vid for vid in video_ids if vid}]
    if not unique_ids:
        return {}
    placeholders = ','.join(['?'] * len(unique_ids))
    params = [username] + unique_ids
    query = f'''
        SELECT video_id, views, likes, comments, shares, create_time, scraped_at
        FROM video_data
        WHERE username = ? AND video_id IN ({placeholders})
        ORDER BY video_id ASC, scraped_at DESC
    '''
    conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
    try:
        cursor = conn.execute(query, params)
        latest_per_id: dict[str, dict] = {}
        for row in cursor.fetchall():
            vid = row[0]
            # Because ordered by scraped_at DESC within each video_id group, first occurrence wins
            if vid in latest_per_id:
                continue
            latest_per_id[vid] = {
                'video_id': row[0],
                'views': row[1],
                'likes': row[2],
                'comments': row[3],
                'shares': row[4],
                'create_time': row[5],
            }
        return latest_per_id
    except Exception as e:
        logging.error(f"❌ Error getting previous data for ids @{username}: {e}")
        return {}
    finally:
        conn.close()

# =============================================================================
# VIRAL DETECTION
# =============================================================================


def save_view_deltas(username, current_videos, previous_videos):
    """Save view deltas to CSV and JSON files."""
    try:
        # Create lookup for previous videos
        prev_lookup = {v['video_id']: v for v in previous_videos}
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Prepare delta data
        deltas = []
        timestamp = datetime.now().isoformat()
        
        # Check if this user has any monitoring history (to avoid fake deltas for new users)
        is_new_user = len(previous_videos) == 0
        if is_new_user:
            logging.info(f"🆕 New user detected: @{username} - initial views will not be counted as gains")
        
        for current_video in current_videos:
            video_id = current_video.get('video_id') or current_video.get('id')
            if not video_id:
                continue
                
            current_views = current_video.get('views', 0)
            previous_video = prev_lookup.get(video_id)
            
            if previous_video:
                # Existing video - calculate real delta
                previous_views = previous_video.get('views', 0)
                delta = current_views - previous_views
            else:
                # New video detection
                if is_new_user:
                    # For new users, don't count initial views as gains
                    previous_views = current_views
                    delta = 0
                    logging.debug(f"🆕 New user's video {video_id[:10]}... - setting delta to 0 (initial: {current_views} views)")
                else:
                    # For existing users, new video is a real gain from 0
                    previous_views = 0
                    delta = current_views
                    logging.info(f"📹 New video detected for existing user @{username}: {video_id[:10]}... (+{delta} views)")
            
            delta_data = {
                'timestamp': timestamp,
                'username': username,
                'video_id': video_id,
                'previous_views': previous_views,
                'current_views': current_views,
                'delta': delta
            }
            deltas.append(delta_data)
            
            # Write to JSON file (append)
            try:
                with open('data/view_deltas.jsonl', 'a') as f:
                    json.dump(delta_data, f)
                    f.write('\n')
            except Exception as e:
                logging.error(f"Error writing to JSON: {e}")
            
            # Write to CSV file (append)
            try:
                file_exists = os.path.exists('data/view_deltas.csv')
                with open('data/view_deltas.csv', 'a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['timestamp', 'username', 'video_id', 'previous_views', 'current_views', 'delta'])
                    writer.writerow([timestamp, username, video_id, previous_views, current_views, delta])
            except Exception as e:
                logging.error(f"Error writing to CSV: {e}")
        
        logging.info(f"📊 Saved {len(deltas)} view deltas for @{username}")
        
    except Exception as e:
        logging.error(f"Error saving view deltas for {username}: {e}")


def check_viral_videos(username, current_videos, previous_videos):
    """Check for viral videos by comparing current and previous data."""
    
    # Save view deltas to files
    save_view_deltas(username, current_videos, previous_videos)
    
    viral_videos = []
    
    # Create lookup for previous videos
    prev_lookup = {v['video_id']: v for v in previous_videos}
    
    # Skip viral detection only if this user has NO database history at all
    # (This prevents fake massive deltas on very first monitoring of a user)
    conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
    try:
        cursor = conn.execute('SELECT COUNT(*) FROM video_data WHERE username = ?', (username,))
        total_user_entries = cursor.fetchone()[0]
        conn.close()
        
        # Only skip if user has less than 5 total entries (very new user)
        if total_user_entries < 5:
            logging.info(f"🆕 Skipping viral detection for new user @{username} (only {total_user_entries} entries)")
            return viral_videos
    except Exception as e:
        logging.error(f"Error checking user history: {e}")
        conn.close()
    
    for current_video in current_videos:
        video_id = current_video.get('video_id') or current_video.get('id')
        if not video_id:
            continue
            
        current_views = current_video.get('views', 0)
        previous_video = prev_lookup.get(video_id)
        
        if previous_video:
            previous_views = previous_video.get('views', 0)
            view_increase = current_views - previous_views
        else:
            # New video for existing user - this is a real gain from 0
            previous_views = 0
            view_increase = current_views
        
        if view_increase >= VIRAL_THRESHOLD:
            viral_videos.append({
                'video_id': video_id,
                'description': current_video.get("desc", ""),
                'current_views': current_views,
                'previous_views': previous_views,
                'view_increase': view_increase,
                'likes': current_video.get('likes', 0),
                'comments': current_video.get('comments', 0),
                'shares': current_video.get('shares', 0),
                'create_time': current_video.get("created", "")
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
            create_time = video.get('create_time', 'Unknown')
            if create_time and create_time != 'Unknown':
                message += f"⏰ Posted: {create_time}\n"
            message += "\n"
        
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
    thread_id = threading.current_thread().ident
    task_id = id(asyncio.current_task())
    
    logging.info(f"🔍 [THREAD-{thread_id}] [TASK-{task_id}] Starting scrape for @{username}")
    
    try:
        # Clean up browsers periodically
        if scrape_count % BROWSER_CLEANUP_INTERVAL == 0:
            logging.info(f"🧹 [THREAD-{thread_id}] Cleaning up browsers for @{username}")
            browser_manager.cleanup_idle_browsers()
            browser_manager.force_garbage_collection()
        
        # Check memory usage
        memory_usage = browser_manager.get_memory_usage()
        logging.info(f"💾 [THREAD-{thread_id}] Memory before @{username}: {memory_usage:.1f}MB")
        
        if memory_usage > 800:  # If using more than 800MB
            logging.warning(f"⚠️  [THREAD-{thread_id}] High memory usage: {memory_usage:.1f}MB")
            browser_manager.force_garbage_collection()
        
        logging.info(f"🔍 [THREAD-{thread_id}] Scraping @{username}...")
        
        # Get latest videos with timeout
        logging.info(f"📺 [THREAD-{thread_id}] Getting videos for @{username}...")
        try:
            videos = await asyncio.wait_for(
                get_latest_videos(username, limit=MAX_VIDEOS_TO_CHECK),
                timeout=max(30, PAGE_TIMEOUT / 1000)
            )
        except asyncio.TimeoutError:
            logging.error(f"⏱️  [THREAD-{thread_id}] Timeout while getting videos for @{username}")
            return
        except Exception as e:
            logging.error(f"❌ [THREAD-{thread_id}] Error in get_latest_videos for @{username}: {e}")
            logging.error(traceback.format_exc())
            return
        logging.info(f"📺 [THREAD-{thread_id}] Got {len(videos) if videos else 0} videos for @{username}")
        
        if not videos:
            logging.warning(f"⚠️  [THREAD-{thread_id}] No videos found for @{username}")
            return
        
        # Get previous data for comparison (match per current video_id)
        logging.info(f"📊 [THREAD-{thread_id}] Getting previous data for @{username} (by video ids)...")
        current_ids = []
        for cv in videos:
            vid = cv.get('video_id') or cv.get('id')
            if vid:
                current_ids.append(str(vid))
        prev_lookup = get_previous_video_data_for_ids(username, current_ids)
        previous_videos = list(prev_lookup.values())
        logging.info(f"�� [THREAD-{thread_id}] Got previous for {len(previous_videos)} of {len(current_ids)} current ids for @{username}")
        
        # Check for viral videos FIRST (before saving new data to avoid race condition)
        logging.info(f"🦠 [THREAD-{thread_id}] Checking viral videos for @{username}...")
        viral_videos = check_viral_videos(username, videos, previous_videos)
        logging.info(f"🦠 [THREAD-{thread_id}] Found {len(viral_videos)} viral videos for @{username}")
        
        if viral_videos:
            logging.info(f"📱 [THREAD-{thread_id}] Sending viral alert for @{username}...")
            send_viral_alert(username, viral_videos)
            logging.info(f"📱 [THREAD-{thread_id}] Sent viral alert for @{username}")
        
        # Save current data AFTER viral detection
        logging.info(f"💾 [THREAD-{thread_id}] Saving video data for @{username}...")
        save_video_data(username, videos)
        logging.info(f"💾 [THREAD-{thread_id}] Saved video data for @{username}")
        
        # Update monitoring stats
        logging.info(f"📈 [THREAD-{thread_id}] Updating stats for @{username}...")
        conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
        try:
            conn.execute('''
                INSERT OR REPLACE INTO monitoring_stats 
                (username, last_scraped, videos_found)
                VALUES (?, CURRENT_TIMESTAMP, ?)
            ''', (username, len(videos)))
            conn.commit()
            logging.info(f"📈 [THREAD-{thread_id}] Updated stats for @{username}")
        finally:
            conn.close()
        
        memory_after = browser_manager.get_memory_usage()
        logging.info(f"✅ [THREAD-{thread_id}] [TASK-{task_id}] Completed @{username}: {len(videos)} videos, {len(viral_videos)} viral. Memory: {memory_after:.1f}MB")
        
    except Exception as e:
        logging.error(f"❌ [THREAD-{thread_id}] [TASK-{task_id}] Error scraping @{username}: {e}")
        logging.error(traceback.format_exc())

async def run_monitoring_cycle():
    """Run one complete monitoring cycle with optimized resource management."""
    print("🚀 [CYCLE] ===== ENTERING run_monitoring_cycle() =====")
    logging.info("🚀 [CYCLE] Starting run_monitoring_cycle...")
    
    try:
        print("🚀 [CYCLE] Loading accounts...")
        accounts = load_accounts()
        if not accounts:
            print("❌ [CYCLE] ERROR: No accounts loaded!")
            logging.error("❌ [CYCLE] No accounts to monitor!")
            return
        
        print(f"📋 [CYCLE] Successfully loaded {len(accounts)} accounts: {accounts}")
        logging.info(f"📋 [CYCLE] Loaded {len(accounts)} accounts from accounts.csv")
        logging.info(f"🚀 [CYCLE] Starting monitoring cycle for {len(accounts)} accounts")
        logging.info(f"💾 [CYCLE] Memory usage: {browser_manager.get_memory_usage():.1f}MB")
        
        # Queue-based multi-browser, multi-tab processing
        acc_queue: asyncio.Queue[str] = asyncio.Queue()
        for acc in accounts:
            await acc_queue.put(acc)

        async def page_worker(browser, worker_id: int):
            # Create a fresh context/page for this worker and reuse
            try:
                user_agent = random.choice(USER_AGENTS)
                context = await browser.new_context(
                    user_agent=user_agent,
                    ignore_https_errors=True,
                    bypass_csp=True,
                    viewport={"width": 1280, "height": 800},
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    },
                )
                try:
                    await context.set_default_navigation_timeout(PAGE_TIMEOUT)
                    await context.set_default_timeout(PAGE_TIMEOUT)
                except Exception:
                    pass
                page = await context.new_page()

                while not acc_queue.empty():
                    try:
                        username = await acc_queue.get()
                    except Exception:
                        break
                    if not username:
                        continue
                    # Scrape using this page
                    videos = await scrape_with_existing_page(page, username, MAX_VIDEOS_TO_CHECK)
                    if videos:
                        previous_videos = get_previous_video_data(username, limit=MAX_VIDEOS_TO_CHECK)
                        
                        # Check for viral videos BEFORE saving new data (to avoid race condition)
                        viral_videos = check_viral_videos(username, videos, previous_videos)
                        if viral_videos:
                            logging.info(f"🚨 Found {len(viral_videos)} viral videos for @{username} - sending alert!")
                            send_viral_alert(username, viral_videos)
                        else:
                            logging.debug(f"No viral videos found for @{username}")
                        
                        # Save video data after viral detection
                        save_video_data(username, videos)
                    # jitter
                    await asyncio.sleep(random.randint(JITTER_SECONDS_MIN, JITTER_SECONDS_MAX))
                    acc_queue.task_done()
            finally:
                try:
                    await context.close()
                except Exception:
                    pass

        async def browser_worker(browser_id: int):
            # Launch a browser and spawn tab workers
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=BROWSER_HEADLESS,
                    args=[
                        "--ignore-certificate-errors",
                        "--ignore-ssl-errors",
                        "--ignore-certificate-errors-spki-list",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-extensions",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--no-first-run",
                        "--no-zygote",
                        "--disable-gpu",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-field-trial-config",
                        "--disable-hang-monitor",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-default-apps",
                        "--disable-component-extensions-with-background-pages",
                        "--allow-running-insecure-content",
                    ],
                )
                try:
                    workers = [asyncio.create_task(page_worker(browser, w)) for w in range(MAX_TABS_PER_BROWSER)]
                    await asyncio.gather(*workers)
                finally:
                    try:
                        await browser.close()
                    except Exception:
                        pass

        # Helper: scraping logic using an existing page (based on main.get_latest_videos)
        async def scrape_with_existing_page(page, username: str, limit: int = 5) -> list:
            videos: list = []
            captured_data = {}
            first_response_captured = False

            async def handle_response(response):
                nonlocal first_response_captured
                logging.info(f"Response: {response.status} {response.url}")
                if (("/api/post/item_list/" in response.url or 
                     "/api/user/detail/" in response.url or
                     "/aweme/v1/web/aweme/post/" in response.url or
                     "itemList" in response.url) and 
                    response.status == 200 and not first_response_captured):
                    try:
                        text = await response.text()
                        if text.strip():
                            data = await response.json()
                            if data.get('itemList'):
                                captured_data['videos'] = data
                                first_response_captured = True
                                logging.info(f"Captured FIRST video data from API response: {response.url}")
                    except Exception as e:
                        logging.error(f"Error capturing API data from {response.url}: {e}")

            page.on("response", handle_response)

            url = f"https://www.tiktok.com/@{username}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            except Exception as nav_err:
                logging.warning(f"page.goto error for @{username}: {nav_err}")
                return []

            # light scroll to trigger API
            await page.evaluate("window.scrollTo(0, 1000)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)

            # Solve captcha if present
            try:
                solved = await solve_captcha(page)
                if not solved:
                    logging.warning("Captcha not solved, continuing anyway")
            except Exception as e:
                logging.warning(f"solve_captcha error: {e}")

            await asyncio.sleep(3)
            json_data = captured_data.get('videos')
            if json_data:
                items = json_data.get('itemList', [])
                for v in items[:limit]:
                    raw_timestamp = v.get("createTime", 0)
                    try:
                        timestamp = int(raw_timestamp)
                        created_date = datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp > 0 else "unknown"
                    except Exception:
                        created_date = "unknown"
                    videos.append({
                        "video_id": v.get("id"),
                        "description": v.get("desc", ""),
                        "views": int(v.get("stats", {}).get("playCount", 0)),
                        "likes": int(v.get("stats", {}).get("diggCount", 0)),
                        "comments": int(v.get("stats", {}).get("commentCount", 0)),
                        "shares": int(v.get("stats", {}).get("shareCount", 0)),
                        "create_time": created_date,
                    })
            return videos

        # Launch up to MAX_CONCURRENT_BROWSERS workers
        num_browsers = min(MAX_CONCURRENT_BROWSERS, max(1, (len(accounts) + MAX_TABS_PER_BROWSER - 1) // MAX_TABS_PER_BROWSER))
        browser_workers = [asyncio.create_task(browser_worker(i)) for i in range(num_browsers)]
        await asyncio.gather(*browser_workers)
 
        # Final cleanup
        print("🧹 [CYCLE] Starting final cleanup...")
        logging.info("🧹 [CYCLE] Final cleanup starting...")
        browser_manager.force_garbage_collection()
        final_memory = browser_manager.get_memory_usage()
        print(f"✅ [CYCLE] Monitoring cycle completed successfully! Final memory: {final_memory:.1f}MB")
        logging.info(f"✅ [CYCLE] Monitoring cycle completed. Final memory: {final_memory:.1f}MB")
 
    except Exception as e:
        print(f"❌ [CYCLE] CRITICAL ERROR in run_monitoring_cycle: {e}")
        print(f"❌ [CYCLE] Exception traceback: {traceback.format_exc()}")
        logging.error(f"❌ [CYCLE] CRITICAL ERROR in run_monitoring_cycle: {e}")
        logging.error(traceback.format_exc())
        raise  # Re-raise to be caught by main()

# =============================================================================
# MAIN MONITORING LOOP
# =============================================================================

async def main():
    """Main monitoring loop with resource management."""
    print("🚀 MAIN: Starting main() function...")
    
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
    
    print("🚀 MAIN: Logging configured, initializing database...")
    
    # Initialize database
    init_database()
    
    print("🚀 MAIN: Database initialized, sending startup notification...")
    
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
        print("🚀 MAIN: Startup notification sent successfully")
    except Exception as e:
        print(f"🚀 MAIN: Failed to send startup notification: {e}")
        logging.error(f"❌ Failed to send startup notification: {e}")
    
    logging.info("🚀 TikTok Viral Monitor (OPTIMIZED) started")
    logging.info(f"💾 Initial memory usage: {browser_manager.get_memory_usage():.1f}MB")
    
    print("🚀 MAIN: Starting main monitoring loop...")
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            print(f"🔄 MAIN: ====== STARTING CYCLE #{cycle_count} ======")
            logging.info(f"🔄 Starting monitoring cycle #{cycle_count}")
            
            start_time = time.time()
            
            print(f"🔄 MAIN: About to call run_monitoring_cycle() for cycle #{cycle_count}")
            try:
                await run_monitoring_cycle()
                print(f"✅ MAIN: run_monitoring_cycle() completed successfully for cycle #{cycle_count}")
            except Exception as cycle_error:
                print(f"❌ MAIN: CRITICAL ERROR in run_monitoring_cycle() for cycle #{cycle_count}: {cycle_error}")
                logging.error(f"❌ CRITICAL ERROR in monitoring cycle #{cycle_count}: {cycle_error}")
                logging.error(traceback.format_exc())
                print("🔄 MAIN: Continuing to next cycle despite error...")
            
            cycle_duration = time.time() - start_time
            
            print(f"⏱️ MAIN: Cycle #{cycle_count} completed in {cycle_duration:.1f} seconds")
            logging.info(f"⏱️  Cycle #{cycle_count} completed in {cycle_duration:.1f} seconds")
            logging.info(f"💾 Memory usage: {browser_manager.get_memory_usage():.1f}MB")
            
            # Wait for next cycle
            wait_time = MONITORING_INTERVAL - cycle_duration
            if wait_time > 0:
                print(f"⏳ MAIN: Waiting {wait_time:.0f} seconds until next cycle...")
                logging.info(f"⏳ Waiting {wait_time:.0f} seconds until next cycle...")
                
                # Break the sleep into smaller chunks to detect hangs
                sleep_chunks = max(1, int(wait_time / 30))  # 30-second chunks
                chunk_time = wait_time / sleep_chunks
                
                for chunk in range(sleep_chunks):
                    print(f"⏳ MAIN: Sleep chunk {chunk + 1}/{sleep_chunks} ({chunk_time:.0f}s)")
                    await asyncio.sleep(chunk_time)
                
                print(f"⏳ MAIN: Sleep completed, starting cycle #{cycle_count + 1}")
            else:
                print("⚠️ MAIN: Cycle took longer than monitoring interval!")
                logging.warning("⚠️  Cycle took longer than monitoring interval!")
                
    except KeyboardInterrupt:
        print("👋 MAIN: Keyboard interrupt received")
        logging.info("👋 Simple Multi-Monitor stopped")
    except Exception as e:
        print(f"❌ MAIN: FATAL ERROR in main loop: {e}")
        logging.error(f"❌ Fatal error: {e}")
        logging.error(traceback.format_exc())
        print("❌ MAIN: Script will exit due to fatal error")
    finally:
        print("🧹 MAIN: Running final cleanup...")
        # Final cleanup
        browser_manager.force_garbage_collection()
        final_memory = browser_manager.get_memory_usage()
        print(f"💾 MAIN: Final memory usage: {final_memory:.1f}MB")
        logging.info(f"💾 Final memory usage: {final_memory:.1f}MB")

if __name__ == "__main__":
    asyncio.run(main())
