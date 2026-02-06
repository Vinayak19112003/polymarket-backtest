#!/usr/bin/env python3
"""Test dynamic market finder."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.market_finder import DynamicMarketFinder

def main():
    print("=" * 80)
    print("TESTING DYNAMIC MARKET FINDER")
    print("=" * 80)
    
    finder = DynamicMarketFinder()
    
    # Test 1: Find current market
    print("\n1. Finding current 15m market...")
    market = finder.find_fifteen_minute_market()
    
    if market:
        print("Market found!")
        info = finder.get_market_info()
        print(f"\nMarket Info:")
        print(f"  Question: {info['question']}")
        print(f"  Time Remaining: {info['time_remaining']/60:.1f} minutes")
        print(f"  YES Token: {info['tokens'].get('Yes', 'N/A')[:30]}...")
        print(f"  NO Token: {info['tokens'].get('No', 'N/A')[:30]}...")
    else:
        print("No market found")
        print("Note: 15m markets may not always be available")
        print("Showing all BTC markets instead:")
        
        all_markets = finder.search_markets()
        btc_markets = finder.filter_btc_markets(all_markets)
        
        for i, m in enumerate(btc_markets[:5], 1):
            print(f"\n{i}. {m.get('question')}")
            print(f"   Ends: {m.get('end_date_iso')}")
    
    # Test 2: Get token ID
    print("\n2. Testing token ID retrieval...")
    token_id = finder.get_current_token_id("Yes")
    
    if token_id:
        print(f"YES Token ID: {token_id[:40]}...")
    else:
        print("No token ID available")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
