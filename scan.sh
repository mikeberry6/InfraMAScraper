#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# scan.sh - One-Command Runner for Infrastructure M&A Tracker
# ═══════════════════════════════════════════════════════════════════
#
# This script makes it easy to run the tracker with a single command.
# It handles:
#   1. Changing to the correct directory
#   2. Activating the Python virtual environment (if it exists)
#   3. Running the daily scanner with any arguments you pass
#
# USAGE:
#   ./scan.sh                    # Full scan + email
#   ./scan.sh --test             # Test mode (5 sites) + email
#   ./scan.sh --test --no-email  # Test mode, no email
#   ./scan.sh --days 7           # Look back 7 days
#
# ═══════════════════════════════════════════════════════════════════

# Get the directory where this script lives
# This way, you can run the script from anywhere and it still works
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR" || exit 1

# Activate the virtual environment if it exists
# A virtual environment keeps our Python packages separate from the system
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: No virtual environment found. Using system Python."
    echo "Run 'python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt' to set up."
fi

# Run the daily scanner, passing along any arguments you gave this script
# "$@" means "all the arguments passed to this script"
echo "Starting Infrastructure M&A Tracker..."
echo ""
python run_daily.py "$@"

# Capture the exit code (0 = success, anything else = error)
EXIT_CODE=$?

# If we activated a venv, deactivate it (clean up)
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null
fi

exit $EXIT_CODE
