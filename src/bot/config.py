
import os


# Manual .env loader to avoid dependencies
POLYMARKET_API_KEY = None
DEMO_START_BALANCE = 100.0
RISK_PER_TRADE = 0.01  # 1% risk per trade (no compounding)
FEE_RATE = 0.01
ORDERBOOK_POLL_SECONDS = 1.0
MARKET_REFRESH_SECONDS = 30
ORDER_TIMEOUT_SECONDS = 60

# Find project root (go up from src/bot/ to project root)
_current_dir = os.path.dirname(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_dir))
env_path = os.path.join(_project_root, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.split('#')[0].strip() # Handle inline comments
                    
                    if key == 'POLYMARKET_API_KEY':
                        POLYMARKET_API_KEY = value
                    elif key == 'DEMO_START_BALANCE':
                        DEMO_START_BALANCE = float(value)
                    elif key == 'RISK_PER_TRADE':
                        RISK_PER_TRADE = float(value)
                    elif key == 'FEE_RATE':
                        FEE_RATE = float(value)
                    elif key == 'ORDERBOOK_POLL_SECONDS':
                        ORDERBOOK_POLL_SECONDS = float(value)
                    elif key == 'MARKET_REFRESH_SECONDS':
                        MARKET_REFRESH_SECONDS = int(value)
                    elif key == 'ORDER_TIMEOUT_SECONDS':
                        ORDER_TIMEOUT_SECONDS = int(value)
                    elif key == 'PRICE_OFFSET_USD':
                        PRICE_OFFSET_USD = float(value)
                    
                    # Fix: Env Vars (Moved inside try block)
                    elif key == 'PRIVATE_KEY':
                        os.environ['PRIVATE_KEY'] = value
                    elif key == 'CLOB_API_KEY':
                        os.environ['CLOB_API_KEY'] = value
                    elif key == 'CLOB_API_SECRET':
                        os.environ['CLOB_API_SECRET'] = value
                    elif key == 'CLOB_PASSPHRASE':
                        os.environ['CLOB_PASSPHRASE'] = value
                    elif key == 'LIVE_TRADING':
                        if value.lower() == 'true':
                            os.environ['LIVE_TRADING'] = 'true'
                except Exception as e:
                    # print(f"Error parsing line {line}: {e}")
                    pass

# Default if not set
if 'PRICE_OFFSET_USD' not in locals():
    PRICE_OFFSET_USD = 0.0

# Common Headers for Polymarket API
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Authorization': f"Bearer {POLYMARKET_API_KEY}" if POLYMARKET_API_KEY else None
}

# Remove None values
HEADERS = {k: v for k, v in HEADERS.items() if v is not None}
