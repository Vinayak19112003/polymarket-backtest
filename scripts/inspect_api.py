
import requests
import json

def inspect_api():
    try:
        resp = requests.get("https://gamma-api.polymarket.com/markets?limit=1&closed=false")
        data = resp.json()
        if data:
            print(json.dumps(data[0], indent=2))
        else:
            print("No data returned")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect_api()
