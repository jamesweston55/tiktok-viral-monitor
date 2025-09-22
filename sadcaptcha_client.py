import logging
from typing import Optional
import asyncio

# Try to import the official SadCaptcha client
try:
    from tiktok_captcha_solver import AsyncPlaywrightSolver
    SADCAPTCHA_AVAILABLE = True
    logging.info("Official SadCaptcha client imported successfully")
except ImportError as e:
    SADCAPTCHA_AVAILABLE = False
    logging.warning(f"SadCaptcha client not available: {e}")
    logging.warning("Install with: pip install tiktok-captcha-solver")
    
    # Fallback class if the official client is not available
    class AsyncPlaywrightSolver:
        def __init__(self, page, api_key: str):
            self.page = page
            self.api_key = api_key
            
        async def solve_captcha_if_present(self) -> bool:
            logging.warning("SadCaptcha not available - captcha solving disabled")
            return False


async def solve_captcha_with_sadcaptcha(page, api_key: str, max_retries: int = 3) -> bool:
    """
    Solve captcha using the official SadCaptcha client
    
    Args:
        page: Playwright page object
        api_key: SadCaptcha API key
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if captcha was solved successfully, False otherwise
    """
    if not SADCAPTCHA_AVAILABLE:
        logging.warning("SadCaptcha client not available - install with: pip install tiktok-captcha-solver")
        return False
        
    if not api_key or api_key == "your_sadcaptcha_api_key_here":
        logging.warning("SadCaptcha API key not configured")
        return False
    
    # Double-check that captcha is actually present before calling SadCaptcha
    if not await check_for_captcha(page):
        logging.info("🛡️ Double-check: No captcha present, skipping SadCaptcha call")
        return True
    
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"🔧 Attempting to solve captcha with SadCaptcha (attempt {attempt}/{max_retries})")
            
            # Create solver instance
            solver = AsyncPlaywrightSolver(page, api_key)
            
            # Attempt to solve captcha
            result = await solver.solve_captcha_if_present()
            
            if result:
                logging.info("✅ SadCaptcha successfully solved the captcha")
                # Wait a moment for the page to update
                await asyncio.sleep(2)
                return True
            else:
                logging.warning(f"⚠️ SadCaptcha attempt {attempt} failed")
                if attempt < max_retries:
                    await asyncio.sleep(3)  # Wait before retry
                    
        except Exception as e:
            logging.error(f"❌ Error in SadCaptcha attempt {attempt}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)  # Wait before retry
    
    logging.error("❌ All SadCaptcha attempts failed")
    return False


async def check_for_captcha(page) -> bool:
    """
    Check if a captcha is present on the page with robust detection
    
    Args:
        page: Playwright page object
        
    Returns:
        True if captcha is detected, False otherwise
    """
    # More specific selectors that actually indicate a real captcha
    specific_captcha_selectors = [
        '#captcha-verify-container-main-page',
        '.secsdk-captcha-drag-icon',
        '#captcha_slide_button',
    ]
    
    # Check for specific, reliable captcha indicators first
    for selector in specific_captcha_selectors:
        try:
            element = page.locator(selector).first
            if await element.is_visible(timeout=1000):  # Short timeout
                logging.info(f"🚨 Real captcha detected with selector: {selector}")
                return True
        except:
            continue
    
    # Check for captcha-related text content (more reliable)
    captcha_text_indicators = [
        "Slide to complete the puzzle",
        "Please complete the security verification",
        "Drag the slider to complete the puzzle",
        "Verification required"
    ]
    
    for text in captcha_text_indicators:
        try:
            if await page.get_by_text(text).is_visible(timeout=1000):
                logging.info(f"🚨 Captcha detected by text: '{text}'")
                return True
        except:
            continue
    
    # If we reach here, no reliable captcha indicators found
    logging.debug("🔍 No reliable captcha indicators found")
    return False
