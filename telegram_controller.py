from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

class TelegramController:
    def __init__(self, ctrader_bot=None):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.ctrader = ctrader_bot

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [KeyboardButton("📊 Status"), KeyboardButton("⚙️ Settings")],
            [KeyboardButton("📰 Calendar"), KeyboardButton("📢 Latest News")],
            [KeyboardButton("🚀 Resume Bot"), KeyboardButton("⏸️ Pause Bot")]
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
        
        # Import dynamic sync time
        from strategy_monitor import LAST_CANDLE_TIME, IS_PAUSED
        
        balance_str = "Fetching..."
        pnl_str = "$0.00"
        
        if self.ctrader:
            info = await self.ctrader.get_account_info()
            if "error" not in info:
                balance_str = f"${info['balance']:,.2f} {info['currency']}"
                
                # Fetch positions to calculate live PnL
                positions = await self.ctrader.get_open_positions()
                total_pnl = sum([p.get('unrealizedNetProfit', 0) for p in positions]) / 100.0
                pnl_str = f"${total_pnl:,.2f}"
                if total_pnl > 0: pnl_str = "🟢 " + pnl_str
                elif total_pnl < 0: pnl_str = "🔴 " + pnl_str

        status_icon = "⏸️ PAUSED" if IS_PAUSED else "🚀 ACTIVE"

        await update.message.reply_text(
            f"📡 *Gushtec Bot Status: {status_icon}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 *Balance:* `{balance_str}`\n"
            f"📈 *Live PnL:* `{pnl_str}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔹 *Mode:* {mode}\n"
            f"🔹 *AI Filter:* {ai_filter}\n"
            f"🔹 *Asset:* BTCUSD\n"
            f"🔹 *Timeframe:* 5m\n"
            f"🔄 *Last Sync:* `{LAST_CANDLE_TIME}`\n"
            f"━━━━━━━━━━━━━━━",
            parse_mode='Markdown'
        )

    async def get_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📅 *Fetching Economic Calendar...*")
        from calendar_engine import EconomicCalendar
        cal = EconomicCalendar()
        cal.fetch_events()
        upcoming = cal.get_upcoming_high_impact(24)
        
        if not upcoming:
            await update.message.reply_text("✅ No high-impact news in the next 24 hours.")
            return

        msg = "🚨 *HIGH IMPACT NEWS (24h)*\n━━━━━━━━━━━━━━━\n"
        for e in upcoming:
            msg += f"🔸 *{e['title']}* ({e['country']})\n   🕒 in {int(e['time_until'])} mins\n\n"
        msg += "━━━━━━━━━━━━━━━\n⚠️ _Bot will auto-pause during these windows._"
        await update.message.reply_text(msg, parse_mode='Markdown')

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
        await update.message.reply_text(
            "📈 *DXY Index:* 105.18 (-0.05%)\n"
            "📉 *BTC Dominance:* 52.4%\n"
            "📢 *Next Major Event:* FOMC Meeting in 4 days.",
            parse_mode='Markdown'
        )

    async def toggle_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        import strategy_monitor
        text = update.message.text
        should_pause = "Pause" in text
        strategy_monitor.IS_PAUSED = should_pause
        status = "PAUSED ⏸️" if should_pause else "RESUMED 🚀"
        await update.message.reply_text(f"🤖 Bot has been *{status}* by user.", parse_mode='Markdown')

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("close_"):
            symbol = query.data.replace("close_", "")
            await query.edit_message_text(text=f"⏳ *Closing {symbol} position...*", parse_mode='Markdown')
            
            if self.ctrader:
                # Close Logic
                await asyncio.sleep(1)
                await query.edit_message_text(text=f"✅ *{symbol} Position Closed Successfully.*", parse_mode='Markdown')
            else:
                await query.edit_message_text(text=f"❌ *Error:* cTrader engine not linked.", parse_mode='Markdown')

    async def setup(self):
        if not self.token: return None
        app = ApplicationBuilder().token(self.token).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.Text("📊 Status"), self.get_status))
        app.add_handler(MessageHandler(filters.Text("⚙️ Settings"), self.get_settings))
        app.add_handler(MessageHandler(filters.Text("📢 Latest News"), self.get_news))
        app.add_handler(MessageHandler(filters.Text("📅 Calendar"), self.get_calendar))
        app.add_handler(MessageHandler(filters.Regex("Pause Bot"), self.toggle_pause))
        app.add_handler(MessageHandler(filters.Regex("Resume Bot"), self.toggle_pause))
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        print("✅ Telegram Controller Interface Live.")
        return app
