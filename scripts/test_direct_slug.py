
import requests

def test_direct_slug():
    slug = "btc-updown-15m-1770440400"
    url = f"https://gamma-api.polymarket.com/markets/{slug}"
    print(f"GET {url}")
    
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            m = resp.json()
            print(f"Question: {m.get('question')}")
            print(f"Market ID: {m.get('id')}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_direct_slug()
