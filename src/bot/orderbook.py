"""
Step 2: CLOB Orderbook Polling
Polls real orderbook from Polymarket CLOB REST API every 1 second.
"""
import requests
import json
import time
import csv
import os
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List
from . import config

# Configuration
CLOB_API = "https://clob.polymarket.com"
POLL_INTERVAL = config.ORDERBOOK_POLL_SECONDS  # Load from config
MARKET_FILE = "active_btc15m_market.json"
SNAPSHOT_FILE = "orderbook_snapshots.csv"


@dataclass
class OrderbookSnapshot:
    """Single orderbook snapshot."""
    timestamp: str
    token_id: str
    side: str  # "YES" or "NO"
    best_bid: float
    best_ask: float
    bid_size: float
    ask_size: float
    spread: float
    mid_price: float


class CLOBOrderbookPoller:
    """Polls CLOB REST API for real orderbook data."""
    
    def __init__(self):
        self.yes_token_id: Optional[str] = None
        self.no_token_id: Optional[str] = None
        self.market_slug: Optional[str] = None
        
        # Current orderbook state
        self.yes_bid: float = 0.0
        self.yes_ask: float = 0.0
        self.yes_bid_size: float = 0.0
        self.yes_ask_size: float = 0.0
        
        self.no_bid: float = 0.0
        self.no_ask: float = 0.0
        self.no_bid_size: float = 0.0
        self.no_ask_size: float = 0.0
        
        self.last_update: Optional[datetime] = None
        self.running = False
        self._lock = threading.Lock()
        
        # Initialize CSV file
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist."""
        if not os.path.exists(SNAPSHOT_FILE):
            with open(SNAPSHOT_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'slug', 'yes_bid', 'yes_ask', 'yes_bid_size', 'yes_ask_size',
                    'no_bid', 'no_ask', 'no_bid_size', 'no_ask_size', 'yes_spread', 'no_spread'
                ])
    
    def load_market(self) -> bool:
        """Load market data from resolver output."""
        try:
            if os.path.exists(MARKET_FILE):
                with open(MARKET_FILE, 'r') as f:
                    data = json.load(f)
                
                self.market_slug = data.get('slug')
                self.yes_token_id = data.get('yes_token_id')
                self.no_token_id = data.get('no_token_id')
                
                if self.yes_token_id and self.no_token_id:
                    print(f"Loaded market: {self.market_slug}")
                    print(f"  YES: {self.yes_token_id[:30]}...")
                    print(f"  NO: {self.no_token_id[:30]}...")
                    return True
                    
            print("No valid market data found")
            return False
            
        except Exception as e:
            print(f"Error loading market: {e}")
            return False
    
    def fetch_orderbook(self, token_id: str) -> Optional[Dict]:
        """Fetch orderbook for a token from CLOB API."""
        try:
            url = f"{CLOB_API}/book?token_id={token_id}"
            r = requests.get(url, timeout=10)
            
            if r.status_code == 429:
                time.sleep(1)
                return None
            
            if r.status_code != 200:
                return None
            
            data = r.json()
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            
            # Parse best bid (Highest Price)
            best_bid = 0.0
            bid_size = 0.0
            
            # Helper to parse price/size from item
            def parse_item(item):
                if isinstance(item, dict):
                    return float(item.get('price', 0)), float(item.get('size', 0))
                elif isinstance(item, list):
                    return float(item[0]), float(item[1]) if len(item) > 1 else 0
                return 0.0, 0.0

            if bids:
                # API seems to return bids sorted ascending (0.01 -> 0.99). Best bid is LAST.
                # But to be safe, let's find the max price
                try:
                    parsed_bids = [parse_item(b) for b in bids]
                    # Sort by price descending
                    parsed_bids.sort(key=lambda x: x[0], reverse=True)
                    if parsed_bids:
                        best_bid = parsed_bids[0][0]
                        bid_size = parsed_bids[0][1]
                except Exception as ex:
                    print(f"Bid parse error: {ex}")
            
            # Parse best ask (Lowest Price)
            best_ask = 0.0
            ask_size = 0.0
            if asks:
                # API seems to return asks sorted descending (0.99 -> 0.01). Best ask is LAST.
                # To be safe, find min price
                try:
                    parsed_asks = [parse_item(a) for a in asks]
                    # Sort by price ascending
                    parsed_asks.sort(key=lambda x: x[0])
                    if parsed_asks:
                        best_ask = parsed_asks[0][0]
                        ask_size = parsed_asks[0][1]
                except Exception as ex:
                    print(f"Ask parse error: {ex}")
            
            return {
                'bid': best_bid,
                'ask': best_ask,
                'bid_size': bid_size,
                'ask_size': ask_size
            }
            
        except Exception as e:
            return None
    
    def poll_once(self) -> bool:
        """Poll orderbook once and update state."""
        if not self.yes_token_id or not self.no_token_id:
            return False
        
        try:
            # Fetch YES orderbook
            yes_book = self.fetch_orderbook(self.yes_token_id)
            if yes_book:
                with self._lock:
                    self.yes_bid = yes_book['bid']
                    self.yes_ask = yes_book['ask']
                    self.yes_bid_size = yes_book['bid_size']
                    self.yes_ask_size = yes_book['ask_size']
            
            # Fetch NO orderbook
            no_book = self.fetch_orderbook(self.no_token_id)
            if no_book:
                with self._lock:
                    self.no_bid = no_book['bid']
                    self.no_ask = no_book['ask']
                    self.no_bid_size = no_book['bid_size']
                    self.no_ask_size = no_book['ask_size']
                    self.last_update = datetime.utcnow()
            
            return yes_book is not None and no_book is not None
            
        except Exception as e:
            print(f"Poll error: {e}")
            return False
    
    def save_snapshot(self):
        """Save current state to CSV."""
        try:
            with open(SNAPSHOT_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.utcnow().isoformat(),
                    self.market_slug or '',
                    self.yes_bid,
                    self.yes_ask,
                    self.yes_bid_size,
                    self.yes_ask_size,
                    self.no_bid,
                    self.no_ask,
                    self.no_bid_size,
                    self.no_ask_size,
                    round(self.yes_ask - self.yes_bid, 4) if self.yes_ask > 0 else 0,
                    round(self.no_ask - self.no_bid, 4) if self.no_ask > 0 else 0
                ])
        except Exception as e:
            pass
    
    def get_orderbook(self) -> Dict:
        """Get current orderbook state (thread-safe)."""
        with self._lock:
            return {
                'slug': self.market_slug,
                'yes_bid': self.yes_bid,
                'yes_ask': self.yes_ask,
                'yes_bid_size': self.yes_bid_size,
                'yes_ask_size': self.yes_ask_size,
                'no_bid': self.no_bid,
                'no_ask': self.no_ask,
                'no_bid_size': self.no_bid_size,
                'no_ask_size': self.no_ask_size,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }
    
    def has_liquidity(self, side: str) -> bool:
        """Check if there's liquidity on the specified side."""
        with self._lock:
            if side.upper() == 'YES':
                return self.yes_bid > 0 and self.yes_ask > 0
            else:
                return self.no_bid > 0 and self.no_ask > 0
    
    def start_polling(self, callback=None):
        """Start background polling thread."""
        self.running = True
        
        def poll_loop():
            while self.running:
                success = self.poll_once()
                if success:
                    self.save_snapshot()
                    if callback:
                        callback(self.get_orderbook())
                time.sleep(POLL_INTERVAL)
        
        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()
        return thread
    
    def stop_polling(self):
        """Stop polling."""
        self.running = False


def main():
    """Test the orderbook poller."""
    print("=" * 60)
    print("CLOB ORDERBOOK POLLER")
    print("=" * 60)
    
    poller = CLOBOrderbookPoller()
    
    # Load market
    if not poller.load_market():
        print("No market loaded. Run resolve_btc15m_market.py first.")
        return
    
    print("\nStarting orderbook polling...")
    print("Press Ctrl+C to stop\n")
    
    def on_update(book):
        ts = datetime.utcnow().strftime('%H:%M:%S')
        print(f"[{ts}] YES bid/ask: {book['yes_bid']:.3f} / {book['yes_ask']:.3f}  |  "
              f"NO bid/ask: {book['no_bid']:.3f} / {book['no_ask']:.3f}")
    
    poller.start_polling(callback=on_update)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        poller.stop_polling()


if __name__ == "__main__":
    main()
