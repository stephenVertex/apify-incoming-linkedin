#!/bin/bash
# Run YouTube data collection scripts in sequence
# 1. Fetch new videos from monitored channels
# 2. Update statistics for existing videos

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================================================="
echo "YouTube Data Collection - $(date)"
echo "==================================================================="

echo ""
echo "Step 1: Fetching new videos..."
echo "-------------------------------------------------------------------"
/opt/homebrew/bin/uv run python3 youtube_fetcher.py

echo ""
echo "Step 2: Updating statistics for existing videos..."
echo "-------------------------------------------------------------------"
/opt/homebrew/bin/uv run python3 update_youtube_stats.py

echo ""
echo "==================================================================="
echo "YouTube data collection completed - $(date)"
echo "==================================================================="
