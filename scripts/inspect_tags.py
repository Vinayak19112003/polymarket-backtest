
import requests

def list_tags():
    try:
        # Try to find a tags endpoint or infer from markets
        print("Attempting to list tags...")
        resp = requests.get("https://gamma-api.polymarket.com/tags")
        if resp.status_code == 200:
            tags = resp.json()
            print(f"Found {len(tags)} tags")
            for t in tags:
                if '15' in t.get('label', '') or 'min' in t.get('label', ''):
                    print(f"ID: {t.get('id')}, Label: {t.get('label')}")
        else:
            print("No /tags endpoint. Inferring from markets...")
            # Fetch diverse markets
            resp = requests.get("https://gamma-api.polymarket.com/markets?limit=100")
            markets = resp.json()
            seen_tags = set()
            for m in markets:
                tags = m.get('tags', [])
                if tags:
                     for t in tags:
                         # Tag structure might be ID or Dict
                         print(f"Tag format: {t}")
                         break
                if tags: break
                
    except Exception as e:
        print(e)

if __name__ == "__main__":
    list_tags()
