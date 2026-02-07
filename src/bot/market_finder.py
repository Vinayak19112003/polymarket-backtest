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
            r'15 m',
        ]
    
    def _get_utc_now(self):
        """Get current UTC time."""
        return datetime.now(timezone.utc)
    
    def search_markets(self, active_only: bool = True, tag_id: str = None) -> List[Dict]:
        """
        Search for markets.
        BTC 15m tag_id is 102467.
        """
        try:
            url = f"{self.base_url}/markets"
            params = {
                "limit": 100,
                "active": "true" if active_only else "false",
                "closed": "false" if active_only else "true"
            }
            
            if tag_id:
                params["tag_id"] = tag_id
            
            # print(f"   Querying: {url} Params: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"   [WARN] Market search failed: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"   [ERROR] Market search error: {type(e).__name__}: {e}")
            return []
            
    def search_15m_markets_directly(self) -> List[Dict]:
        """
        Query markets with '15M' tag ID (102467).
        """
        try:
            # 102467 is the specific tag ID for 15M markets
            markets = self.search_markets(active_only=True, tag_id="102467")
            
            if markets:
                # print(f"   Found {len(markets)} markets with 15M tag")
                return markets
            
            return []
            
        except Exception as e:
            print(f"   [ERROR] Error in 15M search: {e}")
            return []
            
    def find_market_by_slug_pattern(self) -> Optional[Dict]:
        """
        Fallback: Find market by directly constructing expected slug.
        BTC 15m markets follow pattern: btc-updown-15m-{unix_timestamp}
        Timestamps are in 15-minute intervals.
        """
        # print("   Trying direct slug construction...")
        
        # Current time rounded to nearest 15-minute interval
        now = self._get_utc_now()
        
        # Try current and next 15-minute intervals around now
        # Check current, +15, -15 just in case
        for offset in [0, 15, -15]:
            target_time = now + timedelta(minutes=offset)
            
            # Round to 15-minute boundary logic
            # Explicitly finding the next quarter hour
            minute = (target_time.minute // 15) * 15
            target_time = target_time.replace(minute=minute, second=0, microsecond=0)
            
            timestamp = int(target_time.timestamp())
            
            # Try patterns
            patterns = [
                f"btc-updown-15m-{timestamp}",
                f"bitcoin-up-or-down-15min-{timestamp}",
                f"btc-up-down-15m-{timestamp}"
            ]
            
            for slug in patterns:
                try:
                    # Query EVENTS endpoint for slug, as market slug access is unreliable
                    url = f"{self.base_url}/events"
                    params = {"slug": slug}
                    # print(f"   Trying event slug: {slug}")
                    
                    response = requests.get(url, params=params, timeout=5)
                    
                    if response.status_code == 200:
                        events = response.json()
                        if events and isinstance(events, list) and len(events) > 0:
                            event = events[0]
                            # event contains 'markets' list
                            if 'markets' in event and event['markets']:
                                market = event['markets'][0]
                                
                                # Verify it's active
                                if market.get('active') and not market.get('closed'):
                                     # Double check it is actually a BTC market
                                     slug_lower = market.get('slug', '').lower()
                                     if 'btc' in slug_lower or 'bitcoin' in slug_lower:
                                         return market
                except:
                    continue
        
        return None

    def filter_btc_15m_markets(self, markets: List[Dict]) -> List[Dict]:
        """
        Filter specifically for BTC 15-minute markets.
        """
        btc_15m_markets = []
        
        for market in markets:
            question = market.get('question', '').lower()
            slug = market.get('slug', '').lower()
            
            # Strong slug match (definitive)
            if 'btc-updown-15m' in slug or 'bitcoin-up-or-down-15m' in slug:
                btc_15m_markets.append(market)
                continue

            # Secondary filter: Check question or weaker slug match
            is_btc_slug = 'btc' in slug or 'bitcoin' in slug
            has_btc_keywords = any(kw in question for kw in ['bitcoin', 'btc'])
            has_15m_keywords = any(kw in question for kw in ['15 minute', '15-minute', '15m', '15 min'])
            
            if (is_btc_slug and has_15m_keywords) or (has_btc_keywords and has_15m_keywords):
                # Verify it's not expired
                try:
                    end_date_str = market.get('end_date_iso')
                    if end_date_str:
                        if end_date_str.endswith('Z'):
                             end_date_str = end_date_str[:-1] + '+00:00'
                        end_date = datetime.fromisoformat(end_date_str)
                        if end_date.tzinfo is None:
                            end_date = end_date.replace(tzinfo=timezone.utc)
                            
                        now = self._get_utc_now()
                        time_remaining = (end_date - now).total_seconds()
                        
                        # Only include markets that haven't expired yet
                        if time_remaining > 0: 
                            btc_15m_markets.append(market)
                except Exception:
                     pass
        
        return btc_15m_markets

    def find_shortest_duration_market(self, markets: List[Dict]) -> Optional[Dict]:
        """Find market with shortest time to expiry."""
        if not markets:
            return None
        
        now = self._get_utc_now()
        shortest = None
        shortest_duration = timedelta(days=999)
        
        for market in markets:
            end_date_str = market.get('end_date_iso')
            if not end_date_str:
                continue
            
            try:
                if end_date_str.endswith('Z'):
                    end_date_str = end_date_str[:-1] + '+00:00'
                end_date = datetime.fromisoformat(end_date_str)
                if end_date.tzinfo is None:
                     end_date = end_date.replace(tzinfo=timezone.utc)
                     
                duration = end_date - now
                
                if duration.total_seconds() > 0 and duration < shortest_duration:
                    shortest_duration = duration
                    shortest = market
            
            except Exception:
                continue
        
        return shortest

    def _set_current_market(self, market: Dict):
        """Set current market with all metadata."""
        if not market: return

        self.current_market = market
        self.last_refresh = self._get_utc_now()
        
        # Extract expiry
        end_date_str = market.get('end_date_iso')
        if end_date_str:
            if end_date_str.endswith('Z'):
                 end_date_str = end_date_str[:-1] + '+00:00'
            self.market_expiry = datetime.fromisoformat(end_date_str)
            if self.market_expiry.tzinfo is None:
                 self.market_expiry = self.market_expiry.replace(tzinfo=timezone.utc)
        
        # Extract tokens
        self.current_tokens = {}
        
        if 'tokens' in market and isinstance(market['tokens'], list):
             for token in market['tokens']:
                outcome = token.get('outcome', '')
                token_id = token.get('token_id', '')
                self.current_tokens[outcome] = token_id
        elif 'clobTokenIds' in market and 'outcomes' in market:
            try:
                import json
                clob_ids = market['clobTokenIds']
                if isinstance(clob_ids, str): clob_ids = json.loads(clob_ids)
                
                outcomes = market['outcomes']
                if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                
                if len(clob_ids) == len(outcomes):
                    for idx, outcome in enumerate(outcomes):
                        # Map Up/Down to Yes/No for compatibility
                        if outcome == "Up": outcome = "Yes"
                        if outcome == "Down": outcome = "No"
                        self.current_tokens[outcome] = clob_ids[idx]
            except Exception:
                pass
                
        # print(f"   ✅ ACTIVE MARKET SELECTED: {market.get('question', 'N/A')}")
        self._last_active_market_id = market.get('condition_id')

    def find_fifteen_minute_market(self, debug: bool = True) -> Optional[Dict]:
        """Find current active 15-minute BTC market."""
        
        now = self._get_utc_now()
        
        if debug:
            print(f"\n[{now.strftime('%H:%M:%S')} UTC] Searching for 15m BTC markets...")
        
        # Method 1: Try 15M tag search
        if debug: print("   Method 1: Searching with 15M tag...")
        markets_15m = self.search_15m_markets_directly()
        
        if markets_15m:
            btc_markets = self.filter_btc_15m_markets(markets_15m)
            if btc_markets:
                current = self.find_shortest_duration_market(btc_markets)
                if current:
                    if debug: print(f"   [OK] Found via Tag: {current.get('question')}")
                    self._set_current_market(current)
                    return current

        # Method 2: Try direct slug construction
        if debug: print("   Method 2: Searching via slug patterns...")
        slug_market = self.find_market_by_slug_pattern()
        if slug_market:
             # Basic validation
             if self.filter_btc_15m_markets([slug_market]):
                 if debug: print(f"   [OK] Found via Slug: {slug_market.get('question')}")
                 self._set_current_market(slug_market)
                 return slug_market

        # Method 3: General search fallback
        if debug: print("   Method 3: General search fallback...")
        all_markets = self.search_markets(active_only=True)
        btc_markets = self.filter_btc_15m_markets(all_markets)
        
        if btc_markets:
            current = self.find_shortest_duration_market(btc_markets)
            if current:
                if debug: print(f"   [OK] Found via General Search: {current.get('question')}")
                self._set_current_market(current)
                return current
        
        if debug: print("   [FAIL] No BTC 15-minute markets found")
        return None

    
    def is_market_expired(self) -> bool:
        """Check if current market has expired."""
        if not self.current_market:
            return True
        
        # Check if we have an expiry time
        if hasattr(self, 'market_expiry') and self.market_expiry:
            now = self._get_utc_now()
            # If we are past expiry (or very close), it's expired
            if now >= self.market_expiry:
                return True
        
        return False

    def get_current_token_id(self, outcome: str = "Yes") -> Optional[str]:
        """Get token ID for current market."""
        # Refresh market if needed
        # If we don't have a current market or it expired, try to find one
        if not self.current_market or self.is_market_expired():
             self.find_fifteen_minute_market(debug=False)


        if not self.current_market:
            return None
        
        return self.current_tokens.get(outcome)

    def get_market_info(self) -> Dict:
        """Get current market info."""
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
