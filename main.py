#!/usr/bin/env python3
"""
TikTok Profile Scraper - BACKUP VERSION
========================================

A production-ready Python script to scrape TikTok profiles using Playwright 
with captcha solving capabilities.

This is a backup version of the working code as of September 7, 2024.

Features:
- Asynchronous execution using asyncio and Playwright
- Captcha solving using SadCaptcha API with manual fallback
- Proxy support with authentication and SSL handling
- User-Agent rotation for anti-bot evasion
- Complete video data extraction (views, likes, comments, shares, timestamps)
- Robust error handling with comprehensive logging
- Clean JSON output with timestamped filenames

Usage:
    python3 tiktok_scraper_backup.py <username>
    
Example:
    python3 tiktok_scraper_backup.py tiktok

Requirements:
    pip install playwright requests
    pip install git+https://github.com/gbiz123/tiktok-captcha-solver.git
    playwright install chromium

Author: Created for jamesweston55
Date: September 7, 2024
"""

import asyncio
import json
import logging
import os
import random
import re
import sys
import traceback
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from tiktok_captcha_solver import make_async_playwright_solver_context
from playwright_stealth import stealth_async, StealthConfig

# Import the updated SadCaptcha client
try:
    from sadcaptcha_client import solve_captcha_with_sadcaptcha, check_for_captcha, SADCAPTCHA_AVAILABLE
    logging.info("Updated SadCaptcha client imported successfully")
except ImportError as e:
    logging.error(f"Failed to import SadCaptcha client: {e}")
    SADCAPTCHA_AVAILABLE = False
    
    # Fallback functions if import fails
    async def solve_captcha_with_sadcaptcha(page, api_key, max_retries=3):
        logging.warning("SadCaptcha not available - captcha solving disabled")
        return False
        
    async def check_for_captcha(page):
        return False

# Try to import PAGE_TIMEOUT and solver flags from config_optimized with safe fallbacks
try:
    from config_optimized import (
        PAGE_TIMEOUT,
        USE_SADCAPTCHA_EXTENSION,
        USER_DATA_DIR_BASE,
        SADCAPTCHA_API_KEY,
        BROWSER_HEADLESS,
    )
except Exception:
    PAGE_TIMEOUT = 45000  # fallback to 45s if config import fails
    USE_SADCAPTCHA_EXTENSION = True
    USER_DATA_DIR_BASE = "./data/userdata"
    SADCAPTCHA_API_KEY = os.getenv("SADCAPTCHA_API_KEY", "")
    BROWSER_HEADLESS = False

# Proxy configuration (REPLACE WITH YOUR PROXY DETAILS)
PROXY_HOST = "your-proxy-host.com"
PROXY_PORT = 8080
PROXY_USERNAME = "your_proxy_username"
PROXY_PASSWORD = "your_proxy_password"

# SadCaptcha API configuration (REPLACE WITH YOUR API KEY)
# You need to get an API key from https://www.sadcaptcha.com/
# SADCAPTCHA_API_KEY and BROWSER_HEADLESS are imported from config_optimized if available

# User-Agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

async def solve_tiktok_slider_captcha(page):
    """
    Manual slider captcha solving function as fallback for SadCaptcha.
    Attempts to solve TikTok's puzzle slider captcha by dragging the slider.
    """
    try:
        logging.info("Attempting to solve TikTok puzzle slider captcha...")
        
        # Wait for slider to be visible
        slider_button = None
        slider_selectors = [
            '.secsdk-captcha-drag-icon',
            '#captcha_slide_button',
            '[class*="slide"]',
            '[class*="drag"]'
        ]
        
        for selector in slider_selectors:
            try:
                await page.wait_for_selector(selector, timeout=3000)
                slider_button = page.locator(selector).first
                if await slider_button.is_visible():
                    logging.info(f"Found slider button with selector: {selector}")
                    break
            except:
                continue
        
        if not slider_button:
            logging.error("Could not find slider button")
            return False
        
        # Get slider position and container
        slider_box = await slider_button.bounding_box()
        if not slider_box:
            logging.error("Could not get slider bounding box")
            return False
        
        # Calculate drag distance (usually need to drag to the right edge)
        drag_distance = random.randint(200, 300)  # Random distance to appear more human
        
        # Perform the drag action with human-like movement
        await slider_button.hover()
        await page.wait_for_timeout(random.randint(500, 1000))
        
        # Start drag
        await page.mouse.move(slider_box['x'] + slider_box['width']/2, slider_box['y'] + slider_box['height']/2)
        await page.mouse.down()
        
        # Drag with some random movements to simulate human behavior
        steps = 10
        for i in range(steps):
            progress = i / steps
            current_x = slider_box['x'] + (drag_distance * progress)
            # Add some random vertical movement
            current_y = slider_box['y'] + slider_box['height']/2 + random.randint(-2, 2)
            await page.mouse.move(current_x, current_y)
            await page.wait_for_timeout(random.randint(50, 150))
        
        await page.mouse.up()
        await page.wait_for_timeout(2000)
        
        # Check if captcha was solved by looking for success indicators or if captcha disappeared
        captcha_gone = True
        for selector in ['.secsdk-captcha-drag-icon', '#captcha_slide_button', '#captcha-verify-container-main-page']:
            try:
                element = page.locator(selector).first
                if await element.is_visible():
                    captcha_gone = False
                    break
            except:
                continue
        
        if captcha_gone:
            logging.info("Slider captcha appears to be solved!")
            return True
        else:
            logging.warning("Slider captcha may not be solved, trying alternative approach...")
            return False
            
    except Exception as e:
        logging.error(f"Error in manual slider solving: {e}")
        return False

async def solve_captcha(page, max_retries=3):
    """
    Solve captcha using the updated SadCaptcha implementation.
    Returns True if captcha was solved, False otherwise.
    """
    # First check if there's a captcha present
    if not await check_for_captcha(page):
        logging.info("No captcha detected")
        return True
    
    logging.info("Captcha detected, attempting to solve...")
    
    # Use the new SadCaptcha implementation
    result = await solve_captcha_with_sadcaptcha(page, SADCAPTCHA_API_KEY, max_retries)
    
    if result:
        logging.info("Captcha solved successfully")
        # Verify captcha is really gone
        await asyncio.sleep(3)
        if not await check_for_captcha(page):
            return True
        else:
            logging.warning("Captcha still present after solving")
            return False
    else:
        logging.error("Failed to solve captcha with SadCaptcha")
        # Try manual fallback for slider captchas if available
        try:
            manual_result = await solve_tiktok_slider_captcha(page)
            if manual_result:
                logging.info("Manual slider captcha solving succeeded")
                return True
        except Exception as e:
            logging.error(f"Manual captcha solving also failed: {e}")
        
        return False

async def get_latest_videos(username: str, limit: int = 5) -> list:
    """
    Get the latest videos from a TikTok user profile.
    
    Args:
        username: TikTok username (without @)
        limit: Number of videos to retrieve (default: 5)
    
    Returns:
        List of dictionaries containing video information
    """
    videos = []
    
    async with async_playwright() as playwright:
        # Select random user agent
        user_agent = random.choice(USER_AGENTS)
        logging.info(f"Using User-Agent: {user_agent}")

        # Launch context via SadCaptcha extension (preferred), else fall back
        context = None
        if USE_SADCAPTCHA_EXTENSION and (SADCAPTCHA_API_KEY and SADCAPTCHA_API_KEY.strip()):
            try:
                os.makedirs(USER_DATA_DIR_BASE, exist_ok=True)
                user_data_dir = os.path.join(USER_DATA_DIR_BASE, username)
                launch_args = ["--headless=chrome"] if BROWSER_HEADLESS else []
                context = await make_async_playwright_solver_context(
                    playwright,
                    api_key=SADCAPTCHA_API_KEY,
                    user_data_dir=user_data_dir,
                    args=launch_args,
                )
                logging.info("SadCaptcha extension context created (persistent)")
            except Exception as e:
                logging.warning(f"Falling back to vanilla context: {e}")

        if context is None:
            browser = await playwright.chromium.launch(
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

        # Align default timeouts with config
        try:
            await context.set_default_navigation_timeout(PAGE_TIMEOUT)
            await context.set_default_timeout(PAGE_TIMEOUT)
        except Exception as _:
            pass

        page = await context.new_page()
        # Apply Playwright stealth with recommended defaults
        try:
            stealth_config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
            await stealth_async(page, stealth_config)
        except Exception:
            pass

        async def refresh_if_error():
            """Detect TikTok 'Something went wrong' and click Refresh if present.
            - Searches main page and child frames
            - Tries multiple button selectors
            - Falls back to page.reload if click fails
            """
            try:
                # 1) Detect the error text anywhere
                selectors_text = [
                    page.get_by_text(re.compile(r"something\s+went\s+wrong", re.I)).first,
                    page.locator("text=/.*Something\\s+went\\s+wrong.*/i").first,
                    page.locator("text=went wrong").first,
                ]
                err_visible = False
                for loc in selectors_text:
                    try:
                        await loc.wait_for(state="visible", timeout=1500)
                        err_visible = True
                        break
                    except Exception:
                        continue
                if not err_visible:
                    # Search in iframes as well
                    for frame in page.frames:
                        try:
                            loc = frame.get_by_text(re.compile(r"something\s+went\s+wrong", re.I)).first
                            await loc.wait_for(state="visible", timeout=800)
                            err_visible = True
                            break
                        except Exception:
                            continue
                if not err_visible:
                    return False

                logging.warning("Detected 'Something went wrong' – attempting Refresh")

                # 2) Try to click a Refresh/Reload/Try again button by several strategies
                name_regex = re.compile(r"(refresh|reload|try\s*again|retry)", re.I)
                button_candidates = [
                    page.get_by_role("button", name=name_regex).first,
                    page.locator("button:has-text('Refresh')").first,
                    page.locator("button:has-text('Reload')").first,
                    page.locator("button:has-text('Try again')").first,
                    page.locator("[role='button']:has-text('Refresh')").first,
                    page.locator("[role='button']:has-text('Reload')").first,
                    page.locator("[type='button']:has-text('Refresh')").first,
                    page.locator("div[role='button']:has-text('Refresh')").first,
                    page.locator("button.ebef5j00").first,
                    page.locator("button.e1jj6n0n4").first,
                    page.locator("button[class*='StyledButton']").first,
                    page.locator("button[class*='ebef5j00']").first,
                    page.locator("text=/^\\s*Refresh\\s*$/i").first,
                    page.locator("text=/^\\s*Reload\\s*$/i").first,
                    page.locator("text=/^\\s*Try again\\s*$/i").first,
                ]
                clicked = False
                # Try each candidate; if normal click fails, attempt JS click
                for btn in button_candidates:
                    try:
                        await btn.wait_for(state="visible", timeout=3000)
                        try:
                            await btn.scroll_into_view_if_needed(timeout=1500)
                        except Exception:
                            pass
                        try:
                            await btn.click(force=True)
                        except Exception:
                            try:
                                handle = await btn.element_handle()
                                if handle:
                                    await page.evaluate("el => el.click()", handle)
                                else:
                                    raise
                            except Exception:
                                continue
                        clicked = True
                        break
                    except Exception:
                        continue

                if not clicked:
                    # Try frames for the button as well
                    for frame in page.frames:
                        try:
                            frame_candidates = [
                                frame.get_by_role("button", name=name_regex).first,
                                frame.locator("button:has-text('Refresh')").first,
                                frame.locator("[role='button']:has-text('Refresh')").first,
                                frame.locator("button.ebef5j00").first,
                                frame.locator("button.e1jj6n0n4").first,
                                frame.locator("button[class*='StyledButton']").first,
                            ]
                            for btn in frame_candidates:
                                try:
                                    await btn.wait_for(state="visible", timeout=2000)
                                    try:
                                        await btn.scroll_into_view_if_needed(timeout=800)
                                    except Exception:
                                        pass
                                    try:
                                        await btn.click(force=True)
                                    except Exception:
                                        handle = await btn.element_handle()
                                        if handle:
                                            await page.evaluate("el => el.click()", handle)
                                        else:
                                            raise
                                    clicked = True
                                    break
                                except Exception:
                                    continue
                            if clicked:
                                break
                        except Exception:
                            continue

                if not clicked:
                    logging.warning("Refresh button not found; reloading page instead")
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                    except Exception:
                        await page.evaluate("location.reload()")
                        await page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)
                else:
                    await page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT)

                await asyncio.sleep(3)
                logging.info("Recovered from 'Something went wrong' via refresh/reload")
                return True
            except Exception as e:
                logging.error(f"refresh_if_error unexpected: {e}")
                return False
        
        # Set up response logging and data capture
        captured_data = {}
        first_response_captured = False
        
        async def handle_response(response):
            nonlocal first_response_captured
            logging.info(f"Response: {response.status} {response.url}")
            # Capture API responses that contain video data - ONLY THE FIRST ONE
            if (("/api/post/item_list/" in response.url or 
                 "/api/user/detail/" in response.url or
                 "/aweme/v1/web/aweme/post/" in response.url or
                 "itemList" in response.url) and 
                response.status == 200 and not first_response_captured):
                try:
                    text = await response.text()
                    if text.strip():
                        data = await response.json()
                        # Only capture the FIRST API response to get the actual latest videos
                        if data.get('itemList'):
                            captured_data['videos'] = data
                            first_response_captured = True
                            logging.info(f"Captured FIRST video data from API response: {response.url}")
                            logging.info(f"Data contains {len(data.get('itemList', []))} items")
                            
                            # Debug: Show all item descriptions to understand the order
                            items = data.get('itemList', [])
                            if items:
                                logging.info(f"=== API Response Video Order (first 10) ===")
                                for i, item in enumerate(items[:10]):
                                    desc_preview = item.get('desc', '')[:80]
                                    create_time = item.get('createTime', 0)
                                    logging.info(f"#{i+1}: {desc_preview}... (createTime: {create_time})")
                                logging.info("=== End API Order Debug ===")
                                first_item = items[0]
                                logging.info(f"First item structure: id={first_item.get('id')}, createTime={first_item.get('createTime')}, desc preview={first_item.get('desc', '')[:50]}...")
                    else:
                        logging.warning(f"Empty response from {response.url}")
                except Exception as e:
                    logging.error(f"Error capturing API data from {response.url}: {e}")
                    try:
                        text = await response.text()
                        logging.error(f"Response text: {text[:200]}...")
                    except:
                        pass
            elif (("/api/post/item_list/" in response.url) and first_response_captured):
                logging.info(f"Skipping subsequent API response (already captured first): {response.url}")
        
        page.on("response", handle_response)
        
        try:
            # Navigate to TikTok profile
            url = f"https://www.tiktok.com/@{username}"
            logging.info(f"Navigating to: {url}")
            
            # Retry navigation up to 2 times if timing out
            nav_attempts = 0
            while True:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
                    
                    # Handle "Choose your interests" popup if present
                    try:
                        # Try multiple selectors for the Skip button
                        skip_selectors = [
                            'button.TUXButton--secondary:has-text("Skip")',
                            'button.TUXButton.TUXButton--secondary:has(.TUXButton-label:text("Skip"))',
                            'button[style*="width: 50%"]:has-text("Skip")',
                            '.TUXButton-label:text("Skip")',
                        ]
                        
                        button_found = False
                        for selector in skip_selectors:
                            try:
                                skip_button = page.locator(selector).first
                                if await skip_button.is_visible(timeout=2000):
                                    logging.info(f"Found 'Choose your interests' popup with selector: {selector}")
                                    await skip_button.click()
                                    await asyncio.sleep(2)
                                    logging.info("Successfully skipped interests popup")
                                    button_found = True
                                    break
                            except:
                                continue
                        
                        if not button_found:
                            logging.debug("No interests popup found")
                            
                    except Exception as e:
                        logging.debug(f"Error handling interests popup: {e}")
                    
                    # if error banner present, click Refresh (poll up to ~6s)
                    for _ in range(30):
                        hit = await refresh_if_error()
                        if hit:
                            break
                        await asyncio.sleep(1)
                    break
                except Exception as nav_err:
                    nav_attempts += 1
                    logging.warning(f"page.goto timeout/err for @{username} (attempt {nav_attempts}): {nav_err}")
                    if nav_attempts >= 2:
                        raise
                    await asyncio.sleep(3)
            await asyncio.sleep(3)  # Wait for dynamic content
            
            logging.info("Page loaded successfully. Title: '%s'", await page.title())
            logging.info("Current URL: %s", page.url)
            
            # Check if page has content
            try:
                body_text = await page.locator('body').inner_text()
                logging.info(f"Page has body text: {len(body_text)} characters")
            except:
                logging.warning("Could not get body text")
            
            # Check for immediate captcha before proceeding
            immediate_captcha_selectors = [
                '#captcha-verify-container-main-page',
                '.secsdk-captcha-drag-icon',
                '#captcha_slide_button'
            ]
            
            for selector in immediate_captcha_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        logging.warning(f"Immediate captcha detected with selector: {selector}. Solving before proceeding...")
                        if await solve_captcha(page):
                            logging.info("Immediate captcha solved successfully")
                            break
                        else:
                            logging.warning("Failed to solve immediate captcha")
                except:
                    continue
            
            # Trigger video loading by scrolling
            await page.evaluate("window.scrollTo(0, 1000)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 2000)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)

            # If the page error appeared mid-run, try refresh (poll up to ~30s)
            for _ in range(30):
                hit = await refresh_if_error()
                if hit:
                    break
                await asyncio.sleep(1)
            
            # Check for captcha and solve if present
            captcha_solved = True
            captcha_selectors = [
                '#captcha-verify-container-main-page',
                '.secsdk-captcha-drag-icon',
                '#captcha_slide_button',
                '[data-testid="captcha-container"]',
                '.captcha-container'
            ]
            
            for selector in captcha_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        logging.info(f"Captcha detected with selector: {selector}")
                        captcha_solved = await solve_captcha(page)
                        break
                except:
                    continue
            
            if not captcha_solved:
                logging.error("Failed to solve captcha, continuing anyway...")
            
            await asyncio.sleep(5)  # Wait for any final loading
            
            logging.info("Performed scroll interactions to trigger video loading")
            
            # Use captured API data if available
            json_data = captured_data.get('videos')
            if json_data:
                logging.info("Using captured API response data")
                api_data = captured_data['videos']
                items = api_data.get('itemList', [])
                logging.info(f"Found {len(items)} total videos, taking first {limit} as they appear on the page")
                
                for v in items[:limit]:
                    # Debug: Print raw timestamp to understand the format
                    raw_timestamp = v.get("createTime", 0)
                    logging.info(f"Raw timestamp for video {v.get('id')}: {raw_timestamp}")
                    
                    # Convert timestamp (TikTok uses Unix timestamp)
                    try:
                        timestamp = int(raw_timestamp)
                        if timestamp > 0:
                            created_date = datetime.utcfromtimestamp(timestamp).isoformat()
                        else:
                            created_date = "unknown"
                    except (ValueError, OSError) as e:
                        logging.error(f"Error converting timestamp {raw_timestamp}: {e}")
                        created_date = "unknown"
                    
                    logging.info(f"Final converted date for video {v.get('id')}: {created_date}")
                    
                    videos.append({
                        "id": v.get("id"),
                        "desc": v.get("desc", ""),
                        "views": int(v.get("stats", {}).get("playCount", 0)),
                        "likes": int(v.get("stats", {}).get("diggCount", 0)),
                        "comments": int(v.get("stats", {}).get("commentCount", 0)),
                        "shares": int(v.get("stats", {}).get("shareCount", 0)),
                        "created": created_date,
                    })
                
                logging.info(f"Parsed {len(videos)} latest videos from API response")
            
            # Fallback: Try to extract from page content if API data not available
            if not videos:
                logging.warning("No API data captured, trying to extract from page content...")
                
                # Try to find embedded JSON data
                try:
                    # Look for SIGI_STATE or similar embedded data
                    scripts = await page.locator('script').all()
                    for script in scripts:
                        try:
                            content = await script.inner_text()
                            if 'window.__SIGI_STATE__' in content or 'window.SIGI_STATE' in content:
                                # Extract JSON from script
                                start_idx = content.find('{')
                                end_idx = content.rfind('}') + 1
                                if start_idx != -1 and end_idx > start_idx:
                                    json_str = content[start_idx:end_idx]
                                    data = json.loads(json_str)
                                    
                                    # Navigate through the data structure to find videos
                                    def find_videos_in_data(obj, path=""):
                                        if isinstance(obj, dict):
                                            for key, value in obj.items():
                                                if key == 'itemList' and isinstance(value, list):
                                                    return value[:limit]
                                                elif isinstance(value, (dict, list)):
                                                    result = find_videos_in_data(value, f"{path}.{key}")
                                                    if result:
                                                        return result
                                        elif isinstance(obj, list):
                                            for i, item in enumerate(obj):
                                                if isinstance(item, (dict, list)):
                                                    result = find_videos_in_data(item, f"{path}[{i}]")
                                                    if result:
                                                        return result
                                        return None
                                    
                                    video_items = find_videos_in_data(data)
                                    if video_items:
                                        logging.info(f"Found {len(video_items)} videos in SIGI_STATE")
                                        for v in video_items:
                                            if isinstance(v, dict) and v.get('id'):
                                                videos.append({
                                                    "id": v.get("id"),
                                                    "desc": v.get("desc", ""),
                                                    "views": int(v.get("stats", {}).get("playCount", 0)),
                                                    "likes": int(v.get("stats", {}).get("diggCount", 0)),
                                                    "comments": int(v.get("stats", {}).get("commentCount", 0)),
                                                    "shares": int(v.get("stats", {}).get("shareCount", 0)),
                                                    "created": datetime.utcfromtimestamp(int(v.get("createTime", 0))).isoformat() if v.get("createTime") else "unknown",
                                                })
                                        break
                        except:
                            continue
                except Exception as e:
                    logging.error(f"Error extracting from SIGI_STATE: {e}")
                
                # Try __NEXT_DATA__ as alternative
                if not videos:
                    try:
                        all_scripts = await page.locator('script').all()
                        for script in all_scripts:
                            content = await script.inner_text()
                            if '__NEXT_DATA__' in content:
                                start = content.find('__NEXT_DATA__')
                                if start != -1:
                                    json_start = content.find('{', start)
                                    json_end = content.rfind('}') + 1
                                    if json_start != -1 and json_end > json_start:
                                        next_content = content[json_start:json_end]
                                        json_data = json.loads(next_content)
                                        break
                        else:
                            logging.info("No __NEXT_DATA__ script found")
                    except Exception as e:
                        logging.error(f"Error parsing __NEXT_DATA__: {e}")
                
                # Try alternative: look for any script containing video data
                if not json_data:
                    try:
                        for script in all_scripts:
                            content = await script.inner_text()
                            if content and ('ItemList' in content or 'videoData' in content or 'props' in content):
                                logging.info("Found potential data script")
                                # Try to extract JSON from script content
                                if content.strip().startswith('{') and content.strip().endswith('}'):
                                    json_data = json.loads(content)
                                    break
                                elif 'window.__INITIAL_STATE__' in content:
                                    # Extract the JSON part
                                    start = content.find('{')
                                    end = content.rfind('}') + 1
                                    if start != -1 and end > start:
                                        json_data = json.loads(content[start:end])
                                        break
                    except Exception as e:
                        logging.error(f"Error in alternative data extraction: {e}")
            
            if not json_data:
                # Last resort: try to get page content and look for any JSON-like structures
                page_content = await page.content()
                logging.info(f"Page title: {await page.title()}")
                
                # Save page content for debugging
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(page_content)
                logging.info("Saved page content to debug_page.html")
                
                # Skip screenshot due to timeout issues
                # try:
                #     await page.screenshot(path=f"debug_{username}.png")
                #     logging.info(f"Saved screenshot to debug_{username}.png")
                # except Exception as e:
                #     logging.error(f"Could not take screenshot: {e}")
            
            if not videos:
                logging.error("Could not extract TikTok embedded JSON data.")
                return []
            
        except PlaywrightTimeoutError as e:
            logging.error(f"Timeout while loading TikTok page: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            logging.error(traceback.format_exc())
            return []
        finally:
            await context.close()
            await browser.close()
    
    return videos

async def main():
    if len(sys.argv) != 2:
        print("Usage: python3 tiktok_scraper_backup.py <username>")
        print("Example: python3 tiktok_scraper_backup.py tiktok")
        sys.exit(1)
    
    username = sys.argv[1]
    
    logging.info(f"Starting TikTok scraper for user: @{username}")
    
    try:
        results = await get_latest_videos(username, limit=5)
        
        # Output to JSON file
        output_filename = f"tiktok_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        if results:
            print(f"✅ Successfully scraped {len(results)} videos for @{username}")
            print(f"📁 Results saved to: {output_filename}")
        else:
            print(f"⚠️  No videos found for @{username}")
            print(f"📁 Empty results saved to: {output_filename}")
            
    except Exception as e:
        logging.error(f"Script failed: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 