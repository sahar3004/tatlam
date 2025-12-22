#!/bin/bash
# TATLAM System Launcher - Hebrew UI with Hybrid Engine
# For Apple M4 Pro

echo "========================================"
echo "🇮🇱 TATLAM - מערכת תתל״מ - מרכז שליטה"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if llama-server is running
if ! pgrep -x "llama-server" > /dev/null; then
    echo "🧠 Starting Local LLM Engine (Qwen 2.5 32B)..."
    ./run_engine.sh
    echo "⏳ Waiting for model initialization (10 seconds)..."
    sleep 10
else
    echo "✅ Local LLM Engine already running"
fi

# Check model health
echo "🔍 Checking model health..."
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Model is healthy and ready"
else
    echo "⚠️  Model may still be loading. Check llama.log for status."
fi

echo ""
echo "🚀 Starting Streamlit UI..."
echo "   Open: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the system"
echo "========================================"
echo ""

# Run Streamlit
streamlit run main.py --server.port 8501 --server.headless true
