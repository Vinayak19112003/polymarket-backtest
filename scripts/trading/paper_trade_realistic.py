#!/usr/bin/env python3
"""
Realistic Paper Trading Engine
- Uses real Polymarket orderbook
- Simulates real execution with liquidity constraints
- Sends Telegram notifications for all events
- Tracks everything exactly like live trading
"""
import sys
import os
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.features.strategy import check_mean_reversion_signal_v2
from src.bot.orderbook_simulator import OrderbookSimulator
from src.infrastructure.telegram_notifier import TelegramNotifier

class RealisticPaperTrader:
    """Paper trading that mimics real trading exactly."""
    
    def __init__(self, start_balance: float = 100.0):
        self.balance = start_balance
        self.initial_balance = start_balance
        self.positions = {}  # {market: {signal, entry_price, size, timestamp}}
        self.trades = []
        self.signals_generated = 0
        self.orders_placed = 0
        self.orders_filled = 0
        self.orders_rejected = 0
        
        # Initialize components
        self.orderbook = OrderbookSimulator()
        self.notifier = TelegramNotifier()
        
        # Configuration
        self.position_size = 1.0  # Fixed 1 contract per trade
        self.max_positions = 3    # Max concurrent positions
        self.data_file = "data/btcusdt_1m.csv"
        self.log_file = f"logs/paper_trading/session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Market config (replace with real market IDs)
        self.market_id = "btc-15m-yes-token-id"  # Replace with actual token ID
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging directory."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'w') as f:
            f.write(f"=== PAPER TRADING SESSION STARTED ===\n")
            f.write(f"Start Time: {datetime.now()}\n")
            f.write(f"Initial Balance: ${self.initial_balance}\n")
            f.write(f"Position Size: {self.position_size} contracts\n")
            f.write(f"=====================================\n\n")
    
    def _log(self, message: str):
        """Log message to file and console."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
    
    def fetch_market_data(self) -> pd.DataFrame:
        """Fetch and prepare market data."""
        df = pd.read_csv(self.data_file, parse_dates=['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Resample to 15m
        df_15m = df.set_index('timestamp').resample('15min').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        
        # Add indicators (same as backtest)
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
        
        return df_15m.reset_index()
    
    def check_signal(self, row: pd.Series) -> Tuple[Optional[str], float, str]:
        """Check for trading signal using V2 strategy."""
        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            return None, 0.0, ""
        
        dist_ema = (row['close'] / row['ema_50']) - 1
        
        signal, edge, reason = check_mean_reversion_signal_v2(
            rsi_14=row['rsi'],
            dist_ema_50=dist_ema,
            atr_15m=row['atr'],
            close=row['close'],
            enable_vol_filter=True
        )
        
        return signal, edge, reason
    
    def place_order(self, signal: str, entry_price: float, edge: float, reason: str) -> bool:
        """Place limit order with realistic orderbook simulation."""
        self.signals_generated += 1
        
        # Notify signal
        self.notifier.notify_signal(
            signal=signal,
            market="BTC 15m",
            entry_price=entry_price,
            edge=edge,
            reason=reason,
            mode="PAPER"
        )
        
        self._log(f"SIGNAL: {signal} at ${entry_price:.3f} (Edge: {edge:.2f}%, Reason: {reason})")
        
        # Check if we can take more positions
        if len(self.positions) >= self.max_positions:
            self._log(f"REJECTED: Max positions reached ({self.max_positions})")
            self.notifier.notify_order_rejected(signal, "BTC 15m", "Max positions reached", "PAPER")
            self.orders_rejected += 1
            return False
        
        # Check balance
        required = self.position_size * entry_price
        if self.balance < required:
            self._log(f"REJECTED: Insufficient balance (need: ${required:.2f}, have: ${self.balance:.2f})")
            self.notifier.notify_order_rejected(signal, "BTC 15m", "Insufficient balance", "PAPER")
            self.orders_rejected += 1
            return False
        
        # Simulate order placement
        order_id = f"paper_{int(time.time())}_{signal}"
        self.orders_placed += 1
        
        self.notifier.notify_order_placed(
            signal=signal,
            market="BTC 15m",
            size=self.position_size,
            price=entry_price,
            order_id=order_id,
            mode="PAPER"
        )
        
        self._log(f"ORDER PLACED: {order_id} - {signal} {self.position_size} @ ${entry_price:.3f}")
        
        # Simulate orderbook fill
        side = 'BUY' if signal == 'YES' else 'SELL'
        fill_result = self.orderbook.simulate_limit_order_fill(
            token_id=self.market_id,
            side=side,
            price=entry_price,
            size=self.position_size
        )
        
        if fill_result['filled']:
            fill_price = fill_result['fill_price']
            fill_size = fill_result['fill_size']
            slippage = fill_result['slippage']
            
            self.orders_filled += 1
            
            # Record position
            self.positions[order_id] = {
                'signal': signal,
                'entry_price': fill_price,
                'size': fill_size,
                'timestamp': datetime.now(),
                'edge': edge,
                'reason': reason
            }
            
            # Update balance
            self.balance -= fill_size * fill_price
            
            self.notifier.notify_order_filled(
                signal=signal,
                market="BTC 15m",
                size=fill_size,
                fill_price=fill_price,
                slippage=slippage,
                mode="PAPER"
            )
            
            self._log(f"ORDER FILLED: {order_id} - Filled {fill_size} @ ${fill_price:.3f} (Slippage: {slippage:.2f}%)")
            return True
        
        else:
            reason = fill_result['reason']
            self.orders_rejected += 1
            
            self.notifier.notify_order_rejected(signal, "BTC 15m", reason, "PAPER")
            self._log(f"ORDER REJECTED: {order_id} - {reason}")
            return False
    
    def check_exits(self, current_price: float):
        """Check if any positions should be closed."""
        to_close = []
        
        for order_id, pos in self.positions.items():
            signal = pos['signal']
            entry_price = pos['entry_price']
            
            # Simple exit logic (same as backtest)
            if signal == 'YES' and current_price > entry_price:
                to_close.append((order_id, 1.0, 'WIN'))  # Exit at $1.00
            elif signal == 'NO' and current_price < entry_price:
                to_close.append((order_id, 1.0, 'WIN'))
            # Add time-based exit or stop loss here if needed
        
        for order_id, exit_price, result in to_close:
            self.close_position(order_id, exit_price, result)
    
    def close_position(self, order_id: str, exit_price: float, result: str):
        """Close position and calculate PnL."""
        if order_id not in self.positions:
            return
        
        pos = self.positions.pop(order_id)
        entry_price = pos['entry_price']
        size = pos['size']
        signal = pos['signal']
        duration = str(datetime.now() - pos['timestamp']).split('.')
        
        # Calculate PnL
        pnl = (exit_price - entry_price - 0.02) * size  # Include 2% fees
        self.balance += size * exit_price
        
        # Record trade
        self.trades.append({
            'timestamp': datetime.now(),
            'signal': signal,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'size': size,
            'pnl': pnl,
            'result': result,
            'duration': duration
        })
        
        self.notifier.notify_trade_closed(
            signal=signal,
            market="BTC 15m",
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            result=result,
            duration=duration,
            mode="PAPER"
        )
        
        self._log(f"TRADE CLOSED: {signal} - Entry: ${entry_price:.3f}, Exit: ${exit_price:.3f}, PnL: ${pnl:.2f}, Result: {result}")
    
    def run(self, duration_hours: int = 168):  # Default 7 days
        """Run paper trading for specified duration."""
        self._log(f"Starting paper trading for {duration_hours} hours...")
        
        # Send start notification
        self.notifier.send_message("🚀 <b>PAPER TRADING STARTED</b>\n\nMonitoring signals...")
        
        # Implement your trading loop here
        # This is a placeholder - you need to connect to live data stream
        self._log("⚠️ IMPLEMENTATION NEEDED: Connect to live data stream")
        self._log("For now, run backtest in real-time mode or connect to Polymarket WebSocket")
    
    def generate_summary(self):
        """Generate trading summary."""
        wins = sum(1 for t in self.trades if t['result'] == 'WIN')
        losses = len(self.trades) - wins
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = (wins / len(self.trades) * 100) if self.trades else 0
        
        stats = {
            'total_trades': len(self.trades),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'daily_pnl': total_pnl,
            'total_pnl': total_pnl,
            'balance': self.balance,
            'fill_rate': (self.orders_filled / self.orders_placed * 100) if self.orders_placed else 0,
            'avg_slippage': 0.0,  # Calculate from trades
            'avg_entry': sum(t['entry_price'] for t in self.trades) / len(self.trades) if self.trades else 0
        }
        
        self.notifier.notify_daily_summary(stats, mode="PAPER")
        return stats

if __name__ == "__main__":
    trader = RealisticPaperTrader(start_balance=100.0)
    
    # Test Telegram first
    print("Testing Telegram...")
    if not trader.notifier.test_connection():
        print("❌ Fix Telegram setup before continuing")
        sys.exit(1)
    
    print("✅ Telegram working!")
    print("\nStarting paper trading...")
    
    try:
        trader.run(duration_hours=168)  # 7 days
    except KeyboardInterrupt:
        print("\n\nStopping paper trading...")
        trader.generate_summary()
