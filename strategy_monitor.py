import pandas as pd
import numpy as np
import asyncio
from datetime import datetime
from config_manager import config

class HybridStrategy:
    def __init__(self, fvg_threshold=0.0, rr_ratio=1.0):
        self.fvg_threshold = fvg_threshold
        self.rr_ratio = rr_ratio
        
        # State management (Persistence across ticks)
        self.bullish_fvg = None 
        self.bearish_fvg = None
        self.last_candle_processed = None

    def update_with_tick(self, bid, ask, df_5m):
        """
        Core logic updated by every market tick.
        df_5m: Last few closed 5m candles for FVG detection.
        """
        if len(df_5m) < 5: return None
        
        # 1. Price Scaling Check (cTrader sends integers)
        price = (bid + ask) / 2.0
        if price > 10000000: # 5 digits (e.g. 6400000000)
            price = price / 100000.0
        elif price > 1000000: # 2 digits (e.g. 6400000)
            price = price / 100.0
            
        if price == 0: return None

        # 2. Check for New FVG (from closed candles)
        last_candle_ts = df_5m.index[-1]
        if last_candle_ts != self.last_candle_processed:
            self.last_candle_processed = last_candle_ts
            curr_c = df_5m.iloc[-1]
            prev_c = df_5m.iloc[-2]
            old_c = df_5m.iloc[-3]
            
            # Bullish FVG: Low[0] > High[2]
            if curr_c['Low'] > old_c['High']:
                self.bullish_fvg = {"bottom": old_c['High'], "top": curr_c['Low'], "created": last_candle_ts}
                print(f"🆕 FVG DETECTED: Bullish at {self.bullish_fvg['bottom']} - {self.bullish_fvg['top']}")

            # Bearish FVG: High[0] < Low[2]
            if curr_c['High'] < old_c['Low']:
                self.bearish_fvg = {"bottom": curr_c['High'], "top": old_c['Low'], "created": last_candle_ts}
                print(f"🆕 FVG DETECTED: Bearish at {self.bearish_fvg['bottom']} - {self.bearish_fvg['top']}")

            # Efficiency Filter: If candle closes through FVG, kill it
            if self.bullish_fvg and curr_c['Low'] <= self.bullish_fvg['bottom']: 
                print("🗑️ FVG NEUTRALIZED: Bullish box pierced.")
                self.bullish_fvg = None
            if self.bearish_fvg and curr_c['High'] >= self.bearish_fvg['top']: 
                print("🗑️ FVG NEUTRALIZED: Bearish box pierced.")
                self.bearish_fvg = None

        # 3. Entry Logic (Real-time Tick Check)
        
        # Log distance to FVG periodically for visibility (every 50 ticks)
        if not hasattr(self, 'tick_count'): self.tick_count = 0
        self.tick_count += 1
        if self.tick_count % 50 == 0:
            if self.bullish_fvg:
                dist = price - self.bullish_fvg['top']
                print(f"👀 WATCHING BULLISH FVG: BTC at {price:.2f} | Dist to box: {dist:.2f}")
            if self.bearish_fvg:
                dist = self.bearish_fvg['bottom'] - price
                print(f"👀 WATCHING BEARISH FVG: BTC at {price:.2f} | Dist to box: {dist:.2f}")

        # LONG TRIGGER
        if self.bullish_fvg and price <= self.bullish_fvg['top'] and price > self.bullish_fvg['bottom']:
            # Entry Confirmation: We need a slight uptick or 'rejection' 
            # (In Pine this was candle close > open, here we'll trigger on first touch)
            sl = self.bullish_fvg['bottom']
            rr = config.get("rr_ratio")
            tp = price + (price - sl) * rr
            
            signal = {"action": "long", "symbol": "BTCUSD", "price": price, "sl": sl, "tp": tp}
            self.bullish_fvg = None 
            return signal

        # SHORT TRIGGER
        if self.bearish_fvg and price >= self.bearish_fvg['bottom'] and price < self.bearish_fvg['top']:
            sl = self.bearish_fvg['top']
            rr = config.get("rr_ratio")
            tp = price - (sl - price) * rr
            
            signal = {"action": "short", "symbol": "BTCUSD", "price": price, "sl": sl, "tp": tp}
            self.bearish_fvg = None
            return signal

        return None

# Global tracking for Telegram Status
LAST_CANDLE_TIME = "Initializing..."
LAST_TICK_PRICE = 0.0

async def monitor_market_v2(ctrader, callback):
    """Upgraded monitor using cTrader Live Ticks"""
    global LAST_CANDLE_TIME, LAST_TICK_PRICE
    print("🚀 Starting BTC Live Tick Monitor (cTrader Direct Feed)")
    
    import yfinance as yf
    strat = HybridStrategy()

    async def on_tick(payload):
        global LAST_CANDLE_TIME, LAST_TICK_PRICE
        
        if config.get("is_paused"): return

        raw_bid = payload.get('bid', 0)
        raw_ask = payload.get('ask', raw_bid)
        
        # Scaling
        bid, ask = raw_bid, raw_ask
        if bid > 10000000:
            bid, ask = bid / 100000.0, ask / 100000.0
        elif bid > 1000000:
            bid, ask = bid / 100.0, ask / 100.0
            
        LAST_TICK_PRICE = (bid + ask) / 2.0

        # Every 30 ticks, we refresh the 5m candles (using Bitstamp equivalent)
        if not hasattr(on_tick, "counter"): on_tick.counter = 0
        on_tick.counter += 1
        
        if on_tick.counter % 30 == 0 or not hasattr(on_tick, "df_5m"):
            try:
                df = yf.download("BTC-USD", period="1d", interval="5m", progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    on_tick.df_5m = df
                    LAST_CANDLE_TIME = df.index[-1].strftime('%H:%M')
                    if on_tick.counter % 300 == 0:
                        print(f"📊 Market Sync: BTC at {LAST_TICK_PRICE:.2f} (Last Candle: {LAST_CANDLE_TIME})")
            except:
                pass

        # Run Strategy
        if hasattr(on_tick, "df_5m"):
            signal = strat.update_with_tick(bid, ask, on_tick.df_5m)
            if signal:
                print(f"🎯 LIVE TICK SIGNAL: {signal['action'].upper()} @ {signal['price']}")
                # CRITICAL: Run callback in background so it doesn't block the tick loop
                asyncio.create_task(callback(signal))

    # Start the continuous WebSocket subscription
    while True:
        try:
            await ctrader.subscribe_live_prices("BTCUSD", on_tick)
        except Exception as e:
            print(f"Tick Monitor Error: {e}. Restarting in 10s...")
            await asyncio.sleep(10)
