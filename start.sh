#!/bin/bash

# Start Xvfb (virtual display) in the background
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &

# Wait a moment for Xvfb to start
sleep 2

# Run the optimized monitor
python3 simple_multi_monitor_optimized.py
