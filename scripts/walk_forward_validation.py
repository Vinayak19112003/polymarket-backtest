
import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.features.strategy import check_mean_reversion_signal

DATA_FILE = "data/btcusdt_1m.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return None
    df = pd.read_csv(DATA_FILE, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df

def run_backtest_on_window(df_window):
    """Run strategy on a specific window of data."""
    if len(df_window) < 100:
        return {'trades': 0, 'pnl': 0, 'wins': 0}
        
    # Resample to 15m
    df_15m = df_window.set_index('timestamp').resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()
    
    if len(df_15m) < 50:
        return {'trades': 0, 'pnl': 0, 'wins': 0}

    # Features
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # Previous (for signal)
    df_15m['prev_rsi'] = df_15m['rsi'].shift(1)
    df_15m['prev_close'] = df_15m['close'].shift(1)
    df_15m['prev_ema'] = df_15m['ema_50'].shift(1)
    df_15m['dist_ema'] = (df_15m['prev_close'] / df_15m['prev_ema']) - 1
    
    # Apply Strategy (Unified)
    # Vectorized loop for speed or apply
    trades = []
    fees = 0.02
    cost = 0.50
    
    for idx, row in df_15m.iterrows():
        if pd.isna(row['prev_rsi']) or pd.isna(row['dist_ema']):
            continue
            
        signal, _ = check_mean_reversion_signal(row['prev_rsi'], row['dist_ema'])
        
        if signal:
            # Result
            # Entry at Open (row['open']), Exit at Close (row['close'])
            pnl = -cost - fees # Default Loss
            
            if signal == 'YES':
                if row['close'] > row['open']:
                    pnl = (1.0 - cost - fees)
            elif signal == 'NO':
                if row['close'] < row['open']:
                    pnl = (1.0 - cost - fees)
            
            trades.append(pnl)
            
    if not trades:
        return {'trades': 0, 'pnl': 0, 'wins': 0}
        
    # Aggregates
    trades_arr = np.array(trades)
    wins = np.sum(trades_arr > 0)
    total_pnl = np.sum(trades_arr)
    
    return {
        'trades': len(trades),
        'pnl': total_pnl,
        'wins': wins
    }

def run_walk_forward():
    print("Loading data...")
    df = load_data()
    if df is None: return

    # Define Windows (Monthly)
    df['month'] = df['timestamp'].dt.to_period('M')
    unique_months = df['month'].unique()
    
    results = []
    
    print(f"Running Walk-Forward Validation on {len(unique_months)} months...")
    
    # Rolling/Expanding or just per-month? Prompt says "Rolling windows (6m train, 1m test)"
    # But says "run backtest with FIXED strategy parameters". 
    # So we simply evaluate performance on each Test month.
    # The "Train" window is unused if params are fixed, but valid WF would update params.
    # We will assume "Test" window evaluation for stability check.
    
    for month in unique_months:
        # Get data for this month
        mask = (df['month'] == month)
        df_month = df[mask].copy()
        
        res = run_backtest_on_window(df_month)
        
        win_rate = (res['wins'] / res['trades'] * 100) if res['trades'] > 0 else 0
        
        results.append({
            'period': str(month),
            'trades': res['trades'],
            'pnl': res['pnl'],
            'win_rate': win_rate
        })
        print(f"Period {month}: {res['trades']} trades, PnL ${res['pnl']:.2f}, WR {win_rate:.1f}%")

    res_df = pd.DataFrame(results)
    
    # Validation Metrics
    avg_pnl = res_df['pnl'].mean()
    std_pnl = res_df['pnl'].std()
    cv_pnl = std_pnl / avg_pnl if avg_pnl != 0 else 999
    
    print("\n==================================================")
    print("WALK-FORWARD VALIDATION REPORT")
    print("==================================================")
    print(res_df.to_string())
    print("--------------------------------------------------")
    print(f"Average Monthly PnL: ${avg_pnl:.2f}")
    print(f"Std Dev PnL:         ${std_pnl:.2f}")
    print(f"Coefficient of Var:  {cv_pnl:.2f}")
    
    instability_msg = "STABLE"
    if cv_pnl > 2.0:
        instability_msg = "POOR STABILITY (CV > 2.0)"
    elif cv_pnl > 1.0:
        instability_msg = "MODERATE STABILITY (CV > 1.0)"
        
    print(f"Verdict: {instability_msg}")
    
    # Save
    os.makedirs("results", exist_ok=True)
    res_df.to_csv("results/walk_forward_results.csv", index=False)
    print("Saved to results/walk_forward_results.csv")
    
    # Visualization
    try:
        plt.figure(figsize=(10, 6))
        
        ax1 = plt.subplot(2, 1, 1)
        ax1.bar(res_df['period'], res_df['pnl'], color='skyblue')
        ax1.set_title(f'Monthly PnL ({instability_msg})')
        ax1.set_ylabel('PnL ($)')
        plt.setp(ax1.get_xticklabels(), visible=False)
        
        ax2 = plt.subplot(2, 1, 2, sharex=ax1)
        ax2.plot(res_df['period'], res_df['win_rate'], marker='o', color='orange')
        ax2.set_title('Win Rate %')
        ax2.set_ylabel('Win Rate')
        ax2.set_ylim(0, 100)
        ax2.axhline(y=50, color='gray', linestyle='--')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig("results/walk_forward_plot.png")
        print("Saved plot to results/walk_forward_plot.png")
    except Exception as e:
        print(f"Plotting failed: {e}")

if __name__ == "__main__":
    run_walk_forward()
