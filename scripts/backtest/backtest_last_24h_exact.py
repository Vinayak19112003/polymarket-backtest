
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
ENTRY_PRICE = 0.45 # Conservative assumption
FEES = 0.02
SYMBOL = "BTCUSDT"
DAYS = 1

def fetch_data():
    print("Fetching last 24 hours of 1m data from Binance...")
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=DAYS, hours=16)).timestamp() * 1000) # +Buffer for warmup
    
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
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if not data:
            break
            
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
        
        if len(data) < 1000 or last_ts >= end_time:
            break
            
    df = pd.DataFrame(all_candles)
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    print(f"Fetched {len(df)} candles.")
    return df

def run_simulation():
    df = fetch_data()
    engine = RealtimeFeatureEngineV2()
    
    trades = []
    balance = 100.0
    
    print("\nSimulating Live Bot features/timing...")
    
    # Needs warmup
    required = engine.REQUIRED_CANDLES
    if len(df) < required + 100:
        print(f"Not enough data. Need {required}, have {len(df)}")
        return

    # Start simulation after warmup
    # We simulate "Streaming" by feeding candles one by one
    
    sim_start_index = required
    
    for i in range(sim_start_index, len(df)):
        # 1. Feed Candle
        candle_data = df.iloc[i]
        candle_dict = candle_data.to_dict()
        engine.add_candle(candle_dict)
        
        # 2. Check Time (Timing Optimization)
        # Only trade at :00, :15, :30, :45 (allow minute 0 and 1)
        ts = candle_data['timestamp']
        minute = ts.minute
        
        # Strict timing check from main.py
        minute_in_cycle = minute % 15
        if minute_in_cycle > 1:
            continue
            
        # 3. Compute Features (Live logic)
        features = engine.compute_features()
        if not features:
            continue
            
        # 4. Check Signal
        prob = engine.predict_probability(features)
        signal, edge = engine.check_signal(features, prob)
        
        if not signal:
            continue
            
        # 5. Execute Trade
        # Outcome is price 15 mins later
        if i + 15 >= len(df):
            break # Can't settle
            
        settle_candle = df.iloc[i + 15]
        settle_price = settle_candle['close']
        entry_price = candle_data['close'] # Spot price
        
        # Logic: 
        # YES: Win if Settle > Entry
        # NO: Win if Settle < Entry
        
        won = False
        if signal == 'YES':
            if settle_price > entry_price: won = True
        elif signal == 'NO':
            if settle_price < entry_price: won = True
            
        # PnL Calculation
        # Assume $0.45 Entry + 2% Fee
        cost = ENTRY_PRICE
        fees = cost * FEES
        
        if won:
            pnl = 1.00 - cost - fees
        else:
            pnl = -cost - fees
            
        trades.append({
            'timestamp': ts,
            'signal': signal,
            'price': entry_price,
            'settle': settle_price,
            'result': 'WIN' if won else 'LOSS',
            'pnl': pnl
        })
        
        balance += pnl
        
    # Report
    print("-" * 50)
    print("BACKTEST: LAST 24H (EXACT LIVE STRATEGY)")
    print("-" * 50)
    print(f"Trades:     {len(trades)}")
    
    if trades:
        w = [t for t in trades if t['result'] == 'WIN']
        wr = len(w) / len(trades) * 100
        total_pnl = sum(t['pnl'] for t in trades)
        
        print(f"Win Rate:   {wr:.1f}%")
        print(f"Total PnL:  ${total_pnl:.2f} (per share)")
        print(f"Assumptions: Entry=${ENTRY_PRICE}, Fee={FEES*100}%")
        
        # Directions
        yes = [t for t in trades if t['signal'] == 'YES']
        no = [t for t in trades if t['signal'] == 'NO']
        print(f"Bias:       {len(yes)} YES / {len(no)} NO")
    else:
        print("No trades triggered.")

if __name__ == "__main__":
    run_simulation()
