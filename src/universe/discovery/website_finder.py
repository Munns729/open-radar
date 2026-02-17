"""
Website Discovery - Free tier implementation using Google search.

Provides functions to find company websites without paid APIs.
"""
import asyncio
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from .base import rate_limiter

logger = logging.getLogger(__name__)


# Country TLDs for domain guessing
COUNTRY_TLDS = {
    "GB": ".co.uk",
    "UK": ".co.uk",
    "DE": ".de",
    "FR": ".fr",
    "NL": ".nl",
    "IT": ".it",
    "ES": ".es",
    "BE": ".be",
    "AT": ".at",
    "CH": ".ch",
    "SE": ".se",
    "DK": ".dk",
    "NO": ".no",
    "FI": ".fi",
    "IE": ".ie",
    "PL": ".pl",
}


async def find_website_free(
    legal_name: str,
    country: str,
    existing_website: Optional[str] = None,
    sector: Optional[str] = None,
) -> Tuple[Optional[str], str]:
    """
    Find a company's website using free methods.
    
    Hierarchy:
    1. Use existing website if provided
    2. Google search
    3. DNS/domain guessing
    
    Returns:
        (website_url, source) or (None, "not_found")
    """
    # Stage 1: Use existing if provided
    if existing_website:
        return existing_website, "discovery_source"
    
    # Stage 2: Google search
    website = await google_search_website(legal_name, country)
    if website:
        return website, "google_search"
    
    # Stage 3: DNS guess
    website = await dns_guess_website(legal_name, country)
    if website:
        return website, "dns_guess"
    
    return None, "not_found"


async def google_search_website(legal_name: str, country: str) -> Optional[str]:
    """
    Find website via Google search.
    
    Uses Playwright to search Google and extract the first result.
    """
    await rate_limiter.acquire("google_search")
    
    query = f'"{legal_name}" {country} official website'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Navigate to Google
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            await page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            
            # Handle cookie consent if present
            try:
                accept_btn = await page.query_selector('button:has-text("Accept all")')
                if accept_btn:
                    await accept_btn.click()
                    await page.wait_for_timeout(500)
            except:
                pass
            
            # Look for search results
            # Google organic results have various selectors
            result_selectors = [
                'div.g a[href^="http"]:not([href*="google"])',
                'div[data-sokoban-container] a[href^="http"]',
                'a[jsname][data-ved][href^="http"]:not([href*="google"])',
            ]
            
            for selector in result_selectors:
                links = await page.query_selector_all(selector)
                for link in links[:5]:  # Check first 5 results
                    href = await link.get_attribute("href")
                    if href and is_company_website(href, legal_name):
                        await browser.close()
                        return clean_url(href)
            
            # Fallback: get first non-Google link
            all_links = await page.query_selector_all('a[href^="http"]')
            for link in all_links:
                href = await link.get_attribute("href")
                if href and not any(x in href for x in ['google.', 'youtube.', 'wikipedia.']):
                    # Basic validation: does it look like a company site?
                    domain = urlparse(href).netloc
                    if domain and len(domain) > 4:
                        await browser.close()
                        return clean_url(href)
            
        except Exception as e:
            logger.warning(f"Google search failed for {legal_name}: {e}")
        finally:
            await browser.close()
    
    return None


async def dns_guess_website(legal_name: str, country: str) -> Optional[str]:
    """
    Guess the website URL and validate it exists.
    
    Tries common patterns like companyname.co.uk, companyname.com
    """
    import socket
    
    # Normalize name for domain
    base = normalize_for_domain(legal_name)
    if not base:
        return None
    
    # TLDs to try
    tlds = [COUNTRY_TLDS.get(country, ".com"), ".com", ".eu"]
    
    for tld in tlds:
        domain = f"{base}{tld}"
        
        try:
            # Simple DNS check
            socket.gethostbyname(domain.replace(".", ".", 1) if tld.startswith(".") else domain)
            
            url = f"https://www.{domain}"
            # Validate with HEAD request
            if await validate_url(url):
                return url
                
        except socket.gaierror:
            continue
        except Exception:
            continue
    
    return None


def normalize_for_domain(name: str) -> Optional[str]:
    """Normalize company name to a potential domain."""
    # Remove common suffixes
    name = re.sub(r'\s+(Ltd|Limited|PLC|LLP|GmbH|AG|SA|Inc|Corp)\.?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(Holdings?|Group|International|UK|Europe)$', '', name, flags=re.IGNORECASE)
    
    # Convert to lowercase, remove special chars
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', '', name)  # Remove spaces for domain
    
    if len(name) < 3:
        return None
    
    return name


async def validate_url(url: str) -> bool:
    """Validate that a URL responds with a valid page."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                response = await page.goto(url, timeout=5000, wait_until="domcontentloaded")
                valid = response and response.status < 400
                await browser.close()
                return valid
            except:
                await browser.close()
                return False
    except:
        return False


def is_company_website(url: str, company_name: str) -> bool:
    """
    Check if a URL is likely the company's official website.
    Filters out aggregators, directories, LinkedIn, etc.
    """
    excluded_domains = [
        'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
        'youtube.com', 'wikipedia.org', 'crunchbase.com', 'bloomberg.com',
        'reuters.com', 'companieshouse.gov.uk', 'dnb.com', 'zoominfo.com',
        'glassdoor.com', 'indeed.com', 'yelp.com', 'trustpilot.com',
    ]
    
    domain = urlparse(url).netloc.lower()
    
    # Exclude known aggregators
    for excluded in excluded_domains:
        if excluded in domain:
            return False
    
    return True


def clean_url(url: str) -> str:
    """Clean and normalize a URL."""
    # Ensure https
    if not url.startswith('http'):
        url = 'https://' + url
    
    # Remove query params and fragments for base URL
    parsed = urlparse(url)
    clean = f"{parsed.scheme}://{parsed.netloc}"
    
    return clean
