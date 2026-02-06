
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.features.strategy import check_mean_reversion_signal

# Constants
DATA_FILE = "data/btcusdt_1m.csv"
ORDERBOOK_FILE = "orderbook_snapshots.csv"
TIMEOUT_SECONDS = 6000000 # Wait, prompt says "timeout window" (usually 60s). 
# But snapshots might be sparse. Let's assume 60s.
TIMEOUT_SECONDS = 60

# Orderbook CSV Columns (No Header)
OB_COLS = [
    'timestamp', 'slug', 
    'yes_bid', 'yes_ask', 'yes_bid_size', 'yes_ask_size',
    'no_bid', 'no_ask', 'no_bid_size', 'no_ask_size',
    'yes_spread', 'no_spread'
]

def load_data():
    print(f"Loading {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"Loading {ORDERBOOK_FILE}...")
    # Load orderbook snapshots (might be large, maybe load optimization needed?)
    # For now, load all
    ob_df = pd.read_csv(ORDERBOOK_FILE, names=OB_COLS, parse_dates=['timestamp'])
    ob_df = ob_df.sort_values('timestamp').reset_index(drop=True)
    
    return df, ob_df

def run_simulation():
    df, ob_df = load_data()
    
    # 1. Generate Signals (Unified Logic)
    # Resample to 15m
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    
    # Calculate Features
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # Previous values for signal
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    # Apply strategy
    signals = []
    print("Generating signals...")
    for idx, row in df_15m.iterrows():
        if pd.isna(row['prev_rsi']) or pd.isna(row['dist_ema']):
            continue
        sig, _ = check_mean_reversion_signal(row['prev_rsi'], row['dist_ema'])
        if sig:
            signals.append({
                'timestamp': idx,
                'signal': sig,
                'btc_price': row['open'] # Approximation of entry
            })
            
    print(f"Generated {len(signals)} signals.")
    
    # 2. Simulate Execution
    trades = []
    
    for s in signals:
        ts = s['timestamp']
        side = s['signal'] # YES or NO
        
        # Find orderbook snapshots within [ts, ts + 60s]
        window_end = ts + timedelta(seconds=TIMEOUT_SECONDS)
        
        # Subset ob_df (optimize with searchsorted later if slow)
        mask = (ob_df['timestamp'] >= ts) & (ob_df['timestamp'] <= window_end)
        snapshots = ob_df[mask]
        
        filled = False
        fill_price = 0.0
        fill_delay = 0.0
        
        if len(snapshots) == 0:
            # Fallback (No data)
            # Prompt: "If no orderbook data available, use fallback with 80% fill probability"
            if np.random.random() < 0.8:
                filled = True
                fill_price = 0.50 # Assume mid
                fill_delay = 5.0
        else:
            # Simulate Limit Order
            # Logic: Place at Best Bid + 0.01 (Maker) or Take Best Ask (Taker)
            # Simplified: Try to fill at Best Ask (Taker) if Spread is tight?
            # Or Maker: Place at Bid+0.01. Fill if subsequent Ask drops to <= Limit?
            # "Smart Limit" from Live Bot: 
            # if spread > 0.02: place at mid. else: take best ask?
            # Let's use simple TAKER simulation for "Guaranteed Fill" checks, 
            # or MAKER simulation for "Passive".
            # The prompt asks for "Smart limit pricing logic... maker vs taker based on spread".
            
            # Let's assume we place order at t=0
            first_snap = snapshots.iloc[0]
            
            if side == 'YES':
                spread = first_snap['yes_spread']
                best_ask = first_snap['yes_ask']
                if spread <= 0.02:
                     # Taker: Buy at Best Ask
                     limit_price = best_ask
                     # Check if size available? Assume yes for small size.
                     filled = True
                     fill_price = limit_price
                     fill_delay = (first_snap['timestamp'] - ts).total_seconds()
                else:
                    # Maker: Place below best ask, e.g. Mid or Bid++
                    limit_price = first_snap['yes_bid'] + 0.01
                    # Check subsequent snapshots for FILL
                    # Fill condition: Someone calculates match. 
                    # Simpler: If Market Ask comes down to our Limit Price?
                    # Or if Next Trade Price <= Limit? (We don't have trade tape).
                    # Proxy: If subsequent Best Ask <= Limit Price, we filled.
                    for _, snap in snapshots.iterrows():
                        if snap['yes_ask'] <= limit_price: # Price moved in our favor
                            filled = True
                            fill_price = limit_price
                            fill_delay = (snap['timestamp'] - ts).total_seconds()
                            break
            else: # NO
                spread = first_snap['no_spread']
                best_ask = first_snap['no_ask']
                if spread <= 0.02:
                     limit_price = best_ask
                     filled = True
                     fill_price = limit_price
                     fill_delay = (first_snap['timestamp'] - ts).total_seconds()
                else:
                    limit_price = first_snap['no_bid'] + 0.01
                    for _, snap in snapshots.iterrows():
                        if snap['no_ask'] <= limit_price:
                            filled = True
                            fill_price = limit_price
                            fill_delay = (snap['timestamp'] - ts).total_seconds()
                            break
                            
        # Record
        trades.append({
            'timestamp': ts,
            'signal': side,
            'filled': filled,
            'fill_price': fill_price,
            'fill_delay': fill_delay
        })
        
    # Analysis
    res_df = pd.DataFrame(trades)
    if len(res_df) > 0:
        fill_rate = res_df['filled'].mean() * 100
        avg_delay = res_df[res_df['filled']]['fill_delay'].mean()
        avg_price = res_df[res_df['filled']]['fill_price'].mean()
        
        print("==================================================")
        print("ORDERBOOK BACKTEST REPORT")
        print("==================================================")
        print(f"Total Signals: {len(res_df)}")
        print(f"Filled:        {res_df['filled'].sum()}")
        print(f"Fill Rate:     {fill_rate:.2f}%")
        print(f"Avg Delay:     {avg_delay:.2f}s")
        print(f"Avg Price:     {avg_price:.3f}")
        print("==================================================")
        
        os.makedirs("results", exist_ok=True)
        res_df.to_csv("results/backtest_orderbook_aware.csv", index=False)
        print("Saved to results/backtest_orderbook_aware.csv")
    else:
        print("No signals generated.")

if __name__ == "__main__":
    run_simulation()
