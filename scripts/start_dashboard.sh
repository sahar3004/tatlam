#!/bin/bash
# start_dashboard.sh - Launch the TATLAM Operations Dashboard
#
# Real-time monitoring of the scenario database with Textual TUI
# Features: Auto-refreshing scenario table, live log viewer, statistics

set -e

echo "========================================"
echo "  TATLAM Operations Dashboard"
echo "  Real-time Database Monitor"
echo "========================================"
echo ""

# Check if textual is installed
if ! python3 -c "import textual" 2>/dev/null; then
    echo "❌ Textual not installed. Installing..."
    pip3 install textual || {
        echo "❌ Failed to install textual"
        echo "   Try manually: pip3 install textual"
        exit 1
    }
fi

# Launch the dashboard
echo "🚀 Starting dashboard..."
echo "   Press 'q' to quit"
echo "   Press 'r' to refresh"
echo ""

python3 -m tatlam.cli.dashboard
