#!/usr/bin/env python3
"""
Account Management Tool
======================

Helper script to manage TikTok accounts for monitoring.

Usage:
    python3 manage_accounts.py add <username> <priority>
    python3 manage_accounts.py remove <username>
    python3 manage_accounts.py list
    python3 manage_accounts.py status <username>
    python3 manage_accounts.py set-priority <username> <priority>
    python3 manage_accounts.py enable <username>
    python3 manage_accounts.py disable <username>
    python3 manage_accounts.py stats

Examples:
    python3 manage_accounts.py add mrbeast high
    python3 manage_accounts.py remove oldaccount
    python3 manage_accounts.py set-priority tiktok medium
    python3 manage_accounts.py list
"""

import csv
import sys
from typing import List, Dict

ACCOUNTS_FILE = "accounts.csv"

def load_accounts() -> List[Dict]:
    """Load accounts from CSV file."""
    accounts = []
    try:
        with open(ACCOUNTS_FILE, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                accounts.append(row)
        return accounts
    except FileNotFoundError:
        # Create new file with headers
        with open(ACCOUNTS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['username', 'status', 'priority'])
        return []

def save_accounts(accounts: List[Dict]):
    """Save accounts to CSV file."""
    with open(ACCOUNTS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        if accounts:
            fieldnames = accounts[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(accounts)
        else:
            writer = csv.writer(csvfile)
            writer.writerow(['username', 'status', 'priority'])

def add_account(username: str, priority: str = 'medium'):
    """Add a new account."""
    if priority not in ['high', 'medium', 'low']:
        print(f"❌ Invalid priority '{priority}'. Use: high, medium, or low")
        return False
    
    accounts = load_accounts()
    
    # Check if account already exists
    for account in accounts:
        if account['username'].lower() == username.lower():
            print(f"❌ Account @{username} already exists")
            return False
    
    # Add new account
    new_account = {
        'username': username,
        'status': 'active',
        'priority': priority
    }
    accounts.append(new_account)
    save_accounts(accounts)
    
    print(f"✅ Added @{username} with {priority} priority")
    return True

def remove_account(username: str):
    """Remove an account."""
    accounts = load_accounts()
    original_count = len(accounts)
    
    accounts = [acc for acc in accounts if acc['username'].lower() != username.lower()]
    
    if len(accounts) == original_count:
        print(f"❌ Account @{username} not found")
        return False
    
    save_accounts(accounts)
    print(f"✅ Removed @{username}")
    return True

def set_priority(username: str, priority: str):
    """Set account priority."""
    if priority not in ['high', 'medium', 'low']:
        print(f"❌ Invalid priority '{priority}'. Use: high, medium, or low")
        return False
    
    accounts = load_accounts()
    found = False
    
    for account in accounts:
        if account['username'].lower() == username.lower():
            account['priority'] = priority
            found = True
            break
    
    if not found:
        print(f"❌ Account @{username} not found")
        return False
    
    save_accounts(accounts)
    print(f"✅ Set @{username} priority to {priority}")
    return True

def set_status(username: str, status: str):
    """Set account status."""
    if status not in ['active', 'inactive']:
        print(f"❌ Invalid status '{status}'. Use: active or inactive")
        return False
    
    accounts = load_accounts()
    found = False
    
    for account in accounts:
        if account['username'].lower() == username.lower():
            account['status'] = status
            found = True
            break
    
    if not found:
        print(f"❌ Account @{username} not found")
        return False
    
    save_accounts(accounts)
    action = "enabled" if status == "active" else "disabled"
    print(f"✅ {action.capitalize()} @{username}")
    return True

def list_accounts():
    """List all accounts."""
    accounts = load_accounts()
    
    if not accounts:
        print("📝 No accounts found")
        return
    
    # Group by status and priority
    active_accounts = [acc for acc in accounts if acc['status'] == 'active']
    inactive_accounts = [acc for acc in accounts if acc['status'] == 'inactive']
    
    print(f"📊 ACCOUNT SUMMARY ({len(accounts)} total)")
    print(f"  • Active: {len(active_accounts)}")
    print(f"  • Inactive: {len(inactive_accounts)}")
    print()
    
    if active_accounts:
        print("🟢 ACTIVE ACCOUNTS:")
        
        # Group by priority
        priority_groups = {}
        for account in active_accounts:
            priority = account['priority']
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(account['username'])
        
        for priority in ['high', 'medium', 'low']:
            if priority in priority_groups:
                usernames = priority_groups[priority]
                intervals = {'high': '5 min', 'medium': '15 min', 'low': '30 min'}
                print(f"  {priority.upper()} ({len(usernames)} accounts, every {intervals[priority]}):")
                for username in sorted(usernames):
                    print(f"    • @{username}")
    
    if inactive_accounts:
        print("\n🔴 INACTIVE ACCOUNTS:")
        for account in inactive_accounts:
            print(f"    • @{account['username']} ({account['priority']})")

def show_account_status(username: str):
    """Show status of a specific account."""
    accounts = load_accounts()
    
    for account in accounts:
        if account['username'].lower() == username.lower():
            status_emoji = "🟢" if account['status'] == 'active' else "🔴"
            priority_emoji = {"high": "🔥", "medium": "⚡", "low": "🐌"}
            
            print(f"{status_emoji} @{account['username']}")
            print(f"  Status: {account['status']}")
            print(f"  Priority: {priority_emoji.get(account['priority'], '')} {account['priority']}")
            
            if account['status'] == 'active':
                intervals = {'high': '5 minutes', 'medium': '15 minutes', 'low': '30 minutes'}
                print(f"  Monitoring: Every {intervals.get(account['priority'], 'unknown')}")
            
            return True
    
    print(f"❌ Account @{username} not found")
    return False

def show_stats():
    """Show account statistics."""
    accounts = load_accounts()
    
    if not accounts:
        print("📝 No accounts found")
        return
    
    # Calculate statistics
    total = len(accounts)
    active = len([acc for acc in accounts if acc['status'] == 'active'])
    inactive = total - active
    
    priority_counts = {}
    for account in accounts:
        if account['status'] == 'active':
            priority = account['priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    print("📊 MONITORING STATISTICS")
    print(f"  Total accounts: {total}")
    print(f"  Active: {active}")
    print(f"  Inactive: {inactive}")
    print()
    
    if priority_counts:
        print("🎯 PRIORITY DISTRIBUTION:")
        for priority in ['high', 'medium', 'low']:
            count = priority_counts.get(priority, 0)
            if count > 0:
                intervals = {'high': '5 min', 'medium': '15 min', 'low': '30 min'}
                emoji = {'high': '🔥', 'medium': '⚡', 'low': '🐌'}
                print(f"  {emoji[priority]} {priority.upper()}: {count} accounts (every {intervals[priority]})")
        
        # Calculate total scrape load
        scrapes_per_hour = (
            priority_counts.get('high', 0) * 12 +  # Every 5 min = 12 times/hour
            priority_counts.get('medium', 0) * 4 + # Every 15 min = 4 times/hour  
            priority_counts.get('low', 0) * 2      # Every 30 min = 2 times/hour
        )
        
        print()
        print(f"📈 ESTIMATED LOAD:")
        print(f"  Scrapes per hour: ~{scrapes_per_hour}")
        print(f"  Scrapes per day: ~{scrapes_per_hour * 24:,}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("Usage: python3 manage_accounts.py add <username> [priority]")
            return
        username = sys.argv[2]
        priority = sys.argv[3] if len(sys.argv) > 3 else 'medium'
        add_account(username, priority)
    
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("Usage: python3 manage_accounts.py remove <username>")
            return
        username = sys.argv[2]
        remove_account(username)
    
    elif command == 'list':
        list_accounts()
    
    elif command == 'status':
        if len(sys.argv) < 3:
            print("Usage: python3 manage_accounts.py status <username>")
            return
        username = sys.argv[2]
        show_account_status(username)
    
    elif command == 'set-priority':
        if len(sys.argv) < 4:
            print("Usage: python3 manage_accounts.py set-priority <username> <priority>")
            return
        username = sys.argv[2]
        priority = sys.argv[3]
        set_priority(username, priority)
    
    elif command == 'enable':
        if len(sys.argv) < 3:
            print("Usage: python3 manage_accounts.py enable <username>")
            return
        username = sys.argv[2]
        set_status(username, 'active')
    
    elif command == 'disable':
        if len(sys.argv) < 3:
            print("Usage: python3 manage_accounts.py disable <username>")
            return
        username = sys.argv[2]
        set_status(username, 'inactive')
    
    elif command == 'stats':
        show_stats()
    
    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)

if __name__ == "__main__":
    main() 