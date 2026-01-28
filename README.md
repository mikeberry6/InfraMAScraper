# Infrastructure M&A Press Release Tracker

Automated daily scanner that monitors 97 infrastructure investment firms for M&A activity by scraping their press release pages, analyzing content for M&A keywords, and sending a formatted HTML email report.

## Quick Start

```bash
# One-time setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Run a test scan (5 sites, no email)
python run_daily.py --test --no-email

# Full daily scan with email
python run_daily.py
```

## Usage

```bash
python run_daily.py                # Full scan (97 sites) + send email
python run_daily.py --test         # Test mode (5 sites) + send email
python run_daily.py --no-email     # Full scan, skip email
python run_daily.py --days 7       # Look back 7 days instead of 2
python run_daily.py --test --no-email  # Test mode, no email

# Or use the shell script:
./scan.sh --test --no-email
```

## Project Structure

```
infra-ma-tracker/
├── config.py              # Email credentials (not in git)
├── companies.json         # All 97 tracked companies
├── scraper.py             # Fetches HTML from all sites
├── analyzer.py            # Extracts and classifies press releases
├── emailer.py             # Generates and sends HTML email
├── run_daily.py           # Main orchestrator
├── scan.sh                # One-command runner
├── requirements.txt       # Python dependencies
├── .gitignore
├── data/
│   ├── html_cache/        # Cached HTML pages
│   └── site_health.json   # Site reliability tracking
└── reports/               # Daily reports (JSON + HTML)
```

## Configuration

Edit `config.py` with your Gmail credentials. You need a Gmail App Password (not your regular password). Generate one at https://myaccount.google.com/apppasswords.

## How It Works

1. **Scraper** fetches press release pages from 97 infrastructure firms using HTTP requests (or Playwright for JavaScript-heavy sites)
2. **Analyzer** extracts press releases, filters for the last 48 hours, and classifies M&A activity into categories (Acquisition, Divestiture, Fund Closing, Investment, Partnership/JV, IPO/Exit)
3. **Emailer** generates a professional HTML email and sends it via Gmail SMTP
