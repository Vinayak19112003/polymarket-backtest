
import os
import requests
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

FILE_PATH = os.path.join(DATA_DIR, 'btcusdt_1m.csv')

def download_btc_data():
    """
    Download 1m BTC data from public source (or generate dummy data if needed).
    For now, we fetch from Binance API and save.
    """
    print(f"Checking for data in {FILE_PATH}...")
    
    if os.path.exists(FILE_PATH):
        print("Data file already exists. Skipping download.")
        return

    print("Downloading recent BTC data from Binance...")
    try:
        # Fetch last 1000 candles (limit)
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "limit": 1000
        }
        res = requests.get(url, params=params)
        data = res.json()
        
        # Parse
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        
        # Clean
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # Save
        df.to_csv(FILE_PATH, index=False)
        print(f"Successfully saved {len(df)} rows to {FILE_PATH}")
        
    except Exception as e:
        print(f"Error downloading data: {e}")

if __name__ == "__main__":
    download_btc_data()
