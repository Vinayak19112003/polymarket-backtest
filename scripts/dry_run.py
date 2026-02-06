
"""
Paper Trading / Dry Run Script
- Connects to Live Websocket Price Feed
- Computes V2 Features in Real-Time
- Checks V2 Signals (with all filters)
- Logs "Paper Trades" instead of executing
"""
import sys
import os
import time
import logging
import threading
from datetime import datetime

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.price_feed import BinancePriceFeed
from src.bot.features import RealtimeFeatureEngine
from src.features.strategy import check_mean_reversion_signal_v2

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/paper_trading.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PaperTrader")

class PaperTrader:
    def __init__(self):
        self.price_feed = BinancePriceFeed(symbol='BTCUSDT')
        self.feature_engine = RealtimeFeatureEngine()
        self.running = False
        
        # Stats
        self.balance = 100.0 # Paper money
        self.position = None
        self.entry_price = 0.0
        
    def on_candle_close(self, candle):
        """Callback when a 1m candle closes."""
        try:
            # 1. Update Features
            self.feature_engine.add_candle(candle)
            features = self.feature_engine.compute_features()
            
            if not features:
                logger.info("Not enough data for features yet...")
                return
                
            # 2. Check Signals (V2)
            # Use same logic as Live Bot
            rsi = features.rsi_14
            dist = features.dist_ema_50
            atr = features.atr_15m
            close = features.close
            
            # Time-of-Day Filter
            if features.timestamp.hour in [2, 3, 4, 5]:
                logger.debug("Blocked: Asian Session")
                return

            signal, edge, reason = check_mean_reversion_signal_v2(
                rsi, dist, atr, close, enable_vol_filter=True
            )
            
            logger.info(f"RSI: {rsi:.2f} | Trend: {dist:.4f} | ATR: {atr:.2f} | Signal: {signal} ({reason})")
            
            # 3. Execution Logic (Paper)
            if self.position is None:
                if signal:
                    # Enter Position
                    self.position = signal
                    self.entry_price = close
                    logger.info(f"PAPER TRADE: OPEN {signal} @ {close} | Edge: {edge:.2f}")
            else:
                # Exit Logic (Simple: Close at next candle - matching backtest assumptions)
                # Or wait for reverse signal? 
                # Backtest assumes 1-candle hold (15m). Here we proceed candle by candle.
                # Let's close after 15 mins? 
                # Simpler: If we have a position, close it after 15m.
                # For this Dry Run, let's just log "Would Exit" logic.
                pass
                
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

    def start(self):
        logger.info("Starting Paper Trader (Dry Run)...")
        self.running = True
        
        # Connect callbacks
        self.price_feed.register_callback(self.on_candle_close)
        
        # Start Feed
        self.price_feed.start(preload=True)
        
        # Hydrate Feature Engine with preloaded history
        logger.info("Hydrating Feature Engine...")
        history = self.price_feed.candles
        for candle in history:
            self.feature_engine.add_candle(candle)
            
        logger.info(f"Feature Engine hydrated with {len(history)} candles.")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping...")
            self.stop()

    def stop(self):
        self.running = False
        self.price_feed.stop()

if __name__ == "__main__":
    trader = PaperTrader()
    trader.start()
