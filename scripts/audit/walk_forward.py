"""
Walk-Forward Validation Script
Audits the Mean Reversion Strategy for Overfitting.

Methodology:
- Sliding Window: Train on 1 month -> Test on next month.
- For each Training month:
  - Optimize RSI thresholds (Grid Search).
  - Select best params.
- Apply best params to Test month (Out of Sample).
- Accumulate true performance.
"""

import pandas as pd
import numpy as np
from datetime import timedelta

print("="*70)
print("AUDIT: WALK-FORWARD VALIDATION")
print("Checking for Overfitting / Curve Fitting")
print("="*70)

# Load Data
df = pd.read_csv('data/btcusdt_1m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter last 7 months (July 2025 - Jan 2026)
# Need enough data for first training month
end_date = df['timestamp'].max()  # Jan 2026
start_date = pd.to_datetime('2025-07-01')
df = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)

# Add Month column
df['month'] = df['timestamp'].dt.to_period('M')

# Feature Engineering
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

# EMA 50 & Dist
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
df['dist_ema_50'] = df['close'] / df['ema_50'] - 1

# Target (15m future)
df['future_close'] = df['close'].shift(-15)
df['target'] = (df['future_close'] > df['close']).astype(int)

df = df.dropna()
# Filter trading hours (0, 15, 30, 45)
df = df[df['timestamp'].dt.minute.isin([0, 15, 30, 45])].reset_index(drop=True)

# Define Months
months = sorted(df['month'].unique())
print(f"Months available: {[str(m) for m in months]}")

# Simulation
balance = 100.0
history = []

# Grid Search Range
BUY_RANGE = range(30, 48, 2)
SELL_RANGE = range(52, 70, 2)

print("\nStarting Walk-Forward Loop...")
print(f"{'Train':<10} {'Test':<10} {'Best Params':<15} {'Test PnL':<10} {'ROI'}")
print("-" * 65)

total_test_trades = 0

for i in range(len(months) - 1):
    train_month = months[i]
    test_month = months[i+1]
    
    # 1. TRAIN: Minimize Overfitting by finding robust params on Train data
    train_data = df[df['month'] == train_month].copy()
    
    best_pnl = -float('inf')
    best_params = (40, 60) # default
    
    # Grid Search
    for buy_thresh in BUY_RANGE:
        for sell_thresh in SELL_RANGE:
            # Vectorized PnL calc for speed
            # Logic: Dynamic RSI (Trend Adjusted)
            # If Dist < 0 (Downtrend): Buy < buy_thresh - 5
            # If Dist > 0 (Uptrend): Sell > sell_thresh + 5
            # Else standard
            
            # To match the logic being audited, strictly replicate "Dynamic RSI"
            # Logic: 
            # if dist < 0: rsi_buy = baseline - 5
            # if dist > 0: rsi_sell = baseline + 5
            # Note: The "optimized" strat had 43/58. 
            # Let's optimize the BASELINE thresholds.
            
            # Apply signals
            signals = np.zeros(len(train_data))
            rsi = train_data['rsi_14'].values
            dist = train_data['dist_ema_50'].values
            
            # Vectorized Signal Logic
            # Buy Signal:
            #   Standard: rsi < buy_thresh
            #   Downtrend (dist < 0): rsi < (buy_thresh - 5)
            buy_limit = np.where(dist < 0, buy_thresh - 5, buy_thresh)
            
            # Sell Signal:
            #   Standard: rsi > sell_thresh
            #   Uptrend (dist > 0): rsi > (sell_thresh + 5)
            sell_limit = np.where(dist > 0, sell_thresh + 5, sell_thresh)
            
            sigs = np.zeros(len(train_data))
            sigs[rsi < buy_limit] = 1   # YES
            sigs[rsi > sell_limit] = -1 # NO
            
            # Targets
            targs = train_data['target'].values
            
            # Pnl
            # Win: +0.96, Loss: -1.02
            wins = ((sigs == 1) & (targs == 1)) | ((sigs == -1) & (targs == 0))
            losses = ((sigs == 1) & (targs == 0)) | ((sigs == -1) & (targs == 1))
            
            # Filter 0 signals
            traded = (sigs != 0)
            
            # Net PnL (HIGH FRICTION SCENARIO)
            # Assume 5% slippage/spread cost
            # Win: +0.90 (instead of 0.96)
            # Loss: -1.10 (instead of 1.02)
            epoch_pnl = (wins[traded].sum() * 0.90) - (losses[traded].sum() * 1.10)
            
            if epoch_pnl > best_pnl:
                best_pnl = epoch_pnl
                best_params = (buy_thresh, sell_thresh)
    
    # 2. TEST: Run best params on Test Month
    test_data = df[df['month'] == test_month].copy()
    
    buy_thresh, sell_thresh = best_params
    
    rsi = test_data['rsi_14'].values
    dist = test_data['dist_ema_50'].values
    targs = test_data['target'].values
    
    buy_limit = np.where(dist < 0, buy_thresh - 5, buy_thresh)
    sell_limit = np.where(dist > 0, sell_thresh + 5, sell_thresh)
    
    sigs = np.zeros(len(test_data))
    sigs[rsi < buy_limit] = 1
    sigs[rsi > sell_limit] = -1
    
    wins = ((sigs == 1) & (targs == 1)) | ((sigs == -1) & (targs == 0))
    losses = ((sigs == 1) & (targs == 0)) | ((sigs == -1) & (targs == 1))
    traded = (sigs != 0)
    
    test_pnl = (wins[traded].sum() * 0.90) - (losses[traded].sum() * 1.10)
    test_count = traded.sum()
    total_test_trades += test_count
    
    balance += test_pnl
    roi = (balance - 100)
    
    print(f"{str(train_month):<10} {str(test_month):<10} {str(best_params):<15} ${test_pnl:<9.2f} {roi:+.1f}%")
    history.append({'month': test_month, 'pnl': test_pnl})

print("\n" + "="*70)
print("AUDIT RESULTS")
print("="*70)
print(f"Final Balance: ${balance:.2f}")
print(f"True Out-of-Sample ROI: +{balance - 100:.2f}%")
print(f"Total Test Trades: {total_test_trades}")

if balance > 300: # Arbitrary high bar
    print("VERDICT: Strategy is ROBUST. 445% might be slightly lucky but real edge exists.")
elif balance > 150:
    print("VERDICT: Strategy is PROFITABLE but returns are likely inflated by overfitting.")
elif balance > 100:
    print("VERDICT: Strategy is BREAK-EVEN / MARGINAL. Real trading unlikely to match backtest.")
else:
    print("VERDICT: FAILED. Strategy loses money out-of-sample. The 445% was pure overfitting.")
