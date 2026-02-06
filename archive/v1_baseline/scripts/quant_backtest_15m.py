
import pandas as pd
import numpy as np
import os
import sys

# Parameters
ENTRY_PRICE = 0.50  # Fixed entry for both YES and NO
                    # "Entry Price (NO): $0.42 or better (inverse of 0.58)"
                    # This means we pay $0.42 to buy the NO side. 
                    # If we win, we get $1.00. Profit = 0.58.
                    # Wait, fees: "Win Payout: $1.00 - Entry Price - Fees"
FEES_PCT = 0.02     # 2% per trade
RISK_PCT = 0.01     # 1% of balance
INITIAL_CAPITAL = 1000.0

DATA_FILE = "data/backtest_btc_2y.csv"

def run_quant_backtest():
    if not os.path.exists(DATA_FILE):
        print("Data file not found. Please run backtest_2y.py first to download data.")
        return

    print("Loading 1-minute data...")
    df_1m = pd.read_csv(DATA_FILE)
    df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'])
    df_1m.set_index('timestamp', inplace=True)
    
    print("Resampling to 15-minute candles...")
    # Resample to 15T. 
    # Logic: Close of 10:00-10:15 candle is the Close at 10:14:59 (or 10:15:00).
    # Pandas resample '15T' usually labels with the left edge (10:00).
    # The 'close' of that bin is what we use for indicators.
    # The 'outcome' is the Close of the NEXT bin.
    
    df_15m = df_1m.resample('15min', offset='1min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()
    
    # --- Indicators ---
    print("Calculating Technical Indicators...")
    
    # RSI 14
    delta = df_15m['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df_15m['rsi'] = 100 - (100 / (1 + rs))
    
    # EMA 50
    df_15m['ema_50'] = df_15m['close'].ewm(span=50, adjust=False).mean()
    
    # --- Signal Generation ---
    # Shifted Logic: We make decision using Close of Candle T.
    # We enter trade.
    # Result determines by Close of Candle T+1.
    
    df_15m['signal'] = None
    
    # Vectorized Signals
    # Scenario A: Uptrend (Close > EMA 50)
    cond_uptrend = df_15m['close'] > df_15m['ema_50']
    
    # Scenario B: Downtrend (Close < EMA 50)
    cond_downtrend = df_15m['close'] < df_15m['ema_50']
    
    # Signals
    # YES (Long)
    # Uptrend: RSI < 43. Downtrend: RSI < 38
    mask_yes = (cond_uptrend & (df_15m['rsi'] < 43)) | (cond_downtrend & (df_15m['rsi'] < 38))
    
    # NO (Short)
    # Uptrend: RSI > 62. Downtrend: RSI > 58
    mask_no = (cond_uptrend & (df_15m['rsi'] > 62)) | (cond_downtrend & (df_15m['rsi'] > 58))
    
    df_15m.loc[mask_yes, 'signal'] = 'YES'
    df_15m.loc[mask_no, 'signal'] = 'NO'
    
    # --- Backtest Loop ---
    print("Simulating trades...")
    
    balance = INITIAL_CAPITAL
    trades = []
    equity = [INITIAL_CAPITAL]
    
    # Iterate
    # We look at row i to signal. Trade outcome is row i+1 close.
    # Note: Polymarket settlement is often based on specific strike at specific time.
    # Here win condition: 
    # YES: Future > Entry Price (Wait, User said "Entry Price (YES): $0.42").
    # Is "Entry Price" the COST of the option? Or the STRIKE price of BTC?
    # Context: "Entry Price (YES): $0.42" refers to the OPTION COST.
    # Win Condition: "Future Price (t+15m) > Entry Price".
    # This part is ambiguous. Usually:
    # YES wins if Spot Price > Strike Price.
    # NO wins if Spot Price <= Strike Price.
    # The user says: "YES: Future Price (t+15m) > Entry Price". 
    # Does "Entry Price" mean "Spot Price at Entry"? 
    # Usually "Entry Price" in trading means the price you bought at. 
    # But in Polymarket "Strike" is what matters. 
    # Given the previous context was "Market Resolution", typically Start Price vs End Price.
    # I will assume:
    # Strike Price = Spot Price at Candle Close (At Entry).
    # YES WINS if Next Close > Strike Price.
    # NO WINS if Next Close < Strike Price.
    # COST = $0.42.
    
    for i in range(len(df_15m) - 1):
        row = df_15m.iloc[i]
        next_row = df_15m.iloc[i+1] # Outcome
        
        sig = row['signal']
        if not sig:
            continue
            
        # Entry Logic
        strike_price = row['close'] # The spot price at signal time
        
        # Risk Management (FLAT BETTING for clear analysis)
        # 1 Unit = $10.00
        shares = 20 # Fixed 20 shares (~$8.40 risk)
        shares = int(10.0 / ENTRY_PRICE)
        
        if shares < 1:
            continue
            
        cost = shares * ENTRY_PRICE
        fees = cost * FEES_PCT # User: "Fees: 2% per trade". Usually means 2% of volume? Or flat 2%? 
                               # "Win Payout: $1.00 - Entry Price - Fees." -> PnL = 1 - 0.42 - Fees.
                               # Likely Fees is per share? $0.02? Or 2% of $0.42? 
                               # "Fees: 2% per trade". Let's assume on Notional or Cost.
                               # Let's simplify: Net PnL on WIN = ($1.00 - $0.42) - ($0.42 * 0.02)? 
                               # User wrote: "Win Payout: $1.00 - Entry Price - Fees".
                               # If Fees is 2%, let's assume 2% of the trade amount ($0.42). 
                               # 0.42 * 0.02 = 0.0084.
                               # Total Cost = $0.42.
                               # Win Return = $1.00.
                               # Profit = 1.00 - 0.42 - (Cost * 0.02) = 0.5716?
                               # Let's stick to explicit instruction if possible.
                               # Let's assume Fee is 2% of ENTRY COST. 
        
        fee_amt = cost * FEES_PCT
        
        # Determine Win
        won = False
        outcome_price = next_row['close']
        
        if sig == 'YES':
            if outcome_price > strike_price:
                won = True
        elif sig == 'NO':
            if outcome_price < strike_price:
                won = True
        
        # Calculation
        if won:
            # GROSS Payout = shares * $1.00
            # Profit = Gross - Cost - Fees
            # Wait, user said "Win Payout: $1.00 - Entry Price - Fees".
            # This refers to PER SHARE profit.
            # So Total PnL = shares * (1.00 - ENTRY_PRICE - (ENTRY_PRICE*FEES_PCT))
            # Wait, fees might be flat 2% (0.02). 
            # I will assume standard Polymarket style: Fee is taken on winning? No.
            # I will calculate: 
            # Balance -= Cost
            # If Win: Balance += Shares * (1.00 - Fee_per_share?)
            # Let's use simple accounting:
            # Balance -= (Cost + Fee)
            # If Win: Balance += (Shares * 1.00)
            
            # Re-reading: "Fees: 2% per trade."
            # Logic: 
            # Debit: Cost
            # Debit: Fee (2% of Cost)
            # Credit: Payout (Shares * 1.00) if Win
            
            balance -= (cost + fee_amt)
            if won:
                balance += (shares * 1.00)
                pnl = (shares * 1.00) - (cost + fee_amt)
            else:
                pnl = -(cost + fee_amt)
        else:
            # Loss
            balance -= (cost + fee_amt)
            pnl = -(cost + fee_amt)
            
        trades.append({
            'timestamp': row.name, # Signal Time
            'signal': sig,
            'pnl': pnl,
            'result': 'WIN' if won else 'LOSS',
            'shares': shares,
            'balance': balance
        })
        equity.append(balance)
    
    # --- Results ---
    df_trades = pd.DataFrame(trades)
    
    print("-" * 30)
    print("QUANTITATIVE BACKTEST REPORT")
    print("-" * 30)
    
    if len(df_trades) == 0:
        print("No trades triggered.")
        return

    final_balance = equity[-1]
    roi_pct = ((final_balance / INITIAL_CAPITAL) - 1) * 100
    win_rate = (df_trades['result'] == 'WIN').mean() * 100
    
    print(f"Initial Capital: ${INITIAL_CAPITAL}")
    print(f"Final Capital:   ${final_balance:.2f}")
    print(f"Total ROI:       {roi_pct:.2f}%")
    print(f"Total Trades:    {len(df_trades)}")
    print(f"Win Rate:        {win_rate:.2f}%")
    
    # Month by Month PnL
    df_trades['month'] = df_trades['timestamp'].dt.to_period('M')
    monthly = df_trades.groupby('month')['pnl'].sum()
    
    print("\n[Month-by-Month PnL]")
    print(monthly.to_string())
    
    # Save results
    df_trades.to_csv('logs/quant_trades_15m.csv', index=False)

if __name__ == "__main__":
    run_quant_backtest()
