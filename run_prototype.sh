#!/bin/bash
# InsureCo AI Data Platform — Prototype launcher
set -e

cd "$(dirname "$0")"

echo "========================================================"
echo " Corporate Insurance Platform · AI Data Platform"
echo " Prototype launcher"
echo "========================================================"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found" && exit 1
fi

# Install deps if needed
echo ""
echo "Installing dependencies..."
pip install -q -r requirements_prototype.txt

# Check ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "⚠️  WARNING: ANTHROPIC_API_KEY not set."
    echo "   The Agent Chat tab will not work without it."
    echo "   Set it with: export ANTHROPIC_API_KEY=sk-ant-..."
    echo ""
fi

echo ""
echo "Starting Streamlit dashboard..."
echo "Open: http://localhost:8501"
echo ""

streamlit run app/dashboard.py \
    --server.port 8501 \
    --server.headless true \
    --theme.primaryColor "#c8102e" \
    --theme.backgroundColor "#ffffff" \
    --theme.secondaryBackgroundColor "#f8f9fa" \
    --theme.textColor "#1a1a1a"
