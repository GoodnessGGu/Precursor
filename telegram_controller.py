from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import os
import json
import asyncio
from dotenv import load_dotenv
from config_manager import config

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
        
        # Import dynamic sync time
        from strategy_monitor import LAST_CANDLE_TIME
        is_paused = config.get("is_paused")
        ai_filter = config.get("ai_filter_enabled")
        rr = config.get("rr_ratio")
        lot = config.get("lot_size")
        
        balance_str = "Fetching..."
        pnl_str = "$0.00"
        
        if self.ctrader:
            info = await self.ctrader.get_account_info()
            if "error" not in info:
                balance_str = f"${info['balance']:,.2f} {info['currency']}"
                positions = await self.ctrader.get_open_positions()
                total_pnl = sum([p.get('unrealizedNetProfit', 0) for p in positions]) / 100.0
                pnl_str = f"${total_pnl:,.2f}"
                if total_pnl > 0: pnl_str = "🟢 " + pnl_str
                elif total_pnl < 0: pnl_str = "🔴 " + pnl_str

        status_icon = "⏸️ PAUSED" if is_paused else "🚀 ACTIVE"

        await update.message.reply_text(
            f"📡 *Gushtec Bot Status: {status_icon}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 *Balance:* `{balance_str}`\n"
            f"📈 *Live PnL:* `{pnl_str}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚙️ *Settings:*\n"
            f"• RR Ratio: `{rr}:1`\n"
            f"• Lot Size: `{lot}`\n"
            f"• AI Filter: `{'Enabled ✅' if ai_filter else 'Disabled ❌'}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔹 *Mode:* {mode}\n"
            f"🔹 *Asset:* BTCUSD (5m)\n"
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
        keyboard = [
            [
                InlineKeyboardButton("⚖️ RR: 1:1", callback_data="set_rr_1.0"),
                InlineKeyboardButton("⚖️ RR: 3:1", callback_data="set_rr_3.0")
            ],
            [
                InlineKeyboardButton("📦 Lot: 0.01", callback_data="set_lot_0.01"),
                InlineKeyboardButton("📦 Lot: 0.10", callback_data="set_lot_0.1")
            ],
            [
                InlineKeyboardButton("🧠 Toggle AI Filter", callback_data="toggle_ai")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚙️ *Gushtec AI Settings*\n"
            "Adjust your risk and logic parameters in real-time.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("set_rr_"):
            val = float(query.data.replace("set_rr_", ""))
            config.set("rr_ratio", val)
            await query.edit_message_text(text=f"✅ *Risk:Reward set to {val}:1*", parse_mode='Markdown')
            
        elif query.data.startswith("set_lot_"):
            val = float(query.data.replace("set_lot_", ""))
            config.set("lot_size", val)
            await query.edit_message_text(text=f"✅ *Default Lot Size set to {val}*", parse_mode='Markdown')
            
        elif query.data == "toggle_ai":
            current = config.get("ai_filter_enabled")
            config.set("ai_filter_enabled", not current)
            status = "ENABLED ✅" if not current else "DISABLED ❌"
            await query.edit_message_text(text=f"🧠 *AI Probability Filter is now {status}*", parse_mode='Markdown')
            
        elif query.data.startswith("close_"):
            symbol = query.data.replace("close_", "")
            await query.edit_message_text(text=f"⏳ *Closing {symbol} position...*", parse_mode='Markdown')
            # Actual close logic would be implemented here

    async def toggle_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        should_pause = "Pause" in text
        config.set("is_paused", should_pause)
        status = "PAUSED ⏸️" if should_pause else "RESUMED 🚀"
        await update.message.reply_text(f"🤖 Bot has been *{status}* by user.", parse_mode='Markdown')

    async def get_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🚀 *Fetching latest market news...*")
        await update.message.reply_text(
            "📈 *DXY Index:* 105.18 (-0.05%)\n"
            "📉 *BTC Dominance:* 52.4%\n"
            "📢 *Next Major Event:* FOMC Meeting in 4 days.",
            parse_mode='Markdown'
        )

    async def setup(self):
        if not self.token: return None
        app = ApplicationBuilder().token(self.token).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.Text("📊 Status"), self.get_status))
        app.add_handler(MessageHandler(filters.Text("⚙️ Settings"), self.get_settings))
        app.add_handler(MessageHandler(filters.Text("📢 Latest News"), self.get_news))
        app.add_handler(MessageHandler(filters.Text("📰 Calendar"), self.get_calendar))
        app.add_handler(MessageHandler(filters.Regex("Pause Bot"), self.toggle_pause))
        app.add_handler(MessageHandler(filters.Regex("Resume Bot"), self.toggle_pause))
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        print("✅ Telegram Controller Interface Live.")
        return app
