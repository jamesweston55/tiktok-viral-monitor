#!/usr/bin/env python3
"""
Settings Manager for TikTok Viral Monitor
=========================================

Easy command-line tool to view and modify monitoring settings.

Usage:
    python3 settings.py                    # Show current settings
    python3 settings.py --interval 10      # Set monitoring interval to 10 minutes
    python3 settings.py --threshold 200    # Set viral threshold to 200 views
    python3 settings.py --delay 15         # Set scrape delay to 15 seconds
    python3 settings.py --concurrent 5     # Set max concurrent scrapes to 5
    python3 settings.py --preset aggressive # Use aggressive preset
"""

import argparse
import re
import sys
from pathlib import Path

def read_config():
    """Read current configuration from config.py"""
    config_path = Path("config.py")
    if not config_path.exists():
        print("❌ config.py not found!")
        return None
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    return content

def write_config(content):
    """Write updated configuration to config.py"""
    with open("config.py", 'w') as f:
        f.write(content)

def update_setting(content, setting_name, new_value, comment=""):
    """Update a setting in the config content"""
    # Pattern to match the setting line
    pattern = rf'^{setting_name}\s*=\s*.*$'
    replacement = f'{setting_name} = {new_value}'
    if comment:
        replacement += f'  # {comment}'
    
    updated_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if updated_content == content:
        print(f"⚠️  Setting {setting_name} not found in config.py")
        return content
    
    return updated_content

def show_current_settings():
    """Display current settings in a nice format"""
    try:
        from config import (
            MONITORING_INTERVAL, VIRAL_THRESHOLD, SCRAPE_DELAY_SECONDS,
            MAX_CONCURRENT_SCRAPES, BATCH_DELAY_SECONDS, MAX_VIDEOS_TO_CHECK,
            ACCOUNTS_FILE, DATABASE_FILE
        )
        
        print("🔧 Current TikTok Viral Monitor Settings")
        print("=" * 60)
        print()
        print("⏰ TIMING SETTINGS:")
        print(f"  📊 Monitoring Interval: {MONITORING_INTERVAL // 60} minutes ({MONITORING_INTERVAL} seconds)")
        print(f"  ⚡ Scrape Delay: {SCRAPE_DELAY_SECONDS} seconds")
        print(f"  🔄 Batch Delay: {BATCH_DELAY_SECONDS} seconds")
        print()
        print("🎯 DETECTION SETTINGS:")
        print(f"  🔥 Viral Threshold: {VIRAL_THRESHOLD} views")
        print(f"  📱 Videos per Account: {MAX_VIDEOS_TO_CHECK}")
        print()
        print("⚡ PERFORMANCE SETTINGS:")
        print(f"  🔀 Max Concurrent Scrapes: {MAX_CONCURRENT_SCRAPES}")
        print()
        print("📁 FILES:")
        print(f"  📋 Accounts File: {ACCOUNTS_FILE}")
        print(f"  💾 Database File: {DATABASE_FILE}")
        print()
        print("=" * 60)
        
        # Performance analysis
        total_accounts = 0
        try:
            import csv
            with open(ACCOUNTS_FILE, 'r') as f:
                total_accounts = len(list(csv.DictReader(f)))
        except:
            pass
        
        if total_accounts > 0:
            cycle_time = (total_accounts // MAX_CONCURRENT_SCRAPES) * BATCH_DELAY_SECONDS
            cycle_time += (total_accounts * SCRAPE_DELAY_SECONDS)
            
            print("📈 PERFORMANCE ESTIMATE:")
            print(f"  👥 Total Accounts: {total_accounts}")
            print(f"  ⏱️  Est. Cycle Time: ~{cycle_time // 60} minutes")
            print(f"  📊 Cycles per Hour: ~{3600 // MONITORING_INTERVAL}")
            
            if cycle_time > MONITORING_INTERVAL:
                print("  ⚠️  WARNING: Cycle time exceeds monitoring interval!")
                print("  💡 Consider: Increasing concurrent scrapes or monitoring interval")
        
    except ImportError as e:
        print(f"❌ Error importing config: {e}")

def apply_preset(preset_name):
    """Apply a preset configuration"""
    presets = {
        'aggressive': {
            'MONITORING_INTERVAL': '2 * 60',
            'SCRAPE_DELAY_SECONDS': '5',
            'VIRAL_THRESHOLD': '50',
            'MAX_CONCURRENT_SCRAPES': '5'
        },
        'conservative': {
            'MONITORING_INTERVAL': '15 * 60',
            'SCRAPE_DELAY_SECONDS': '20',
            'VIRAL_THRESHOLD': '500',
            'MAX_CONCURRENT_SCRAPES': '2'
        },
        'high_volume': {
            'MONITORING_INTERVAL': '10 * 60',
            'SCRAPE_DELAY_SECONDS': '5',
            'VIRAL_THRESHOLD': '200',
            'MAX_CONCURRENT_SCRAPES': '6'
        }
    }
    
    if preset_name not in presets:
        print(f"❌ Unknown preset: {preset_name}")
        print(f"Available presets: {', '.join(presets.keys())}")
        return False
    
    content = read_config()
    if not content:
        return False
    
    preset = presets[preset_name]
    print(f"🎛️  Applying {preset_name} preset...")
    
    for setting, value in preset.items():
        content = update_setting(content, setting, value, f"{preset_name} preset")
        print(f"  ✅ Updated {setting} = {value}")
    
    write_config(content)
    print(f"✅ {preset_name.title()} preset applied successfully!")
    return True

def main():
    parser = argparse.ArgumentParser(description="Manage TikTok Viral Monitor Settings")
    parser.add_argument('--interval', type=int, help='Monitoring interval in minutes')
    parser.add_argument('--threshold', type=int, help='Viral threshold in views')
    parser.add_argument('--delay', type=int, help='Scrape delay in seconds')
    parser.add_argument('--concurrent', type=int, help='Max concurrent scrapes')
    parser.add_argument('--preset', choices=['aggressive', 'conservative', 'high_volume'], 
                       help='Apply a preset configuration')
    parser.add_argument('--batch-delay', type=int, help='Batch delay in seconds')
    parser.add_argument('--videos', type=int, help='Max videos to check per account')
    
    args = parser.parse_args()
    
    # If no arguments, just show current settings
    if len(sys.argv) == 1:
        show_current_settings()
        return
    
    # Apply preset if specified
    if args.preset:
        if apply_preset(args.preset):
            print("\n" + "="*50)
            show_current_settings()
        return
    
    # Update individual settings
    content = read_config()
    if not content:
        return
    
    updated = False
    
    if args.interval:
        content = update_setting(content, 'MONITORING_INTERVAL', f'{args.interval} * 60', f'{args.interval} minutes')
        print(f"✅ Updated monitoring interval to {args.interval} minutes")
        updated = True
    
    if args.threshold:
        content = update_setting(content, 'VIRAL_THRESHOLD', str(args.threshold), f'{args.threshold} views')
        print(f"✅ Updated viral threshold to {args.threshold} views")
        updated = True
    
    if args.delay:
        content = update_setting(content, 'SCRAPE_DELAY_SECONDS', str(args.delay), f'{args.delay} seconds')
        print(f"✅ Updated scrape delay to {args.delay} seconds")
        updated = True
    
    if args.concurrent:
        content = update_setting(content, 'MAX_CONCURRENT_SCRAPES', str(args.concurrent), f'{args.concurrent} concurrent')
        print(f"✅ Updated max concurrent scrapes to {args.concurrent}")
        updated = True
    
    if args.batch_delay:
        content = update_setting(content, 'BATCH_DELAY_SECONDS', str(args.batch_delay), f'{args.batch_delay} seconds')
        print(f"✅ Updated batch delay to {args.batch_delay} seconds")
        updated = True
    
    if args.videos:
        content = update_setting(content, 'MAX_VIDEOS_TO_CHECK', str(args.videos), f'{args.videos} videos')
        print(f"✅ Updated max videos per account to {args.videos}")
        updated = True
    
    if updated:
        write_config(content)
        print("\n" + "="*50)
        print("📝 Settings updated! New configuration:")
        print("="*50)
        show_current_settings()
        print("\n💡 Restart the monitor for changes to take effect.")

if __name__ == "__main__":
    main() 