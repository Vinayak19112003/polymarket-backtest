#!/usr/bin/env python3
"""
Dynamic Paper Trading - Automatically tracks current 15m BTC markets
"""
import sys
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

from src.features.strategy import check_mean_reversion_signal_v2
from src.bot.orderbook_simulator import OrderbookSimulator
from src.infrastructure.telegram_notifier import TelegramNotifier
from src.bot.market_finder import DynamicMarketFinder

class DynamicPaperTrader:
    """Paper trader that automatically finds and trades current 15m markets."""
    
    def __init__(self, start_balance: float = 100.0):
        self.balance = start_balance
        self.initial_balance = start_balance
        self.positions = {}
        self.trades = []
        self.signals_count = 0
        self.orders_placed = 0
        self.orders_filled = 0
        self.orders_rejected = 0
        
        # Initialize components
        self.market_finder = DynamicMarketFinder(market_keywords=['btc', 'bitcoin'])
        self.orderbook = OrderbookSimulator()
        self.notifier = TelegramNotifier()
        
        # Configuration
        self.position_size = 1.0
        self.max_positions = 3
        self.check_interval = 60  # Check every 60 seconds
        
        # Current market tracking
        self.current_market_id = None
        self.current_token_id = None
        self.market_question = None
        
        # Logging
        self.log_file = f"logs/paper_trading/dynamic_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'w') as f:
            f.write("=== DYNAMIC PAPER TRADING SESSION ===\n")
            f.write(f"Start Time: {datetime.now()}\n")
            f.write(f"Initial Balance: ${self.initial_balance}\n")
            f.write(f"Mode: Dynamic 15m Market Tracking\n")
            f.write("=" * 60 + "\n\n")
    
    def _log(self, message: str):
        """Log message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
    
    def run_diagnostics(self):
         """Run startup diagnostics."""
         self._log("=== DIAGNOSTIC CHECK ===")
         self._log("Testing Polymarket connectivity...")
         
         # Test market search
         try:
             test_markets = self.market_finder.search_markets(active_only=True)
             self._log(f"Can access markets API: {len(test_markets)} markets found")
         except Exception as e:
             self._log(f"ERROR: Market API failed: {e}")

         # Test orderbook API with a known token (or empty check)
         try:
             # Use a generic token ID or fetch from a market to be sure
             # If we have markets, use one
             if self.market_finder.search_markets(active_only=True):
                  # This is just a test, logic above already verified markets
                  pass
             
             test_token = "16678291189211314787145083999015737376658799626183230671758641503291735614088"  # Example
             test_ob = self.orderbook.fetch_live_orderbook(test_token)
             self._log(f"Can access orderbook API: {test_ob is not None}")
             
         except Exception as e:
             self._log(f"ERROR: Orderbook API failed: {e}")
         
         self._log("=== DIAGNOSTIC COMPLETE ===\n")

    def update_current_market(self) -> bool:
        """Update to current active market."""
        
        # Check if current market expired
        if self.current_market_id and not self.market_finder.is_market_expired():
            # Market still valid
            return True
        
        if self.current_market_id:
            self._log("Current market expired, switching to new market...")
            self.notifier.send_message("Market expired, searching for new market...")
        
        # Find new market
        market = self.market_finder.find_fifteen_minute_market()
        
        if not market:
            self._log("No active 15m market found")
            return False
        
        # Update market info
        market_info = self.market_finder.get_market_info()
        self.current_market_id = market_info.get('condition_id')
        self.current_token_id = market_info['tokens'].get('Yes')
        self.market_question = market_info.get('question')
        
        # VALIDATE TOKEN ID
        if not self.current_token_id:
            self._log("ERROR: No YES token ID found in market")
            return False
        
        self._log(f"   Token ID (YES): {self.current_token_id[:30]}...")
        
        # TEST ORDERBOOK IMMEDIATELY
        test_book = self.orderbook.fetch_live_orderbook(self.current_token_id)
        if not test_book:
            self._log("WARNING: Cannot fetch orderbook for this market")
            # Continue anyway but log warning
        
        time_remaining = market_info.get('time_remaining', 0) / 60
        
        self._log(f"Switched to new market:")
        self._log(f"   Question: {self.market_question}")
        self._log(f"   Market ID: {self.current_market_id}")
        self._log(f"   Time Remaining: {time_remaining:.1f} minutes")
        
        # Notify via Telegram
        message = f"""
<b>MARKET SWITCHED</b>

New Market: {self.market_question}
Time Remaining: {time_remaining:.1f} minutes
Market ID: {self.current_market_id[:16] if self.current_market_id else 'N/A'}...

Now monitoring this market for signals
"""
        self.notifier.send_message(message)
        
        return True
    
    def fetch_live_price_data(self) -> Optional[Dict]:
        """
        Fetch live price data for current market.
        
        For paper trading, we'll use historical data patterns.
        In production, connect to real-time price feed.
        """
        
        # Get current orderbook mid-price
        if not self.current_token_id:
            return None
        
        mid_price = self.orderbook.get_mid_price(self.current_token_id)
        
        if mid_price:
            # Simulate market data structure
            return {
                'timestamp': datetime.now(),
                'close': mid_price,
                'open': mid_price,  # Simplified
                'high': mid_price * 1.01,
                'low': mid_price * 0.99
            }
        
        return None
    
    def calculate_indicators(self, price_history: list) -> Optional[Dict]:
        """
        Calculate indicators from price history.
        
        For realistic paper trading, maintain a rolling window of prices
        and calculate RSI, EMA, ATR in real-time.
        """
        
        if len(price_history) < 50:
            return None  # Need at least 50 periods for EMA50
        
        # Convert to DataFrame
        df = pd.DataFrame(price_history)
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # EMA50
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR
        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # Return latest values
        return {
            'rsi': rsi.iloc[-1],
            'ema_50': ema_50.iloc[-1],
            'atr': atr.iloc[-1],
            'close': df['close'].iloc[-1]
        }
    
    def check_signal(self, indicators: Dict) -> Tuple[Optional[str], float, str]:
        """Check for trading signal."""
        
        if not indicators:
            return None, 0.0, ""
        
        dist_ema = (indicators['close'] / indicators['ema_50']) - 1
        
        signal, edge, reason = check_mean_reversion_signal_v2(
            rsi_14=indicators['rsi'],
            dist_ema_50=dist_ema,
            atr_15m=indicators['atr'],
            close=indicators['close'],
            enable_vol_filter=True
        )
        
        return signal, edge, reason
    
    def place_order(self, signal: str, entry_price: float, edge: float, reason: str) -> bool:
        """Place order with realistic execution simulation."""
        
        self.signals_count += 1
        
        # Notify signal
        self.notifier.notify_signal(
            signal=signal,
            market=self.market_question[:50] if self.market_question else "BTC 15m",
            entry_price=entry_price,
            edge=edge,
            reason=reason,
            mode="PAPER-DYNAMIC"
        )
        
        self._log(f"SIGNAL: {signal} @ ${entry_price:.3f} (Edge: {edge:.2f}%)")
        
        # Check constraints
        if len(self.positions) >= self.max_positions:
            self._log(f"REJECTED: Max positions ({self.max_positions})")
            self.notifier.notify_order_rejected(signal, self.market_question[:50] if self.market_question else "BTC 15m", 
                                                "Max positions", "PAPER-DYNAMIC")
            self.orders_rejected += 1
            return False
        
        required = self.position_size * entry_price
        if self.balance < required:
            self._log(f"REJECTED: Insufficient balance")
            self.notifier.notify_order_rejected(signal, self.market_question[:50] if self.market_question else "BTC 15m",
                                                "Insufficient balance", "PAPER-DYNAMIC")
            self.orders_rejected += 1
            return False
        
        # Simulate order
        order_id = f"dyn_{int(time.time())}_{signal}"
        self.orders_placed += 1
        
        self.notifier.notify_order_placed(
            signal=signal,
            market=self.market_question[:50] if self.market_question else "BTC 15m",
            size=self.position_size,
            price=entry_price,
            order_id=order_id,
            mode="PAPER-DYNAMIC"
        )
        
        # Simulate fill with orderbook
        side = 'BUY' if signal == 'YES' else 'SELL'
        fill_result = self.orderbook.simulate_limit_order_fill(
            token_id=self.current_token_id or "",
            side=side,
            price=entry_price,
            size=self.position_size
        )
        
        if fill_result['filled']:
            fill_price = fill_result['fill_price']
            slippage = fill_result['slippage']
            
            self.orders_filled += 1
            
            self.positions[order_id] = {
                'signal': signal,
                'entry_price': fill_price,
                'size': self.position_size,
                'timestamp': datetime.now(),
                'market_id': self.current_market_id,
                'market_question': self.market_question
            }
            
            self.balance -= self.position_size * fill_price
            
            self.notifier.notify_order_filled(
                signal=signal,
                market=self.market_question[:50] if self.market_question else "BTC 15m",
                size=self.position_size,
                fill_price=fill_price,
                slippage=slippage,
                mode="PAPER-DYNAMIC"
            )
            
            self._log(f"FILLED: {order_id} @ ${fill_price:.3f} (Slippage: {slippage:.2f}%)")
            return True
        
        else:
            self.orders_rejected += 1
            reason = fill_result['reason']
            self.notifier.notify_order_rejected(signal, self.market_question[:50] if self.market_question else "BTC 15m",
                                                reason, "PAPER-DYNAMIC")
            self._log(f"REJECTED: {reason}")
            return False
    
    def monitor_positions(self):
        """Monitor and close positions when market resolves."""
        
        # In real implementation, check market resolution
        # For now, close positions when market expires
        
        to_close = []
        
        for order_id, pos in self.positions.items():
            # Check if position's market has expired
            if pos['market_id'] != self.current_market_id:
                # Old market, needs to be closed
                to_close.append(order_id)
        
        for order_id in to_close:
            # Close with simulated outcome
            # In reality, query Polymarket for actual resolution
            self.close_position(order_id, exit_price=0.5, result='UNKNOWN')
    
    def close_position(self, order_id: str, exit_price: float, result: str):
        """Close position."""
        
        if order_id not in self.positions:
            return
        
        pos = self.positions.pop(order_id)
        entry_price = pos['entry_price']
        signal = pos['signal']
        duration = str(datetime.now() - pos['timestamp']).split('.')[0]
        
        # Calculate PnL
        pnl = (exit_price - entry_price - 0.02) * self.position_size
        self.balance += self.position_size * exit_price
        
        self.trades.append({
            'timestamp': datetime.now(),
            'signal': signal,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'result': result,
            'duration': duration,
            'market': pos['market_question']
        })
        
        self.notifier.notify_trade_closed(
            signal=signal,
            market=pos['market_question'][:50] if pos['market_question'] else "BTC 15m",
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            result=result,
            duration=duration,
            mode="PAPER-DYNAMIC"
        )
        
        self._log(f"CLOSED: {signal} - PnL: ${pnl:.2f}, Result: {result}")
    
    def run(self, duration_hours: int = 168):
        """Run dynamic paper trading."""
        
        self._log(f"Starting dynamic paper trading for {duration_hours} hours...")
        
        # Run diagnostics
        self.run_diagnostics()
        
        # Test Telegram
        if not self.notifier.test_connection():
            self._log("Telegram not working, exiting")
            return
        
        # Send start notification
        self.notifier.send_message("""
<b>DYNAMIC PAPER TRADING STARTED</b>

Mode: Automatic 15m Market Tracking
Balance: $100

Will automatically switch markets every 15 minutes
All trades will be notified here

Good luck!
""")
        
        end_time = datetime.now() + timedelta(hours=duration_hours)
        price_history = []
        
        self._log(f"Running until: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        while datetime.now() < end_time:
            try:
                # Update to current market
                if not self.update_current_market():
                    self._log("No market available, waiting 2 minutes...")
                    time.sleep(120)
                    continue
                
                # Fetch current price
                price_data = self.fetch_live_price_data()
                
                if price_data:
                    price_history.append(price_data)
                    
                    # Keep only recent history (last 100 periods)
                    if len(price_history) > 100:
                        price_history = price_history[-100:]
                    
                    # Calculate indicators
                    indicators = self.calculate_indicators(price_history)
                    
                    if indicators:
                        # Check for signal
                        signal, edge, reason = self.check_signal(indicators)
                        
                        if signal:
                            entry_price = indicators['close']
                            self.place_order(signal, entry_price, edge, reason)
                
                # Monitor positions
                self.monitor_positions()
                
                # Wait before next check
                time.sleep(self.check_interval)
            
            except KeyboardInterrupt:
                self._log("\nInterrupted by user")
                break
            
            except Exception as e:
                self._log(f"Error: {e}")
                self.notifier.notify_error(str(e), "Main loop", "PAPER-DYNAMIC")
                time.sleep(60)
        
        self._log("Trading session ended")
        self.generate_summary()
    
    def generate_summary(self):
        """Generate final summary."""
        
        wins = sum(1 for t in self.trades if t['result'] == 'WIN')
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = (wins / len(self.trades) * 100) if self.trades else 0
        
        stats = {
            'total_trades': len(self.trades),
            'wins': wins,
            'losses': len(self.trades) - wins,
            'win_rate': win_rate,
            'daily_pnl': total_pnl,
            'total_pnl': total_pnl,
            'balance': self.balance,
            'fill_rate': (self.orders_filled / self.orders_placed * 100) if self.orders_placed else 0,
            'avg_slippage': 0.0,
            'avg_entry': sum(t['entry_price'] for t in self.trades) / len(self.trades) if self.trades else 0
        }
        
        self.notifier.notify_daily_summary(stats, mode="PAPER-DYNAMIC")
        
        self._log("=" * 60)
        self._log("FINAL SUMMARY:")
        self._log(f"  Trades: {stats['total_trades']}")
        self._log(f"  Win Rate: {stats['win_rate']:.1f}%")
        self._log(f"  Total PnL: ${stats['total_pnl']:.2f}")
        self._log(f"  Final Balance: ${stats['balance']:.2f}")
        self._log(f"  Fill Rate: {stats['fill_rate']:.1f}%")
        self._log("=" * 60)

if __name__ == "__main__":
    trader = DynamicPaperTrader(start_balance=100.0)
    
    try:
        trader.run(duration_hours=168)  # 7 days
    except KeyboardInterrupt:
        print("\n\nStopping...")
        trader.generate_summary()
