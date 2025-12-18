#!/bin/bash

# Tatlam Trinity System - Streamlit UI Launcher
# Usage: ./start_ui.sh

echo "🎭 Starting Tatlam Trinity System..."
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected."
    echo "   Consider activating your venv first:"
    echo "   source venv/bin/activate"
    echo ""
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found."
    echo "   Make sure to configure your API keys:"
    echo "   - ANTHROPIC_API_KEY (for Claude Writer)"
    echo "   - GOOGLE_API_KEY (for Gemini Judge)"
    echo "   - LOCAL_BASE_URL (for Local Llama Simulator)"
    echo ""
fi

# Launch Streamlit
streamlit run main_ui.py
