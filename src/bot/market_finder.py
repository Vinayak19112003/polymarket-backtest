"""
Dynamic Polymarket Market Finder
Automatically finds and tracks current 15-minute BTC markets
"""
import requests
import time
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

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
        
        # 15-minute market patterns
        self.fifteen_minute_patterns = [
            r'15[\s-]?min',
            r'15[\s-]?minute',
            r'fifteen[\s-]?min',
        ]
    
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
                print(f"[WARN] Market search failed: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"[ERROR] Market search error: {e}")
            return []
    
    def filter_btc_markets(self, markets: List[Dict]) -> List[Dict]:
        """Filter for BTC-related markets (case-insensitive)."""
        btc_markets = []
        
        for market in markets:
            question = market.get('question', '').lower()
            description = market.get('description', '').lower()
            tags = [t.lower() for t in market.get('tags', [])]
            
            # Check if any keyword matches (case-insensitive)
            search_text = f"{question} {description} {' '.join(tags)}"
            
            if any(keyword.lower() in search_text for keyword in self.market_keywords):
                btc_markets.append(market)
        
        return btc_markets
    
    def is_fifteen_minute_market(self, market: Dict) -> tuple:
        """
        Check if market is a 15-minute market.
        Returns (is_15m, reason)
        """
        question = market.get('question', '').lower()
        
        # Check keyword patterns
        for pattern in self.fifteen_minute_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return True, "keyword match"
        
        # Check market duration if creation/end dates available
        end_date_str = market.get('end_date_iso')
        created_at_str = market.get('created_at') or market.get('createdAt')
        
        if end_date_str and created_at_str:
            try:
                end_date = self._parse_datetime(end_date_str)
                created_at = self._parse_datetime(created_at_str)
                
                if end_date and created_at:
                    duration = (end_date - created_at).total_seconds()
                    
                    # 15 minutes = 900 seconds (allow some tolerance: 800-1000s)
                    if 800 <= duration <= 1000:
                        return True, f"duration: {duration/60:.1f}min"
            except Exception as e:
                pass
        
        return False, "not 15-minute market"
    
    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse datetime string to UTC datetime."""
        if not dt_string:
            return None
        
        try:
            # Handle ISO format with Z suffix
            if dt_string.endswith('Z'):
                dt_string = dt_string[:-1] + '+00:00'
            
            dt = datetime.fromisoformat(dt_string)
            
            # Ensure timezone aware (assume UTC if naive)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
        except Exception:
            return None
    
    def _get_utc_now(self) -> datetime:
        """Get current UTC time."""
        return datetime.now(timezone.utc)
    
    def find_fifteen_minute_market(self, debug: bool = True) -> Optional[Dict]:
        """Find current 15-minute BTC market."""
        
        now = self._get_utc_now()
        
        # Check if we need to refresh
        if self.last_refresh and \
           (now - self.last_refresh).total_seconds() < self.cache_duration:
            if self.current_market and self.market_expiry and now < self.market_expiry:
                return self.current_market
        
        if debug:
            print(f"\n[{now.strftime('%H:%M:%S')} UTC] Searching for 15m BTC markets...")
        
        # Search all markets
        all_markets = self.search_markets(active_only=True)
        
        if not all_markets:
            print("[WARN] No markets found from API")
            return None
        
        if debug:
            print(f"[INFO] Total markets from API: {len(all_markets)}")
        
        # Filter for BTC
        btc_markets = self.filter_btc_markets(all_markets)
        
        if not btc_markets:
            print("[WARN] No BTC markets found")
            return None
        
        if debug:
            print(f"[INFO] BTC markets found: {len(btc_markets)}")
        
        # Analyze each BTC market
        valid_15m_markets = []
        other_markets = []
        
        for market in btc_markets:
            question = market.get('question', 'N/A')
            end_date_str = market.get('end_date_iso')
            status = market.get('status', market.get('active', 'unknown'))
            
            # Parse end date
            end_date = self._parse_datetime(end_date_str)
            
            # Check if market is still active (hasn't expired)
            if end_date and end_date <= now:
                if debug:
                    print(f"[SKIP] Expired: {question[:60]}...")
                continue
            
            # Check if it's a 15-minute market
            is_15m, reason = self.is_fifteen_minute_market(market)
            
            time_remaining = (end_date - now).total_seconds() / 60 if end_date else 0
            
            if debug:
                print(f"\n[MARKET] {question[:70]}...")
                print(f"   End: {end_date_str}")
                print(f"   Time Remaining: {time_remaining:.1f} min")
                print(f"   Status: {status}")
                print(f"   Is 15m: {is_15m} ({reason})")
            
            if is_15m and time_remaining > 0:
                valid_15m_markets.append({
                    'market': market,
                    'end_date': end_date,
                    'time_remaining': time_remaining
                })
            else:
                other_markets.append({
                    'question': question,
                    'time_remaining': time_remaining,
                    'reason': reason
                })
        
        # Select best 15m market (one with most time remaining, but still active)
        if valid_15m_markets:
            # Sort by time remaining (descending) - prefer markets with more time
            valid_15m_markets.sort(key=lambda x: x['time_remaining'], reverse=True)
            
            best = valid_15m_markets[0]
            market = best['market']
            
            self.current_market = market
            self.market_expiry = best['end_date']
            self.last_refresh = now
            
            # Extract tokens
            tokens = market.get('tokens', [])
            self.current_tokens = {}
            for token in tokens:
                outcome = token.get('outcome', '')
                token_id = token.get('token_id', '')
                self.current_tokens[outcome] = token_id
            
            question = market.get('question', 'N/A')
            condition_id = market.get('condition_id', 'N/A')
            
            print(f"\n[SUCCESS] Found valid 15m market!")
            print(f"   Question: {question}")
            print(f"   Condition ID: {condition_id}")
            print(f"   Time Remaining: {best['time_remaining']:.1f} minutes")
            print(f"   YES Token: {self.current_tokens.get('Yes', 'N/A')[:30]}...")
            print(f"   NO Token: {self.current_tokens.get('No', 'N/A')[:30]}...")
            
            return market
        
        # No 15m markets found - show what's available
        print(f"\n[WARN] No valid 15-minute markets currently available")
        
        if other_markets:
            print("\n[INFO] Available BTC markets (non-15m):")
            for m in other_markets[:5]:
                print(f"   - {m['question'][:50]}... ({m['time_remaining']:.1f}min remaining)")
        
        # Suggest when to check next
        print(f"\n[TIP] 15-minute markets are created periodically.")
        print(f"[TIP] Next check in {self.cache_duration} seconds...")
        
        return None
    
    def get_current_token_id(self, outcome: str = "Yes") -> Optional[str]:
        """Get token ID for current market."""
        
        # Refresh market if needed
        market = self.find_fifteen_minute_market(debug=False)
        
        if not market:
            return None
        
        return self.current_tokens.get(outcome)
    
    def is_market_expired(self) -> bool:
        """Check if current market has expired."""
        if not self.market_expiry:
            return True
        
        return self._get_utc_now() >= self.market_expiry
    
    def get_market_info(self) -> Dict:
        """Get current market information."""
        if not self.current_market:
            return {}
        
        now = self._get_utc_now()
        
        return {
            'question': self.current_market.get('question'),
            'condition_id': self.current_market.get('condition_id'),
            'market_id': self.current_market.get('id'),
            'end_date': self.current_market.get('end_date_iso'),
            'tokens': self.current_tokens,
            'time_remaining': (self.market_expiry - now).total_seconds() 
                             if self.market_expiry else 0
        }
    
    def wait_for_new_market(self, max_wait_seconds: int = 300):
        """Wait for new 15m market to be created."""
        print(f"[INFO] Waiting for new market (max {max_wait_seconds}s)...")
        
        start_time = time.time()
        check_interval = 30  # Check every 30 seconds
        
        while (time.time() - start_time) < max_wait_seconds:
            # Force refresh
            self.last_refresh = None
            market = self.find_fifteen_minute_market(debug=False)
            
            if market:
                print("[SUCCESS] New market found!")
                return market
            
            elapsed = int(time.time() - start_time)
            print(f"[WAIT] Still waiting... ({elapsed}s / {max_wait_seconds}s)")
            time.sleep(check_interval)
        
        print("[TIMEOUT] No new market found within wait period")
        return None
