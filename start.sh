#!/bin/bash

# MediaCrawler Startup Script
# This script handles dependency sync and starts the API server.
# test

echo "========================================"
echo "   🔥 MediaCrawler Startup Script 🔥   "
echo "========================================"

# Check for uv
if ! command -v uv &> /dev/null
then
    echo "❌ Error: 'uv' is not installed."
    echo "Please install it via: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies
echo "📦 [1/2] Syncing dependencies..."
uv sync

# Run the API server
echo "🌐 [2/2] Starting WebUI API server..."
echo "👉 Access the dashboard at: http://localhost:8080"
echo "----------------------------------------"

uv run uvicorn api.main:app --port 8080 --host 0.0.0.0 --no-access-log
