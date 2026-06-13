from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
import json
from dotenv import load_dotenv

load_dotenv()

class TelegramController:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [KeyboardButton("📊 Status"), KeyboardButton("⚙️ Settings")],
            [KeyboardButton("📰 Latest News")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "💎 *Gushtec AI Command Center*\n"
            "Cloud Trading Bot is connected. Use the menu below to control your trades.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def get_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mode = os.getenv("EXECUTION_MODE", "MT5")
        ai_filter = os.getenv("USE_AI_FILTER", "False")
        await update.message.reply_text(
            f"📡 *Current Bot Status*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔹 *Mode:* {mode}\n"
            f"🔹 *AI Filter:* {ai_filter}\n"
            f"🔹 *Asset:* BTCUSD\n"
            f"🔹 *Timeframe:* 5m\n"
            f"━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )

    async def get_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Template for news fetching
        await update.message.reply_text("🚀 *Fetching latest market news...*")
        # Logic to call News API or FRED would go here
        await update.message.reply_text("✅ *DXY Index:* 105.2 (Trending Down 📉)\n✅ *FED Sentiment:* Hawkish but stable.", parse_mode='Markdown')

    async def setup(self):
        if not self.token: return None
        app = ApplicationBuilder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.Text("📊 Status"), self.get_status))
        app.add_handler(MessageHandler(filters.Text("📰 Latest News"), self.get_news))
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        print("✅ Telegram Polling Started.")
        return app

if __name__ == "__main__":
    controller = TelegramController(".env")
    controller.run()
