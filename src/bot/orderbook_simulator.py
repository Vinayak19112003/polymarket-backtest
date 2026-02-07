"""
Realistic Orderbook Simulator
Simulates real Polymarket orderbook behavior for paper trading
"""
import requests
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

class OrderbookSimulator:
    """Simulates Polymarket orderbook for realistic paper trading."""
    
    def __init__(self, market_slug: str = "btc-15m"):
        self.market_slug = market_slug
        self.base_url = "https://clob.polymarket.com"
        self.orderbook_cache = {}
        self.cache_timestamp = {}  # Per token timestamp
        self.cache_duration = 5  # Cache for 5 seconds
    
    def get_cached_orderbook(self, token_id: str) -> Optional[Dict]:
        """Get cached orderbook if still valid."""
        if token_id in self.orderbook_cache:
            cache_time = self.cache_timestamp.get(token_id)
            if cache_time and (datetime.now() - cache_time).total_seconds() < self.cache_duration:
                return self.orderbook_cache[token_id]
        return None

    def fetch_live_orderbook(self, token_id: str) -> Optional[Dict]:
        """Fetch real-time orderbook from Polymarket CLOB."""
        if not token_id:
            print("⚠️ No token_id provided")
            return None
            
        try:
            # Check cache first
            cached = self.get_cached_orderbook(token_id)
            if cached:
                return cached

            # Polymarket CLOB API expects token_id as query parameter
            url = f"{self.base_url}/book"
            params = {"token_id": token_id}
            
            # print(f"   Fetching orderbook for token: {token_id[:20]}...")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                if 'bids' in data and 'asks' in data:
                    # bids_count = len(data.get('bids', []))
                    # asks_count = len(data.get('asks', []))
                    # print(f"   ✓ Orderbook: {bids_count} bids, {asks_count} asks")
                    
                    self.orderbook_cache[token_id] = data
                    self.cache_timestamp[token_id] = datetime.now()
                    return data
                else:
                    print(f"   ⚠️ Invalid orderbook structure: {data.keys()}")
                    return None
            else:
                print(f"   ⚠️ Orderbook fetch failed: {response.status_code}")
                # print(f"   Response: {response.text[:200]}")
                return None
        
        except requests.exceptions.Timeout:
            print(f"   ❌ Orderbook request timeout")
            return None
        except Exception as e:
            print(f"   ❌ Orderbook error: {type(e).__name__}: {e}")
            return None
    
    def get_best_bid_ask(self, token_id: str) -> Tuple[Optional[float], Optional[float]]:
        """Get best bid and ask with fallback to mid-price."""
        # Check cache first
        orderbook = self.get_cached_orderbook(token_id)
        if not orderbook:
            orderbook = self.fetch_live_orderbook(token_id)
        
        if not orderbook:
            print("   Using fallback prices (0.48, 0.52)")
            return 0.48, 0.52  # Fallback to reasonable spread
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            print(f"   Empty orderbook: {len(bids)} bids, {len(asks)} asks")
            return 0.48, 0.52
        
        try:
            # Polymarket return string prices in list of dicts or list of lists depending on endpoint
            # checking structure first
            best_bid_raw = bids[0]
            best_ask_raw = asks[0]
            
            if isinstance(best_bid_raw, dict):
                 best_bid = float(best_bid_raw.get('price', 0))
            else:
                 best_bid = float(best_bid_raw.price)

            if isinstance(best_ask_raw, dict):
                 best_ask = float(best_ask_raw.get('price', 0))
            else:
                 best_ask = float(best_ask_raw.price)

            return best_bid, best_ask
        except (KeyError, ValueError, IndexError, AttributeError) as e:
            print(f"   Error parsing prices: {e}")
            return 0.48, 0.52

    def get_available_liquidity(self, token_id: str, side: str, 
                                price: float) -> float:
        """Get available liquidity at price level."""
        # Ensure we have orderbook
        orderbook = self.fetch_live_orderbook(token_id)
        
        if not orderbook:
            return 0.0
        
        orders = orderbook.get('bids' if side == 'BUY' else 'asks', [])
        
        total_size = 0.0
        for order in orders:
            try:
                if isinstance(order, dict):
                     order_price = float(order.get('price', 0))
                     order_size = float(order.get('size', 0))
                else:
                     order_price = float(order.price)
                     order_size = float(order.size)
                
                if side == 'BUY' and order_price >= price:
                    total_size += order_size
                elif side == 'SELL' and order_price <= price:
                    total_size += order_size
            except:
                continue
        
        return total_size
    
    def simulate_limit_order_fill(self, token_id: str, side: str, 
                                  price: float, size: float) -> Dict:
        """Simulate limit order fill with robust error handling."""
        
        if not token_id:
            return {
                'filled': False, 'fill_price': 0.0, 'fill_size': 0.0,
                'slippage': 0.0, 'reason': 'No token_id provided'
            }
        
        best_bid, best_ask = self.get_best_bid_ask(token_id)
        
        # Check if limit price is competitive
        if side == 'BUY':
            if not best_ask:
                 return { 'filled': False, 'fill_price': 0.0, 'fill_size': 0.0, 'slippage': 0.0, 'reason': 'No asks available'}

            # For buying YES, we need to pay at least best_ask
            if price < best_ask * 0.99:  # Allow 1% tolerance
                return {
                    'filled': False,
                    'fill_price': 0.0,
                    'fill_size': 0.0,
                    'slippage': 0.0,
                    'reason': f'Price too low (limit: ${price:.3f}, ask: ${best_ask:.3f})'
                }
            
            # Use simplified liquidity check for robustness if detailed fails
            # Assume sufficient liquidity for small sizes (paper trading simplification)
            if size <= 10:
                 return {
                    'filled': True,
                    'fill_price': best_ask,
                    'fill_size': size,
                    'slippage': 0.0,
                    'reason': 'Filled'
                }
            
            # Check liquidity for larger sizes
            available = self.get_available_liquidity(token_id, side, price)
            
            if available < size * 0.5:  # Need at least 50% available
                return {
                    'filled': False,
                    'fill_price': 0.0,
                    'fill_size': 0.0,
                    'slippage': 0.0,
                    'reason': f'Insufficient liquidity (need: {size}, available: {available:.1f})'
                }
            
            # Simulate fill with slight slippage
            actual_fill_price = best_ask * 1.002  # 0.2% worse than best ask
            fill_size = min(size, available * 0.8)  # Fill 80% of available
            slippage = ((actual_fill_price - price) / price) * 100
            
            return {
                'filled': True,
                'fill_price': actual_fill_price,
                'fill_size': fill_size,
                'slippage': slippage,
                'reason': 'Filled'
            }
        
        else:  # SELL
            if price > best_bid * 1.01:  # Allow 1% tolerance
                return {
                    'filled': False,
                    'fill_price': 0.0,
                    'fill_size': 0.0,
                    'slippage': 0.0,
                    'reason': f'Price too high (limit: ${price:.3f}, bid: ${best_bid:.3f})'
                }
            
            if size <= 10:
                 return {
                    'filled': True,
                    'fill_price': best_bid,
                    'fill_size': size,
                    'slippage': 0.0,
                    'reason': 'Filled'
                }

            available = self.get_available_liquidity(token_id, side, price)
            
            if available < size * 0.5:
                return {
                    'filled': False,
                    'fill_price': 0.0,
                    'fill_size': 0.0,
                    'slippage': 0.0,
                    'reason': f'Insufficient liquidity (need: {size}, available: {available:.1f})'
                }
            
            actual_fill_price = best_bid * 0.998  # 0.2% worse than best bid
            fill_size = min(size, available * 0.8)
            slippage = ((price - actual_fill_price) / price) * 100
            
            return {
                'filled': True,
                'fill_price': actual_fill_price,
                'fill_size': fill_size,
                'slippage': slippage,
                'reason': 'Filled'
            }
    
    def get_mid_price(self, token_id: str) -> Optional[float]:
        """Get mid price (average of best bid and ask)."""
        best_bid, best_ask = self.get_best_bid_ask(token_id)
        return (best_bid + best_ask) / 2
