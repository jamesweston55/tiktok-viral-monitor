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
    
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Attempting to solve captcha with SadCaptcha (attempt {attempt}/{max_retries})")
            
            # Create solver instance
            solver = AsyncPlaywrightSolver(page, api_key)
            
            # Attempt to solve captcha
            result = await solver.solve_captcha_if_present()
            
            if result:
                logging.info("SadCaptcha successfully solved the captcha")
                # Wait a moment for the page to update
                await asyncio.sleep(2)
                return True
            else:
                logging.warning(f"SadCaptcha attempt {attempt} failed")
                if attempt < max_retries:
                    await asyncio.sleep(3)  # Wait before retry
                    
        except Exception as e:
            logging.error(f"Error in SadCaptcha attempt {attempt}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(3)  # Wait before retry
    
    logging.error("All SadCaptcha attempts failed")
    return False


async def check_for_captcha(page) -> bool:
    """
    Check if a captcha is present on the page
    
    Args:
        page: Playwright page object
        
    Returns:
        True if captcha is detected, False otherwise
    """
    captcha_selectors = [
        '#captcha-verify-container-main-page',
        '.secsdk-captcha-drag-icon', 
        '#captcha_slide_button',
        '[data-testid="captcha-container"]',
        '.captcha-container',
        '[class*="captcha"]',
        '[data-cy="captcha"]',
        '.captcha',
        'iframe[src*="captcha"]',
        'iframe[src*="verification"]',
        '[class*="verification"]',
        '[id*="verification"]',
        '.verify-container',
        '#verify-container'
    ]
    
    for selector in captcha_selectors:
        try:
            element = page.locator(selector).first
            if await element.is_visible():
                logging.info(f"Captcha detected with selector: {selector}")
                return True
        except:
            continue
    
    return False
