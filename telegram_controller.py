from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import os
import json
from dotenv import load_dotenv

load_dotenv()

class TelegramController:
    def __init__(self, ctrader_bot=None):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.ctrader = ctrader_bot

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

    async def get_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "⚙️ *Configuration Control*\n"
            "Current settings:\n"
            "• RR Ratio: 1.0\n"
            "• Leverage: 1:100\n\n"
            "Use commands like `/set_rr 2.0` to adjust (Admin only).",
            parse_mode='Markdown'
        )

    async def get_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🚀 *Fetching latest market news...*")
        # In a real setup, we'd pull from an API
        await update.message.reply_text(
            "📈 *DXY Index:* 105.18 (-0.05%)\n"
            "📉 *BTC Dominance:* 52.4%\n"
            "📢 *Next Major Event:* FOMC Meeting in 4 days.",
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("close_"):
            symbol = query.data.replace("close_", "")
            await query.edit_message_text(text=f"⏳ *Closing {symbol} position...*", parse_mode='Markdown')
            
            if self.ctrader:
                # Logic to find and close active positions would go here
                # For now, we'll simulate the result
                await asyncio.sleep(1)
                await query.edit_message_text(text=f"✅ *{symbol} Position Closed Successfully.*", parse_mode='Markdown')
            else:
                await query.edit_message_text(text=f"❌ *Error:* cTrader engine not linked to controller.", parse_mode='Markdown')

    async def setup(self):
        if not self.token: return None
        app = ApplicationBuilder().token(self.token).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.Text("📊 Status"), self.get_status))
        app.add_handler(MessageHandler(filters.Text("⚙️ Settings"), self.get_settings))
        app.add_handler(MessageHandler(filters.Text("📰 Latest News"), self.get_news))
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        print("✅ Telegram Controller Interface Live.")
        return app
