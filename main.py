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
import pandas as pd

app = FastAPI()

# --- Load AI System ---
MODEL_PATH = os.path.join('models', 'fvg_ai_filter_v2.h5')
SCALER_MEAN = np.load(os.path.join('models', 'scaler_mean_v2.npy'))
SCALER_SCALE = np.load(os.path.join('models', 'scaler_scale_v2.npy'))
model = keras.models.load_model(MODEL_PATH)

FRED_API_KEY = os.getenv('FRED_API_KEY', '6fde9aa3f283e43086ae4423e7769e37')
DERIV_TOKEN = os.getenv('DERIV_TOKEN')
deriv_client = DerivBot(DERIV_TOKEN)

def get_market_context():
    """Fetches macro and technical data for AI Brain"""
    fred = Fred(api_key=FRED_API_KEY)
    
    # Macro
    rates = fred.get_series('FEDFUNDS', observation_start=datetime.now() - timedelta(days=60)).iloc[-1]
    dxy = fred.get_series('DTWEXBGS', observation_start=datetime.now() - timedelta(days=60)).iloc[-1]
    cpi = fred.get_series('CPIAUCSL', observation_start=datetime.now() - timedelta(days=60)).iloc[-1]
    
    # Technical (GLD proxy)
    data = yf.download('GLD', period='5d', interval='15m', progress=False)
    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
    rsi = RSIIndicator(close=data['Close'], window=14).rsi().iloc[-1]
    atr = AverageTrueRange(high=data['High'], low=data['Low'], close=data['Close'], window=14).average_true_range().iloc[-1]
    
    return {'CPI': cpi, 'Rates': rates, 'DXY': dxy, 'RSI': rsi, 'ATR': atr}

async def process_trade(signal_data):
    """The brain of the execution"""
    side_str = signal_data.get('action') # 'long' or 'short'
    symbol = signal_data.get('symbol', 'frxXAUUSD')
    price = float(signal_data.get('price', 0))
    sl = float(signal_data.get('sl', 0))
    tp = float(signal_data.get('tp', 0))

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
        print(f"✅ AI APPROVED - Sending order to Deriv...")
        await deriv_client.place_order(symbol, side_str, price, sl, tp)
    else:
        print(f"❌ AI BLOCKED - Trade rejected due to low probability.")

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Entry point for TradingView alerts"""
    payload = await request.json()
    print(f"Received Webhook: {payload}")
    background_tasks.add_task(process_trade, payload)
    return {"status": "received"}

@app.get("/")
def health():
    return {"status": "online", "model": "Gushtec Gold v2"}
