"""
Step 1: Resolve BTC 15m Market from Polymarket API (V2)
Uses DynamicMarketFinder to robustly locate 15-minute Bitcoin markets.
"""
import json
import os
from datetime import datetime
from . import config
from .market_finder import DynamicMarketFinder

# Output file
OUTPUT_FILE = "active_btc15m_market.json"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def save_market_data(data):
    """Save market data to JSON file."""
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    log(f"Saved to {OUTPUT_FILE}")

def resolve_market():
    """Main function to resolve the current BTC 15m market."""
    log("=" * 60)
    log("RESOLVING BTC 15M MARKET (API V2)")
    log("=" * 60)
    
    finder = DynamicMarketFinder()
    market = finder.find_fifteen_minute_market(debug=True)
    
    if market:
        # Adapt to expected format for main.py
        # main.py expects: slug, yes_token_id, no_token_id
        
        # Get tokens from finder (it already maps Up/Down to Yes/No)
        yes_token = finder.get_current_token_id("Yes")
        no_token = finder.get_current_token_id("No")
        
        # If tokens are missing for some reason, try to extract from market object
        if not yes_token or not no_token:
            log("Warning: Tokens not found in finder. Checking raw market data...")
            # (Fallback logic is mostly handled inside finder now)
            
        result = {
            'slug': market.get('slug'),
            'question': market.get('question'),
            'yes_token_id': yes_token,
            'no_token_id': no_token,
            'end_date_iso': market.get('end_date_iso'),
            'discovered_at': datetime.utcnow().isoformat(),
            'raw_market': market # Keep raw data just in case
        }
        
        save_market_data(result)
        
        log(f"SUCCESS: Found market {market.get('slug')}")
        log(f"  YES: {yes_token}")
        log(f"  NO: {no_token}")
        
        return result
    
    log("FAILED: Could not resolve market")
    return None

def get_market_result(yes_token_id: str):
    """
    Check if the market has resolved and who won.
    Returns: "YES", "NO", or None (if not resolved).
    Delegate to finder logic or raw API check? simpler to check API.
    """
    import requests
    try:
        url = f'https://clob.polymarket.com/markets?limit=1&token_id={yes_token_id}'
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data.get('data'):
                m_info = data['data'][0]
                
                # Check if resolved
                winner_id = m_info.get('winning_outcome_id')
                
                if winner_id:
                    if winner_id == yes_token_id:
                        return "YES"
                    else:
                        return "NO" 
    except Exception as e:
        log(f"Error checking market result: {e}")
        
    return None

if __name__ == "__main__":
    market = resolve_market()
    if market:
        print("\n" + "=" * 60)
        print("RESOLVED MARKET:")
        print("=" * 60)
        print(json.dumps(market, indent=2))
