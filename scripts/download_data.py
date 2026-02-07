
import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

FILE_PATH = os.path.join(DATA_DIR, 'btcusdt_1m.csv')

def download_btc_data_range(start_str: str, end_str: str):
    """
    Download 1m BTC data from Binance for a specific range.
    start_str, end_str format: '2026-02-06'
    """
    print(f"Downloading BTC data from {start_str} to {end_str}...")
    
    try:
        # Convert to timestamps (ms)
        start_ts = int(datetime.strptime(start_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_date = datetime.strptime(end_str, '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(days=1)
        end_ts = int(end_date.timestamp() * 1000)
        
        all_data = []
        current_start = start_ts
        
        while current_start < end_ts:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": "BTCUSDT",
                "interval": "1m",
                "limit": 1000,
                "startTime": current_start,
                "endTime": end_ts
            }
            # print(f"Fetching chunk from {current_start}...")
            res = requests.get(url, params=params)
            data = res.json()
            
            if not data or not isinstance(data, list):
                break
                
            all_data.extend(data)
            
            # Update start time to last close time + 1ms
            last_close_time = data[-1][6]
            current_start = last_close_time + 1
            
            if len(data) < 1000:
                break
        
        # Parse
        df = pd.DataFrame(all_data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        
        # Clean
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # Save
        df.to_csv(FILE_PATH, index=False)
        print(f"Successfully saved {len(df)} rows to {FILE_PATH}")
        print(f"Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
    except Exception as e:
        print(f"Error downloading data: {e}")

if __name__ == "__main__":
    # Download 10 days + buffer: Jan 26 to Feb 8
    download_btc_data_range('2026-01-26', '2026-02-08')
