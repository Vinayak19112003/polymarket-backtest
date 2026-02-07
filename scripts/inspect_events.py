
import requests

def inspect_events():
    print("Inspecting /events endpoint...")
    try:
        # Try finding events related to BTC
        url = "https://gamma-api.polymarket.com/events"
        params = {"limit": 20, "slug": "btc-price"} # Guessing
        
        # List recent events
        resp = requests.get(url, params={"limit": 10})
        if resp.status_code == 200:
            events = resp.json()
            print(f"Fetched {len(events)} events")
            for e in events:
                print(f"Event: {e.get('title')}")
                print(f"Slug: {e.get('slug')}")
                print(f"ID: {e.get('id')}")
                
        # Try searching by query if supported
        print("\nSearching events for 'Bitcoin'...")
        resp = requests.get(url, params={"limit": 20, "q": "Bitcoin"}) # or query
        if resp.status_code == 200:
            events = resp.json()
            print(f"Found {len(events)} Bitcoin events")
            for e in events:
                print(f" - {e.get('title')} (Slug: {e.get('slug')})")

    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect_events()
