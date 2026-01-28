"""
run_daily.py - Main Orchestrator for Infrastructure M&A Tracker
================================================================
This is the MAIN FILE you run to scan for M&A press releases.

It coordinates everything:
1. Loads the company list
2. Scrapes all press release pages (using scraper.py)
3. Analyzes the HTML for M&A activity (using analyzer.py)
4. Generates and sends an HTML email report (using emailer.py)
5. Saves reports to the reports/ folder

HOW TO USE:
    # Full scan of all 97 companies + send email:
    python run_daily.py

    # Test mode: scan only the first 5 companies + send email:
    python run_daily.py --test

    # Scan but DON'T send email (just save reports):
    python run_daily.py --no-email

    # Test mode without email:
    python run_daily.py --test --no-email

    # Look back 7 days instead of the default 2:
    python run_daily.py --days 7

WHAT IS argparse?
    argparse is Python's built-in way to handle command-line arguments.
    When you type "python run_daily.py --test", argparse is what reads
    the "--test" part and tells our code about it.
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Import our custom modules (the other files we created)
from scraper import load_companies, scrape_all
from analyzer import analyze_results
from emailer import generate_html_report, send_email

# ──────────────────────────────────────────────────────────────────────
# DIRECTORY SETUP
# Figure out where this script lives so we can find related files
# ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")


def setup_directories():
    """
    Create necessary directories if they don't exist.

    os.makedirs with exist_ok=True means:
    - Create the directory if it doesn't exist
    - Do nothing if it already exists (no error)
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "html_cache"), exist_ok=True)


def save_reports(analysis_results, html_report):
    """
    Save the analysis results and HTML report to the reports/ folder.

    We save two files:
    1. A JSON file (machine-readable data) — useful for programmatic access
    2. An HTML file (the email) — useful for viewing in a browser

    Both files are named with today's date, e.g.:
    - reports/2024-01-15.json
    - reports/2024-01-15.html

    Args:
        analysis_results (dict): The analysis data from analyzer.py.
        html_report (str): The HTML email content from emailer.py.

    Returns:
        tuple: (json_path, html_path) — the paths where files were saved.
    """
    # Create filename based on today's date
    date_str = datetime.now().strftime("%Y-%m-%d")

    json_path = os.path.join(REPORTS_DIR, f"{date_str}.json")
    html_path = os.path.join(REPORTS_DIR, f"{date_str}.html")

    # Save JSON report
    # We need to filter out the raw HTML content — it's too big to save
    # and not useful in the report (it's the original webpage HTML)
    save_data = {
        "scan_date": analysis_results["scan_date"],
        "days_lookback": analysis_results["days_lookback"],
        "summary": analysis_results["summary"],
        "ma_items": analysis_results["ma_items"],
        "ma_by_category": analysis_results["ma_by_category"],
        "releases_by_company": analysis_results.get("releases_by_company", {}),
        "all_press_releases": analysis_results.get("all_press_releases", []),
        "company_stats": analysis_results["company_stats"],
    }

    with open(json_path, "w") as f:
        # indent=2 makes the JSON human-readable (pretty-printed)
        json.dump(save_data, f, indent=2, default=str)

    # Save HTML report
    with open(html_path, "w") as f:
        f.write(html_report)

    return json_path, html_path


def save_site_health(analysis_results):
    """
    Save site health data so we can track which sites work over time.

    This creates/updates data/site_health.json with the latest scrape status
    for each company. Over time, this helps identify sites that consistently
    fail (they might have changed their page structure or blocked us).

    Args:
        analysis_results (dict): The analysis data from analyzer.py.
    """
    health_path = os.path.join(DATA_DIR, "site_health.json")

    # Load existing health data if it exists
    health_data = {}
    if os.path.exists(health_path):
        try:
            with open(health_path, "r") as f:
                health_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            health_data = {}

    # Update with latest results
    for stat in analysis_results.get("company_stats", []):
        name = stat["name"]
        if name not in health_data:
            health_data[name] = {
                "total_scans": 0,
                "successful_scans": 0,
                "last_status": None,
                "last_scan": None,
            }

        health_data[name]["total_scans"] += 1
        if stat["status"] == "success":
            health_data[name]["successful_scans"] += 1
        health_data[name]["last_status"] = stat["status"]
        health_data[name]["last_scan"] = datetime.now().isoformat()

    # Save updated health data
    with open(health_path, "w") as f:
        json.dump(health_data, f, indent=2, default=str)


def print_banner():
    """Print a nice banner when the script starts."""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       INFRASTRUCTURE M&A PRESS RELEASE TRACKER          ║")
    print("║                    Daily Scanner                        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p'):<49}║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def print_final_summary(analysis_results, json_path, html_path, email_sent):
    """Print a nice summary at the end of the scan."""
    summary = analysis_results["summary"]

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                    SCAN COMPLETE                        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Companies scanned: {summary['successful_scrapes']}/{summary['total_companies']:<35}║")
    print(f"║  Press releases found: {summary['total_press_releases']:<33}║")
    print(f"║  M&A items detected: {summary['total_ma_items']:<35}║")
    print(f"║  Email sent: {'Yes ✓' if email_sent else 'No (skipped or failed)':<43}║")
    print(f"║  JSON report: {os.path.basename(json_path):<42}║")
    print(f"║  HTML report: {os.path.basename(html_path):<42}║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Show M&A findings if any
    if analysis_results.get("ma_items"):
        print("  M&A ITEMS FOUND:")
        print("  " + "─" * 56)
        for item in analysis_results["ma_items"]:
            cat = item.get("ma_category", "Unknown")
            company = item.get("company", "Unknown")
            title = item.get("title", "No title")
            # Truncate long titles
            if len(title) > 60:
                title = title[:57] + "..."
            print(f"  [{cat}] {company}")
            print(f"    → {title}")
            print()


def main():
    """
    Main function — orchestrates the entire scanning pipeline.

    This is what runs when you execute: python run_daily.py
    """
    # ── Parse command-line arguments ──
    # This is how we handle flags like --test, --no-email, --days
    parser = argparse.ArgumentParser(
        description="Infrastructure M&A Press Release Tracker — Daily Scanner",
        # formatter_class makes the help text look nicer
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_daily.py              # Full scan + send email
  python run_daily.py --test       # Quick test (5 sites) + send email
  python run_daily.py --no-email   # Full scan, no email
  python run_daily.py --days 7     # Look back 7 days instead of 2
  python run_daily.py --test --no-email  # Quick test, no email
        """,
    )

    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to look back for press releases (default: 1)",
    )

    parser.add_argument(
        "--no-email",
        action="store_true",  # This means: if --no-email is present, set it to True
        help="Skip sending the email report",
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: only scan the first 5 companies",
    )

    # Parse the arguments the user typed
    args = parser.parse_args()

    # ── Start the scan ──
    print_banner()

    # Create directories if needed
    setup_directories()

    # Load companies
    companies = load_companies()
    total_companies = len(companies)

    # In test mode, only use the first 5 companies
    if args.test:
        companies = companies[:5]
        print(f"  ⚠ TEST MODE: Scanning only {len(companies)} of {total_companies} companies\n")

    # ── STEP 1: Scrape all websites ──
    print("  STEP 1/3: Scraping press release pages...")
    scraper_results = scrape_all(companies)

    # ── STEP 2: Analyze the scraped content ──
    print("  STEP 2/3: Analyzing for M&A activity...")
    analysis_results = analyze_results(scraper_results, days=args.days)

    # ── STEP 3: Generate report and optionally send email ──
    print("  STEP 3/3: Generating report...")
    html_report = generate_html_report(analysis_results)

    # Save reports to files
    json_path, html_path = save_reports(analysis_results, html_report)
    print(f"  Reports saved to:")
    print(f"    → {json_path}")
    print(f"    → {html_path}")

    # Save site health data
    save_site_health(analysis_results)

    # Send email (unless --no-email was specified)
    email_sent = False
    if not args.no_email:
        email_sent = send_email(html_report, analysis_results)
    else:
        print("\n  Email skipped (--no-email flag used)")

    # ── Show final summary ──
    print_final_summary(analysis_results, json_path, html_path, email_sent)


# ──────────────────────────────────────────────────────────────────────
# This is the standard Python way to run a script
# "__name__ == '__main__'" is True when you run this file directly
# (not when it's imported by another file)
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
