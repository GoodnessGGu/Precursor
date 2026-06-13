import asyncio
import sys
from ctrader_engine import CTraderBot
import os
from dotenv import load_dotenv

load_dotenv()

async def execute(side, qty=0.01, symbol="XAUUSD"):
    print(f"--- EXECUTING TEST TRADE ---")
    print(f"Target: {side.upper()} {qty} Lots of {symbol}")
    
    bot = CTraderBot()
    success = await bot.connect_trade()
    
    if not success:
        print(f"❌ Trade Connection Failed.")
        return

    # Execute trade
    result = await bot.place_order(symbol, side, qty)
    
    if "error" in result:
        print(f"❌ Trade Failed: {result['error']}")
    else:
        print(f"✅ TRADE SUCCESSFUL!")
        print(f"Execution Data: {result['data']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python execute_trade.py <BUY/SELL> [qty] [symbol]")
    else:
        side = sys.argv[1]
        qty = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01
        symbol = sys.argv[3] if len(sys.argv) > 3 else "XAUUSD"
        asyncio.run(execute(side, qty, symbol))
