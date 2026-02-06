
import sys
import os
import pandas as pd
import numpy as np
from datetime import timedelta

# Constants
ENTRY_PRICE = 0.50
FEES = 0.02
DATA_FILE = "data/btcusdt_1m.csv"

def run_simulation():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    print(f"Loading {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # FILTER LAST 30 DAYS
    end_date = df['timestamp'].max()
    start_date = end_date - timedelta(days=30)
    print(f"Filtering data from {start_date} to {end_date} (Last 30 Days)...")
    
    df = df[df['timestamp'] >= start_date].copy()
    df = df.reset_index(drop=True)
    print(f"Loaded {len(df)} candles for the period.")

    print("Resampling to 15m (Strict Snapshot Logic)...")
    
    # Resample to 15m
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    
    # Compute Indicators on 15m
    # RSI 14
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    
    # EMA 50
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # Shift indicators by 1 (We use PREVIOUS Close to decide at CURRENT Open)
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    
    # Signal Logic (Vectorized)
    # Dist < 0 means Prev Close < Prev EMA (Downtrend)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    # Thresholds
    # Default
    threshold_buy = 43
    threshold_sell = 58
    
    # Dynamic
    # If Downtrend (dist < 0), Stricter Buy (38)
    # If Uptrend (dist > 0), Stricter Sell (62)
    
    conditions = [
        (df_15m['dist_ema'] < 0), # Downtrend
        (df_15m['dist_ema'] > 0)  # Uptrend
    ]
    choices_buy = [38, 43]
    choices_sell = [58, 62]
    
    df_15m['thresh_buy'] = np.select(conditions, choices_buy, default=43)
    df_15m['thresh_sell'] = np.select(conditions, choices_sell, default=58)
    
    # Generate Signals
    # BUY YES if RSI < Buy Thresh
    # BUY NO if RSI > Sell Thresh
    
    df_15m['signal'] = 'NONE'
    df_15m.loc[df_15m['prev_rsi'] < df_15m['thresh_buy'], 'signal'] = 'YES'
    df_15m.loc[df_15m['prev_rsi'] > df_15m['thresh_sell'], 'signal'] = 'NO'
    
    # Filter only trades
    trades = df_15m[df_15m['signal'] != 'NONE'].copy()
    
    # Calculate Outcome
    # Entry: Open of Current Candle (Minute :00)
    # Exit: Close of Current Candle (Minute :15)
    # This precisely matches "Entry at :00, Exit at :15"
    
    trades['entry_price'] = trades['open']
    trades['exit_price'] = trades['close']
    
    # Win/Loss
    # YES: Win if Exit > Entry
    # NO: Win if Exit < Entry
    
    trades['result'] = 'LOSS'
    trades.loc[(trades['signal'] == 'YES') & (trades['exit_price'] > trades['entry_price']), 'result'] = 'WIN'
    trades.loc[(trades['signal'] == 'NO') & (trades['exit_price'] < trades['entry_price']), 'result'] = 'WIN'
    
    # PnL
    cost = ENTRY_PRICE
    fees = cost * FEES
    trades['pnl'] = np.where(trades['result'] == 'WIN', (1.0 - cost - fees), (-cost - fees))
    
    # REPORTING
    total_trades = len(trades)
    win_rate = len(trades[trades['result'] == 'WIN']) / total_trades * 100 if total_trades > 0 else 0
    total_pnl = trades['pnl'].sum()
    
    # Streak
    trades['loss'] = trades['result'] == 'LOSS'
    streak = trades['loss'].astype(int).groupby((trades['loss'] != trades['loss'].shift()).cumsum()).cumsum()
    max_loss_streak = streak[trades['loss']].max() if not streak.empty else 0
    
    # Monthly
    trades['month'] = trades.index.to_period('M')
    monthly = trades.groupby('month').agg({'pnl': 'sum', 'result': 'count'})
    if not trades.empty:
        monthly['win_rate'] = trades[trades['result']=='WIN'].groupby('month').count()['result'] / monthly['result'] * 100
    
    # Daily (Tail)
    trades['date'] = trades.index.date
    daily = trades.groupby('date').agg({'pnl': 'sum', 'result': 'count'}).tail(30)
    
    # CSV
    os.makedirs("results", exist_ok=True)
    trades['timestamp'] = trades.index
    trades[['timestamp','signal','entry_price','exit_price','result','pnl']].to_csv("results/backtest_30d_trades.csv", index=False)
    
    # Text Report
    with open("results/backtest_30d_report.txt", "w") as f:
        f.write("==================================================\n")
        f.write("POLYMARKET BOT - 30 DAY BACKTEST (STRICT RSI)\n")
        f.write("==================================================\n")
        f.write(f"Period:      {start_date} to {end_date}\n")
        f.write(f"Strategy:    Strict Mean Reversion (Signal @ :00)\n")
        f.write(f"Entry Price: ${ENTRY_PRICE:.2f}\n")
        f.write(f"Fee:         {FEES*100}%\n")
        f.write("--------------------------------------------------\n")
        f.write("\n")
        f.write("### 1. OVERALL PERFORMANCE\n")
        f.write(f"Total Trades:      {total_trades}\n")
        f.write(f"Win Rate:          {win_rate:.2f}%\n")
        f.write(f"Total PnL ($):     ${total_pnl:.2f}\n")
        f.write(f"Avg PnL/Trade:     ${total_pnl/total_trades:.4f}" if total_trades > 0 else "Avg PnL/Trade: 0\n")
        f.write(f"\nMax Loss Streak:   {max_loss_streak} trades\n")
        f.write("\n")
        f.write("### 2. DAILY BREAKDOWN (Last 30 Days)\n")
        f.write(daily.to_string())
        
    print(f"Done. PnL: ${total_pnl:.2f}. WR: {win_rate:.1f}%")

if __name__ == "__main__":
    run_simulation()
