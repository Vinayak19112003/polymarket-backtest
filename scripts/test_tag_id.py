
import requests
import json

def test_tag_id():
    tag_id = "102467" # 15M tag from inspection
    print(f"Testing /markets with tag_id={tag_id}...")
    
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 20,
        "active": "true",
        "closed": "false",
        "tag_id": tag_id
    }
    
    try:
        resp = requests.get(url, params=params)
        markets = resp.json()
        print(f"Fetched {len(markets)} markets")
        
        for m in markets:
            print(f"- {m.get('question')}")
            print(f"  Slug: {m.get('slug')}")
            
    except Exception as e:
        print(e)
        
    print("\nTesting /events with tag_id...")
    url2 = "https://gamma-api.polymarket.com/events"
    try:
        resp = requests.get(url2, params=params)
        events = resp.json()
        print(f"Fetched {len(events)} events")
        for e in events:
            print(f"- {e.get('title')}")
            print(f"  Slug: {e.get('slug')}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_tag_id()
