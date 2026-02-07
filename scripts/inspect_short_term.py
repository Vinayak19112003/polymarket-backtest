
import requests
import json
from datetime import datetime, timedelta, timezone

def find_short_term_markets():
    print("Searching for markets expiring SOON (Short Term)...")
    url = "https://gamma-api.polymarket.com/markets"
    
    # Get active markets
    try:
        resp = requests.get(url, params={"limit": 500, "active": "true", "closed": "false"})
        markets = resp.json()
        
        now = datetime.now(timezone.utc)
        short_term = []
        
        for m in markets:
            end_date_str = m.get('end_date_iso')
            if end_date_str:
                try:
                    if end_date_str.endswith('Z'): end_date_str = end_date_str[:-1] + '+00:00'
                    end_date = datetime.fromisoformat(end_date_str)
                    if end_date.tzinfo is None: end_date = end_date.replace(tzinfo=timezone.utc)
                    
                    diff = (end_date - now).total_seconds()
                    
                    # Look for markets expiring in < 2 hours
                    if 0 < diff < 7200:
                        short_term.append(m)
                except:
                    pass
                    
        print(f"Found {len(short_term)} markets expiring in < 2h")
        
        btc_short = [m for m in short_term if 'bitcoin' in m.get('question', '').lower() or 'btc' in m.get('slug', '').lower()]
        print(f"Found {len(btc_short)} BTC short-term markets")
        
        for m in btc_short:
            print(f"\nQuestion: {m.get('question')}")
            print(f"Slug: {m.get('slug')}")
            print(f"End: {m.get('end_date_iso')}")
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    find_short_term_markets()
