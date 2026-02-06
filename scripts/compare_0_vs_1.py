
import pandas as pd
import numpy as np
import os

DATA_FILE = "data/backtest_btc_2y.csv"

def get_signals(df_1m, offset_str):
    # Resample
    df_15m = df_1m.resample('15min', offset=offset_str).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    
    # Indicators
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    cond_uptrend = df_15m['close'] > df_15m['ema_50']
    cond_downtrend = df_15m['close'] < df_15m['ema_50']
    
    # Signals
    mask_yes = (cond_uptrend & (df_15m['rsi'] < 43)) | (cond_downtrend & (df_15m['rsi'] < 38))
    mask_no = (cond_uptrend & (df_15m['rsi'] > 62)) | (cond_downtrend & (df_15m['rsi'] > 58))
    
    df_15m['signal'] = None
    df_15m.loc[mask_yes, 'signal'] = 'YES'
    df_15m.loc[mask_no, 'signal'] = 'NO'
    
    return df_15m[['close', 'rsi', 'signal']]

def compare():
    print("Loading data...")
    df_1m = pd.read_csv(DATA_FILE)
    df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'])
    df_1m.set_index('timestamp', inplace=True)
    
    print("Generating Signals :00...")
    s0 = get_signals(df_1m, '0min')
    
    print("Generating Signals :01...")
    s1 = get_signals(df_1m, '1min')
    
    # Alignment:
    # s0 index: 10:00, 10:15...
    # s1 index: 10:01, 10:16...
    # We want to compare the decision made "around the same time".
    # So we align s1 to s0 by shifting s1's index back by 1 minute.
    s1_aligned = s1.copy()
    s1_aligned.index = s1_aligned.index - pd.Timedelta(minutes=1)
    
    # Join
    merged = s0.join(s1_aligned, lsuffix='_0', rsuffix='_1')
    
    # Filter for interesting rows (where signals differ)
    # We care about:
    # 1. Row had signal in 0, but NOT in 1 (Missed trade)
    # 2. Row had signal in 0, and CHANGED in 1 (Flip? unlikely)
    # 3. Row had No signal in 0, but NEW signal in 1 (Late entry)
    
    merged['differs'] = (merged['signal_0'].fillna('NONE') != merged['signal_1'].fillna('NONE'))
    diffs = merged[merged['differs']].copy()
    
    print(f"\nTotal Comparison Windows: {len(merged)}")
    print(f"Total Mismatches:       {len(diffs)} ({len(diffs)/len(merged)*100:.1f}%)")
    
    missed = diffs[diffs['signal_0'].notna() & diffs['signal_1'].isna()]
    new = diffs[diffs['signal_0'].isna() & diffs['signal_1'].notna()]
    flips = diffs[diffs['signal_0'].notna() & diffs['signal_1'].notna()]
    
    print(f"\nType 1: Signal LOST after 1 min (The 'Faders'): {len(missed)}")
    print(f"Type 2: Signal GAINED after 1 min (The 'Laggards'): {len(new)}")
    print(f"Type 3: Signal FLIPPED (Rare): {len(flips)}")
    
    print("\n--- Example: LOST SIGNALS (Why 00 is better) ---")
    if not missed.empty:
        print(missed[['close_0', 'rsi_0', 'signal_0', 'close_1', 'rsi_1']].head(10).to_string())
    
    print("\n--- Analysis ---")
    print("Close_0 vs Close_1 shows price movement in that 1 minute.")
    print("If Price moved AGAINST the signal, RSI normalized, matches 'Fading'.")

if __name__ == "__main__":
    compare()
