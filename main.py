from fastapi import FastAPI, Request, BackgroundTasks
import os
import json
import numpy as np
from tensorflow import keras
from fredapi import Fred
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from ctrader_engine import CTraderBot
from notifier import TelegramNotifier

import asyncio
from contextlib import asynccontextmanager
from strategy_monitor import monitor_market_v2

from telegram_controller import TelegramController

from calendar_engine import EconomicCalendar
from config_manager import config

# Initialize global components
ctrader = CTraderBot()
telegram = TelegramNotifier()
tg_controller = TelegramController(ctrader_bot=ctrader)
calendar = EconomicCalendar()

async def news_check_task():
    """Background task to monitor news and auto-pause the bot"""
    while True:
        try:
            calendar.fetch_events()
            is_active, event_title = calendar.is_news_active(buffer_before=15, buffer_after=15)
            
            if is_active and not config.get("is_paused"):
                config.set("is_paused", True)
                await telegram.send_message(f"⚠️ *AUTO-PAUSE:* {event_title}\nTrading paused to avoid news volatility.")
            
            elif not is_active and config.get("is_paused"):
                config.set("is_paused", False)
                await telegram.send_message("🚀 *RESUMING:* News window passed. Strategy monitor active.")

            await asyncio.sleep(300)
        except Exception as e:
            print(f"News Task Error: {e}")
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🌍 Starting STANDALONE CLOUD MODE (Execution: {os.getenv('EXECUTION_MODE', 'MT5')})")
    await telegram.send_message("🚀 *Gushtec AI Cloud Bot Initialized*\n\nMonitoring BTCUSD Live Ticks.")
    
    # 1. Start LIVE TICK Market Monitor (v2)
    asyncio.create_task(monitor_market_v2(ctrader, process_trade))
    
    # 2. Start News Monitor
    asyncio.create_task(news_check_task())
    
    # 3. Start Telegram Controller (for commands/status)
    await tg_controller.setup()
    yield

app = FastAPI(lifespan=lifespan)

# --- Configuration ---
EXECUTION_MODE = os.getenv('EXECUTION_MODE', 'MT5').upper()
USE_AI_FILTER = os.getenv('USE_AI_FILTER', 'False').upper() == 'TRUE'
FRED_API_KEY = os.getenv('FRED_API_KEY', '6fde9aa3f283e43086ae4423e7769e37')
MT5_SIGNAL_PATH = r"C:\Users\GushEx\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\signals"

# --- Load AI System ---
model = None
SCALER_MEAN = None
SCALER_SCALE = None
if USE_AI_FILTER:
    MODEL_PATH = os.path.join('models', 'fvg_ai_filter_v2.h5')
    if os.path.exists(MODEL_PATH):
        SCALER_MEAN = np.load(os.path.join('models', 'scaler_mean_v2.npy'))
        SCALER_SCALE = np.load(os.path.join('models', 'scaler_scale_v2.npy'))
        model = keras.models.load_model(MODEL_PATH)

def get_market_context():
    fred = Fred(api_key=FRED_API_KEY)
    rates = fred.get_series('FEDFUNDS', observation_start=datetime.now() - timedelta(days=60)).iloc[-1]
    dxy = fred.get_series('DTWEXBGS', observation_start=datetime.now() - timedelta(days=60)).iloc[-1]
    cpi = fred.get_series('CPIAUCSL', observation_start=datetime.now() - timedelta(days=60)).iloc[-1]
    data = yf.download('GLD', period='5d', interval='15m', progress=False)
    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
    rsi = RSIIndicator(close=data['Close'], window=14).rsi().iloc[-1]
    atr = AverageTrueRange(high=data['High'], low=data['Low'], close=data['Close'], window=14).average_true_range().iloc[-1]
    return {'CPI': cpi, 'Rates': rates, 'DXY': dxy, 'RSI': rsi, 'ATR': atr}

async def process_trade(signal_data):
    """The brain of the execution - Supports MT5 and cTrader"""
    side_str = signal_data.get('action') 
    symbol = signal_data.get('symbol', 'BTCUSD')
    price = float(signal_data.get('price', 0))
    sl = float(signal_data.get('sl', 0))
    tp = float(signal_data.get('tp', 0))
    
    qty = float(signal_data.get('qty', config.get("lot_size"))) 

    approved = True
    if config.get("ai_filter_enabled") and model:
        try:
            ctx = get_market_context()
            side = 1 if side_str.lower() == 'long' else 0
            raw_input = np.array([[side, ctx['CPI'], ctx['Rates'], ctx['DXY'], ctx['RSI'], ctx['ATR']]])
            scaled_input = (raw_input - SCALER_MEAN) / SCALER_SCALE
            prediction = model.predict(scaled_input, verbose=0)[0][0]
            score = prediction * 100
            approved = (side == 1 and score > 55) or (side == 0 and score < 45)
        except Exception as e:
            print(f"AI Filter Error: {e}")

    if approved:
        print(f"✅ TRADE APPROVED - Mode: {EXECUTION_MODE} | Asset: {symbol}")
        await telegram.notify_entry(signal_data)
        
        if EXECUTION_MODE == 'CTRADER' and ctrader:
            result = await ctrader.place_order(symbol, side_str, qty, sl_price=sl, tp_price=tp)
            if "error" in result:
                await telegram.send_message(f"❌ *Broker Rejection:* {result['error']}")
        else:
            if os.path.exists(MT5_SIGNAL_PATH):
                signal_file = os.path.join(MT5_SIGNAL_PATH, f"signal_{int(datetime.now().timestamp())}.json")
                with open(signal_file, 'w') as f:
                    json.dump(signal_data, f)
    else:
        print(f"❌ AI BLOCKED - Trade rejected due to low probability.")

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(process_trade, payload)
    return {"status": "received"}

@app.get("/")
def health():
    return {"status": "online", "mode": EXECUTION_MODE, "ai_filter": config.get("ai_filter_enabled")}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port)
