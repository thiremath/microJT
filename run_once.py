#!/usr/bin/env python3
"""
Single-run tracker for GitHub Actions
Runs once and exits - perfect for scheduled workflows
"""

import os
import sys

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tracker import (
    load_config, check_website, send_telegram_alert,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)

if __name__ == "__main__":
    print("🚀 Starting Single-Run Website Tracker (GitHub Actions Mode)...")
    print(f"📡 Telegram Bot: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print("-" * 50)
    
    # Load configuration
    CONFIG = load_config()
    
    # Get enabled websites
    websites = [w for w in CONFIG.get('websites', []) if w.get('enabled', True)]
    
    if not websites:
        print("❌ No enabled websites found in configuration!")
        sys.exit(1)
    
    print(f"\n📋 Checking {len(websites)} website(s):")
    for website in websites:
        print(f"  • {website['name']}")
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Check all websites once
    errors = []
    for website in websites:
        try:
            check_website(website)
        except Exception as e:
            error_msg = f"Error checking {website['name']}: {str(e)}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
    
    # Report completion
    if errors:
        print(f"\n⚠️ Completed with {len(errors)} error(s)")
        for error in errors:
            print(f"  • {error}")
        sys.exit(1)
    else:
        print(f"\n✅ Successfully checked all {len(websites)} websites")
        sys.exit(0)
