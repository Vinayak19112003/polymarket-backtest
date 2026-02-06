# Realistic Paper Trading Guide

## Setup

1. Get Telegram credentials:
   - Create bot via @BotFather
   - Get chat ID from @userinfobot
   - Add to .env:
     ```
     TELEGRAM_BOT_TOKEN=your_token
     TELEGRAM_CHAT_ID=your_chat_id
     ```

2. Test Telegram:
   ```bash
   python scripts/test_telegram.py
   ```

3. Get Polymarket market token ID:
   - Find BTC 15m market on Polymarket
   - Get YES token ID from market page
   - Update in paper_trade_realistic.py

4. Start paper trading:
   ```bash
   python scripts/trading/paper_trade_realistic.py
   ```

## What You'll Receive on Telegram

- 🟢 Signal generated
- 📤 Order placed
- ✅ Order filled (with slippage)
- ❌ Order rejected (with reason)
- 💚 Trade closed (with PnL)
- 📊 Daily summary
- 🚨 Errors

## Monitoring

- Check Telegram for all events
- Check logs/paper_trading/ for detailed logs
- Monitor balance, fill rate, slippage

## Success Criteria (7 days)

- Win rate: 55-61%
- Fill rate: >80%
- Avg slippage: <1.5%
- No critical errors
