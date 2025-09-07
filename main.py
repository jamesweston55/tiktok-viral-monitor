import asyncio
import json
import logging
import os
import random
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import requests
try:
    from tiktok_captcha_solver import AsyncPlaywrightSolver
    SADCAPTCHA_AVAILABLE = True
except ImportError:
    logging.warning("TikTok captcha solver not available, captcha solving will be disabled")
    SADCAPTCHA_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# Proxy configuration
PROXY_HOST = "your-proxy-host.com"
PROXY_PORT = 8080
PROXY_USERNAME = "your_proxy_username"
PROXY_PASSWORD = "your_proxy_password"

# SadCaptcha API configuration
# You need to get an API key from https://www.sadcaptcha.com/
SADCAPTCHA_API_KEY = os.getenv("SADCAPTCHA_API_KEY", "your_sadcaptcha_api_key_here")  # Can be set via environment variable

# User-Agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# SadCaptcha configuration handled in import section above

async def solve_tiktok_slider_captcha(page):
    """
    Solve TikTok's puzzle slider captcha by trying different positions.
    This is a puzzle piece fitting challenge where the slider controls the position.
    """
    try:
        logging.info("Attempting to solve TikTok puzzle slider captcha...")
        
        # Wait for captcha to fully load
        await asyncio.sleep(3)
        
        # Find the slider button
        slider_button = await page.query_selector('#captcha_slide_button')
        if not slider_button:
            logging.error("Could not find slider button")
            return False
        
        # Get the slider container to calculate available range
        slider_track = await page.query_selector('.cap-w-full.cap-h-40')
        if not slider_track:
            logging.error("Could not find slider track")
            return False
        
        # Get the bounding boxes
        slider_box = await slider_button.bounding_box()
        track_box = await slider_track.bounding_box()
        
        if not slider_box or not track_box:
            logging.error("Could not get bounding boxes")
            return False
        
        # Calculate the available drag range
        max_drag_distance = track_box['width'] - slider_box['width'] - 5
        
        logging.info(f"Trying different slider positions across {max_drag_distance}px range...")
        
        # Try multiple positions to solve the puzzle
        # We'll try different percentages of the total range
        test_positions = [0.3, 0.5, 0.7, 0.4, 0.6, 0.8, 0.2, 0.9]  # Different positions to try
        
        for i, position_ratio in enumerate(test_positions):
            try:
                logging.info(f"Attempt {i+1}: Trying position at {position_ratio*100:.0f}% of slider range")
                
                # Reset slider to start position first
                await slider_button.hover()
                await page.mouse.down()
                await page.mouse.move(slider_box['x'] + slider_box['width']/2, slider_box['y'] + slider_box['height']/2)
                await page.mouse.up()
                await asyncio.sleep(0.5)
                
                # Calculate target position
                drag_distance = max_drag_distance * position_ratio
                
                # Perform the drag operation
                await slider_button.hover()
                await asyncio.sleep(0.2)
                await page.mouse.down()
                
                # Drag smoothly to target position
                start_x = slider_box['x'] + slider_box['width'] / 2
                target_x = start_x + drag_distance
                
                steps = max(10, int(drag_distance / 5))  # More steps for longer distances
                step_size = drag_distance / steps
                
                current_x = start_x
                for step in range(steps):
                    current_x += step_size
                    await page.mouse.move(current_x, slider_box['y'] + slider_box['height'] / 2)
                    await asyncio.sleep(0.02)  # Smooth movement
                
                await page.mouse.up()
                
                logging.info(f"Dragged slider {drag_distance:.1f}px, waiting for verification...")
                
                # Wait for the captcha to process this attempt
                await asyncio.sleep(2)
                
                # Check if captcha was solved (captcha container should disappear)
                captcha_still_present = await page.query_selector('#captcha-verify-container-main-page')
                
                if not captcha_still_present:
                    logging.info(f"TikTok slider captcha solved successfully on attempt {i+1}!")
                    return True
                
                # If not solved, try a small adjustment around this position
                if i < len(test_positions) - 1:
                    logging.info(f"Position {position_ratio*100:.0f}% didn't work, trying next position...")
                    await asyncio.sleep(1)
                
            except Exception as e:
                logging.error(f"Error on attempt {i+1}: {e}")
                continue
        
        logging.warning("Could not solve slider captcha after trying all positions")
        return False
            
    except Exception as e:
        logging.error(f"Error solving TikTok slider captcha: {e}")
        return False

async def solve_captcha(page, max_retries=3):
    """
    Detect and solve TikTok captcha using TikTok captcha solver. Retry up to max_retries.
    """
    if not SADCAPTCHA_AVAILABLE:
        logging.warning("TikTok captcha solver not available, skipping captcha solving")
        return False
    
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Attempting to solve captcha (try {attempt}/{max_retries})...")
            
            # Check for various TikTok captcha types
            captcha_selectors = [
                '#captcha-verify-container-main-page',  # TikTok main slider captcha
                '.secsdk-captcha-drag-icon',            # TikTok drag button
                '#captcha_slide_button',                # TikTok slide button
                'iframe[src*="hcaptcha.com"]',          # hCaptcha
                '.captcha_verify_container',            # TikTok captcha container
                'iframe[src*="verification"]',          # TikTok verification iframe
                '[id*="captcha"]',                      # Any element with captcha in ID
                '.captcha-container',                   # Captcha container class
                'iframe[src*="captcha"]',               # Captcha iframe
                '.secsdk-captcha-drag',                 # TikTok's drag captcha
                '.captcha',                             # Generic captcha class
            ]
            
            captcha_present = False
            captcha_type = None
            
            for selector in captcha_selectors:
                element = await page.query_selector(selector)
                if element:
                    captcha_present = True
                    captcha_type = selector
                    logging.info(f"Captcha detected with selector: {selector}")
                    break
            
            if not captcha_present:
                logging.info("No captcha detected")
                return True
            
            # Use the TikTok captcha solver
            logging.info(f"Captcha detected ({captcha_type}), attempting to solve...")
            
            # Wait a moment for captcha to fully load
            await asyncio.sleep(3)
            
            # Try TikTok captcha solver first (it should handle all TikTok captcha types)
            try:
                if SADCAPTCHA_API_KEY == "YOUR_SADCAPTCHA_API_KEY_HERE":
                    logging.warning("SadCaptcha API key not configured. Please set SADCAPTCHA_API_KEY.")
                    raise Exception("No API key configured")
                
                solver = AsyncPlaywrightSolver(page, SADCAPTCHA_API_KEY)
                result = await solver.solve_captcha_if_present()
                
                if result:
                    logging.info("SadCaptcha solver succeeded")
                else:
                    # If SadCaptcha fails and it's a slider, try manual approach
                    if captcha_type in ['#captcha-verify-container-main-page', '.secsdk-captcha-drag-icon', '#captcha_slide_button']:
                        logging.info("SadCaptcha failed, trying manual slider solve...")
                        result = await solve_tiktok_slider_captcha(page)
                    else:
                        logging.warning("SadCaptcha solver failed for non-slider captcha")
                        
            except Exception as e:
                logging.error(f"SadCaptcha solver error: {e}")
                # Fallback to manual for slider types
                if captcha_type in ['#captcha-verify-container-main-page', '.secsdk-captcha-drag-icon', '#captcha_slide_button']:
                    logging.info("Trying manual slider solve as fallback...")
                    result = await solve_tiktok_slider_captcha(page)
                else:
                    result = False
            
            if result:
                logging.info("Captcha solved successfully.")
                # Wait for the page to process the solution
                await asyncio.sleep(5)
                
                # Check if captcha is gone
                still_has_captcha = False
                for selector in captcha_selectors:
                    if await page.query_selector(selector):
                        still_has_captcha = True
                        break
                
                if not still_has_captcha:
                    logging.info("Captcha successfully cleared from page.")
                    return True
                else:
                    logging.warning("Captcha still present after solving attempt.")
                    
            else:
                raise Exception("Captcha solver returned failure")
                
        except Exception as e:
            logging.error(f"Captcha solving attempt {attempt} failed: {e}")
            await asyncio.sleep(3)
    
    logging.error("Failed to solve captcha after multiple attempts.")
    return False

async def get_latest_videos(username: str, limit: int = 5) -> list:
    """
    Scrape the latest TikTok videos for a given username.
    """
    user_agent = random.choice(USER_AGENTS)
    results = []
    playwright = await async_playwright().start()
    browser = None
    context = None
    page = None
    try:
        browser = await playwright.chromium.launch(
            headless=False,
            # proxy={
            #     "server": f"http://{PROXY_HOST}:{PROXY_PORT}",
            #     "username": PROXY_USERNAME,
            #     "password": PROXY_PASSWORD,
            # },
            args=[
                "--ignore-certificate-errors",
                "--ignore-ssl-errors",
                "--ignore-certificate-errors-spki-list",
                "--disable-web-security",
                "--allow-running-insecure-content",
                "--disable-features=VizDisplayCompositor",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-default-apps",
                "--disable-hang-monitor",
                "--disable-prompt-on-repost",
                "--disable-sync",
                "--disable-translate",
                "--metrics-recording-only",
                "--no-first-run",
                "--safebrowsing-disable-auto-update",
                "--disable-ipc-flooding-protection",
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
        page = await context.new_page()
        url = f"https://www.tiktok.com/@{username}"
        logging.info(f"Navigating to {url} with User-Agent: {user_agent}")
        
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
        
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Wait a bit for dynamic content to load
        await asyncio.sleep(3)
        
        # Log page status
        title = await page.title()
        current_url = page.url
        logging.info(f"Page loaded successfully. Title: '{title}'")
        logging.info(f"Current URL: {current_url}")
        
        # Check if we were redirected or blocked
        if 'tiktok.com' not in current_url.lower():
            logging.warning(f"Redirected away from TikTok: {current_url}")
        
        # Get basic page info
        try:
            body_text = await page.locator('body').inner_text()
            logging.info(f"Page has body text: {len(body_text)} characters")
            if 'blocked' in body_text.lower() or 'access denied' in body_text.lower():
                logging.warning("Page indicates access may be blocked")
        except Exception as e:
            logging.error(f"Could not get body text: {e}")
        
        # Check for immediate captcha challenge after page load
        await asyncio.sleep(2)  # Wait for any captcha to appear
        captcha_selectors = [
            '#captcha-verify-container-main-page',
            '.secsdk-captcha-drag-icon',
            '#captcha_slide_button',
            'iframe[src*="hcaptcha.com"]',
            '.captcha_verify_container',
            'iframe[src*="verification"]',
            '[id*="captcha"]',
            '.captcha-container',
            'iframe[src*="captcha"]',
            '.secsdk-captcha-drag',
            '.captcha',
        ]
        
        for selector in captcha_selectors:
            if await page.query_selector(selector):
                logging.warning(f"Immediate captcha detected with selector: {selector}. Solving before proceeding...")
                solved = await solve_captcha(page)
                if not solved:
                    logging.error("Failed to solve immediate captcha, continuing anyway...")
                break
        
        # Trigger video loading by scrolling and interacting with the page
        try:
            # Scroll down to trigger lazy loading of videos
            await page.evaluate("window.scrollTo(0, 1000)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 2000)")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(3)
            logging.info("Performed scroll interactions to trigger video loading")
        except Exception as e:
            logging.error(f"Error during scroll interactions: {e}")
        # Detect captcha with multiple selectors
        captcha_selectors = [
            '#captcha-verify-container-main-page',
            '.secsdk-captcha-drag-icon',
            '#captcha_slide_button',
            'iframe[src*="hcaptcha.com"]',
            '.captcha_verify_container',
            'iframe[src*="verification"]',
            '[id*="captcha"]',
            '.captcha-container',
            'iframe[src*="captcha"]',
            '.secsdk-captcha-drag',
            '.captcha',
        ]
        
        captcha_found = False
        for selector in captcha_selectors:
            if await page.query_selector(selector):
                captcha_found = True
                logging.warning(f"Captcha detected with selector: {selector}. Attempting to solve...")
                break
        
        if captcha_found:
            solved = await solve_captcha(page)
            if not solved:
                raise Exception("Could not solve captcha.")
            # Retry navigation after solving captcha
            await page.reload(wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
        # Wait for embedded JSON data
        await asyncio.sleep(5)  # Give more time for scripts to load
        
        # Check if we captured video data from API responses
        json_data = captured_data.get('videos')
        
        if json_data:
            logging.info("Using captured API response data")
        else:
            logging.info("No API data captured, trying script extraction...")
            
            # Debug: Check what scripts are available
            all_scripts = await page.query_selector_all('script')
            logging.info(f"Found {len(all_scripts)} script tags on the page")
            
            # Try SIGI_STATE
            try:
                sigi_script = await page.query_selector('script#SIGI_STATE')
                if sigi_script:
                    sigi_content = await sigi_script.inner_text()
                    logging.info("Found SIGI_STATE script")
                    json_data = json.loads(sigi_content)
                else:
                    logging.info("No SIGI_STATE script found")
            except Exception as e:
                logging.error(f"Error parsing SIGI_STATE: {e}")
            
            # Try __NEXT_DATA__ if SIGI_STATE not found
            if not json_data:
                try:
                    next_script = await page.query_selector('script[id="__NEXT_DATA__"]')
                    if next_script:
                        next_content = await next_script.inner_text()
                        logging.info("Found __NEXT_DATA__ script")
                        json_data = json.loads(next_content)
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
            # await page.screenshot(path='debug_screenshot.png')
            # logging.info("Saved screenshot to debug_screenshot.png")
            
            # Check if the page contains any video-related content
            if 'video' in page_content.lower() or 'tiktok' in page_content.lower():
                logging.info("Page contains video/TikTok content, but no embedded JSON found")
            else:
                logging.info("Page doesn't seem to contain expected TikTok content")
            
            logging.info("Could not find embedded JSON data, page may have different structure")
            raise Exception("Could not extract TikTok embedded JSON data.")
        # Parse videos
        videos = []
        
        # Try API response format first
        if 'videos' in captured_data:
            try:
                # API response structure
                api_data = captured_data['videos']
                items = api_data.get('itemList', [])
                
                # Take the first 'limit' videos as they appear on the page (most recent posts)
                # TikTok serves videos in the order they appear on the profile page
                logging.info(f"Found {len(items)} total videos, taking first {limit} as they appear on the page")
                
                for v in items[:limit]:
                    # Debug: Print raw timestamp to understand the format
                    raw_timestamp = v.get("createTime", 0)
                    logging.info(f"Raw timestamp for video {v.get('id')}: {raw_timestamp}")
                    
                    # Handle different timestamp formats
                    if isinstance(raw_timestamp, str):
                        # If it's a string, try to convert to int
                        try:
                            timestamp = int(raw_timestamp)
                        except ValueError:
                            logging.warning(f"Could not parse timestamp: {raw_timestamp}")
                            timestamp = 0
                    else:
                        timestamp = int(raw_timestamp) if raw_timestamp else 0
                    
                    # Check if timestamp is in milliseconds (common for JavaScript timestamps)
                    if timestamp > 1e12:  # If timestamp is too large, it's likely in milliseconds
                        timestamp = timestamp // 1000
                        logging.info(f"Converted millisecond timestamp to seconds: {timestamp}")
                    
                    created_date = datetime.utcfromtimestamp(timestamp).isoformat() if timestamp > 0 else "unknown"
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
            except Exception as e:
                logging.error(f"Error parsing API response: {e}")
        
        # Try to find video list in SIGI_STATE if no API data
        if not videos:
            try:
                # SIGI_STATE structure
                items = json_data['ItemList']['user-post']['list']
                item_module = json_data['ItemModule']
                
                # Take the first 'limit' videos as they appear in the items list (page order)
                logging.info(f"Found {len(items)} total videos in SIGI_STATE, taking first {limit} as they appear on page")
                
                for video_id in items[:limit]:
                    v = item_module.get(video_id)
                    if not v:
                        continue
                    videos.append({
                        "id": v.get("id"),
                        "desc": v.get("desc"),
                        "views": int(v.get("stats", {}).get("playCount", 0)),
                        "likes": int(v.get("stats", {}).get("diggCount", 0)),
                        "comments": int(v.get("stats", {}).get("commentCount", 0)),
                        "shares": int(v.get("stats", {}).get("shareCount", 0)),
                        "created": datetime.utcfromtimestamp(int(v.get("createTime", 0))).isoformat(),
                    })
            except Exception as e:
                logging.error(f"Error parsing SIGI_STATE: {e}")
        
        # Try __NEXT_DATA__ structure if needed
        if not videos:
            try:
                # __NEXT_DATA__ structure
                items = json_data['props']['pageProps']['items']
                for v in items[:limit]:
                    videos.append({
                        "id": v.get("id"),
                        "desc": v.get("desc"),
                        "views": int(v.get("stats", {}).get("playCount", 0)),
                        "likes": int(v.get("stats", {}).get("diggCount", 0)),
                        "comments": int(v.get("stats", {}).get("commentCount", 0)),
                        "shares": int(v.get("stats", {}).get("shareCount", 0)),
                        "created": datetime.utcfromtimestamp(int(v.get("createTime", 0))).isoformat(),
                    })
            except Exception as e:
                logging.error(f"Error parsing __NEXT_DATA__: {e}")
        if not videos:
            raise Exception("No videos found for user.")
        results = videos
    except PlaywrightTimeoutError as e:
        logging.error(f"Timeout while loading TikTok page: {e}")
    except Exception as e:
        logging.error(f"Error scraping TikTok: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        # If captcha, try to solve and retry once
        captcha_found = False
        if page:
            captcha_selectors = [
                '#captcha-verify-container-main-page',
                '.secsdk-captcha-drag-icon',
                '#captcha_slide_button',
                'iframe[src*="hcaptcha.com"]',
                '.captcha_verify_container',
                'iframe[src*="verification"]',
                '[id*="captcha"]',
                '.captcha-container',
                'iframe[src*="captcha"]',
                '.secsdk-captcha-drag',
                '.captcha',
            ]
            
            for selector in captcha_selectors:
                if await page.query_selector(selector):
                    captcha_found = True
                    logging.warning(f"Retrying after captcha detected with selector: {selector}")
                    break
        
        if captcha_found:
            solved = await solve_captcha(page)
            if solved:
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(3)
                    # Repeat extraction logic
                    await asyncio.sleep(2)
                    sigi_script = await page.query_selector('script#SIGI_STATE')
                    if sigi_script:
                        sigi_content = await sigi_script.inner_text()
                        json_data = json.loads(sigi_content)
                        # Parse as above
                        items = json_data['ItemList']['user-post']['list']
                        item_module = json_data['ItemModule']
                        for video_id in items[:limit]:
                            v = item_module.get(video_id)
                            if not v:
                                continue
                            results.append({
                                "id": v.get("id"),
                                "desc": v.get("desc"),
                                "views": int(v.get("stats", {}).get("playCount", 0)),
                                "likes": int(v.get("stats", {}).get("diggCount", 0)),
                                "comments": int(v.get("stats", {}).get("commentCount", 0)),
                                "shares": int(v.get("stats", {}).get("shareCount", 0)),
                                "created": datetime.utcfromtimestamp(int(v.get("createTime", 0))).isoformat(),
                            })
                except Exception as e2:
                    logging.error(f"Retry after captcha failed: {e2}")
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        await playwright.stop()
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
    
    return results

if __name__ == "__main__":
    import sys
    username = "tiktok"
    if len(sys.argv) > 1:
        username = sys.argv[1]
    asyncio.run(get_latest_videos(username)) 