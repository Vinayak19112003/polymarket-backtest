"""
Binance WebSocket Price Feed for Real-Time BTC Data
"""

import json
import time
import threading
import requests
from collections import deque
from datetime import datetime
from typing import Callable, Dict, List, Optional
import websocket
from . import config


class BinancePriceFeed:
    """Real-time BTC price feed from Binance WebSocket."""
    
    def __init__(self, symbol: str = "btcusdt", max_candles: int = 2000):
        self.symbol = symbol.lower()
        self.ws = None
        self.running = False
        self.candles = []
        self.current_candle = None
        self._lock = threading.Lock()
        
        # Callbacks for new candles
        self.callbacks = []

    def register_callback(self, callback):
        """Register a function to be called on new candle."""
        self.callbacks.append(callback)
        
    def add_callback(self, callback: Callable):
        """Add callback for price updates."""
        self.callbacks.append(callback)
        
    def get_candles_df(self):
        """Get candles as pandas DataFrame."""
        import pandas as pd
        with self._lock:
            if not self.candles:
                return pd.DataFrame()
            df = pd.DataFrame(list(self.candles))
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
    
    def get_current_price(self) -> Optional[float]:
        """Get current BTC price."""
        with self._lock:
            if self.current_candle:
                return self.current_candle.get('close')
            # Fallback to last historical candle
            if self.candles:
                return self.candles[-1].get('close')
        return None
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            kline = data.get('k', {})
            
            offset = getattr(config, 'PRICE_OFFSET_USD', 0.0)
            
            candle = {
                'timestamp': datetime.utcfromtimestamp(kline['t'] / 1000),
                'open': float(kline['o']) + offset,
                'high': float(kline['h']) + offset,
                'low': float(kline['l']) + offset,
                'close': float(kline['c']) + offset,
                'volume': float(kline['v']),
                'is_closed': kline['x']
            }
            
            with self._lock:
                self.current_candle = candle
                
                # If candle is closed, add to history
                if kline['x']:
                    self.candles.append({
                        'timestamp': candle['timestamp'],
                        'open': candle['open'],
                        'high': candle['high'],
                        'low': candle['low'],
                        'close': candle['close'],
                        'volume': candle['volume']
                    })
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(candle)
                except Exception as e:
                    print(f"Callback error: {e}")
                    
        except Exception as e:
            print(f"Message parse error: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
    
    def _on_open(self, ws):
        """Handle WebSocket open."""
        print(f"Connected to Binance WebSocket for {self.symbol.upper()}")
    
    def _connect(self):
        """Establish WebSocket connection."""
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_1m"
        
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                print(f"Connection error: {e}")
            
            if self.running:
                print("Reconnecting in 5 seconds...")
                time.sleep(5)
    
    def preload_history(self, num_candles: int = 200) -> int:
        """
        Preload historical candles from Binance REST API.
        This allows features to be computed immediately.
        
        Returns:
            Number of candles loaded
        """
        try:
            print(f"Preloading {num_candles} candles...")
            
            # Pagination Logic
            # Binance limit is 1000 per request.
            # We calculate the start time needed to get 'num_candles' back.
            # Start Time = Now - (N minutes)
            
            end_ts = int(time.time() * 1000)
            start_ts = end_ts - (num_candles * 60 * 1000)
            
            final_candles = []
            current_start = start_ts
            
            while len(final_candles) < num_candles:
                # Ask for 1000 at a time
                params = {
                    'symbol': self.symbol.upper(),
                    'interval': '1m',
                    'startTime': current_start,
                    'limit': 1000 
                }
                
                url = "https://api.binance.com/api/v3/klines"
                resp = requests.get(url, params=params, timeout=10)
                
                if resp.status_code != 200:
                    print(f"Binance Error: {resp.text}")
                    break
                    
                data = resp.json()
                if not data:
                    break
                    
                offset = getattr(config, 'PRICE_OFFSET_USD', 0.0)
                
                for kline in data:
                    candle = {
                        'timestamp': datetime.utcfromtimestamp(kline[0] / 1000),
                        'open': float(kline[1]) + offset,
                        'high': float(kline[2]) + offset,
                        'low': float(kline[3]) + offset,
                        'close': float(kline[4]) + offset,
                        'volume': float(kline[5])
                    }
                    final_candles.append(candle)
                
                # Advance cursor
                last_ts = data[-1][0]
                current_start = last_ts + 60000 
                
                if last_ts >= end_ts:
                    break
                    
            # Deduplicate just in case
            seen = set()
            unique_candles = []
            for c in final_candles:
                if c['timestamp'] not in seen:
                    seen.add(c['timestamp'])
                    unique_candles.append(c)
            
            # Sort
            unique_candles.sort(key=lambda x: x['timestamp'])
             
            # Keep last N (if we fetched slightly more)
            unique_candles = unique_candles[-num_candles:]
            
            with self._lock:
                self.candles = unique_candles
                
            print(f"Preloaded {len(self.candles)} historical candles")
            return len(self.candles)
            
        except Exception as e:
            print(f"Failed to preload history: {e}")
            return 0
    
    def start(self, preload: bool = True):
        """Start the price feed in background thread."""
        if preload:
            self.preload_history(3000)
        
        self.running = True
        thread = threading.Thread(target=self._connect, daemon=True)
        thread.start()
        print("Binance price feed started")
        
    def stop(self):
        """Stop the price feed."""
        self.running = False
        if self.ws:
            self.ws.close()
        print("Binance price feed stopped")
    
    def get_price_at_15m_start(self, market_open_ts: int = None) -> Optional[float]:
        """
        Get BTC price at the exact 15-minute window start.
        
        Args:
            market_open_ts: Unix timestamp of market open (e.g., from slug)
                           If None, uses current 15m window start
        
        Returns:
            BTC price at that exact moment (OPEN price of that minute candle)
        """
        try:
            if market_open_ts is None:
                # Calculate current 15m window start
                now = int(time.time())
                market_open_ts = (now // 900) * 900  # Round down to nearest 15m
            
            # Get the 1-minute candle at that exact timestamp
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': self.symbol.upper(),
                'interval': '1m',
                'startTime': market_open_ts * 1000,  # ms
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                # Return OPEN price of that candle
                open_price = float(data[0][1])
                offset = getattr(config, 'PRICE_OFFSET_USD', 0.0)
                return open_price + offset
            
            return None
            
        except Exception as e:
            print(f"Error getting price at timestamp: {e}")
            return None


def test_feed():
    """Test the price feed."""
    feed = BinancePriceFeed()
    
    def on_price(candle):
        print(f"[{candle['timestamp']}] BTC: ${candle['close']:,.2f} {'(closed)' if candle['is_closed'] else ''}")
    
    feed.add_callback(on_price)
    feed.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        feed.stop()


if __name__ == "__main__":
    test_feed()
