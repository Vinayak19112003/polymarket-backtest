
import requests
import json
from datetime import datetime, timezone

def find_any_15m_market():
    print("Searching for ANY 15-minute market to inspect slug...")
    
    # Fetch a large number of markets
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 500, # Max limit
        "active": "true", 
        "closed": "false"
    }
    
    try:
        resp = requests.get(url, params=params)
        markets = resp.json()
        print(f"Fetched {len(markets)} markets")
        
        candidates = []
        for m in markets:
            q = m.get('question', '').lower()
            if 'up or down' in q or 'updown' in q:
                candidates.append(m)
                
        print(f"Found {len(candidates)} candidates with '15' or 'minute'")
        
        for m in candidates[:10]:
            print(f"\nQuestion: {m.get('question')}")
            print(f"Slug: {m.get('slug')}")
            print(f"End Date: {m.get('end_date_iso')}")
            
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    find_any_15m_market()
