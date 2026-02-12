"""
Browser automation utilities
Handles web scraping with requests and Playwright
"""

import asyncio
import requests
from playwright.async_api import async_playwright
from .logger import logger


def initialize_no_driver(url, timeout=30):
    """
    Fetch webpage content using requests (no browser automation)
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        HTML content as string or None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        logger.info(f"Request to {url} failed: {e}")
        return None


async def initialize_driver(url, timeout=30000):
    """
    Fetch webpage content using Playwright (for dynamic content)
    
    Args:
        url: URL to fetch
        timeout: Page load timeout in milliseconds
        
    Returns:
        HTML content as string or None if failed
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(url, timeout=timeout, wait_until='networkidle')
            content = await page.content()
            
            await browser.close()
            
            return content
            
    except Exception as e:
        logger.error(f"Playwright request to {url} failed: {e}")
        return None