
import sys
import os
import pandas as pd
from datetime import datetime
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bot.features import RealtimeFeatureEngine

def run_backtest():
    print("="*60)
    print("EXTENDED BACKTEST: PAST 10 DAYS (V2 Strategy)")
    print("="*60)
    
    # Load Data
    data_path = 'data/btcusdt_1m.csv'
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # We want to test approx Jan 28 to Feb 7
    # But we use all data for warm up
    # We start LOGGING trades from Jan 28
    
    start_logging_date = pd.Timestamp('2026-01-28')
    
    print(f"Total Data Points: {len(df)}")
    print(f"Range: {df['timestamp'].min()} - {df['timestamp'].max()}")
    print(f"Analysis Start: {start_logging_date}")
    
    # Initialize Engine
    engine = RealtimeFeatureEngine()
    
    trades = [] # List of closed trades
    open_position = None # {signal, entry_price, entry_time, expiry_time}
    
    # Stats
    wins = 0
    losses = 0
    total_pnl = 0.0 # Assuming $10 bet per trade
    
    print(f"\nRunning Simulation...")
    
    for i, row in df.iterrows():
        ts = row['timestamp']
        price = row['close']
        
        # 1. Check for Exits (at expiry)
        if open_position:
            if ts >= open_position['expiry_time']:
                # Close Trade
                direction = open_position['signal']
                entry = open_position['entry_price']
                
                # Determine Result (Binary Mock)
                # In 15m markets, if Price > Entry => YES Wins, NO Loses
                # (Ignoring Strike nuances, assuming Strike ~ Entry at creation)
                
                pnl = 0
                outcome = "LOSS"
                
                if price > entry:
                    if direction == 'YES':
                        outcome = "WIN"
                        pnl = 10 # profit (assuming approx 50/50 odds for simplicity or just $10 win)
                        # Actually Polymarket prices vary. Let's assume we bought at market price ~0.50
                        # Profit = $1 - $0.50 = $0.50 per share.
                        # Let's just track Win/Loss count primarily.
                    else: # NO
                        outcome = "LOSS"
                        pnl = -10
                elif price < entry:
                    if direction == 'NO':
                        outcome = "WIN"
                        pnl = 10
                    else: # YES
                        outcome = "LOSS"
                        pnl = -10
                
                trade_record = {
                    'entry_time': open_position['entry_time'],
                    'exit_time': ts,
                    'signal': direction,
                    'entry_price': entry,
                    'exit_price': price,
                    'outcome': outcome,
                    'pnl': pnl,
                    'reason': open_position.get('reason', '')
                }
                trades.append(trade_record)
                
                if outcome == "WIN": wins += 1
                else: losses += 1
                total_pnl += pnl
                
                # Log Result
                # print(f"[{ts}] CLOSED {direction} | {outcome} | PnL: ${pnl} | Price: {price:.2f}")
                
                open_position = None

        # 2. Feed Candle
        candle = {
            'timestamp': row['timestamp'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        }
        engine.add_candle(candle)
        
        # 3. Check for New Signal (Only if no open position? Or parallel?
        # Real bot can have multiple positions. For simple backtest, let's do 1 at a time to avoid overlap complexity)
        # But we should allow overlap if we want to test frequency.
        # Let's stick to: If we have a position, we skip new signals? 
        # Or better: We assume we enter every 15m if signal exists. But simplified to 1 concurrent for clarity.
        
        # Check at :00, :15, :30, :45
        if ts.minute % 15 == 0 and open_position is None:
            
            features = engine.compute_features()
            if features:
                # Only analyze after logging date
                if ts >= start_logging_date:
                    
                    prob = engine.predict_probability(features)
                    signal, edge = engine.check_signal(features, prob)
                    
                    # Hack: The updated strategy returns (signal, edge, reason) but previous signature might be (signal, edge)
                    # Let's handle both just in case, though we know we updated it.
                    # check_signal is in RealtimeFeatureEngine (features.py).
                    # It calls strategy.check_mean_reversion_signal_v2 which returns 3 values.
                    # But features.check_signal implementation in features.py usually returns (signal, edge).
                    # Let's check features.py...
                    # Wait, in features.py: 
                    # signal, edge, reason = check_mean_reversion_signal_v2(...)
                    # return (signal, edge) <--- It drops reason!
                    
                    if signal:
                        # Open Trade
                        # Expiry is 15 mins later
                        expiry = ts + pd.Timedelta(minutes=15)
                        
                        open_position = {
                            'signal': signal,
                            'entry_price': price,
                            'entry_time': ts,
                            'expiry_time': expiry,
                            'edge': edge
                        }
                        # print(f"[{ts}] OPEN {signal} | Edge: {edge:.2f} | Price: {price:.2f}")

    # Summary
    print("\n" + "="*30)
    print("BACKTEST RESULTS (10 Days)")
    print("="*30)
    
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    print(f"Period: {start_logging_date.date()} to {df['timestamp'].max().date()}")
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Approx PnL ($10/trade): ${total_pnl}")
    
    # Save to CSV
    if trades:
        res_df = pd.DataFrame(trades)
        res_df.to_csv('results/backtest_10d.csv', index=False)
        print("\nDetailed results saved to results/backtest_10d.csv")
        
        # Breakdown by Signal
        print("\nBreakdown by Type:")
        print(res_df.groupby('signal')['outcome'].value_counts())

if __name__ == "__main__":
    run_backtest()
