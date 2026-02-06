
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
ENTRY_PRICE = 0.45 # Conservative assumption (Limit Order fill)
FEES = 0.02        # 2% Fee (Taker/Maker blend)
SYMBOL = "BTCUSDT"
DAYS = 7           # Last Week

def fetch_data():
    print(f"Fetching last {DAYS} days of 1m data from Binance...")
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=DAYS, hours=24)).timestamp() * 1000) # +Buffer
    
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
            print("Error fetching data")
            break
        
        if not data or not isinstance(data, list):
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
        
        sys.stdout.write(f"\rFetched {len(all_candles)} candles...")
        sys.stdout.flush()
        
        if len(data) < 1000 or last_ts >= end_time:
            break
            
    print("\nProcessing...")
    df = pd.DataFrame(all_candles)
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return df

def run_simulation():
    df = fetch_data()
    engine = RealtimeFeatureEngineV2()
    
    trades = []
    balance = 100.0
    
    print("\nSimulating STRICT LIVE STRATEGY (Signal at :00 Only)...")
    
    required = engine.REQUIRED_CANDLES
    sim_start_index = required
    
    if len(df) < required:
        print("Not enough data.")
        return

    # To simulate correctly, we must feed candles sequentially
    # But for speed, we can warm up, then iterate
    
    # Init buffer with history
    init_candles = df.iloc[:sim_start_index].to_dict('records')
    engine.candles = init_candles # Direct injection for speed
    
    print(f"Starting simulation from {df.iloc[sim_start_index]['timestamp']}")
    
    for i in range(sim_start_index, len(df)):
        candle_data = df.iloc[i]
        timestamp = candle_data['timestamp']
        
        # 1. Feed Candle
        engine.add_candle(candle_data.to_dict())
        
        # 2. Check Timing (Strict :00)
        # We only calculate features at Minute 0 (New 15m candle open effectively)
        # Assuming timestamp is the 'Active' minute. 
        # Candle 06:00 timestamp means 06:00-06:01.
        # So at 06:00, we have data up to 05:59 close? NO.
        # Binance kline timestamp is open time.
        # So at 06:00 timestamp, we technically don't have the 06:00 close yet.
        # The bot receives the callback for 05:59 CLOSE at 06:00:00.
        # And the "timestamp" of the closed candle is 05:59.
        # So we should check if `timestamp.minute % 15 == 14` (Close of cycle)?
        # Or `timestamp.minute % 15 == 0` (Open of NEW cycle)?
        
        # In Live Bot: `update_loop` checks `datetime.utcnow().minute`.
        # Callback is `on_candle_close`.
        # If timestamp is 06:00, that candle CLOSES at 06:01.
        # The bot logic checks `minute % 15 == 0`.
        # This corresponds to the candle with timestamp `:00` BEING OPEN.
        
        if timestamp.minute % 15 != 0:
            continue
            
        # 3. Compute Features (Snapshot)
        features = engine.compute_features()
        if not features: continue
        
        # 4. Check Signal
        prob = engine.predict_probability(features)
        signal, edge = engine.check_signal(features, prob)
        
        if not signal:
            continue
            
        # 5. Execute Trade (5m Hunt Simulation)
        # We assume we get filled.
        # Outcome is decided by Price Change over next 15m.
        # But wait, Polymarket settles on the Strike Price.
        # Here we rely on "Directional Correctness" (Delta).
        
        # Find outcome candle (15 mins later)
        # Actually, we settle against the Strike.
        # In this backtest, we use Spot Price Change as proxy for Win/Loss.
        
        target_idx = i + 15
        if target_idx >= len(df): break
        
        entry_price_btc = candle_data['close']
        settle_price_btc = df.iloc[target_idx]['close']
        
        won = False
        if signal == 'YES':
            if settle_price_btc > entry_price_btc: won = True
        elif signal == 'NO':
            if settle_price_btc < entry_price_btc: won = True
            
        # PnL
        cost = ENTRY_PRICE
        fees = cost * FEES
        pnl = (1.0 - cost - fees) if won else (-cost - fees)
        
        trades.append({
            'timestamp': timestamp,
            'signal': signal,
            'result': 'WIN' if won else 'LOSS',
            'pnl': pnl
        })
        
    # Analysis
    if not trades:
        print("No trades found.")
        return

    df_res = pd.DataFrame(trades)
    win_rate = len(df_res[df_res['result'] == 'WIN']) / len(df_res) * 100
    total_pnl = df_res['pnl'].sum()
    
    print("\n" + "="*60)
    print(f"BACKTEST RESULTS (Last {DAYS} Days)")
    print(f"Strategy: Strict Signal at :00 | Entry ${ENTRY_PRICE} | Fee 2%")
    print("="*60)
    print(f"Total Trades: {len(trades)}")
    print(f"Win Rate:     {win_rate:.1f}%")
    print(f"Total PnL:    ${total_pnl:.2f}")
    print(f"Avg PnL/Trade:${total_pnl/len(trades):.2f}")
    print("="*60)

if __name__ == "__main__":
    run_simulation()
