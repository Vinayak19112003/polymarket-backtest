"""
Telegram Notifier for PolyBot
Sends trade notifications to Telegram without modifying core bot logic.
"""
import os
import requests
from datetime import datetime
from typing import Optional

# Load .env from project root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_ROOT, '.env')
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

# Load credentials from environment
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to all configured Telegram chat IDs."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Missing credentials, skipping notification")
        return False
    
    # Support multiple comma-separated IDs
    chat_ids = [cid.strip() for cid in TELEGRAM_CHAT_ID.split(',') if cid.strip()]
    
    success = True
    for chat_id in chat_ids:
        try:
            response = requests.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=10
            )
            if response.status_code != 200:
                print(f"[Telegram] Error for {chat_id}: {response.status_code} - {response.text}")
                success = False
        except Exception as e:
            print(f"[Telegram] Exception for {chat_id}: {e}")
            success = False
            
    return success


def notify_order_placed(
    order_id: str,
    side: str,
    shares: int,
    price: float,
    btc_price: float,
    market_slug: str,
    balance: float
):
    """Notify when a new order is placed."""
    emoji = "🟢" if side == "YES" else "🔴"
    message = f"""
{emoji} <b>NEW ORDER PLACED</b>

📌 <b>Order:</b> {order_id}
📊 <b>Side:</b> {side}
🎯 <b>Shares:</b> {shares} @ ${price:.2f}
💰 <b>Cost:</b> ${shares * price:.2f}
₿ <b>BTC Price:</b> ${btc_price:,.2f}
📈 <b>Market:</b> {market_slug}
💼 <b>Balance:</b> ${balance:.2f}

⏳ Waiting for settlement...
"""
    send_message(message.strip())


def notify_order_filled(
    order_id: str,
    side: str,
    shares: int,
    fill_price: float,
    btc_price: float
):
    """Notify when an order is filled."""
    emoji = "🟢" if side == "YES" else "🔴"
    message = f"""
✅ <b>ORDER FILLED</b>

📌 <b>Order:</b> {order_id}
📊 <b>Side:</b> {side}
🎯 <b>Shares:</b> {shares} @ ${fill_price:.2f}
₿ <b>BTC:</b> ${btc_price:,.2f}
"""
    send_message(message.strip())


def notify_settlement(
    order_id: str,
    side: str,
    shares: int,
    result: str,
    pnl: float,
    price_to_beat: float,
    btc_settle: float,
    new_balance: float,
    fees: float
):
    """Notify trade settlement result."""
    win = result == "WIN"
    emoji = "🏆" if win else "❌"
    pnl_emoji = "📈" if pnl >= 0 else "📉"
    
    message = f"""
{emoji} <b>TRADE SETTLED - {result}</b>

📌 <b>Order:</b> {order_id}
📊 <b>Side:</b> {side} ({shares} shares)
₿ <b>Price to Beat:</b> ${price_to_beat:,.2f}
₿ <b>Settle Price:</b> ${btc_settle:,.2f}
{pnl_emoji} <b>PnL:</b> ${pnl:+.4f}
💸 <b>Fees:</b> ${fees:.4f}
💼 <b>New Balance:</b> ${new_balance:.2f}
"""
    send_message(message.strip())


def notify_bot_started(balance: float, btc_price: float):
    """Notify when bot starts."""
    message = f"""
🚀 <b>POLYBOT STARTED</b>

💼 <b>Balance:</b> ${balance:.2f}
₿ <b>BTC Price:</b> ${btc_price:,.2f}
⏰ <b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Ready to trade!
"""
    send_message(message.strip())


def notify_market_found(slug: str, price_to_beat: float):
    """Notify when a new market is discovered."""
    message = f"""
🔍 <b>MARKET FOUND</b>

📈 <b>Slug:</b> {slug}
₿ <b>Price to Beat:</b> ${price_to_beat:,.2f}
"""
    send_message(message.strip())


# Test function
if __name__ == "__main__":
    # Load .env manually for testing
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # Simple .env loader
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Reload credentials
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    print(f"Testing Telegram notifier...")
    print(f"Token: {TELEGRAM_BOT_TOKEN[:10]}... Chat: {TELEGRAM_CHAT_ID}")
    
    success = send_message("🤖 <b>PolyBot Test</b>\n\nTelegram notifications are working!")
    print(f"Test result: {'Success!' if success else 'Failed'}")
