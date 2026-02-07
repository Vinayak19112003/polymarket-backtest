
import sys
import os
import requests
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bot.market_finder import DynamicMarketFinder
from src.bot.orderbook_simulator import OrderbookSimulator

def test_market_logic():
    print("\n--- Testing Market Finder Logic (Unit Test) ---")
    finder = DynamicMarketFinder()
    
    # Create a simulated 15-min market
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=10)
    
    simulated_market = {
        "question": "Will Bitcoin be above $100k in 15 mins?",
        "end_date_iso": expiry.isoformat().replace("+00:00", "Z"),
        "tokens": [{"outcome": "Yes", "token_id": "123"}]
    }
    
    # Test is_fifteen_minute_market
    is_15m = finder.is_fifteen_minute_market(simulated_market)
    print(f"Test 1 (Valid 15m): {'PASS' if is_15m else 'FAIL'}")
    
    # Test non-15m
    simulated_market_long = {
        "question": "Will Bitcoin be above $100k in 2025?",
        "end_date_iso": (now + timedelta(days=300)).isoformat().replace("+00:00", "Z"),
        "tokens": [{"outcome": "Yes", "token_id": "456"}]
    }
    is_15m_long = finder.is_fifteen_minute_market(simulated_market_long)
    print(f"Test 2 (Long duration): {'PASS' if not is_15m_long else 'FAIL'}")

    # Test BTC filter
    filtered = finder.filter_btc_markets([simulated_market, simulated_market_long])
    print(f"Test 3 (Filter BTC): Found {len(filtered)} markets (Expected 1)")

def test_orderbook_real():
    print("\n--- Testing Orderbook Simulator (Live API) ---")
    
    # 1. Get ANY valid token ID from live markets
    try:
        resp = requests.get("https://gamma-api.polymarket.com/markets?limit=10&closed=false")
        markets = resp.json()
        
        token_id = None
        market_q = ""
        for m in markets:
            # Check for tokens list (legacy)
            if 'tokens' in m and isinstance(m['tokens'], list):
                for t in m['tokens']:
                    if t.get('outcome') == 'Yes':
                        token_id = t.get('token_id')
                        market_q = m.get('question')
                        break
            
            # Check for clobTokenIds (Gamma API)
            elif 'clobTokenIds' in m and 'outcomes' in m and not token_id:
                try:
                    import json
                    clob_ids = json.loads(m['clobTokenIds'])
                    outcomes = json.loads(m['outcomes'])
                    if "Yes" in outcomes:
                        idx = outcomes.index("Yes")
                        if idx < len(clob_ids):
                            token_id = clob_ids[idx]
                            market_q = m.get('question')
                except:
                    continue

            if token_id: break
            
        if not token_id:
            print("SKIPPING: No token ID found in active markets")
            return

        print(f"Using token from market: '{market_q}'")
        print(f"Token ID: {token_id}")

        ob = OrderbookSimulator()
        
        # Test 1: Fetch
        book = ob.fetch_live_orderbook(token_id)
        if book:
            print(f"SUCCESS: Orderbook fetched. Bids: {len(book.get('bids', []))}, Asks: {len(book.get('asks', []))}")
            
            # Test 2: Best Bid/Ask
            bb, ba = ob.get_best_bid_ask(token_id)
            print(f"Best Bid: {bb}, Best Ask: {ba}")
            
            # Test 3: Simulation
            fill = ob.simulate_limit_order_fill(token_id, 'BUY', ba, 10.0)
            print(f"Simulation Result: {fill}")
            
        else:
            print("FAILURE: Fetch returned None")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_market_logic()
    test_orderbook_real()
