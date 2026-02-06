
import pandas as pd
import numpy as np
import os
import sys

# Parameters
ENTRY_PRICE = 0.50
FEES_PCT = 0.02
INITIAL_CAPITAL = 1000.0
DATA_FILE = "data/backtest_btc_2y.csv"

def run_offset_analysis():
    if not os.path.exists(DATA_FILE):
        print("Data file not found.")
        return

    print("Loading 1-minute data...")
    df_1m = pd.read_csv(DATA_FILE)
    df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'])
    df_1m.set_index('timestamp', inplace=True)
    
    results = []
    
    print("-" * 65)
    print(f"{'Offset':<8} | {'Trades':<8} | {'Win Rate':<8} | {'ROI %':<10} | {'Status':<10}")
    print("-" * 65)
    
    # Loop through offsets 0 to 14 minutes
    for offset_min in range(15):
        offset_str = f"{offset_min}min"
        
        # Resample with offset
        # Note: pandas offset shifts the BIN LABELS or the BIN EDGES?
        # offset='1min' shifts the standard 00:00-00:15 bin origin.
        df_15m = df_1m.resample('15min', offset=offset_str).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        # Calculation (Identical Logic)
        delta = df_15m['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_15m['rsi'] = 100 - (100 / (1 + rs))
        df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
        
        cond_uptrend = df_15m['close'] > df_15m['ema_50']
        cond_downtrend = df_15m['close'] < df_15m['ema_50']
        
        mask_yes = (cond_uptrend & (df_15m['rsi'] < 43)) | (cond_downtrend & (df_15m['rsi'] < 38))
        mask_no = (cond_uptrend & (df_15m['rsi'] > 62)) | (cond_downtrend & (df_15m['rsi'] > 58))
        
        df_15m['signal'] = None
        df_15m.loc[mask_yes, 'signal'] = 'YES'
        df_15m.loc[mask_no, 'signal'] = 'NO'
        
        # Simulation
        balance = INITIAL_CAPITAL
        wins = 0
        total_trades = 0
        
        for i in range(len(df_15m) - 1):
            row = df_15m.iloc[i]
            sig = row['signal']
            if not sig: continue
            
            # Risk Management (Fixed $10)
            shares = int(10.0 / ENTRY_PRICE) # 20
            if shares < 1: continue
            
            cost = shares * ENTRY_PRICE
            fee_amt = cost * FEES_PCT
            
            won = False
            outcome = df_15m.iloc[i+1]['close'] # Next candle close
            strike = row['close']
            
            if sig == 'YES' and outcome > strike: won = True
            elif sig == 'NO' and outcome < strike: won = True
            
            balance -= (cost + fee_amt)
            if won:
                balance += (shares * 1.00)
                wins += 1
            
            total_trades += 1
            
        roi = ((balance / INITIAL_CAPITAL) - 1) * 100
        wr = (wins / total_trades * 100) if total_trades > 0 else 0
        
        status = "PROFIT" if roi > 0 else "LOSS"
        print(f"{offset_str:<8} | {total_trades:<8} | {wr:.2f}%    | {roi:.2f}%    | {status:<10}")
        
        results.append({
            'offset': offset_min,
            'roi': roi,
            'win_rate': wr,
            'trades': total_trades
        })
        
    # Find Best
    best = max(results, key=lambda x: x['roi'])
    print("-" * 65)
    print(f"BEST PERFORMANCE: Offset {best['offset']}min (:0{best['offset']})")
    print(f"ROI: {best['roi']:.2f}% | Win Rate: {best['win_rate']:.2f}%")

if __name__ == "__main__":
    run_offset_analysis()
