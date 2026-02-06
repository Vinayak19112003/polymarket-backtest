"""
Dynamic Polymarket Market Finder
Automatically finds and tracks current 15-minute BTC markets
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json

class DynamicMarketFinder:
    """Finds and tracks time-based Polymarket markets dynamically."""
    
    def __init__(self, market_keywords: List[str] = None):
        self.market_keywords = market_keywords or ['btc', 'bitcoin']
        self.base_url = "https://gamma-api.polymarket.com"
        self.current_market = None
        self.current_tokens = {}
        self.market_expiry = None
        self.cache_duration = 60  # Refresh every 60 seconds
        self.last_refresh = None
    
    def search_markets(self, active_only: bool = True) -> List[Dict]:
        """Search for markets matching keywords."""
        try:
            url = f"{self.base_url}/markets"
            params = {
                "closed": "false" if active_only else "true",
                "limit": 100
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Market search failed: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"❌ Market search error: {e}")
            return []
    
    def filter_btc_markets(self, markets: List[Dict]) -> List[Dict]:
        """Filter for BTC-related markets."""
        btc_markets = []
        
        for market in markets:
            question = market.get('question', '').lower()
            
            # Check if any keyword matches
            if any(keyword in question for keyword in self.market_keywords):
                btc_markets.append(market)
        
        return btc_markets
    
    def find_shortest_duration_market(self, markets: List[Dict]) -> Optional[Dict]:
        """Find market with shortest time to expiry (most likely 15m)."""
        if not markets:
            return None
        
        now = datetime.now()
        shortest = None
        shortest_duration = timedelta(days=999)
        
        for market in markets:
            end_date_str = market.get('end_date_iso')
            
            if not end_date_str:
                continue
            
            try:
                # Parse end date
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                duration = end_date - now
                
                # Only consider future markets
                if duration.total_seconds() > 0 and duration < shortest_duration:
                    shortest_duration = duration
                    shortest = market
            
            except Exception as e:
                print(f"⚠️ Date parse error: {e}")
                continue
        
        return shortest
    
    def find_fifteen_minute_market(self) -> Optional[Dict]:
        """Find current 15-minute BTC market."""
        
        # Check if we need to refresh
        if self.last_refresh and \
           (datetime.now() - self.last_refresh).total_seconds() < self.cache_duration:
            if self.current_market and self.market_expiry and \
               datetime.now() < self.market_expiry:
                # Current market still valid
                return self.current_market
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching for current 15m market...")
        
        # Search all markets
        all_markets = self.search_markets(active_only=True)
        
        if not all_markets:
            print("No markets found")
            return None
        
        # Filter for BTC
        btc_markets = self.filter_btc_markets(all_markets)
        
        if not btc_markets:
            print("No BTC markets found")
            return None
        
        print(f"Found {len(btc_markets)} BTC markets")
        
        # Find shortest duration (likely 15m)
        current_market = self.find_shortest_duration_market(btc_markets)
        
        if current_market:
            self.current_market = current_market
            self.last_refresh = datetime.now()
            
            # Extract expiry
            end_date_str = current_market.get('end_date_iso')
            if end_date_str:
                self.market_expiry = datetime.fromisoformat(
                    end_date_str.replace('Z', '+00:00')
                )
            
            # Extract tokens
            tokens = current_market.get('tokens', [])
            self.current_tokens = {
                token['outcome']: token['token_id'] 
                for token in tokens
            }
            
            question = current_market.get('question', 'N/A')
            condition_id = current_market.get('condition_id', 'N/A')
            
            time_until_expiry = (self.market_expiry - datetime.now()).total_seconds() / 60 if self.market_expiry else 0
            
            print(f"Found market: {question}")
            print(f"   Condition ID: {condition_id}")
            print(f"   Expires in: {time_until_expiry:.1f} minutes")
            print(f"   YES Token: {self.current_tokens.get('Yes', 'N/A')[:20]}...")
            print(f"   NO Token: {self.current_tokens.get('No', 'N/A')[:20]}...")
            
            return current_market
        
        else:
            print("No suitable market found")
            return None
    
    def get_current_token_id(self, outcome: str = "Yes") -> Optional[str]:
        """Get token ID for current market."""
        
        # Refresh market if needed
        market = self.find_fifteen_minute_market()
        
        if not market:
            return None
        
        return self.current_tokens.get(outcome)
    
    def is_market_expired(self) -> bool:
        """Check if current market has expired."""
        if not self.market_expiry:
            return True
        
        return datetime.now() >= self.market_expiry
    
    def get_market_info(self) -> Dict:
        """Get current market information."""
        if not self.current_market:
            return {}
        
        return {
            'question': self.current_market.get('question'),
            'condition_id': self.current_market.get('condition_id'),
            'market_id': self.current_market.get('id'),
            'end_date': self.current_market.get('end_date_iso'),
            'tokens': self.current_tokens,
            'time_remaining': (self.market_expiry - datetime.now()).total_seconds() 
                             if self.market_expiry else 0
        }
    
    def wait_for_new_market(self, max_wait_seconds: int = 300):
        """Wait for new 15m market to be created."""
        print(f"Waiting for new market (max {max_wait_seconds}s)...")
        
        start_time = time.time()
        check_interval = 30  # Check every 30 seconds
        
        while (time.time() - start_time) < max_wait_seconds:
            market = self.find_fifteen_minute_market()
            
            if market:
                print("New market found!")
                return market
            
            print(f"   Still waiting... ({int(time.time() - start_time)}s)")
            time.sleep(check_interval)
        
        print("Timeout waiting for new market")
        return None
