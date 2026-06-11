import pandas as pd
import numpy as np
import yfinance as yf
from ta.trend import EMAIndicator, SMAIndicator
from ta.momentum import RSIIndicator
import asyncio
from datetime import datetime

class HybridStrategy:
    def __init__(self, fvg_threshold=0.0, rr_ratio=2.0):
        self.fvg_threshold = fvg_threshold
        self.rr_ratio = rr_ratio
        
        # State management (similar to var float in Pine)
        self.bullish_fvg = None # {"top": x, "bottom": y}
        self.bearish_fvg = None
        self.active_position = None # "LONG" or "SHORT"

    def calculate_indicators(self, df):
        """Calculates all necessary indicators from the Dragon Trader Pro logic"""
        # EMA 100 (Main Trend)
        df['ema100'] = EMAIndicator(close=df['Close'], window=100).ema_indicator()
        
        # SMA 3 & 50 (Flow)
        df['sma3'] = SMAIndicator(close=df['Close'], window=3).sma_indicator()
        df['sma50'] = SMAIndicator(close=df['Close'], window=50).sma_indicator()
        
        # MAD Oscillator (Momentum)
        df['mad_mean'] = SMAIndicator(close=df['Close'], window=12).sma_indicator()
        df['mad'] = df['Close'] - df['mad_mean']
        df['mad_rising'] = df['mad'] > df['mad'].shift(1)
        df['mad_falling'] = df['mad'] < df['mad'].shift(1)
        
        return df

    def scan_for_signals(self, df):
        """Replicates the Pine Script signal logic"""
        if len(df) < 5: return None
        
        # 1. Update Indicators
        df = self.calculate_indicators(df)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        old = df.iloc[-3] # Equivalent to high[2] / low[2]
        
        # 2. FVG Detection Logic
        # Bullish FVG: Low[0] > High[2]
        if curr['Low'] > old['High']:
            self.bullish_fvg = {"bottom": old['High'], "top": curr['Low']}
            print(f"[{datetime.now()}] 🟢 New Bullish FVG Detected: {self.bullish_fvg}")

        # Bearish FVG: High[0] < Low[2]
        if curr['High'] < old['Low']:
            self.bearish_fvg = {"bottom": curr['High'], "top": old['Low']}
            print(f"[{datetime.now()}] 🔴 New Bearish FVG Detected: {self.bearish_fvg}")

        # 3. Efficiency Neutralization (Box becomes invalid if touched)
        if self.bullish_fvg and curr['Low'] <= self.bullish_fvg['bottom']:
            self.bullish_fvg = None
        if self.bearish_fvg and curr['High'] >= self.bearish_fvg['top']:
            self.bearish_fvg = None

        # 4. HYBRID ENTRY LOGIC
        
        # Dragon Filters
        bull_trend_ok = curr['Close'] > curr['ema100']
        bull_mom_ok   = curr['mad_rising'] and curr['mad'] > 0
        bull_flow_ok  = curr['sma3'] > curr['sma50']

        bear_trend_ok = curr['Close'] < curr['ema100']
        bear_mom_ok   = curr['mad_falling'] and curr['mad'] < 0
        bear_flow_ok  = curr['sma3'] < curr['sma50']

        # Entry Signal (Price inside FVG + Dragon OK + Rejection)
        # We simulate rejection by checking if current candle is green and previous was red (simple version)
        is_green = curr['Close'] > curr['Open']
        was_red = prev['Close'] < prev['Open']

        # LONG TRIGGER
        if self.bullish_fvg and curr['Low'] <= self.bullish_fvg['top'] and curr['Low'] > self.bullish_fvg['bottom']:
            if bull_trend_ok and bull_mom_ok and bull_flow_ok and is_green and was_red:
                sl = self.bullish_fvg['bottom']
                tp = curr['Close'] + (curr['Close'] - sl) * self.rr_ratio
                signal = {
                    "action": "long",
                    "symbol": "XAUUSD",
                    "price": curr['Close'],
                    "sl": sl,
                    "tp": tp
                }
                self.bullish_fvg = None # Reset after entry
                return signal

        # SHORT TRIGGER
        if self.bearish_fvg and curr['High'] >= self.bearish_fvg['bottom'] and curr['High'] < self.bearish_fvg['top']:
            if bear_trend_ok and bear_mom_ok and bear_flow_ok and not is_green and not was_red:
                sl = self.bearish_fvg['top']
                tp = curr['Close'] - (sl - curr['Close']) * self.rr_ratio
                signal = {
                    "action": "short",
                    "symbol": "XAUUSD",
                    "price": curr['Close'],
                    "sl": sl,
                    "tp": tp
                }
                self.bearish_fvg = None # Reset after entry
                return signal

        return None

async def monitor_market(callback):
    """Background loop to fetch data and run strategy"""
    print("🚀 Starting Standalone Strategy Monitor (No-Subscription Mode)")
    strat = HybridStrategy()
    
    while True:
        try:
            # Fetch Gold Data (5m timeframe)
            # GC=F is Gold Futures, GLD is ETF. For Spot XAUUSD we use GLD as proxy or a real-time feed.
            data = yf.download("GC=F", period="1d", interval="5m", progress=False)
            if data.empty:
                await asyncio.sleep(60)
                continue

            # Flatten MultiIndex if present
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            signal = strat.scan_for_signals(data)
            
            if signal:
                print(f"🎯 STRATEGY SIGNAL TRIGGERED: {signal['action'].upper()}")
                await callback(signal)

            # Wait for next check (e.g., every 60 seconds)
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"❌ Monitor Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    async def dummy_callback(sig): print(f"Executing: {sig}")
    asyncio.run(monitor_market(dummy_callback))
