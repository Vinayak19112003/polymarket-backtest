"""
Slippage Sensitivity Test
Tests V2 Strategy with varying slippage and entry prices.
"""
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.features.strategy import check_mean_reversion_signal_v2

DATA_FILE = "data/btcusdt_1m.csv"
FEES = 0.02
BLOCKED_HOURS = [2, 3, 4, 5]
HIGH_LIQUIDITY_HOURS = list(range(12, 22))

def run_backtest_with_slippage(entry_price=0.50, slippage_pct=0.0):
    """Run V2 backtest with specified entry price and slippage."""
    df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    df_15m = df.set_index('timestamp').resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    
    # Indicators
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    tr = pd.concat([
        df_15m['high'] - df_15m['low'],
        abs(df_15m['high'] - df_15m['close'].shift(1)),
        abs(df_15m['low'] - df_15m['close'].shift(1))
    ], axis=1).max(axis=1)
    df_15m['atr'] = tr.rolling(14).mean()
    
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    df_1h = df_15m['close'].resample('1h').last().dropna()
    ema_20_1h = df_1h.ewm(span=20, adjust=False).mean()
    h1_dist_df = (df_1h / ema_20_1h) - 1
    h1_dist_df = h1_dist_df.reindex(df_15m.index, method='ffill')
    df_15m['h1_dist'] = h1_dist_df
    
    trades = []
    
    for idx, row in df_15m.iterrows():
        if pd.isna(row['prev_rsi']) or pd.isna(row['dist_ema']) or pd.isna(row['atr']):
            continue
            
        hour = idx.hour
        close = row['open']
        atr = row['atr']
        
        if hour in BLOCKED_HOURS:
            continue
        
        signal, edge, reason = check_mean_reversion_signal_v2(
            rsi_14=row['prev_rsi'],
            dist_ema_50=row['dist_ema'],
            atr_15m=atr,
            close=close,
            enable_vol_filter=True
        )
        
        if not signal:
            continue
        
        h1_dist = row['h1_dist'] if not pd.isna(row['h1_dist']) else 0
        
        if h1_dist > 0.02 and signal == 'NO':
            continue
        elif h1_dist < -0.02 and signal == 'YES':
            continue
        
        # Slippage: Worse entry price
        adjusted_entry = entry_price * (1 + slippage_pct)
        
        if signal == 'YES':
            won = row['close'] > row['open']
        else:
            won = row['close'] < row['open']
        
        # Exit slippage: Worse exit price
        exit_price = 1.0 if won else 0.0
        adjusted_exit = exit_price * (1 - slippage_pct if won else 1 + slippage_pct)
        
        pnl = (adjusted_exit - adjusted_entry - FEES)
        trades.append({'pnl': pnl, 'result': 'WIN' if won else 'LOSS'})
    
    res_df = pd.DataFrame(trades)
    total_pnl = res_df['pnl'].sum()
    win_rate = len(res_df[res_df['result'] == 'WIN']) / len(res_df) * 100
    return len(res_df), total_pnl, win_rate

if __name__ == "__main__":
    print("=" * 60)
    print("SLIPPAGE SENSITIVITY ANALYSIS")
    print("=" * 60)
    
    # Baseline (no slippage)
    trades_base, pnl_base, wr_base = run_backtest_with_slippage(entry_price=0.50, slippage_pct=0.0)
    print(f"\nBaseline ($0.50 entry, 0% slippage):")
    print(f"  Trades: {trades_base}, PnL: ${pnl_base:.2f}, WR: {wr_base:.2f}%")
    
    # Test 1: 1% Slippage
    trades_1, pnl_1, wr_1 = run_backtest_with_slippage(entry_price=0.50, slippage_pct=0.01)
    print(f"\nWith 1% Slippage:")
    print(f"  Trades: {trades_1}, PnL: ${pnl_1:.2f}, WR: {wr_1:.2f}%")
    print(f"  Delta PnL: ${pnl_1 - pnl_base:.2f}")
    
    # Test 2: 2% Slippage
    trades_2, pnl_2, wr_2 = run_backtest_with_slippage(entry_price=0.50, slippage_pct=0.02)
    print(f"\nWith 2% Slippage:")
    print(f"  Trades: {trades_2}, PnL: ${pnl_2:.2f}, WR: {wr_2:.2f}%")
    print(f"  Delta PnL: ${pnl_2 - pnl_base:.2f}")
    
    # Test 3: Entry at $0.48
    trades_48, pnl_48, wr_48 = run_backtest_with_slippage(entry_price=0.48, slippage_pct=0.0)
    print(f"\nEntry at $0.48 (liquidity constraint):")
    print(f"  Trades: {trades_48}, PnL: ${pnl_48:.2f}, WR: {wr_48:.2f}%")
    print(f"  Delta PnL vs $0.50: ${pnl_48 - pnl_base:.2f}")
    
    # Test 4: Entry at $0.52 (worse price)
    trades_52, pnl_52, wr_52 = run_backtest_with_slippage(entry_price=0.52, slippage_pct=0.0)
    print(f"\nEntry at $0.52 (worse fill):")
    print(f"  Trades: {trades_52}, PnL: ${pnl_52:.2f}, WR: {wr_52:.2f}%")
    print(f"  Delta PnL vs $0.50: ${pnl_52 - pnl_base:.2f}")
    
    print("\n" + "=" * 60)
    print("VERDICT:")
    if pnl_1 > 500:
        print("  1% Slippage: ✅ ROBUST (PnL > $500)")
    elif pnl_1 > 400:
        print("  1% Slippage: ⚠️ MARGINAL (PnL $400-$500)")
    else:
        print("  1% Slippage: ❌ FRAGILE (PnL < $400)")
    print("=" * 60)
