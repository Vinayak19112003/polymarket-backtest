"""
Telegram Notification Module
Sends real-time trade alerts to Telegram
"""
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any

class TelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            # Silent warning to avoid cluttering logs if not invoked
            pass
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram."""
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ Telegram send failed: {response.text}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Telegram send failed: {e}")
            return False
    
    def notify_signal(self, signal: str, market: str, entry_price: float, 
                     edge: float, reason: str, mode: str = "PAPER"):
        """Notify when strategy generates a signal."""
        emoji = "🟢" if signal == "YES" else "🔴"
        
        message = f"""
{emoji} <b>SIGNAL GENERATED</b> ({mode})

📊 Market: {market}
🎯 Direction: <b>{signal}</b>
💰 Entry Price: ${entry_price:.3f}
📈 Edge: {edge:.2f}%
💡 Reason: {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_order_placed(self, signal: str, market: str, size: float, 
                           price: float, order_id: str, mode: str = "PAPER"):
        """Notify when order is placed."""
        emoji = "📤"
        
        message = f"""
{emoji} <b>ORDER PLACED</b> ({mode})

🎯 Direction: <b>{signal}</b>
📊 Market: {market}
💵 Size: {size} contracts
💰 Price: ${price:.3f}
🆔 Order ID: {order_id[:12]}...

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_order_filled(self, signal: str, market: str, size: float, 
                           fill_price: float, slippage: float, mode: str = "PAPER"):
        """Notify when order is filled."""
        emoji = "✅"
        
        message = f"""
{emoji} <b>ORDER FILLED</b> ({mode})

🎯 Direction: <b>{signal}</b>
📊 Market: {market}
💵 Filled: {size} contracts
💰 Fill Price: ${fill_price:.3f}
📉 Slippage: {slippage:.2f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_order_rejected(self, signal: str, market: str, reason: str, mode: str = "PAPER"):
        """Notify when order is rejected."""
        emoji = "❌"
        
        message = f"""
{emoji} <b>ORDER REJECTED</b> ({mode})

🎯 Direction: <b>{signal}</b>
📊 Market: {market}
⚠️ Reason: {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_trade_closed(self, signal: str, market: str, entry_price: float,
                           exit_price: float, pnl: float, result: str, 
                           duration: str, mode: str = "PAPER"):
        """Notify when trade is closed."""
        emoji = "💚" if result == "WIN" else "💔"
        pnl_emoji = "📈" if pnl > 0 else "📉"
        
        message = f"""
{emoji} <b>TRADE CLOSED</b> ({mode})

🎯 Direction: <b>{signal}</b>
📊 Market: {market}
📥 Entry: ${entry_price:.3f}
📤 Exit: ${exit_price:.3f}
{pnl_emoji} PnL: ${pnl:.2f}
🏆 Result: <b>{result}</b>
⏱️ Duration: {duration}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_daily_summary(self, stats: Dict[str, Any], mode: str = "PAPER"):
        """Send daily performance summary."""
        emoji = "📊"
        
        message = f"""
{emoji} <b>DAILY SUMMARY</b> ({mode})

📅 Date: {datetime.now().strftime('%Y-%m-%d')}

📈 Performance:
• Trades: {stats.get('total_trades', 0)}
• Wins: {stats.get('wins', 0)}
• Losses: {stats.get('losses', 0)}
• Win Rate: {stats.get('win_rate', 0):.1f}%

💰 PnL:
• Today: ${stats.get('daily_pnl', 0):.2f}
• Total: ${stats.get('total_pnl', 0):.2f}
• Balance: ${stats.get('balance', 100):.2f}

📊 Execution:
• Fill Rate: {stats.get('fill_rate', 0):.1f}%
• Avg Slippage: {stats.get('avg_slippage', 0):.2f}%
• Avg Entry: ${stats.get('avg_entry', 0):.3f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def notify_error(self, error: str, context: str, mode: str = "PAPER"):
        """Notify on critical errors."""
        emoji = "🚨"
        
        message = f"""
{emoji} <b>ERROR ALERT</b> ({mode})

⚠️ Error: {error}
📍 Context: {context}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message)
    
    def test_connection(self) -> bool:
        """Test Telegram connection."""
        if not self.enabled:
            print("❌ Telegram not configured")
            return False
        
        message = """
✅ <b>TELEGRAM CONNECTED</b>

Paper trading bot is ready!
You will receive notifications for:
• Signal generation
• Order placement
• Order fills
• Trade closure
• Daily summaries
• Errors

Good luck! 🚀
"""
        success = self.send_message(message)
        if success:
            print("✅ Telegram test message sent!")
        return success
