"""
analyzer.py - Press Release Analyzer for Infrastructure M&A
=============================================================
This module takes the raw HTML from the scraper and:
1. Finds press release links, titles, and dates
2. Filters for recent items (last 48 hours by default)
3. Classifies items as M&A-related using keyword matching
4. Categorizes M&A type (Acquisition, Divestiture, etc.)

HOW IT WORKS (for beginners):
- HTML is like the source code of a webpage
- We use BeautifulSoup to "parse" (read and understand) the HTML
- We look for patterns that indicate press releases:
  * <a> tags (links) with text that looks like headlines
  * <time> tags or text that looks like dates
  * Common CSS classes like "news-item", "press-release", etc.
- Once we find items, we check if they're about M&A (mergers & acquisitions)
"""

import re
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

# BeautifulSoup parses HTML so we can search through it easily
from bs4 import BeautifulSoup

# python-dateutil is amazing at parsing dates in many different formats
# (e.g., "Jan 15, 2024", "2024-01-15", "15/01/2024", etc.)
from dateutil import parser as date_parser

# ──────────────────────────────────────────────────────────────────────
# M&A KEYWORDS - Words that suggest a press release is about M&A activity
# ──────────────────────────────────────────────────────────────────────

# These keywords help us identify M&A-related press releases
MA_KEYWORDS = [
    "acquire", "acquisition", "acquired",
    "merge", "merger", "merged",
    "divest", "divestiture", "divestment",
    "purchase", "purchased",
    "buy", "bought",
    "sell", "sold", "sale",
    "investment", "invest", "invested",
    "stake",
    "take-private", "take private",
    "ipo",
    "spac",
    "partnership", "joint venture",
    "fund closing", "fund close", "final close",
    "portfolio company",
    "platform",
    "add-on", "bolt-on", "tuck-in",
    "exit", "exited",
    "transaction",
]

# ──────────────────────────────────────────────────────────────────────
# M&A CATEGORIES - How we classify different types of M&A activity
# ──────────────────────────────────────────────────────────────────────

# Each category has a list of keywords that trigger it
# We check categories in order — the FIRST match wins
MA_CATEGORIES = [
    {
        "name": "Acquisition",
        "keywords": ["acquire", "acquisition", "acquired", "purchase", "purchased",
                      "buy", "bought", "take-private", "take private",
                      "add-on", "bolt-on", "tuck-in", "platform"],
    },
    {
        "name": "Divestiture",
        "keywords": ["divest", "divestiture", "divestment", "sell", "sold", "sale"],
    },
    {
        "name": "Fund Closing",
        "keywords": ["fund closing", "fund close", "final close"],
    },
    {
        "name": "Investment",
        "keywords": ["investment", "invest", "invested", "stake",
                      "portfolio company"],
    },
    {
        "name": "Partnership/JV",
        "keywords": ["partnership", "joint venture"],
    },
    {
        "name": "IPO/Exit",
        "keywords": ["ipo", "spac", "exit", "exited"],
    },
    {
        "name": "Other M&A",
        "keywords": ["merge", "merger", "merged", "transaction"],
    },
]


def extract_press_releases(html, base_url):
    """
    Extract press release items from raw HTML content.

    This function looks for common patterns in how websites display press releases:
    - Links inside article/news containers
    - Links with nearby date information
    - Structured data (like <time> tags)

    Args:
        html (str): Raw HTML content of the press release page.
        base_url (str): The page's URL (needed to convert relative links to absolute).

    Returns:
        list: List of dicts with 'title', 'url', 'date_text', 'date_parsed' keys.
    """
    if not html:
        return []

    # Parse the HTML with BeautifulSoup using the 'lxml' parser (fast and reliable)
    soup = BeautifulSoup(html, "lxml")

    press_releases = []
    seen_urls = set()  # Track URLs we've already found (avoid duplicates)

    # ── STRATEGY 1: Look for common news/press release container patterns ──
    # Many websites wrap each press release in a container with a predictable class name
    container_selectors = [
        "article",                          # HTML5 article tag
        "[class*='press']",                 # Classes containing "press"
        "[class*='news']",                  # Classes containing "news"
        "[class*='release']",               # Classes containing "release"
        "[class*='announcement']",          # Classes containing "announcement"
        "[class*='media']",                 # Classes containing "media"
        "[class*='post']",                  # Blog-style posts
        "[class*='item']",                  # Generic items
        "li",                               # List items (many sites use <ul>/<li>)
    ]

    for selector in container_selectors:
        # Find all elements matching this selector
        containers = soup.select(selector)

        for container in containers:
            # Look for a link (<a> tag) inside this container
            link = container.find("a", href=True)
            if not link:
                continue

            # Get the link text (this is usually the headline/title)
            title = link.get_text(strip=True)

            # Skip if the title is too short (probably not a real headline)
            # or too long (probably scraped a whole paragraph by mistake)
            if not title or len(title) < 10 or len(title) > 500:
                continue

            # Convert relative URLs to absolute
            # e.g., "/news/article1" becomes "https://example.com/news/article1"
            href = urljoin(base_url, link["href"])

            # Skip if we've already found this URL
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Try to find a date near this link
            date_text = _find_date_near_element(container)
            date_parsed = _parse_date(date_text) if date_text else None

            press_releases.append({
                "title": title,
                "url": href,
                "date_text": date_text,
                "date_parsed": date_parsed.isoformat() if date_parsed else None,
            })

    # ── STRATEGY 2: If we didn't find much, try standalone links ──
    # Some sites have simpler structures — just a list of links
    if len(press_releases) < 3:
        all_links = soup.find_all("a", href=True)

        for link in all_links:
            title = link.get_text(strip=True)

            # Same filters as above
            if not title or len(title) < 15 or len(title) > 500:
                continue

            href = urljoin(base_url, link["href"])

            # Skip external links, anchors, and already-seen URLs
            if href in seen_urls:
                continue
            if not _is_likely_press_release_url(href, base_url):
                continue

            seen_urls.add(href)

            # Look for date in the link's parent element
            parent = link.parent
            date_text = _find_date_near_element(parent) if parent else None
            date_parsed = _parse_date(date_text) if date_text else None

            press_releases.append({
                "title": title,
                "url": href,
                "date_text": date_text,
                "date_parsed": date_parsed.isoformat() if date_parsed else None,
            })

    return press_releases


def _find_date_near_element(element):
    """
    Try to find a date string near an HTML element.

    Websites display dates in many ways:
    - <time datetime="2024-01-15">January 15, 2024</time>
    - <span class="date">Jan 15, 2024</span>
    - Just plain text like "January 15, 2024" near the headline

    Args:
        element: A BeautifulSoup element to search in/around.

    Returns:
        str or None: The date text if found, None otherwise.
    """
    if not element:
        return None

    # Method 1: Look for <time> tags (the proper HTML5 way to mark dates)
    time_tag = element.find("time")
    if time_tag:
        # The 'datetime' attribute has a machine-readable date
        if time_tag.get("datetime"):
            return time_tag["datetime"]
        # Otherwise use the visible text
        return time_tag.get_text(strip=True)

    # Method 2: Look for elements with date-related class names
    date_classes = ["date", "time", "published", "post-date", "entry-date", "meta"]
    for cls in date_classes:
        date_el = element.find(class_=lambda c: c and cls in c.lower() if c else False)
        if date_el:
            text = date_el.get_text(strip=True)
            if text and len(text) < 50:  # Dates shouldn't be super long
                return text

    # Method 3: Search the element's text for date-like patterns
    text = element.get_text(" ", strip=True)
    date_match = _find_date_in_text(text)
    if date_match:
        return date_match

    return None


def _find_date_in_text(text):
    """
    Use regex patterns to find dates in plain text.

    Handles formats like:
    - "January 15, 2024" or "Jan 15, 2024"
    - "15 January 2024"
    - "2024-01-15"
    - "01/15/2024" or "15/01/2024"

    Args:
        text (str): Text to search for dates.

    Returns:
        str or None: The matched date string, or None.
    """
    if not text:
        return None

    # Common date patterns (regex = "regular expressions" = pattern matching)
    date_patterns = [
        # "January 15, 2024" or "Jan 15, 2024"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}",

        # "15 January 2024"
        r"\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}",

        # "2024-01-15" (ISO format)
        r"\d{4}-\d{2}-\d{2}",

        # "01/15/2024" or "15/01/2024"
        r"\d{1,2}/\d{1,2}/\d{4}",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return None


def _parse_date(date_text):
    """
    Parse a date string into a Python datetime object.

    Uses python-dateutil which can handle almost any date format automatically.

    Args:
        date_text (str): A date string like "January 15, 2024" or "2024-01-15".

    Returns:
        datetime or None: Parsed datetime object, or None if parsing fails.
    """
    if not date_text:
        return None

    try:
        # dateutil.parser.parse is incredibly flexible — it handles most formats
        # fuzzy=True means it will try to find a date even in messy text
        parsed = date_parser.parse(date_text, fuzzy=True)
        return parsed
    except (ValueError, OverflowError, TypeError):
        # If even dateutil can't parse it, give up
        return None


def _is_likely_press_release_url(url, base_url):
    """
    Check if a URL looks like it could be a press release page.

    We want to avoid navigation links, social media links, etc.

    Args:
        url (str): The URL to check.
        base_url (str): The base URL of the site.

    Returns:
        bool: True if it looks like a press release URL.
    """
    # Parse the URLs to compare their domains
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)

    # Must be from the same domain (or a subdomain of it)
    if parsed_url.netloc and parsed_base.netloc:
        base_domain = parsed_base.netloc.replace("www.", "")
        url_domain = parsed_url.netloc.replace("www.", "")
        if base_domain not in url_domain and url_domain not in base_domain:
            return False

    # Skip obvious non-press-release URLs
    skip_patterns = [
        "#",                    # Anchor links (same page)
        "javascript:",          # JavaScript links
        "mailto:",              # Email links
        "tel:",                 # Phone links
        "/login", "/sign",      # Login pages
        "/contact",             # Contact pages
        "/about",               # About pages (generic)
        "/career", "/job",      # Career pages
        "/cookie", "/privacy",  # Legal pages
        "/terms",               # Terms pages
        ".pdf", ".jpg", ".png", # File downloads
        "linkedin.com", "twitter.com", "facebook.com",  # Social media
    ]

    url_lower = url.lower()
    for pattern in skip_patterns:
        if pattern in url_lower:
            return False

    return True


def is_ma_related(title):
    """
    Check if a press release title suggests M&A activity.

    We look for specific keywords that are commonly used in M&A announcements.

    Args:
        title (str): The press release title/headline.

    Returns:
        bool: True if the title contains M&A-related keywords.
    """
    title_lower = title.lower()

    for keyword in MA_KEYWORDS:
        # Use word boundary matching to avoid false positives
        # e.g., "invest" should match "investment" but we're okay with that
        if keyword.lower() in title_lower:
            return True

    return False


def categorize_ma(title):
    """
    Determine what TYPE of M&A activity a press release is about.

    Categories (checked in order — first match wins):
    - Acquisition: buying another company
    - Divestiture: selling off a business unit
    - Fund Closing: completing fundraising for an investment fund
    - Investment: making an investment or taking a stake
    - Partnership/JV: forming a partnership or joint venture
    - IPO/Exit: going public or exiting an investment
    - Other M&A: any other M&A activity

    Args:
        title (str): The press release title/headline.

    Returns:
        str: The M&A category name.
    """
    title_lower = title.lower()

    # Check each category in order (first match wins)
    for category in MA_CATEGORIES:
        for keyword in category["keywords"]:
            if keyword.lower() in title_lower:
                return category["name"]

    # Shouldn't reach here if is_ma_related() returned True, but just in case
    return "Other M&A"


def filter_recent(press_releases, days=2):
    """
    Filter press releases to only include recent ones.

    Args:
        press_releases (list): List of press release dicts.
        days (int): How many days back to include (default: 2 = last 48 hours).

    Returns:
        list: Only the press releases from the last N days.
    """
    # Calculate the cutoff date (N days ago from right now)
    cutoff = datetime.now() - timedelta(days=days)

    recent = []
    for pr in press_releases:
        if pr.get("date_parsed"):
            try:
                # Parse the ISO format date string back to a datetime
                pr_date = datetime.fromisoformat(pr["date_parsed"])

                # Keep it if it's newer than our cutoff
                if pr_date >= cutoff:
                    recent.append(pr)
            except (ValueError, TypeError):
                # If we can't parse the date, skip this item
                pass
        else:
            # If there's no date, include it anyway (might be recent)
            # Better to show a potentially relevant item than miss one
            recent.append(pr)

    return recent


def analyze_results(scraper_results, days=2):
    """
    Analyze scraped HTML from all companies and find M&A press releases.

    This is the MAIN FUNCTION of this module. It:
    1. Takes raw HTML from the scraper
    2. Extracts press releases from each company's page
    3. Filters for recent items
    4. Identifies M&A-related items
    5. Categorizes each M&A item

    Args:
        scraper_results (list): Results from scraper.scrape_all().
        days (int): How many days back to look (default: 2).

    Returns:
        dict: Complete analysis results with M&A items and statistics.
    """
    print(f"\n{'='*60}")
    print(f"  ANALYZER: Processing scraped data")
    print(f"  Looking back: {days} days")
    print(f"{'='*60}\n")

    all_press_releases = []  # Every press release we find
    ma_items = []            # Only the M&A-related ones
    company_stats = []       # Stats for each company

    for result in scraper_results:
        company_name = result["name"]
        base_url = result["url"]
        html = result.get("html")

        if not html or result["status"] != "success":
            company_stats.append({
                "name": company_name,
                "status": "failed",
                "press_releases_found": 0,
                "ma_items_found": 0,
            })
            continue

        # Step 1: Extract all press releases from this company's page
        press_releases = extract_press_releases(html, base_url)

        # Step 2: Filter for recent items only
        recent_releases = filter_recent(press_releases, days=days)

        # Step 3: Check each recent item for M&A relevance
        company_ma_count = 0
        for pr in recent_releases:
            # Add the company name to each press release
            pr["company"] = company_name

            all_press_releases.append(pr)

            # Check if this is M&A-related
            if is_ma_related(pr["title"]):
                pr["ma_category"] = categorize_ma(pr["title"])
                ma_items.append(pr)
                company_ma_count += 1

        company_stats.append({
            "name": company_name,
            "status": "success",
            "press_releases_found": len(recent_releases),
            "ma_items_found": company_ma_count,
        })

        # Show progress for companies with findings
        if recent_releases:
            print(f"  {company_name}: {len(recent_releases)} press releases"
                  f" ({company_ma_count} M&A)")

    # ── Build the final results ──
    # Group M&A items by category for the email report
    ma_by_category = {}
    for item in ma_items:
        category = item.get("ma_category", "Other M&A")
        if category not in ma_by_category:
            ma_by_category[category] = []
        ma_by_category[category].append(item)

    # Calculate summary statistics
    success_count = sum(1 for s in company_stats if s["status"] == "success")
    failed_count = sum(1 for s in company_stats if s["status"] == "failed")

    results = {
        "scan_date": datetime.now().isoformat(),
        "days_lookback": days,
        "summary": {
            "total_companies": len(scraper_results),
            "successful_scrapes": success_count,
            "failed_scrapes": failed_count,
            "total_press_releases": len(all_press_releases),
            "total_ma_items": len(ma_items),
        },
        "ma_items": ma_items,
        "ma_by_category": ma_by_category,
        "all_press_releases": all_press_releases,
        "company_stats": company_stats,
    }

    # Print summary
    print(f"\n{'='*60}")
    print(f"  ANALYSIS COMPLETE")
    print(f"  Companies scanned: {success_count}/{len(scraper_results)}")
    print(f"  Press releases found: {len(all_press_releases)}")
    print(f"  M&A items found: {len(ma_items)}")
    if ma_by_category:
        print(f"  Categories:")
        for cat, items in sorted(ma_by_category.items()):
            print(f"    - {cat}: {len(items)}")
    print(f"{'='*60}\n")

    return results


# ──────────────────────────────────────────────────────────────────────
# Run this file directly to test the analyzer with sample HTML
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Create a simple test HTML page
    test_html = """
    <html>
    <body>
        <article>
            <a href="/news/blackrock-acquires-infrastructure-platform">
                BlackRock Acquires Major Infrastructure Platform
            </a>
            <time datetime="2024-01-15">January 15, 2024</time>
        </article>
        <article>
            <a href="/news/quarterly-results">
                Q4 2024 Quarterly Results Announcement
            </a>
            <time datetime="2024-01-14">January 14, 2024</time>
        </article>
    </body>
    </html>
    """

    # Test extraction
    releases = extract_press_releases(test_html, "https://example.com")
    print(f"Found {len(releases)} press releases:")
    for r in releases:
        ma = "✓ M&A" if is_ma_related(r["title"]) else "  ---"
        print(f"  {ma} | {r['title']}")
        if is_ma_related(r["title"]):
            print(f"        Category: {categorize_ma(r['title'])}")
