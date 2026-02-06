#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.orderbook_simulator import OrderbookSimulator

orderbook = OrderbookSimulator()

# Test with actual Polymarket token ID
token_id = "YOUR_TOKEN_ID_HERE"  # Replace with real token

print("Fetching orderbook...")
best_bid, best_ask = orderbook.get_best_bid_ask(token_id)

if best_bid and best_ask:
    print(f"✅ Best Bid: ${best_bid:.3f}")
    print(f"✅ Best Ask: ${best_ask:.3f}")
    print(f"✅ Spread: ${(best_ask - best_bid):.3f}")
else:
    print("❌ Failed to fetch orderbook (Check token_id or connection)")
