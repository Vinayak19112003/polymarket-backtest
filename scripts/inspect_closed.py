
import requests
import json

def find_closed_15m():
    print("Searching for CLOSED 15-minute markets...")
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 100, 
        "active": "false", 
        "closed": "true",
        "tag_id": "91" # specific tag for 15m? Try guessing or filtering
    }
    
    # Try searching for "bitcoin" and "15"
    try:
        resp = requests.get(url, params={"limit": 500, "active": "false", "closed": "true"})
        markets = resp.json()
        print(f"Fetched {len(markets)} closed markets")
        
        candidates = []
        for m in markets:
            q = m.get('question', '').lower()
            if 'bitcoin' in q and ('15' in q or 'minute' in q or '15m' in q):
                candidates.append(m)
                
        print(f"Found {len(candidates)} CLOSED 15m BTC markets")
        
        for m in candidates[:3]:
            print(f"\nQuestion: {m.get('question')}")
            print(f"Slug: {m.get('slug')}")
            print(f"End: {m.get('end_date_iso')}")
            print(f"Tags: {m.get('tags')}")
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    find_closed_15m()
