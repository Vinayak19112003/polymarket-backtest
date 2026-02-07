
import sys
import os
import pandas as pd
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Correct import based on findings
from src.bot.features import RealtimeFeatureEngine

def run_backtest():
    print("="*60)
    print("BACKTESTING YESTERDAY (2026-02-06)")
    print("="*60)
    
    # Load Data
    data_path = 'data/btcusdt_1m.csv'
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for 2026-02-06 only? NO. We need warm up.
    # But we only want to analyze 2026-02-06.
    target_date = pd.Timestamp('2026-02-06').date()
    
    print(f"Total Data Points (inc. warmup): {len(df)}")
    print(f"Range: {df['timestamp'].min()} - {df['timestamp'].max()}")
    
    # Initialize Engine
    engine = RealtimeFeatureEngine()
    
    trades = []
    signals_log = []
    
    print(f"\nRunning Simulation (Simulating Real-Time Feed)...")
    print(f"Signals will only be logged for {target_date}")
    
    for i, row in df.iterrows():
        ts = row['timestamp']
        
        candle = {
            'timestamp': row['timestamp'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        }
        
        # 1. Feed Candle (Always feed for warm up)
        engine.add_candle(candle)
        
        # 2. Check for Signal at :00, :15, :30, :45
        if ts.minute % 15 == 0:
            
            # Compute Snapshot
            features = engine.compute_features()
            
            if features:
                # Check target date
                if ts.date() == target_date:
                    
                    # Get Probability (Mock or Real if model loaded)
                    prob = engine.predict_probability(features)
                    
                    # Check Signal
                    signal, edge = engine.check_signal(features, prob)
                    
                    # Log state for debugging
                    rsi = features.rsi_14
                    
                    if signal:
                        print(f"[{ts}] [ALERT] SIGNAL: {signal} | Edge: {edge:.2f} | RSI: {rsi:.2f}")
                        signals_log.append({
                            'timestamp': ts,
                            'signal': signal,
                            'edge': edge,
                            'rsi': rsi,
                            'price': row['close']
                        })
                    
                    # Debug print periodically
                    if ts.minute == 0 and ts.hour % 4 == 0:
                       print(f"[{ts}] Heartbeat | RSI: {rsi:.2f} | Trend: {features.dist_ema_50:.4f}")

    print("\nSimulation Complete.")
    print(f"Total Signals: {len(signals_log)}")
    
    if signals_log:
        out_file = 'results/yesterday_signals.csv'
        os.makedirs('results', exist_ok=True)
        pd.DataFrame(signals_log).to_csv(out_file, index=False)
        print(f"Signals saved to {out_file}")
        
    # Analyze frequency
    yes_signals = len([s for s in signals_log if s['signal'] == 'YES'])
    no_signals = len([s for s in signals_log if s['signal'] == 'NO'])
    print(f"YES Signals: {yes_signals}")
    print(f"NO Signals: {no_signals}")

if __name__ == "__main__":
    run_backtest()
