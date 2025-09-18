#!/bin/bash

# Bulletproof TikTok Monitor Startup Script
# =========================================

echo "🚀 Starting Bulletproof TikTok Monitor..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if required files exist
if [ ! -f "accounts.csv" ]; then
    echo "❌ Error: accounts.csv not found"
    exit 1
fi

if [ ! -f "monitor_bulletproof.py" ]; then
    echo "❌ Error: monitor_bulletproof.py not found"
    exit 1
fi

# Create required directories
mkdir -p data logs

# Set environment variables if not already set
export PYTHONUNBUFFERED=1

# Start the monitor
echo "🎯 Launching bulletproof monitor..."
python3 monitor_bulletproof.py 