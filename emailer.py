"""
emailer.py - HTML Email Generator and Sender
==============================================
This module creates a professional-looking HTML email report of M&A findings
and sends it via Gmail's SMTP server.

HOW EMAIL SENDING WORKS (for beginners):
- SMTP = "Simple Mail Transfer Protocol" — the standard way computers send email
- Gmail lets you send email through their servers if you have an "App Password"
- TLS = encryption that protects your email credentials during transmission
- We connect to smtp.gmail.com on port 587, authenticate, and send the email

HOW THE HTML EMAIL WORKS:
- Email clients (Gmail, Outlook, etc.) can display HTML emails
- We build an HTML page with inline CSS (email clients don't support external CSS)
- The email groups M&A findings by category with a professional design
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
}

# Colors for each M&A category (makes the email visually scannable)
CATEGORY_COLORS = {
    "Acquisition": "#e53e3e",       # Red — big deal, attention-grabbing
    "Divestiture": "#dd6b20",       # Orange
    "Fund Closing": "#38a169",      # Green — positive milestone
    "Investment": "#3182ce",        # Blue — standard activity
    "Partnership/JV": "#805ad5",    # Purple
    "IPO/Exit": "#d69e2e",         # Gold — milestone event
    "Other M&A": "#718096",        # Gray — catch-all
}


def generate_html_report(analysis_results):
    """
    Generate a professional HTML email from the analysis results.

    This builds a complete HTML page with inline CSS styling that looks good
    in email clients like Gmail, Outlook, and Apple Mail.

    Args:
        analysis_results (dict): Output from analyzer.analyze_results().

    Returns:
        str: Complete HTML string ready to be sent as an email.
    """
    summary = analysis_results["summary"]
    ma_by_category = analysis_results.get("ma_by_category", {})
    ma_items = analysis_results.get("ma_items", [])
    scan_date = datetime.now().strftime("%B %d, %Y")
    scan_time = datetime.now().strftime("%I:%M %p")

    # ── Build the M&A findings section ──
    # Group items by category and create HTML for each group
    ma_sections_html = ""

    if ma_items:
        for category in ["Acquisition", "Divestiture", "Fund Closing",
                         "Investment", "Partnership/JV", "IPO/Exit", "Other M&A"]:
            items = ma_by_category.get(category, [])
            if not items:
                continue

            cat_color = CATEGORY_COLORS.get(category, "#718096")

            # Start the category section
            ma_sections_html += f"""
            <div style="margin-bottom: 24px;">
                <div style="
                    background-color: {cat_color};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 6px 6px 0 0;
                    font-size: 14px;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                ">
                    {category.upper()} ({len(items)})
                </div>
                <div style="
                    border: 1px solid {COLORS['border']};
                    border-top: none;
                    border-radius: 0 0 6px 6px;
                    overflow: hidden;
                ">
            """

            # Add each item in this category
            for i, item in enumerate(items):
                # Alternate row colors for readability
                row_bg = "#ffffff" if i % 2 == 0 else "#f7fafc"
                date_str = item.get("date_text", "Date unknown") or "Date unknown"

                ma_sections_html += f"""
                    <div style="
                        padding: 12px 16px;
                        background-color: {row_bg};
                        border-bottom: 1px solid {COLORS['border']};
                    ">
                        <div style="font-size: 14px; color: {COLORS['text_primary']}; margin-bottom: 4px;">
                            <strong>{item.get('company', 'Unknown')}</strong>
                        </div>
                        <div style="font-size: 13px; margin-bottom: 4px;">
                            <a href="{item.get('url', '#')}"
                               style="color: {COLORS['accent_blue']}; text-decoration: none;"
                               target="_blank">
                                {item.get('title', 'No title')}
                            </a>
                        </div>
                        <div style="font-size: 12px; color: {COLORS['text_secondary']};">
                            {date_str}
                        </div>
                    </div>
                """

            ma_sections_html += """
                </div>
            </div>
            """
    else:
        # No M&A items found
        ma_sections_html = f"""
        <div style="
            text-align: center;
            padding: 40px 20px;
            color: {COLORS['text_secondary']};
            font-size: 16px;
        ">
            <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
            <div>No M&A-related press releases found in the last
                 {analysis_results.get('days_lookback', 2)} days.</div>
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
        health_color = "#d69e2e"  # Yellow/gold
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
                    Infrastructure M&amp;A Tracker
                </h1>
                <p style="margin: 8px 0 0; font-size: 14px; opacity: 0.85;">
                    Daily Press Release Scan — {scan_date}
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
                        <!-- M&A Items Found -->
                        <td style="text-align: center; padding: 12px; width: 25%;">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['header_bg']};">
                                {summary['total_ma_items']}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                M&amp;A Items
                            </div>
                        </td>
                        <!-- Total Press Releases -->
                        <td style="text-align: center; padding: 12px; width: 25%; border-left: 1px solid {COLORS['border']};">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['header_bg']};">
                                {summary['total_press_releases']}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                Press Releases
                            </div>
                        </td>
                        <!-- Sites Scanned -->
                        <td style="text-align: center; padding: 12px; width: 25%; border-left: 1px solid {COLORS['border']};">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['accent_green']};">
                                {summary['successful_scrapes']}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                Sites OK
                            </div>
                        </td>
                        <!-- Failed Sites -->
                        <td style="text-align: center; padding: 12px; width: 25%; border-left: 1px solid {COLORS['border']};">
                            <div style="font-size: 28px; font-weight: 700; color: {COLORS['accent_red']};">
                                {summary['failed_scrapes']}
                            </div>
                            <div style="font-size: 11px; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px;">
                                Failed
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

            <!-- ═══════ M&A FINDINGS ═══════ -->
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
                    M&amp;A Activity Detected
                </h2>

                {ma_sections_html}
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
                    Infrastructure M&amp;A Tracker — Automated Daily Scan
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

    # Build a descriptive subject line
    summary = analysis_results.get("summary", {})
    ma_count = summary.get("total_ma_items", 0)
    date_str = datetime.now().strftime("%b %d, %Y")

    if ma_count > 0:
        subject = f"[Infra M&A] {ma_count} M&A Items Found — {date_str}"
    else:
        subject = f"[Infra M&A] Daily Scan Complete — No M&A Activity — {date_str}"

    print(f"\n  Sending email report...")
    print(f"  From: {sender_email}")
    print(f"  To:   {recipient_email}")
    print(f"  Subject: {subject}")

    try:
        # Create the email message
        # MIMEMultipart allows us to send both plain text and HTML versions
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Infra M&A Tracker <{sender_email}>"
        msg["To"] = recipient_email

        # Plain text version (fallback for email clients that don't support HTML)
        plain_text = (
            f"Infrastructure M&A Daily Report - {date_str}\n\n"
            f"M&A Items Found: {ma_count}\n"
            f"Total Press Releases: {summary.get('total_press_releases', 0)}\n"
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
        "days_lookback": 2,
        "summary": {
            "total_companies": 97,
            "successful_scrapes": 85,
            "failed_scrapes": 12,
            "total_press_releases": 42,
            "total_ma_items": 7,
        },
        "ma_items": [
            {
                "title": "Brookfield Acquires European Data Center Platform",
                "url": "https://example.com/article1",
                "company": "Brookfield Asset Management",
                "ma_category": "Acquisition",
                "date_text": "January 15, 2024",
            },
            {
                "title": "BlackRock Completes Sale of Infrastructure Portfolio",
                "url": "https://example.com/article2",
                "company": "BlackRock",
                "ma_category": "Divestiture",
                "date_text": "January 14, 2024",
            },
        ],
        "ma_by_category": {
            "Acquisition": [
                {
                    "title": "Brookfield Acquires European Data Center Platform",
                    "url": "https://example.com/article1",
                    "company": "Brookfield Asset Management",
                    "date_text": "January 15, 2024",
                },
            ],
            "Divestiture": [
                {
                    "title": "BlackRock Completes Sale of Infrastructure Portfolio",
                    "url": "https://example.com/article2",
                    "company": "BlackRock",
                    "date_text": "January 14, 2024",
                },
            ],
        },
    }

    # Generate the HTML
    html = generate_html_report(sample_results)
    print(f"Generated HTML email: {len(html)} characters")

    # Save to a file so you can preview it in a browser
    with open("test_email.html", "w") as f:
        f.write(html)
    print("Saved to test_email.html — open it in a browser to preview!")
