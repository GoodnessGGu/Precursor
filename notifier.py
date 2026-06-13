import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class TelegramNotifier:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
        self.chat_id = TELEGRAM_CHAT_ID

    async def send_message(self, text):
        if self.bot and self.chat_id:
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode='Markdown')
            except Exception as e:
                print(f"Telegram Error: {e}")

    async def notify_entry(self, signal):
        msg = (
            f"🚀 *TRADE EXECUTED*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔹 *Asset:* {signal['symbol']}\n"
            f"🔹 *Action:* {signal['action'].upper()}\n"
            f"🔹 *Price:* {signal['price']:.2f}\n"
            f"🛑 *SL:* {signal['sl']:.2f}\n"
            f"🎯 *TP:* {signal['tp']:.2f}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🤖 _Monitoring market for exit..._"
        )
        await self.send_message(msg)

    async def notify_exit(self, symbol, pnl, reason):
        icon = "✅" if pnl > 0 else "❌"
        msg = (
            f"{icon} *TRADE CLOSED*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔹 *Asset:* {symbol}\n"
            f"🔹 *Result:* {'PROFIT' if pnl > 0 else 'LOSS'}\n"
            f"🔹 *Net PnL:* ${pnl:.2f}\n"
            f"🔹 *Reason:* {reason}\n"
            f"━━━━━━━━━━━━━━━"
        )
        await self.send_message(msg)

    async def notify_news(self, news_item):
        msg = (
            f"📰 *MARKET UPDATE*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔸 *Source:* {news_item['source']}\n"
            f"🔸 *Headline:* {news_item['title']}\n"
            f"🔗 [Read More]({news_item['url']})"
        )
        await self.send_message(msg)
