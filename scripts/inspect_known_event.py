
import requests
import json
from datetime import datetime, timezone

def inspect_known_event():
    slug = "btc-updown-15m-1770440400"
    print(f"Inspecting known event slug: {slug}")
    
    # Try /events endpoint
    url = "https://gamma-api.polymarket.com/events"
    try:
        resp = requests.get(url, params={"slug": slug})
        if resp.status_code == 200:
            events = resp.json()
            print(f"Fetched {len(events)} events matching slug")
            
            if events:
                e = events[0]
                print(json.dumps(e, indent=2))
                return
        else:
            print(f"Event fetch failed: {resp.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

    # Fallback: Try /markets with this slug just in case
    print("\nTrying /markets endpoint with same slug...")
    try:
        url = "https://gamma-api.polymarket.com/markets"
        resp = requests.get(url, params={"slug": slug}) # usually markets have their own slugs
        if resp.status_code == 200:
            markets = resp.json()
            print(f"Fetched {len(markets)} markets matching slug")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect_known_event()
