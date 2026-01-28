#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# cron_run.sh - Cron Wrapper for Infrastructure M&A Tracker
# ═══════════════════════════════════════════════════════════════════
#
# This script is designed to be called by cron. It handles:
#   1. Setting up the correct working directory
#   2. Activating the Python virtual environment
#   3. Running the daily scanner
#   4. Logging output with timestamps
#
# CRON SETUP:
#   Run: crontab -e
#   Add: 0 6 * * * /home/user/InfraMAScraper/cron_run.sh
#
# This runs the tracker every day at 6:00 AM.
#
# ═══════════════════════════════════════════════════════════════════

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR" || exit 1

# Create logs directory if it doesn't exist
mkdir -p logs

# Log file with date
LOG_FILE="logs/cron.log"

# Add timestamp to log
echo "" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "  Cron job started at: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"

# Activate the virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found at $SCRIPT_DIR/venv" >> "$LOG_FILE"
    exit 1
fi

# Run the daily scanner and log output
python run_daily.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Log completion
echo "" >> "$LOG_FILE"
echo "  Cron job finished at: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "  Exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"

exit $EXIT_CODE
