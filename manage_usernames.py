#!/usr/bin/env python3
"""
Simple Username Management Tool
==============================

Helper script to manage TikTok usernames for monitoring.

Usage:
    python3 manage_usernames.py add <username>
    python3 manage_usernames.py remove <username>
    python3 manage_usernames.py list
    python3 manage_usernames.py count

Examples:
    python3 manage_usernames.py add mrbeast
    python3 manage_usernames.py remove oldaccount  
    python3 manage_usernames.py list
"""

import csv
import sys
from typing import List

ACCOUNTS_FILE = "accounts.csv"

def load_usernames() -> List[str]:
    """Load usernames from CSV file."""
    usernames = []
    try:
        with open(ACCOUNTS_FILE, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                username = row['username'].strip()
                if username:
                    usernames.append(username)
        return usernames
    except FileNotFoundError:
        # Create new file with headers
        with open(ACCOUNTS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['username'])
        return []

def save_usernames(usernames: List[str]):
    """Save usernames to CSV file."""
    with open(ACCOUNTS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['username'])
        for username in usernames:
            writer.writerow([username])

def add_username(username: str):
    """Add a new username."""
    usernames = load_usernames()
    
    # Check if username already exists (case insensitive)
    for existing in usernames:
        if existing.lower() == username.lower():
            print(f"❌ Username @{username} already exists")
            return False
    
    # Add new username
    usernames.append(username)
    save_usernames(usernames)
    
    print(f"✅ Added @{username}")
    return True

def remove_username(username: str):
    """Remove a username."""
    usernames = load_usernames()
    original_count = len(usernames)
    
    # Remove username (case insensitive)
    usernames = [u for u in usernames if u.lower() != username.lower()]
    
    if len(usernames) == original_count:
        print(f"❌ Username @{username} not found")
        return False
    
    save_usernames(usernames)
    print(f"✅ Removed @{username}")
    return True

def list_usernames():
    """List all usernames."""
    usernames = load_usernames()
    
    if not usernames:
        print("📝 No usernames found")
        return
    
    print(f"📊 MONITORING LIST ({len(usernames)} accounts)")
    print("=" * 50)
    
    for i, username in enumerate(sorted(usernames), 1):
        print(f"{i:2d}. @{username}")
    
    print("=" * 50)
    print(f"Total: {len(usernames)} accounts")

def count_usernames():
    """Show username count."""
    usernames = load_usernames()
    print(f"📊 Total accounts: {len(usernames)}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("Usage: python3 manage_usernames.py add <username>")
            return
        username = sys.argv[2]
        add_username(username)
    
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("Usage: python3 manage_usernames.py remove <username>")
            return
        username = sys.argv[2]
        remove_username(username)
    
    elif command == 'list':
        list_usernames()
    
    elif command == 'count':
        count_usernames()
    
    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)

if __name__ == "__main__":
    main() 