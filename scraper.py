"""
scraper.py - Website Scraper for Infrastructure M&A Press Releases
===================================================================
This module fetches HTML content from company press release pages.

HOW IT WORKS:
1. Reads the list of companies from companies.json
2. For each company, it visits their press release webpage
3. Downloads the HTML content of that page
4. Some sites need JavaScript to load (js_render=true) — for those, we use
   Playwright (a browser automation tool) instead of simple HTTP requests

KEY CONCEPTS FOR BEGINNERS:
- HTTP request: Like asking a website "give me your page content"
- HTML: The code that makes up a webpage
- JavaScript rendering: Some sites load content AFTER the page loads using JS
  (think: content that appears after a spinner). We need a real browser for those.
- ThreadPoolExecutor: Lets us fetch multiple sites at the same time (parallel)
  instead of one-by-one (which would be very slow for 97 sites)
"""

import json
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 'requests' is the most popular Python library for making HTTP requests
import requests

# BeautifulSoup helps us parse (read/understand) HTML content
from bs4 import BeautifulSoup

# Check if Playwright is available (it needs a browser binary to be installed)
# If it's not available, we'll fall back to regular HTTP requests for all sites
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    # Try to actually check if the browser is installed
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# ──────────────────────────────────────────────────────────────────────
# CONSTANTS - Settings that control how the scraper behaves
# ──────────────────────────────────────────────────────────────────────

# How long to wait (in seconds) before giving up on a slow website
TIMEOUT_SECONDS = 15

# How many websites to fetch at the same time (too many = might get blocked)
MAX_WORKERS = 5

# How many times to retry a failed request before giving up
MAX_RETRIES = 3

# These headers make our requests look like they come from a real web browser
# Without them, many websites will block us (they don't like bots)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    # Referer tells the site where we "came from" — Google makes us look legit
    "Referer": "https://www.google.com/",
}

# Path to the companies list file
COMPANIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.json")


def load_companies(filepath=None):
    """
    Load the list of companies from the JSON file.

    Returns:
        list: A list of dictionaries, each with 'name', 'url', and 'js_render' keys.

    Example return value:
        [{"name": "BlackRock", "url": "https://...", "js_render": true}, ...]
    """
    if filepath is None:
        filepath = COMPANIES_FILE

    # Open the file, read it, and parse the JSON into a Python dictionary
    with open(filepath, "r") as f:
        data = json.load(f)

    return data["companies"]


def fetch_with_requests(url):
    """
    Fetch a webpage using the 'requests' library (simple HTTP GET).

    This works for most websites that show their content immediately
    without needing JavaScript to load first.

    Args:
        url (str): The webpage URL to fetch.

    Returns:
        str: The HTML content of the page.

    Raises:
        Exception: If the request fails after all retries.
    """
    # Try up to MAX_RETRIES times (with increasing wait between attempts)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Make the HTTP GET request
            # - headers: pretend to be a real browser
            # - timeout: don't wait forever if the site is slow
            # - allow_redirects: follow if the site redirects us somewhere else
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT_SECONDS,
                allow_redirects=True,
            )

            # "raise_for_status" will throw an error if the server returned
            # an error code (like 404 Not Found or 500 Server Error)
            response.raise_for_status()

            # Success! Return the HTML content
            return response.text

        except Exception as e:
            # If this wasn't our last attempt, wait and try again
            if attempt < MAX_RETRIES:
                # Exponential backoff: wait 2s, then 4s, then 8s, etc.
                # This is polite — gives the server time to recover
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                # We've used all our retries — give up and report the error
                raise Exception(
                    f"Failed after {MAX_RETRIES} attempts: {str(e)}"
                )


def fetch_with_playwright(url):
    """
    Fetch a webpage using Playwright (a real browser).

    Some websites load their content using JavaScript AFTER the initial page
    loads. For these sites, we need to use a real browser that can execute
    JavaScript and wait for the content to appear.

    If Playwright/Chromium is not installed, this automatically falls back
    to regular HTTP requests (you may get less content from JS-heavy sites,
    but it still works for most).

    Args:
        url (str): The webpage URL to fetch.

    Returns:
        str: The fully-rendered HTML content of the page.
    """
    # If Playwright isn't available, fall back to regular requests
    if not PLAYWRIGHT_AVAILABLE:
        return fetch_with_requests(url)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Start up a browser instance
            with sync_playwright() as p:
                # Launch Chromium (Chrome's open-source version) in headless mode
                # headless=True means no visible window — it runs in the background
                browser = p.chromium.launch(headless=True)

                # Create a new browser tab (called a "context" and "page")
                context = browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    # viewport sets the browser window size
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()

                # Navigate to the URL and wait until the network is mostly quiet
                # "domcontentloaded" means the page structure is ready
                page.goto(url, timeout=TIMEOUT_SECONDS * 1000, wait_until="domcontentloaded")

                # Wait a bit extra for JavaScript to finish loading content
                page.wait_for_timeout(3000)  # 3 seconds

                # Get the fully-rendered HTML
                html_content = page.content()

                # Clean up — close the browser
                browser.close()

                return html_content

        except Exception as e:
            if attempt < MAX_RETRIES:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                # Last resort: try with regular requests instead of failing
                try:
                    return fetch_with_requests(url)
                except Exception:
                    raise Exception(
                        f"Playwright failed after {MAX_RETRIES} attempts: {str(e)}"
                    )


def fetch_single_site(company, index, total):
    """
    Fetch HTML from a single company's press release page.

    This function decides whether to use simple requests or Playwright
    based on the company's js_render setting.

    Args:
        company (dict): Company info with 'name', 'url', 'js_render' keys.
        index (int): Current company number (for progress display).
        total (int): Total number of companies (for progress display).

    Returns:
        dict: Result with company info, HTML content, and status.
    """
    name = company["name"]
    url = company["url"]
    use_js = company.get("js_render", False)

    # Show progress so you know what's happening
    if use_js and PLAYWRIGHT_AVAILABLE:
        method = "JS"
    elif use_js:
        method = "HTTP*"  # Asterisk means it wanted JS but Playwright isn't available
    else:
        method = "HTTP"
    print(f"  Fetching [{index}/{total}]: {name} ({method})... ", end="", flush=True)

    try:
        # Choose the right fetching method based on whether JS rendering is needed
        if use_js:
            html = fetch_with_playwright(url)
        else:
            html = fetch_with_requests(url)

        # Success! Print a checkmark
        print("✓")

        return {
            "name": name,
            "url": url,
            "html": html,
            "status": "success",
            "error": None,
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        # Failed! Print an X and the error message
        print(f"✗ ({str(e)[:80]})")

        return {
            "name": name,
            "url": url,
            "html": None,
            "status": "failed",
            "error": str(e),
            "fetched_at": datetime.now().isoformat(),
        }


def scrape_all(companies=None):
    """
    Scrape press release pages from all companies in parallel.

    This is the main function you call to start scraping. It:
    1. Loads the company list (or uses one you provide)
    2. Fetches all sites using parallel threads
    3. Returns results for every company

    Args:
        companies (list, optional): List of company dicts. If None, loads from file.

    Returns:
        list: List of result dicts with HTML content and status for each company.
    """
    # Load companies from file if none were provided
    if companies is None:
        companies = load_companies()

    total = len(companies)
    print(f"\n{'='*60}")
    print(f"  SCRAPER: Fetching {total} company press release pages")
    print(f"  Workers: {MAX_WORKERS} parallel | Timeout: {TIMEOUT_SECONDS}s")
    print(f"{'='*60}\n")

    results = []
    start_time = time.time()

    # ThreadPoolExecutor lets us run multiple fetches at the same time
    # max_workers=5 means up to 5 sites are being fetched simultaneously
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all fetch jobs to the thread pool
        # "future_to_company" maps each running job back to its company info
        future_to_company = {}
        for i, company in enumerate(companies, 1):
            future = executor.submit(fetch_single_site, company, i, total)
            future_to_company[future] = company

        # Collect results as they complete (not necessarily in order)
        for future in as_completed(future_to_company):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # This shouldn't happen (errors are caught in fetch_single_site)
                # but just in case...
                company = future_to_company[future]
                results.append({
                    "name": company["name"],
                    "url": company["url"],
                    "html": None,
                    "status": "failed",
                    "error": str(e),
                    "fetched_at": datetime.now().isoformat(),
                })

    # Calculate and display summary statistics
    elapsed = time.time() - start_time
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    print(f"\n{'='*60}")
    print(f"  SCRAPER COMPLETE")
    print(f"  Total: {total} | Success: {success_count} | Failed: {failed_count}")
    print(f"  Time: {elapsed:.1f} seconds")
    print(f"{'='*60}\n")

    return results


# ──────────────────────────────────────────────────────────────────────
# This block runs only when you execute this file directly
# (not when it's imported by another file)
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick test: scrape just the first 3 companies
    companies = load_companies()[:3]
    results = scrape_all(companies)

    # Show what we got
    for r in results:
        status = "✓" if r["status"] == "success" else "✗"
        html_len = len(r["html"]) if r["html"] else 0
        print(f"  {status} {r['name']}: {html_len} chars of HTML")
