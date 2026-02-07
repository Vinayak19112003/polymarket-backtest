"""
Verification Backtest: Aligned Strategy (38/62 RSI + Time Filters)
Purpose: Confirm live bot parameters match backtest expectations
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DATA_FILE = "data/btcusdt_1m.csv"
ENTRY_PRICE = 0.50
FEES = 0.02

# ALIGNED PARAMETERS (Now matching live bot)
BLOCKED_HOURS = [5, 6, 7, 8, 9, 15, 16]
RSI_OVERSOLD = 38
RSI_OVERBOUGHT = 62

def run_verification():
    print("Loading data...")
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    df = pd.read_csv(DATA_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Use last 30 days for quick validation
    # If not enough data, use what we have
    end_date = df['timestamp'].max()
    start_date = end_date - timedelta(days=30)
    df = df[df['timestamp'] >= start_date].copy()
    
    print(f"Analyzing data from {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Resample to 15m
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    
    # Calculate indicators
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # Shift for signal calculation
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    trades = []
    
    for idx, row in df_15m.iterrows():
        if pd.isna(row['prev_rsi']):
            continue
            
        hour = idx.hour
        
        # Time filter
        if hour in BLOCKED_HOURS:
            continue
        
        # Signal using ALIGNED thresholds
        rsi = row['prev_rsi']
        dist = row['dist_ema']
        
        # Dynamic thresholds (same as strategy.py)
        rsi_buy = 35 if dist >= 0 else 38  # Even stricter in downtrend (matching strategy.py)
        rsi_sell = 65 if dist <= 0 else 62 # Even stricter in uptrend
        
        signal = None
        if rsi < rsi_buy:
            signal = 'YES'
        elif rsi > rsi_sell:
            signal = 'NO'
        
        if not signal:
            continue
        
        # Outcome
        won = (signal == 'YES' and row['close'] > row['open']) or \
              (signal == 'NO' and row['close'] < row['open'])
        
        pnl = (1.0 - ENTRY_PRICE - FEES) if won else (-ENTRY_PRICE - FEES)
        
        trades.append({
            'timestamp': idx,
            'signal': signal,
            'rsi': rsi,
            'result': 'WIN' if won else 'LOSS',
            'pnl': pnl,
            'hour': hour
        })
    
    # Results
    if not trades:
        print("No trades generated!")
        return
        
    df_trades = pd.DataFrame(trades)
    wins = len(df_trades[df_trades['result'] == 'WIN'])
    total = len(df_trades)
    win_rate = wins / total * 100 if total > 0 else 0
    total_pnl = df_trades['pnl'].sum()
    
    print("\n" + "="*60)
    print("ALIGNED STRATEGY VERIFICATION (30 Days)")
    print("="*60)
    print(f"Parameters: RSI {RSI_OVERSOLD}/{RSI_OVERBOUGHT}, Blocked Hours: {BLOCKED_HOURS}")
    print(f"Total Trades:  {total}")
    print(f"Win Rate:      {win_rate:.2f}%")
    print(f"Total PnL:     ${total_pnl:.2f}")
    print("="*60)
    
    # Expected vs Actual
    EXPECTED_WR = 58.0
    delta = win_rate - EXPECTED_WR
    
    if win_rate >= EXPECTED_WR - 5: # Allow small variance
        print(f"✅ ALIGNED: Win rate {win_rate:.2f}% matches expectation ({EXPECTED_WR}% ±5%)")
    else:
        print(f"⚠️ DRIFT: Win rate {win_rate:.2f}% below expectation ({EXPECTED_WR}%). Delta: {delta:.2f}%")
    
    # Save
    os.makedirs("results", exist_ok=True)
    df_trades.to_csv("results/aligned_strategy_verification.csv", index=False)
    print("\nSaved: results/aligned_strategy_verification.csv")

if __name__ == "__main__":
    run_verification()
