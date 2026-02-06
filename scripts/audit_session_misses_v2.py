
import sys
import os
import requests
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.bot.features import RealtimeFeatureEngineV2

SYMBOL = "BTCUSDT"
HOURS = 12 
WARMUP = 1500 # Valid warmup

def run_audit():
    # Fetch ample history
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=HOURS, minutes=1500)).timestamp() * 1000)
    
    print(f"Fetching data from {datetime.fromtimestamp(start_time/1000)}...")
    
    all_candles = []
    current_start = start_time
    
    while True:
        url = "https://api.binance.com/api/v3/klines"
        params = {'symbol': SYMBOL, 'interval': '1m', 'startTime': current_start, 'limit': 1000}
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
        except: break
        if not data: break
        for k in data:
            all_candles.append({
                'timestamp': datetime.utcfromtimestamp(k[0]/1000),
                'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])
            })
        last_ts = data[-1][0]
        current_start = last_ts + 60000 
        if len(data) < 1000 or last_ts >= end_time: break
            
    df = pd.DataFrame(all_candles)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    engine = RealtimeFeatureEngineV2()
    
    # Pre-feed warmup
    warmup_df = df.iloc[:-HOURS*60] # Approximate
    session_df = df.iloc[-HOURS*60:] # The session we care about
    
    # Just iterate all
    expected = 0
    
    for i in range(len(df)):
        candle = df.iloc[i]
        engine.add_candle(candle.to_dict())
        
        # Only check signals in the "Session Window"
        if i < 1500: continue
        
        # Timing
        if candle['timestamp'].minute % 15 != 0: continue
            
        features = engine.compute_features()
        if not features: continue
        
        prob = engine.predict_probability(features)
        signal, edge = engine.check_signal(features, prob)
        
        if signal:
            # Check if this signal is in the "Check against actual" window
            # (Last 8 Hours)
            if candle['timestamp'] > datetime.utcnow() - timedelta(hours=8):
                expected += 1
                # print(f"Signal: {candle['timestamp']} {signal}")
                
    print(f"EXPECTED_SIGNALS: {expected}")
    
if __name__ == "__main__":
    run_audit()
