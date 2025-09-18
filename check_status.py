#!/usr/bin/env python3
"""
Bulletproof Monitor Status Check
===============================
Comprehensive status verification script
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

def check_files():
    """Check if all required files exist"""
    print("📁 Checking required files...")
    
    required_files = [
        'accounts.csv',
        'monitor_bulletproof.py',
        'main.py'
    ]
    
    required_dirs = [
        'data',
        'logs'
    ]
    
    all_good = True
    
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_good = False
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ - MISSING")
            all_good = False
    
    return all_good

def check_database():
    """Check database status"""
    print("\n💾 Checking database...")
    
    db_path = "data/monitor.db"
    if not Path(db_path).exists():
        print(f"  ❌ Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['video_data', 'monitoring_stats']
        for table in expected_tables:
            if table in tables:
                print(f"  ✅ Table: {table}")
            else:
                print(f"  ❌ Table missing: {table}")
                return False
        
        # Check data
        cursor.execute("SELECT COUNT(*) FROM video_data")
        video_count = cursor.fetchone()[0]
        print(f"  📊 Total videos: {video_count}")
        
        cursor.execute("SELECT COUNT(*) FROM monitoring_stats")
        stats_count = cursor.fetchone()[0]
        print(f"  📊 Monitored accounts: {stats_count}")
        
        # Check recent activity
        cursor.execute("""
            SELECT username, last_scraped, videos_found, error_count 
            FROM monitoring_stats 
            ORDER BY last_scraped DESC
        """)
        
        print("\n  📈 Recent activity:")
        for row in cursor.fetchall():
            username, last_scraped, videos_found, error_count = row
            status = "✅" if error_count == 0 else f"⚠️ ({error_count} errors)"
            print(f"    {status} @{username}: {videos_found} videos, last: {last_scraped}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def check_process():
    """Check if monitor process is running"""
    print("\n🔍 Checking process status...")
    
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'monitor_bulletproof.py' in result.stdout:
            print("  ✅ Bulletproof monitor is running")
            
            # Extract process info
            lines = result.stdout.split('\n')
            for line in lines:
                if 'monitor_bulletproof.py' in line:
                    parts = line.split()
                    if len(parts) > 10:
                        pid = parts[1]
                        cpu = parts[2]
                        mem = parts[3]
                        print(f"    PID: {pid}, CPU: {cpu}%, Memory: {mem}%")
            return True
        else:
            print("  ❌ Monitor process not running")
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking process: {e}")
        return False

def check_logs():
    """Check log files"""
    print("\n📋 Checking logs...")
    
    log_file = "logs/monitor.log"
    if not Path(log_file).exists():
        print(f"  ❌ Log file not found: {log_file}")
        return False
    
    try:
        # Get file size
        size = Path(log_file).stat().st_size
        print(f"  📊 Log file size: {size:,} bytes")
        
        # Check recent entries
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        recent_lines = lines[-10:]
        print(f"  📊 Total log entries: {len(lines)}")
        
        # Count different log levels in recent entries
        errors = sum(1 for line in recent_lines if '[ERROR]' in line or '❌' in line)
        warnings = sum(1 for line in recent_lines if '[WARNING]' in line or '⚠️' in line)
        successes = sum(1 for line in recent_lines if '✅' in line)
        
        print(f"  📊 Recent activity: {successes} successes, {warnings} warnings, {errors} errors")
        
        if errors > 0:
            print("  ⚠️ Recent errors detected")
            return False
        else:
            print("  ✅ No recent errors")
            return True
            
    except Exception as e:
        print(f"  ❌ Error checking logs: {e}")
        return False

def check_accounts():
    """Check accounts file"""
    print("\n👥 Checking accounts...")
    
    if not Path('accounts.csv').exists():
        print("  ❌ accounts.csv not found")
        return False
    
    try:
        import csv
        with open('accounts.csv', 'r') as f:
            reader = csv.DictReader(f)
            accounts = list(reader)
        
        print(f"  📊 Total accounts: {len(accounts)}")
        
        for account in accounts:
            username = account.get('username', '').strip()
            if username:
                print(f"    ✅ @{username}")
            else:
                print(f"    ❌ Empty username")
        
        return len(accounts) > 0
        
    except Exception as e:
        print(f"  ❌ Error reading accounts: {e}")
        return False

def main():
    """Main status check"""
    print("🚀 Bulletproof TikTok Monitor - Status Check")
    print("=" * 50)
    
    checks = [
        ("Files", check_files),
        ("Accounts", check_accounts),
        ("Database", check_database),
        ("Process", check_process),
        ("Logs", check_logs)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error in {name} check: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("✅ Bulletproof TikTok Monitor is running perfectly!")
        print("📊 Zero errors detected - 100% functional!")
    else:
        print("⚠️ Some issues detected")
        print("❌ Please check the failed components above")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 