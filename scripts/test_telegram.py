#!/usr/bin/env python3
"""Test Telegram notification setup."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.telegram_notifier import TelegramNotifier

def main():
    print("Testing Telegram setup...")
    notifier = TelegramNotifier()
    
    if notifier.test_connection():
        print("✅ Telegram setup successful!")
        print("Check your Telegram for test message.")
        return 0
    else:
        print("❌ Telegram setup failed!")
        print("Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return 1

if __name__ == "__main__":
    sys.exit(main())
