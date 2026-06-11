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

import asyncio
from contextlib import asynccontextmanager
from strategy_monitor import monitor_market

# Initialize cTrader (Single instance)
ctrader = CTraderBot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Standalone Monitor
    print(f"🌍 Starting STANDALONE CLOUD MODE (Execution: {EXECUTION_MODE})")
    asyncio.create_task(monitor_market(process_trade))
    yield

app = FastAPI(lifespan=lifespan)

# --- Configuration ---
EXECUTION_MODE = os.getenv('EXECUTION_MODE', 'MT5').upper()
FRED_API_KEY = os.getenv('FRED_API_KEY', '6fde9aa3f283e43086ae4423e7769e37')
# Path where MT5 can read files (Specific Terminal Instance)
MT5_SIGNAL_PATH = r"C:\Users\GushEx\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\signals"

# --- Load AI System ---
MODEL_PATH = os.path.join('models', 'fvg_ai_filter_v2.h5')
SCALER_MEAN = np.load(os.path.join('models', 'scaler_mean_v2.npy'))
SCALER_SCALE = np.load(os.path.join('models', 'scaler_scale_v2.npy'))
model = keras.models.load_model(MODEL_PATH)

def get_market_context():
    """Fetches macro and technical data for AI Brain"""
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
    symbol = signal_data.get('symbol', 'XAUUSD')
    price = float(signal_data.get('price', 0))
    sl = float(signal_data.get('sl', 0))
    tp = float(signal_data.get('tp', 0))
    qty = float(signal_data.get('qty', 0.01)) 

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
        print(f"✅ AI APPROVED - Mode: {EXECUTION_MODE}")
        
        if EXECUTION_MODE == 'CTRADER' and ctrader:
            # Direct cTrader Execution
            result = await ctrader.place_order(symbol, side_str, qty, sl_price=sl, tp_price=tp)
            print(f"cTrader Result: {result}")
            
        else:
            # Fallback to MT5 File Bridge
            signal_file = os.path.join(MT5_SIGNAL_PATH, f"signal_{int(datetime.now().timestamp())}.json")
            payload = {
                "symbol": symbol,
                "side": side_str.upper(),
                "price": price,
                "sl": sl,
                "tp": tp,
                "qty": qty
            }
            with open(signal_file, 'w') as f:
                json.dump(payload, f)
            print(f"Signal saved to MT5 Bridge: {signal_file}")
    else:
        print(f"❌ AI BLOCKED - Trade rejected due to low probability.")

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    print(f"Received Signal: {payload}")
    background_tasks.add_task(process_trade, payload)
    return {"status": "received"}

@app.get("/")
def health():
    return {"status": "online", "mode": EXECUTION_MODE}

if __name__ == "__main__":
    # Railway sets the 'PORT' environment variable automatically.
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
