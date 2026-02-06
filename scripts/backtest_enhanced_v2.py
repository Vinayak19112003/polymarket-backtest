"""
Backtest Enhanced Strategy V2
Includes: Volatility Filter, MTF (1H Trend), Time-of-Day Filter
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.features.strategy import (
    check_mean_reversion_signal_v2, 
    get_volatility_regime
)

# Constants
DATA_FILE = "data/btcusdt_1m.csv"
ENTRY_PRICE = 0.50
FEES = 0.02

# Time-of-Day Filter (UTC)
BLOCKED_HOURS = [2, 3, 4, 5]
HIGH_LIQUIDITY_HOURS = list(range(12, 22))

def run_simulation():
    print(f"Loading {DATA_FILE}...")
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return
        
    df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    print(f"Loaded {len(df)} candles.")
    
    # Resample to 15m
    print("Resampling to 15m...")
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    
    # Calculate Indicators (15m)
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # ATR for Volatility Filter
    tr = pd.concat([
        df_15m['high'] - df_15m['low'],
        abs(df_15m['high'] - df_15m['close'].shift(1)),
        abs(df_15m['low'] - df_15m['close'].shift(1))
    ], axis=1).max(axis=1)
    df_15m['atr'] = tr.rolling(14).mean()
    
    # Previous values for signals
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    # Resample 15m -> 1H for MTF
    print("Computing 1H Trend...")
    df_1h = df_15m['close'].resample('1h').last().dropna()
    ema_20_1h = df_1h.ewm(span=20, adjust=False).mean()
    h1_dist_df = (df_1h / ema_20_1h) - 1
    h1_dist_df = h1_dist_df.reindex(df_15m.index, method='ffill')
    df_15m['h1_dist'] = h1_dist_df
    
    # Run V2 Strategy
    print("Applying Enhanced Strategy V2...")
    trades = []
    blocked_vol = 0
    blocked_mtf = 0
    blocked_tod = 0
    
    for idx, row in df_15m.iterrows():
        if pd.isna(row['prev_rsi']) or pd.isna(row['dist_ema']) or pd.isna(row['atr']):
            continue
            
        hour = idx.hour
        close = row['open']
        atr = row['atr']
        
        # 1. Time-of-Day Filter
        if hour in BLOCKED_HOURS:
            blocked_tod += 1
            continue
        
        # Calculate liquidity boost
        liquidity_boost = 1.05 if hour in HIGH_LIQUIDITY_HOURS else 1.0
            
        # 2. V2 Signal Check (Volatility Filter included)
        signal, edge, reason = check_mean_reversion_signal_v2(
            rsi_14=row['prev_rsi'],
            dist_ema_50=row['dist_ema'],
            atr_15m=atr,
            close=close,
            enable_vol_filter=True
        )
        
        if not signal:
            if "High Volatility" in reason:
                blocked_vol += 1
            continue
        
        # 3. MTF Filter (1H Trend)
        h1_dist = row['h1_dist'] if not pd.isna(row['h1_dist']) else 0
        
        if h1_dist > 0.02:
            if signal == 'NO':
                blocked_mtf += 1
                continue
            else:
                edge *= 1.1
        elif h1_dist < -0.02:
            if signal == 'YES':
                blocked_mtf += 1
                continue
            else:
                edge *= 1.1
        
        edge *= liquidity_boost
        
        # Determine Result
        # Entry at Open, Exit at Close
        if signal == 'YES':
            won = row['close'] > row['open']
        else:
            won = row['close'] < row['open']
            
        pnl = (1.0 - ENTRY_PRICE - FEES) if won else (-ENTRY_PRICE - FEES)
        
        trades.append({
            'timestamp': idx,
            'signal': signal,
            'entry_price': ENTRY_PRICE,
            'exit_price': 1.0 if won else 0.0,
            'result': 'WIN' if won else 'LOSS',
            'pnl': pnl,
            'edge': edge,
            'h1_trend': h1_dist,
            'hour': hour
        })
    
    # Results
    res_df = pd.DataFrame(trades)
    
    if len(res_df) == 0:
        print("No trades generated.")
        return
        
    wins = len(res_df[res_df['result'] == 'WIN'])
    losses = len(res_df[res_df['result'] == 'LOSS'])
    total_pnl = res_df['pnl'].sum()
    win_rate = wins / len(res_df) * 100
    roi = total_pnl / 1.0 * 100 # Initial 1 unit
    
    print("\n==================================================")
    print("ENHANCED STRATEGY V2 - BACKTEST REPORT")
    print("==================================================")
    print(f"Period:        {df_15m.index.min()} to {df_15m.index.max()}")
    print(f"Total Signals: {len(res_df) + blocked_vol + blocked_mtf + blocked_tod}")
    print(f"Blocked (Time-of-Day): {blocked_tod}")
    print(f"Blocked (Volatility):  {blocked_vol}")
    print(f"Blocked (MTF):         {blocked_mtf}")
    print("--------------------------------------------------")
    print(f"Trades Taken:  {len(res_df)}")
    print(f"Wins:          {wins}")
    print(f"Losses:        {losses}")
    print(f"Win Rate:      {win_rate:.2f}%")
    print("--------------------------------------------------")
    print(f"Total PnL:     ${total_pnl:.2f}")
    print(f"ROI:           {roi:.2f}%")
    print("==================================================")
    
    # Comparison (Try to load V1 results if available)
    try:
        v1_df = pd.read_csv("results/backtest_2y_trades.csv")
        v1_wr = len(v1_df[v1_df['result'] == 'WIN']) / len(v1_df) * 100
        v1_roi = v1_df['pnl'].sum() / 1.0 * 100
        
        print("\nCOMPARISON vs V1 (Original Strategy)")
        print("--------------------------------------------------")
        print(f"V1 Trades: {len(v1_df)} | V2 Trades: {len(res_df)}")
        print(f"V1 WR:     {v1_wr:.2f}% | V2 WR:     {win_rate:.2f}%")
        print(f"V1 ROI:    {v1_roi:.2f}% | V2 ROI:    {roi:.2f}%")
        
        delta_wr = win_rate - v1_wr
        delta_roi = roi - v1_roi
        print(f"Delta WR:  {delta_wr:+.2f}%")
        print(f"Delta ROI: {delta_roi:+.2f}%")
        print("==================================================")
    except:
        pass
    
    # Save
    os.makedirs("results", exist_ok=True)
    res_df.to_csv("results/backtest_enhanced_v2_trades.csv", index=False)
    print("\nSaved trades to results/backtest_enhanced_v2_trades.csv")

if __name__ == "__main__":
    run_simulation()
