#!/bin/bash

# Clean up any existing X server locks
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

# Start Xvfb (virtual display) in the background
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &

# Wait a moment for Xvfb to start
sleep 3

# Create data directory if it doesn't exist (permissions already set in Dockerfile)
mkdir -p /app/data

# Run the optimized monitor
python3 simple_multi_monitor_optimized.py
