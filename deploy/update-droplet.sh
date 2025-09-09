#!/bin/bash
# Update Script for DigitalOcean Droplet

set -e

echo "🔄 Updating TikTok Monitor on DigitalOcean..."

# Navigate to the project directory
cd /root/tiktok-viral-monitor

# Stop the current containers
echo "⏹️  Stopping current containers..."
docker-compose -f docker-compose.optimized.yml down

# Pull the latest changes
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Rebuild the optimized container
echo "🏗️  Rebuilding optimized container..."
docker-compose -f docker-compose.optimized.yml build --no-cache

# Start the updated containers
echo "🚀 Starting updated containers..."
docker-compose -f docker-compose.optimized.yml up -d

# Restart resource monitoring
echo "🔍 Restarting resource monitoring..."
systemctl restart tiktok-resource-monitor

echo "✅ Update completed successfully!"
echo ""
echo "📊 Container Status:"
docker-compose -f docker-compose.optimized.yml ps

echo ""
echo "📝 Recent logs:"
docker-compose -f docker-compose.optimized.yml logs --tail=20
