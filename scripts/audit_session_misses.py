
import sys
import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.features import RealtimeFeatureEngineV2

# Constants
SYMBOL = "BTCUSDT"
HOURS = 12 # Cover the full session

def fetch_data():
    print(f"Fetching last {HOURS} hours of 1m data from Binance...")
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=HOURS)).timestamp() * 1000)
    
    all_candles = []
    current_start = start_time
    
    while True:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': SYMBOL,
            'interval': '1m',
            'startTime': current_start,
            'limit': 1000
        }
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
        except:
            break
            
        if not data: break
            
        for k in data:
            all_candles.append({
                'timestamp': datetime.utcfromtimestamp(k[0]/1000),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            })
            
        last_ts = data[-1][0]
        current_start = last_ts + 60000 
        if len(data) < 1000 or last_ts >= end_time: break
            
    df = pd.DataFrame(all_candles)
    return df

def run_audit():
    df = fetch_data()
    engine = RealtimeFeatureEngineV2()
    
    expected_signals = []
    
    # Warmup
    sim_start = 50 
    
    print("\nAuditing Session Signals (Strict Mode)...")
    
    for i in range(sim_start, len(df)):
        candle = df.iloc[i]
        ts = candle['timestamp']
        
        # Feed
        engine.add_candle(candle.to_dict())
        
        # Check Timing (:00)
        # Note: Candle timestamp 12:00 corresponds to 12:00-12:01.
        # This matches live bot receiving 11:59 close at 12:00.
        if ts.minute % 15 != 0:
            continue
            
        features = engine.compute_features()
        if not features: continue
        
        prob = engine.predict_probability(features)
        signal, edge = engine.check_signal(features, prob)
        
        if signal:
            # We found a signal in simulation
            expected_signals.append({
                'timestamp': ts,
                'signal': signal,
                'rsi': features.rsi_14
            })
            
    # Load ACTUAL trades
    try:
        actual_df = pd.read_csv("logs/trades.csv")
        actual_df['timestamp'] = pd.to_datetime(actual_df['timestamp'])
        # Filter for same window
        start_ts = df.iloc[0]['timestamp']
        actual_trades = actual_df[actual_df['timestamp'] >= start_ts]
    except:
        actual_trades = []
        
    print("\nRESULTS:")
    print(f"Expected Signals: {len(expected_signals)}")
    print(f"Actual Trades:    {len(actual_trades)}")
    
    print("\nExpected Times:")
    for s in expected_signals:
        print(f"{s['timestamp']} {s['signal']} (RSI {s['rsi']:.1f})")

if __name__ == "__main__":
    run_audit()
