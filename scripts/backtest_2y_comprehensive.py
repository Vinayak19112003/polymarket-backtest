
import sys
import os
import pandas as pd
import numpy as np

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
    print(f"Loaded {len(df)} candles.")

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
    
    # Signal Logic (Unified Strategy Import)
    try:
        from src.features.strategy import check_mean_reversion_signal
    except ImportError:
        # Allow running from scripts/ dir
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.features.strategy import check_mean_reversion_signal
        
    print("Applying Unified Strategy Logic (Row-wise)...")
    
    # Helper for apply
    def apply_signal(row):
        # We use PREVIOUS candle's features to decide at OPEN
        rsi = row['prev_rsi']
        dist = row['dist_ema']
        
        # Handle NaN
        if pd.isna(rsi) or pd.isna(dist):
            return 'NONE'
            
        signal, _ = check_mean_reversion_signal(rsi, dist)
        return signal if signal else 'NONE'
        
    # Apply row-wise (slower but guarantees exact parity with live bot)
    df_15m['signal'] = df_15m.apply(apply_signal, axis=1)
    
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
    win_rate = len(trades[trades['result'] == 'WIN']) / total_trades * 100
    total_pnl = trades['pnl'].sum()
    
    # Streak
    trades['loss'] = trades['result'] == 'LOSS'
    streak = trades['loss'].astype(int).groupby((trades['loss'] != trades['loss'].shift()).cumsum()).cumsum()
    max_loss_streak = streak[trades['loss']].max()
    
    # Monthly
    trades['month'] = trades.index.to_period('M')
    monthly = trades.groupby('month').agg({'pnl': 'sum', 'result': 'count'})
    monthly['win_rate'] = trades[trades['result']=='WIN'].groupby('month').count()['result'] / monthly['result'] * 100
    
    # Daily (Tail)
    trades['date'] = trades.index.date
    daily = trades.groupby('date').agg({'pnl': 'sum', 'result': 'count'}).tail(20)
    
    # CSV
    os.makedirs("results", exist_ok=True)
    trades['timestamp'] = trades.index
    trades[['timestamp','signal','entry_price','exit_price','result','pnl']].to_csv("results/backtest_2y_trades.csv", index=False)
    
    # Text Report
    with open("results/backtest_2y_full_report.txt", "w") as f:
        f.write("==================================================\n")
        f.write("POLYMARKET BOT - 2 YEAR COMPREHENSIVE AUDIT (VECTORIZED)\n")
        f.write("==================================================\n")
        f.write(f"Strategy:    Strict Mean Reversion (Signal @ :00)\n")
        f.write(f"Period:      2 Years\n")
        f.write(f"Entry Price: ${ENTRY_PRICE:.2f}\n")
        f.write(f"Fee:         {FEES*100}%\n")
        f.write("--------------------------------------------------\n")
        f.write("\n")
        f.write("### 1. OVERALL PERFORMANCE\n")
        f.write(f"Total Trades:      {total_trades}\n")
        f.write(f"Win Rate:          {win_rate:.2f}%\n")
        f.write(f"Total PnL ($):     ${total_pnl:.2f}\n")
        f.write(f"Avg PnL/Trade:     ${total_pnl/total_trades:.4f}\n")
        f.write(f"Max Loss Streak:   {max_loss_streak} trades\n")
        f.write("\n")
        f.write("### 2. MONTHLY BREAKDOWN\n")
        f.write(monthly.to_string())
        f.write("\n\n")
        f.write("### 3. DAILY BREAKDOWN (Tail 20)\n")
        f.write(daily.to_string())
        
    print(f"Done. ROI: {total_pnl}% (on 1 unit). WR: {win_rate:.1f}%")

if __name__ == "__main__":
    run_simulation()
