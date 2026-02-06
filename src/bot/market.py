"""
Step 1: Resolve BTC 15m Market from Polymarket Website
Scrapes polymarket.com/crypto to find the active BTC 15-minute Up/Down market.
"""
import requests
import json
import re
import os
import time
from datetime import datetime, timedelta

from . import config

# Output file
OUTPUT_FILE = "active_btc15m_market.json"


from datetime import datetime, timedelta

def log(msg):
    # Convert UTC to ET (approx -5h)
    et_time = datetime.utcnow() - timedelta(hours=5)
    print(f"[{et_time.strftime('%H:%M:%S')}] {msg}")


def scrape_btc15m_market():
    """Scrape Polymarket website for BTC 15m market data."""
    log("Fetching Polymarket crypto page...")
    
    headers = config.HEADERS
    
    # Outer try block for the whole scraping process
    try:
        r = requests.get('https://polymarket.com/crypto', headers=headers, timeout=60)
        log(f"Status: {r.status_code}, Size: {len(r.text)} bytes")
        
        if r.status_code != 200:
            return None
        
        html = r.text
        
        # Step 1: Find all btc-updown-15m slugs
        slug_matches = re.findall(r'(btc-updown-15m-\d+)', html, re.IGNORECASE)
        
        best_slug = None
        if slug_matches:
            # Get unique slugs, sorted by timestamp (newest first)
            unique_slugs = list(set(slug_matches))
            unique_slugs.sort(key=lambda x: int(x.split('-')[-1]), reverse=True)
            log(f"Found {len(unique_slugs)} unique BTC 15m slugs")
            for slug in unique_slugs[:3]:
                log(f"  {slug}")
            best_slug = unique_slugs[0]
        else:
            log("No btc-updown-15m slugs found")

        # Step 4: Try to predict the next ones (Priority)
        try:
            # Predict next few 15m timestamps
            # User requested "less 15m" to target "current" market 
            # Logic changed from targetting (current_slot + 1) to (current_slot)
            current_ts = int(time.time())
            # Look ahead 30s to find next market if we are close to boundary
            base_ts = ((current_ts + 30) // 900) * 900 
            
            # Generate candidates: [current, next]
            # Generate candidates: [current, next]
            candidates = []
            candidates.append(f"btc-updown-15m-{base_ts}")      # Current active market
            candidates.append(f"btc-updown-15m-{base_ts + 900}") # Next market (Enabled)
            
            log(f"Checking predicted slugs: {candidates}")
            
            for slug in candidates:
                log(f"Checking predicted slug: {slug}")
                
                # Check CLOB
                # Strict Expiry Check
                try:
                    s_ts = int(slug.split('-')[-1])
                    if s_ts + 900 - 60 < time.time():
                        log(f"Skipping expiring/expired candidate: {slug}")
                        continue
                except: pass

                # SPEED FIX: Skip slow CLOB API (always fails for 15m markets anyway)
                # Go directly to Event Page scraping (1-2 seconds vs 70 seconds)
                try:
                    event_url = f'https://polymarket.com/event/{slug}'
                    r_event = requests.get(event_url, headers=headers, timeout=10)
                    if r_event.status_code == 200:
                        event_html = r_event.text
                        token_matches = re.findall(r'"clobTokenIds"\s*:\s*\["([^"]+)","([^"]+)"\]', event_html)
                        if token_matches:
                            log(f"Found tokens via event page: {slug}")
                            market = {
                                'slug': slug,
                                'question': 'Bitcoin Up or Down - 15 min',
                                'yes_token_id': token_matches[0][0],
                                'no_token_id': token_matches[0][1],
                                'discovered_at': datetime.utcnow().isoformat()
                            }
                            save_market_data(market)
                            return market
                except Exception as ex:
                    log(f"Event page scrape failed: {ex}")
                    
        except Exception as e:
            log(f"Prediction error: {e}")

        # Fallback to best scraped slug
        if best_slug:
            try:
                ts = int(best_slug.split('-')[-1])
                # Only expire if the 15m window has CLOSED
                if ts + 900 - 60 < time.time():
                    log(f"Scraped fallback slug is expired (Closed): {best_slug}")
                    return None
            except:
                pass
                
            log("Could not find newer market via prediction, using scraped slug")
            
            # Build a context window around the slug
            slug_pos = html.find(best_slug)
            if slug_pos > 0:
                context_start = max(0, slug_pos - 5000)
                context_end = min(len(html), slug_pos + 5000)
                context = html[context_start:context_end]
                
                token_matches = re.findall(r'"clobTokenIds"\s*:\s*\["([^"]+)","([^"]+)"\]', context)
                if token_matches:
                    return {
                        'slug': best_slug,
                        'question': 'Bitcoin Up or Down - 15 min',
                        'yes_token_id': token_matches[0][0],
                        'no_token_id': token_matches[0][1],
                        'discovered_at': datetime.utcnow().isoformat()
                    }

            # Step 3: Fetch specific event page
            event_url = f'https://polymarket.com/event/{best_slug}'
            try:
                r2 = requests.get(event_url, headers=headers, timeout=10)
                if r2.status_code == 200:
                    event_html = r2.text
                    token_matches = re.findall(r'"clobTokenIds"\s*:\s*\["([^"]+)","([^"]+)"\]', event_html)
                    if token_matches:
                        # Validate outcome labels and fetch times with CLOB API
                        yes_id = token_matches[0][0]
                        no_id = token_matches[0][1]
                        market_active = True
                        end_time_iso = "Unknown"
                        strike_price = None

                        # Try to find Strike Price in HTML
                        # Pattern 1: "Price to Beat: $89,123.45"
                        strike_matches = re.findall(r'Price to Beat:? \$([\d,]+\.?\d*)', event_html)
                        if strike_matches:
                            try:
                                strike_price = float(strike_matches[0].replace(',', ''))
                                log(f"Found Strike Price in HTML: ${strike_price:,.2f}")
                            except: pass
                        
                        # Pattern 2: "Bitcoin > 89123.45"
                        if not strike_price:
                            desc_matches = re.findall(r'Bitcoin > ([\d,]+\.?\d*)', event_html)
                            if desc_matches:
                                try:
                                    strike_price = float(desc_matches[0].replace(',', ''))
                                    log(f"Found Strike Price in Description: ${strike_price:,.2f}")
                                except: pass
                        
                        try:
                            # Verify details
                            r_valid = requests.get(f'https://clob.polymarket.com/markets?limit=1&token_id={yes_id}', headers=config.HEADERS, timeout=5)
                            if r_valid.status_code == 200:
                                m_data = r_valid.json()
                                if m_data.get('data'):
                                    m_info = m_data['data'][0]
                                    end_time_iso = m_info.get('end_date_iso')
                                    market_active = m_info.get('active', True)
                                    closed = m_info.get('closed', False)
                                    
                                    log(f"Market Details: Active={market_active}, Closed={closed}, Expires={end_time_iso}")
                                    
                                    tokens = m_info.get('tokens', [])
                                    for t in tokens:
                                        if t.get('token_id') == yes_id:
                                            outcome = t.get('outcome', '').upper()
                                            if outcome in ['NO', 'DOWN']:
                                                log(f"WARNING: Scraped YES_ID actually maps to {outcome}. SWAPPING.")
                                                yes_id, no_id = no_id, yes_id
                                            break
                        except Exception as val_ex:
                            log(f"Validation warning: {val_ex}")

                        return {
                            'slug': best_slug,
                            'question': 'Bitcoin Up or Down - 15 min',
                            'yes_token_id': yes_id,
                            'no_token_id': no_id,
                            'end_date_iso': end_time_iso,
                            'strike_price': strike_price,
                            'active': market_active,
                            'discovered_at': datetime.utcnow().isoformat()
                        }
            except:
                pass
                
        # Return fallback data with slug only
        if best_slug:
            return {
                'slug': best_slug,
                'question': 'Bitcoin Up or Down - 15 min',
                'yes_token_id': None,
                'no_token_id': None,
                'discovered_at': datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        log(f"Scraping error: {e}")
        return None
    
    return None


def fetch_tokens_from_clob(slug: str):
    """Try to find tokens for this market from CLOB API."""
    try:
        cursor = ""
        max_pages = 50
        page = 0
        
        while page < max_pages:
            url = f'https://clob.polymarket.com/markets?limit=500&active=true&next_cursor={cursor}' 
            
            r = requests.get(url, headers=config.HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                markets = data.get('data', [])
                
                if not markets:
                    break
                
                # Filter specifically
                for m in markets:
                    mslug = m.get('market_slug', '').lower()
                    
                    if slug in mslug:
                        tokens = m.get('tokens', [])
                        if len(tokens) >= 2:
                            outcomes = {t.get('outcome', '').lower(): t.get('token_id', '') for t in tokens}
                            yes_token = outcomes.get('up', outcomes.get('yes', tokens[0].get('token_id', '')))
                            no_token = outcomes.get('down', outcomes.get('no', tokens[1].get('token_id', '')))
                            
                            strike_price = 0.0
                            try:
                                # Parse strike from question: "Bitcoin > $104,500.25 on ..."
                                q_text = m.get('question', '')
                                match = re.search(r'Bitcoin\s*>\s*\$?([\d,]+\.?\d*)', q_text)
                                if match:
                                    strike_price = float(match.group(1).replace(',', ''))
                                    log(f"Parsed Strike Price from API: ${strike_price:,.2f}")
                            except Exception as e:
                                log(f"Error parsing strike: {e}")

                            return {
                                'slug': slug,
                                'question': m.get('question'),
                                'yes_token_id': yes_token,
                                'no_token_id': no_token,
                                'strike_price': strike_price,
                                'discovered_at': datetime.utcnow().isoformat()
                            }
                
                cursor = data.get('next_cursor')
                if not cursor or cursor == "lte=":
                    break
                page += 1
            else:
                log(f"CLOB error status: {r.status_code}")
                break
                
        return None
        
    except Exception as e:
        log(f"CLOB error: {e}")
        return None


def save_market_data(data):
    """Save market data to JSON file."""
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    log(f"Saved to {OUTPUT_FILE}")


def load_cached_market():
    """Load previously cached market data."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                data = json.load(f)
            
            # Check if it's still valid (within 1 hour) AND in the future
            discovered = datetime.fromisoformat(data.get('discovered_at', '2000-01-01'))
            slug = data.get('slug', '')
            try:
                ts = int(slug.split('-')[-1])
                # Only expire if closed (with 60s buffer to avoid race conditions)
                if ts + 900 - 60 < time.time():
                    log(f"Cached market expiring soon/expired (ts={ts})")
                    return None
            except:
                pass
                
            if (datetime.utcnow() - discovered).total_seconds() < 3600:
                pass 
                # Don't return automatically, prefer fresh if possible
                # return data
        except:
            pass
    return None


def get_market_result(yes_token_id: str):
    """
    Check if the market has resolved and who won.
    Returns: "YES", "NO", or None (if not resolved).
    """
    try:
        url = f'https://clob.polymarket.com/markets?limit=1&token_id={yes_token_id}'
        r = requests.get(url, headers=config.HEADERS, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data.get('data'):
                m_info = data['data'][0]
                
                # Check if resolved
                winner_id = m_info.get('winning_outcome_id')
                
                if winner_id:
                    if winner_id == yes_token_id:
                        return "YES"
                    else:
                        return "NO"  # Assumes binary market
                        
                # Alternative: Check closed status but no winner yet
                # We return None to indicate "Wait longer"
                
    except Exception as e:
        log(f"Error checking market result: {e}")
        
    return None


def resolve_market():
    """Main function to resolve the current BTC 15m market."""
    log("=" * 60)
    log("RESOLVING BTC 15M MARKET FROM POLYMARKET")
    log("=" * 60)
    
    # Check cache first
    cached = load_cached_market()
    
    # Scrape fresh data
    market = scrape_btc15m_market()
    
    if market:
        # If we have slug but no tokens, try CLOB API more broadly
        if not market.get('yes_token_id'):
            clob_data = fetch_tokens_from_clob(market['slug'])
            if clob_data and clob_data.get('yes_token_id'):
                market = clob_data
        
        save_market_data(market)
        
        if market.get('yes_token_id'):
            log(f"SUCCESS: Found market {market['slug']}")
            log(f"  YES: {market['yes_token_id'][:30]}...")
            log(f"  NO: {market['no_token_id'][:30]}...")
        else:
            log(f"PARTIAL: Found slug {market['slug']} but no tokens")
        
        return market
    
    log("FAILED: Could not resolve market")
    return None


if __name__ == "__main__":
    market = resolve_market()
    if market:
        print("\n" + "=" * 60)
        print("RESOLVED MARKET:")
        print("=" * 60)
        print(json.dumps(market, indent=2))
