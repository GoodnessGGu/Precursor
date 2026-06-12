import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, SMAIndicator
from ta.momentum import RSIIndicator
import asyncio
from datetime import datetime

class HybridStrategy:
    def __init__(self, fvg_threshold=0.0, rr_ratio=3.0):
        self.fvg_threshold = fvg_threshold
        self.rr_ratio = rr_ratio
        
        # State management
        self.bullish_fvg = None 
        self.bearish_fvg = None

    def scan_for_signals(self, df):
        """Replicates the $100 Budget Edition logic"""
        if len(df) < 5: return None
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        old = df.iloc[-3] 
        
        # 1. FVG Detection
        if curr['Low'] > old['High']:
            self.bullish_fvg = {"bottom": old['High'], "top": curr['Low']}
        if curr['High'] < old['Low']:
            self.bearish_fvg = {"bottom": curr['High'], "top": old['Low']}

        # 2. Efficiency Filter (Neutralize if touched)
        if self.bullish_fvg and curr['Low'] <= self.bullish_fvg['bottom']:
            self.bullish_fvg = None
        if self.bearish_fvg and curr['High'] >= self.bearish_fvg['top']:
            self.bearish_fvg = None

        # 3. Simple Confirmation Trigger
        is_green = curr['Close'] > curr['Open']
        was_red = prev['Close'] < prev['Open']

        # LONG
        if self.bullish_fvg and curr['Low'] <= self.bullish_fvg['top'] and curr['Low'] > self.bullish_fvg['bottom']:
            if is_green and was_red:
                sl = self.bullish_fvg['bottom']
                tp = curr['Close'] + (curr['Close'] - sl) * self.rr_ratio
                self.bullish_fvg = None 
                return {"action": "long", "symbol": "BTCUSD", "price": curr['Close'], "sl": sl, "tp": tp}

        # SHORT
        if self.bearish_fvg and curr['High'] >= self.bearish_fvg['bottom'] and curr['High'] < self.bearish_fvg['top']:
            if not is_green and not was_red:
                sl = self.bearish_fvg['top']
                tp = curr['Close'] - (sl - curr['Close']) * self.rr_ratio
                self.bearish_fvg = None
                return {"action": "short", "symbol": "BTCUSD", "price": curr['Close'], "sl": sl, "tp": tp}

        return None

async def monitor_market(callback):
    """Background loop for BTC 5m (Optimized Cloud Mode)"""
    print("🚀 Starting BTC 5m Monitor ($100 Budget Mode - Optimized)")
    strat = HybridStrategy(rr_ratio=3.0)
    
    while True:
        try:
            # Fetch Bitcoin Data (5m timeframe)
            data = yf.download("BTC-USD", period="1d", interval="5m", progress=False)
            if data.empty:
                await asyncio.sleep(60)
                continue
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            signal = strat.scan_for_signals(data)
            if signal:
                print(f"🎯 BTC SIGNAL: {signal['action'].upper()} @ {signal['price']}")
                await callback(signal)

            # Check every 60 seconds for 5m candle updates
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"❌ Monitor Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    async def dummy_callback(sig): print(f"Executing: {sig}")
    asyncio.run(monitor_market(dummy_callback))
