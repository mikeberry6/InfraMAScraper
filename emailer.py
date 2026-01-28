"""
emailer.py - HTML Email Generator and Sender
==============================================
This module creates a professional-looking HTML email report of ALL press
releases found, grouped by company, with M&A items highlighted.

HOW EMAIL SENDING WORKS (for beginners):
- SMTP = "Simple Mail Transfer Protocol" — the standard way computers send email
- Gmail lets you send email through their servers if you have an "App Password"
- TLS = encryption that protects your email credentials during transmission
- We connect to smtp.gmail.com on port 587, authenticate, and send the email

HOW THE HTML EMAIL WORKS:
- Email clients (Gmail, Outlook, etc.) can display HTML emails
- We build an HTML page with inline CSS (email clients don't support external CSS)
- The email shows ALL press releases grouped by company
- Items matching M&A keywords get a bold [M&A] tag so they stand out
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────
# COLOR SCHEME - Used throughout the email design
# ──────────────────────────────────────────────────────────────────────
COLORS = {
    "header_bg": "#1a365d",        # Dark blue — for headers and accent elements
    "header_text": "#ffffff",      # White text on dark backgrounds
    "body_bg": "#f7fafc",          # Light gray — main background
    "card_bg": "#ffffff",          # White — for content cards
    "text_primary": "#2d3748",     # Dark gray — main text
    "text_secondary": "#718096",   # Medium gray — secondary text
    "accent_green": "#38a169",     # Green — for success indicators
    "accent_red": "#e53e3e",       # Red — for failure indicators
    "accent_blue": "#3182ce",      # Blue — for links
    "border": "#e2e8f0",           # Light gray — for borders
    "ma_tag_bg": "#e53e3e",        # Red background for M&A tags
    "ma_tag_text": "#ffffff",      # White text for M&A tags
}

# Colors for each M&A category tag
CATEGORY_COLORS = {
    "Acquisition": "#e53e3e",
    "Divestiture": "#dd6b20",
    "Fund Closing": "#38a169",
    "Investment": "#3182ce",
    "Partnership/JV": "#805ad5",
    "IPO/Exit": "#d69e2e",
    "Other M&A": "#718096",
}


def _build_ma_tag(category):
    """
    Build an inline HTML tag badge for an M&A category.

    Args:
        category (str): The M&A category name (e.g., "Acquisition").

    Returns:
        str: HTML string for the colored tag badge.
    """
    color = CATEGORY_COLORS.get(category, "#718096")
    return (
        f'<span style="'
        f"display: inline-block; "
        f"background-color: {color}; "
        f"color: white; "
        f"font-size: 10px; "
        f"font-weight: 700; "
        f"padding: 2px 6px; "
        f"border-radius: 3px; "
        f"letter-spacing: 0.3px; "
        f"margin-right: 6px; "
        f"vertical-align: middle; "
        f'">{category}</span>'
    )


def generate_html_report(analysis_results):
    """
    Generate a professional HTML email showing ALL press releases grouped
    by company, with M&A items highlighted using colored tags.

    Args:
        analysis_results (dict): Output from analyzer.analyze_results().

    Returns:
        str: Complete HTML string ready to be sent as an email.
    """
    summary = analysis_results["summary"]
    releases_by_company = analysis_results.get("releases_by_company", {})
    scan_date = datetime.now().strftime("%B %d, %Y")
    scan_time = datetime.now().strftime("%I:%M %p")

    # ── Build the press releases section, grouped by company ──
    # Sort companies alphabetically for consistent ordering
    sorted_companies = sorted(releases_by_company.keys())

    releases_html = ""

    if sorted_companies:
        for company_name in sorted_companies:
            items = releases_by_company[company_name]
            if not items:
                continue

            # Count M&A items for this company
            ma_count = sum(1 for item in items if item.get("is_ma"))

            # Company header — show M&A count if any
            ma_badge = ""
            if ma_count > 0:
                ma_badge = (
                    f' <span style="'
                    f"background-color: {COLORS['ma_tag_bg']}; "
                    f"color: white; "
                    f"font-size: 10px; "
                    f"font-weight: 700; "
                    f"padding: 2px 6px; "
                    f"border-radius: 3px; "
                    f"margin-left: 8px; "
                    f"vertical-align: middle; "
                    f'">{ma_count} M&amp;A</span>'
                )

            releases_html += f"""
            <div style="margin-bottom: 16px;">
                <div style="
                    background-color: {COLORS['header_bg']};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 6px 6px 0 0;
                    font-size: 13px;
                    font-weight: bold;
                ">
                    {company_name}{ma_badge}
                </div>
                <div style="
                    border: 1px solid {COLORS['border']};
                    border-top: none;
                    border-radius: 0 0 6px 6px;
                    overflow: hidden;
                ">
            """

            # Add each press release for this company
            for i, item in enumerate(items):
                row_bg = "#ffffff" if i % 2 == 0 else "#f7fafc"
                date_str = item.get("date_text", "") or ""
                is_ma = item.get("is_ma", False)
                ma_category = item.get("ma_category")

                # Build the title line — with M&A tag if applicable
                tag_html = ""
                if is_ma and ma_category:
                    tag_html = _build_ma_tag(ma_category)

                # M&A items get bold titles to stand out during scanning
                title_style = "font-weight: 700;" if is_ma else ""

                releases_html += f"""
                    <div style="
                        padding: 8px 16px;
                        background-color: {row_bg};
                        border-bottom: 1px solid {COLORS['border']};
                        line-height: 1.4;
                    ">
                        <div style="font-size: 13px;">
                            {tag_html}<a href="{item.get('url', '#')}"
                               style="color: {COLORS['accent_blue']}; text-decoration: none; {title_style}"
                               target="_blank">{item.get('title', 'No title')}</a>
                        </div>
                """

                # Only show date if we have one
                if date_str:
                    releases_html += f"""
                        <div style="font-size: 11px; color: {COLORS['text_secondary']}; margin-top: 2px;">
                            {date_str}
                        </div>
                    """

                releases_html += """
                    </div>
                """

            releases_html += """
                </div>
            </div>
            """
    else:
        # No press releases found at all
        releases_html = f"""
        <div style="
            text-align: center;
            padding: 40px 20px;
            color: {COLORS['text_secondary']};
            font-size: 16px;
        ">
            <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
            <div>No press releases found in the last
                 {analysis_results.get('days_lookback', 1)} day(s).</div>
            <div style="font-size: 13px; margin-top: 8px;">
                This could mean a quiet day, or some sites may have blocked our scraper.
            </div>
        </div>
        """

    # ── Build the scan health section ──
    success_rate = 0
    if summary["total_companies"] > 0:
        success_rate = (summary["successful_scrapes"] / summary["total_companies"]) * 100

    # Choose color based on success rate
    if success_rate >= 80:
        health_color = COLORS["accent_green"]
        health_label = "Healthy"
    elif success_rate >= 50:
        health_color = "#d69e2e"
        health_label = "Degraded"
    else:
        health_color = COLORS["accent_red"]
        health_label = "Poor"

    # ── Assemble the complete HTML email ──
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="
        margin: 0;
        padding: 0;
        background-color: {COLORS['body_bg']};
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    ">
        <!-- Main container (max width for readability) -->
        <div style="max-width: 680px; margin: 0 auto; padding: 20px;">

            <!-- ═══════ HEADER ═══════ -->
            <div style="
                background-color: {COLORS['header_bg']};
                color: {COLORS['header_text']};
                padding: 24px 32px;
                border-radius: 8px 8px 0 0;
                text-align: center;
            ">
                <h1 style="margin: 0; font-size: 22px; font-weight: 700;">
                    Infrastructure Press Release Digest
                </h1>
                <p style="margin: 8px 0 0; font-size: 14px; opacity: 0.85;">
                    Daily Scan — {scan_date}
                </p>
            </div>

            <!-- ═══════ SUMMARY STATS ═══════ -->
            <div style="
                background-color: {COLORS['card_bg']};
                padding: 20px 32px;
                border-left: 1px solid {COLORS['border']};
                border-right: 1px solid {COLORS['border']};
            ">
                <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                    <tr>
                        <!-- Total Press Releases -->
                        <td style="text-align: center; padding: 12px; width: 25%;">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['header_bg']};">
                                {summary['total_press_releases']}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                Total Items
                            </div>
                        </td>
                        <!-- M&A Tagged -->
                        <td style="text-align: center; padding: 12px; width: 25%; border-left: 1px solid {COLORS['border']};">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['ma_tag_bg']};">
                                {summary['total_ma_items']}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                M&amp;A Tagged
                            </div>
                        </td>
                        <!-- Companies with releases -->
                        <td style="text-align: center; padding: 12px; width: 25%; border-left: 1px solid {COLORS['border']};">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['accent_green']};">
                                {len(sorted_companies) if sorted_companies else 0}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                Companies
                            </div>
                        </td>
                        <!-- Sites Scanned -->
                        <td style="text-align: center; padding: 12px; width: 25%; border-left: 1px solid {COLORS['border']};">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['text_secondary']};">
                                {summary['successful_scrapes']}/{summary['total_companies']}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                Sites OK
                            </div>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- ═══════ SCAN HEALTH BAR ═══════ -->
            <div style="
                background-color: {COLORS['card_bg']};
                padding: 12px 32px 20px;
                border-left: 1px solid {COLORS['border']};
                border-right: 1px solid {COLORS['border']};
                border-bottom: 1px solid {COLORS['border']};
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 12px; color: {COLORS['text_secondary']};">Scan Health</span>
                    <span style="font-size: 12px; font-weight: 600; color: {health_color};">{health_label} ({success_rate:.0f}%)</span>
                </div>
                <div style="
                    background-color: {COLORS['border']};
                    border-radius: 4px;
                    height: 8px;
                    overflow: hidden;
                ">
                    <div style="
                        background-color: {health_color};
                        width: {success_rate:.0f}%;
                        height: 100%;
                        border-radius: 4px;
                    "></div>
                </div>
            </div>

            <!-- ═══════ ALL PRESS RELEASES BY COMPANY ═══════ -->
            <div style="
                background-color: {COLORS['card_bg']};
                padding: 24px 32px;
                margin-top: 16px;
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            ">
                <h2 style="
                    margin: 0 0 20px;
                    font-size: 18px;
                    color: {COLORS['header_bg']};
                    border-bottom: 2px solid {COLORS['header_bg']};
                    padding-bottom: 8px;
                ">
                    Press Releases by Company
                </h2>

                {releases_html}
            </div>

            <!-- ═══════ FOOTER ═══════ -->
            <div style="
                text-align: center;
                padding: 20px;
                font-size: 12px;
                color: {COLORS['text_secondary']};
            ">
                <p style="margin: 0;">
                    Generated at {scan_time} on {scan_date}
                </p>
                <p style="margin: 4px 0 0;">
                    Infrastructure Press Release Tracker — Automated Daily Scan
                </p>
            </div>

        </div>
    </body>
    </html>
    """

    return html


def send_email(html_content, analysis_results):
    """
    Send the HTML report via Gmail SMTP.

    HOW THIS WORKS:
    1. We load your Gmail credentials from config.py
    2. We connect to Gmail's SMTP server (smtp.gmail.com) on port 587
    3. We upgrade the connection to TLS (encrypted)
    4. We log in with your email and App Password
    5. We send the email
    6. We close the connection

    Args:
        html_content (str): The HTML email body (from generate_html_report).
        analysis_results (dict): Used to build the subject line.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    # Import credentials from config.py
    # (This is a separate file so your password isn't in the main code)
    try:
        from config import EMAIL_CONFIG
    except ImportError:
        print("  ERROR: config.py not found!")
        print("  Make sure config.py exists with your EMAIL_CONFIG settings.")
        return False

    sender_email = EMAIL_CONFIG["sender_email"]
    sender_password = EMAIL_CONFIG["sender_password"]
    recipient_email = EMAIL_CONFIG["recipient_email"]

    # Build a descriptive subject line showing total items (not just M&A)
    summary = analysis_results.get("summary", {})
    total_count = summary.get("total_press_releases", 0)
    ma_count = summary.get("total_ma_items", 0)
    date_str = datetime.now().strftime("%b %d, %Y")

    if total_count > 0:
        subject = f"[Infra Digest] {total_count} Press Releases ({ma_count} M&A) — {date_str}"
    else:
        subject = f"[Infra Digest] No Press Releases Found — {date_str}"

    print(f"\n  Sending email report...")
    print(f"  From: {sender_email}")
    print(f"  To:   {recipient_email}")
    print(f"  Subject: {subject}")

    try:
        # Create the email message
        # MIMEMultipart allows us to send both plain text and HTML versions
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Infra Digest <{sender_email}>"
        msg["To"] = recipient_email

        # Plain text version (fallback for email clients that don't support HTML)
        plain_text = (
            f"Infrastructure Press Release Digest - {date_str}\n\n"
            f"Total Press Releases: {total_count}\n"
            f"M&A Tagged: {ma_count}\n"
            f"Sites Scanned: {summary.get('successful_scrapes', 0)}/{summary.get('total_companies', 0)}\n\n"
            f"View the HTML version of this email for the full report."
        )

        # Attach both versions (email client will pick the best one it supports)
        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Connect to Gmail's SMTP server and send
        # Port 587 is for TLS (encrypted) connections
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            # Start TLS encryption (protects your password during login)
            server.starttls()

            # Log in with your credentials
            server.login(sender_email, sender_password)

            # Send the email
            server.sendmail(sender_email, recipient_email, msg.as_string())

        print("  Email sent successfully! ✓")
        return True

    except smtplib.SMTPAuthenticationError:
        print("  ERROR: Gmail authentication failed!")
        print("  Check that your App Password in config.py is correct.")
        print("  You may need to generate a new one at:")
        print("  https://myaccount.google.com/apppasswords")
        return False

    except Exception as e:
        print(f"  ERROR sending email: {str(e)}")
        return False


# ──────────────────────────────────────────────────────────────────────
# Test the email generator with sample data
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Create sample analysis results for testing
    sample_results = {
        "scan_date": datetime.now().isoformat(),
        "days_lookback": 1,
        "summary": {
            "total_companies": 97,
            "successful_scrapes": 85,
            "failed_scrapes": 12,
            "total_press_releases": 42,
            "total_ma_items": 3,
        },
        "ma_items": [],
        "ma_by_category": {},
        "releases_by_company": {
            "Brookfield Asset Management": [
                {
                    "title": "Brookfield Acquires European Data Center Platform",
                    "url": "https://example.com/article1",
                    "company": "Brookfield Asset Management",
                    "is_ma": True,
                    "ma_category": "Acquisition",
                    "date_text": "January 15, 2024",
                },
                {
                    "title": "Brookfield Reports Record Q4 Revenue",
                    "url": "https://example.com/article3",
                    "company": "Brookfield Asset Management",
                    "is_ma": False,
                    "ma_category": None,
                    "date_text": "January 15, 2024",
                },
            ],
            "BlackRock": [
                {
                    "title": "BlackRock Completes Sale of Infrastructure Portfolio",
                    "url": "https://example.com/article2",
                    "company": "BlackRock",
                    "is_ma": True,
                    "ma_category": "Divestiture",
                    "date_text": "January 14, 2024",
                },
                {
                    "title": "BlackRock Launches New ESG Infrastructure Fund",
                    "url": "https://example.com/article4",
                    "company": "BlackRock",
                    "is_ma": True,
                    "ma_category": "Fund Closing",
                    "date_text": "January 14, 2024",
                },
                {
                    "title": "BlackRock CEO Speaks at Davos 2024",
                    "url": "https://example.com/article5",
                    "company": "BlackRock",
                    "is_ma": False,
                    "ma_category": None,
                    "date_text": "January 13, 2024",
                },
            ],
        },
        "all_press_releases": [],
        "company_stats": [],
    }

    # Generate the HTML
    html = generate_html_report(sample_results)
    print(f"Generated HTML email: {len(html)} characters")

    # Save to a file so you can preview it in a browser
    with open("test_email.html", "w") as f:
        f.write(html)
    print("Saved to test_email.html — open it in a browser to preview!")
