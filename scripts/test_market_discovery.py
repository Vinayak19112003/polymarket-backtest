#!/usr/bin/env python3
"""
Diagnostic script to test Polymarket market discovery.
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.join(__file__, "../../"))))
# Adjust path to find src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bot.market_finder import DynamicMarketFinder

def main():
    print("=" * 70)
    print("POLYMARKET MARKET DISCOVERY TEST (V2)")
    print("=" * 70)
    
    finder = DynamicMarketFinder()
    
    # Test 1: Raw API Query (Limit 5)
    print("\n### TEST 1: Raw API Query (Limit 5) ###")
    all_markets = finder.search_markets(active_only=True)
    print(f"Total markets returned: {len(all_markets)}")
    
    if all_markets:
        print("\nFirst 3 markets:")
        for i, market in enumerate(all_markets[:3]):
            print(f"\n{i+1}. {market.get('question', 'N/A')}")
            print(f"   Slug: {market.get('slug', 'N/A')}")
            print(f"   End: {market.get('end_date_iso', 'N/A')}")
    
    # Test 2: 15M tag search (internal method uses tag_id=102467)
    print("\n### TEST 2: 15M Tag Search (ID 102467) ###")
    markets_15m = finder.search_15m_markets_directly()
    print(f"Markets with 15M tag: {len(markets_15m)}")
    
    if markets_15m:
        print("Sample 15M tagged market:")
        m = markets_15m[0]
        print(f" - {m.get('question')}")
        print(f"   Tags: {m.get('tags')}")
        print(f"   Slug: {m.get('slug')}")

    # Test 3: Slug Construction
    print("\n### TEST 3: Slug Construction ###")
    slug_market = finder.find_market_by_slug_pattern()
    if slug_market:
        print(f"✅ Found via slug: {slug_market.get('question')}")
    else:
        print("❌ Slug construction found no active markets")
    
    # Test 4: Full workflow
    print("\n### TEST 4: Full Market Discovery (Method Priority) ###")
    market = finder.find_fifteen_minute_market(debug=True)
    
    if market:
        print("\n✅ SUCCESS: Found active market")
        print(json.dumps(finder.get_market_info(), indent=2))
        
        # Verify tokens
        tokens = finder.current_tokens
        val = tokens.get('Yes')
        print(f"YES Token ID: {val}")
        if not val:
             print("⚠️ WARNING: Token ID missing!")
    else:
        print("\n❌ FAILED: No market found")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
