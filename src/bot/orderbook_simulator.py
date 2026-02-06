"""
Realistic Orderbook Simulator
Simulates real Polymarket orderbook behavior for paper trading
"""
import requests
from typing import Dict, Optional, Tuple, List
from datetime import datetime

class OrderbookSimulator:
    """Simulates Polymarket orderbook for realistic paper trading."""
    
    def __init__(self, market_slug: str = "btc-15m"):
        self.market_slug = market_slug
        self.base_url = "https://clob.polymarket.com"
        self.orderbook_cache = {}
        self.cache_timestamp = None
    
    def fetch_live_orderbook(self, token_id: str) -> Optional[Dict]:
        """Fetch real-time orderbook from Polymarket."""
        try:
            url = f"{self.base_url}/book?token_id={token_id}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.orderbook_cache[token_id] = data
                self.cache_timestamp = datetime.now()
                return data
            else:
                print(f"⚠️ Orderbook fetch failed: {response.status_code}")
                return None
        
        except Exception as e:
            print(f"❌ Orderbook error: {e}")
            return None
    
    def get_best_bid_ask(self, token_id: str) -> Tuple[Optional[float], Optional[float]]:
        """Get best bid and ask from live orderbook."""
        orderbook = self.fetch_live_orderbook(token_id)
        
        if not orderbook:
            return None, None
        
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        best_bid = float(bids[0]['price']) if bids else None
        best_ask = float(asks[0]['price']) if asks else None
        
        return best_bid, best_ask
    
    def get_available_liquidity(self, token_id: str, side: str, 
                                price: float) -> float:
        """Get available liquidity at price level."""
        orderbook = self.fetch_live_orderbook(token_id)
        
        if not orderbook:
            return 0.0
        
        orders = orderbook.get('bids' if side == 'BUY' else 'asks', [])
        
        total_size = 0.0
        for order in orders:
            order_price = float(order['price'])
            order_size = float(order['size'])
            
            if side == 'BUY' and order_price >= price:
                total_size += order_size
            elif side == 'SELL' and order_price <= price:
                total_size += order_size
        
        return total_size
    
    def simulate_limit_order_fill(self, token_id: str, side: str, 
                                  price: float, size: float) -> Dict:
        """
        Simulate realistic limit order fill.
        
        Returns:
            {
                'filled': bool,
                'fill_price': float,
                'fill_size': float,
                'slippage': float,
                'reason': str
            }
        """
        best_bid, best_ask = self.get_best_bid_ask(token_id)
        
        if not best_bid or not best_ask:
            return {
                'filled': False,
                'fill_price': 0.0,
                'fill_size': 0.0,
                'slippage': 0.0,
                'reason': 'Orderbook unavailable'
            }
        
        # Check if limit price is competitive
        if side == 'BUY':
            # For buying YES, we need to pay at least best_ask
            # If our limit price is below best_ask, order won't fill
            if price < best_ask * 0.99:  # Allow 1% tolerance
                return {
                    'filled': False,
                    'fill_price': 0.0,
                    'fill_size': 0.0,
                    'slippage': 0.0,
                    'reason': f'Price too low (limit: ${price:.3f}, ask: ${best_ask:.3f})'
                }
            
            # Check liquidity at our price
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
            # For selling YES, we get paid at least best_bid
            if price > best_bid * 1.01:  # Allow 1% tolerance
                return {
                    'filled': False,
                    'fill_price': 0.0,
                    'fill_size': 0.0,
                    'slippage': 0.0,
                    'reason': f'Price too high (limit: ${price:.3f}, bid: ${best_bid:.3f})'
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
        
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return None
