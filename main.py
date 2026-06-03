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
from deriv_engine import DerivBot
from bybit_engine import BybitBot
import pandas as pd

app = FastAPI()

# --- Load Config & Engines ---
FRED_API_KEY = os.getenv('FRED_API_KEY', '6fde9aa3f283e43086ae4423e7769e37')
DERIV_TOKEN = os.getenv('DERIV_TOKEN')
BYBIT_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_SECRET = os.getenv('BYBIT_API_SECRET')

deriv_client = DerivBot(DERIV_TOKEN)
bybit_client = BybitBot(BYBIT_KEY, BYBIT_SECRET) if BYBIT_KEY else None

# ... (keep AI model loading and context fetching same) ...

async def process_trade(signal_data):
    """The brain of the execution"""
    side_str = signal_data.get('action') # 'long' or 'short'
    symbol = signal_data.get('symbol', 'BTCUSDT')
    price = float(signal_data.get('price', 0))
    sl = float(signal_data.get('sl', 0))
    tp = float(signal_data.get('tp', 0))
    qty = float(signal_data.get('qty', 0.001)) # Default to min Bybit size

    # 1. AI Probability Filter
    ctx = get_market_context()
    side = 1 if side_str.lower() == 'long' else 0
    raw_input = np.array([[side, ctx['CPI'], ctx['Rates'], ctx['DXY'], ctx['RSI'], ctx['ATR']]])
    scaled_input = (raw_input - SCALER_MEAN) / SCALER_SCALE
    prediction = model.predict(scaled_input, verbose=0)[0][0]
    
    score = prediction * 100
    print(f"AI Score for {side_str}: {score:.2f}%")

    # 2. Execution Decision
    if (side == 1 and score > 55) or (side == 0 and score < 45):
        print(f"✅ AI APPROVED - Executing Trade...")
        # Priority: Bybit -> Deriv
        if bybit_client:
            bybit_client.place_order(symbol, side_str, qty, sl, tp)
        else:
            await deriv_client.place_order(symbol, side_str, price, sl, tp)
    else:
        print(f"❌ AI BLOCKED - Trade rejected due to low probability.")

@app.get("/bybit-account")
def bybit_info():
    if not bybit_client: return {"error": "Bybit not configured"}
    return {"balance": bybit_client.get_balance(), "coin": "USDT"}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Entry point for TradingView alerts"""
    payload = await request.json()
    print(f"Received Webhook: {payload}")
    background_tasks.add_task(process_trade, payload)
    return {"status": "received"}

@app.get("/account")
async def account_info():
    """Returns real-time balance and account details"""
    info = await deriv_client.get_account_info()
    return info

@app.get("/")
def health():
    return {"status": "online", "model": "Gushtec Gold v2"}
