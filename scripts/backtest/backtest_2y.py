"""
2-YEAR BACKTEST (Jan 2024 - Jan 2026)
Strategy: Dynamic RSI + Smart Execution (Assumed in pricing)
Risk: 1% Fixed
"""
import pandas as pd
import numpy as np

print("="*60)
print("2-YEAR BACKTEST: DYNAMIC RSI (MEAN REVERSION)")
print("="*60)

df = pd.read_csv('data/btcusdt_1m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Uses full 2 years automatically (no filtering)
# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

# EMA
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
df['dist_ema_50'] = df['close'] / df['ema_50'] - 1

# Target
df['future_close'] = df['close'].shift(-15)
df['target'] = (df['future_close'] > df['close']).astype(int)

df = df.dropna()
df = df[df['timestamp'].dt.minute.isin([0, 15, 30, 45])].reset_index(drop=True)

# =========================================================
# SENSITIVITY ANALYSIS: The "Fill Price" Trap
# =========================================================
# We test 3 scenarios:
# 1. OPTIMISTIC (Limit Order): Get filled at 0.42 (Cheap)
# 2. REALISTIC (Mid-Market):   Get filled at 0.45 (Fair)
# 3. PESSIMISTIC (Market Buy): Get filled at 0.48 (Expensive)

# =========================================================
# FIXED PRICE BACKTEST: ENTRY @ $0.50
# =========================================================

balance = 100.0
equity = [100.0]
trades = []

print(f"\n{'DATE':<20} {'SIDE':<5} {'RESULT':<5} {'PnL':<6} {'BAL'}")
print("-" * 65)

for i in range(len(df)):
    row = df.iloc[i]
    
    # Signals
    rsi = row['rsi_14']
    dist = row['dist_ema_50']
    
    rsi_buy = 43
    rsi_sell = 58
    if dist < 0: rsi_buy = 38
    if dist > 0: rsi_sell = 62
        
    signal = None
    if rsi < rsi_buy: signal = 'YES'
    elif rsi > rsi_sell: signal = 'NO'
    
    if not signal: continue
    
    # Execution
    # USER REQUEST: Fixed entry at 0.50
    entry_price = 0.50 
    
    # Outcome
    won = (signal == 'YES' and row['target'] == 1) or (signal == 'NO' and row['target'] == 0)
    result = 'WIN' if won else 'LOSS'
    
    shares = 1.0 / entry_price # 2 shares
    cost = 1.0
    
    if won:
        # Payout $1.00 per share - 2% fee
        # Revenue = 2 * 1.00 = $2.00
        # Fees = $0.04
        # Profit = 2.00 - 0.04 - 1.00 = +0.96
        payout = shares * 0.98 
        pnl = payout - cost
    else:
        pnl = -cost
        
    balance += pnl
    equity.append(balance)
    
    trades.append({
        'timestamp': row['timestamp'],
        'pnl': pnl
    })

print("-" * 65)
print(f"FINAL BALANCE: ${balance:.2f}")

# Calculate Stats
wins = sum(1 for t in trades if t['pnl'] > 0)
total = len(trades)
win_rate = (wins/total*100) if total > 0 else 0

print(f"Total Trades: {total}")
print(f"Win Rate:     {win_rate:.1f}%")
print(f"ROI:          {balance-100:.1f}%")
print("=" * 65)
exit()

with open(f"{output_dir}/backtest_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\n[OK] Saved: {output_dir}/backtest_results.json")

# 2. Save Trades (CSV) - Full detail format
tdf_export = tdf[['timestamp', 'slug', 'side', 'p_up', 'entry_price', 'fill_price', 'result', 'pnl', 'fees', 'balance']].copy()
tdf_export.to_csv(f"{output_dir}/backtest_trades.csv", index=False)
print(f"[OK] Saved: {output_dir}/backtest_trades.csv")

# 3. Save Equity Curve (CSV)
eq_df = pd.DataFrame({"trade_num": range(len(equity)), "balance": equity})
eq_df.to_csv(f"{output_dir}/backtest_equity.csv", index=False)
print(f"[OK] Saved: {output_dir}/backtest_equity.csv")


