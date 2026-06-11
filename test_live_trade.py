import asyncio
import json
import os
from dotenv import load_dotenv
from deriv_engine import DerivBot

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
DERIV_APP_ID = os.getenv("DERIV_APP_ID")

async def test_live_trade():
    print("🚀 INITIATING LIVE TEST TRADE...")
    bot = DerivBot(DERIV_TOKEN, DERIV_APP_ID)
    
    # 1. Verification
    info = await bot.get_account_info()
    if "error" in info:
        print(f"❌ Verification Failed: {info['error']}")
        return

    print(f"✅ Verified Account: {info.get('balance')} {info.get('currency')}")

    # 2. Execute Trade
    # Asset: Gold (frxXAUUSD)
    # Side: Long (CALL)
    # Amount: $10 (Tiny test)
    print("\n📦 Sending $10 Volatility 100 Long order to Deriv...")
    order = await bot.place_order(
        symbol="R_100", # Synthetic indices are always open and accept 15m durations
        side="long",
        price=2300, 
        sl=2280,
        tp=2350,
        amount=10
    )

    if "error" in order:
        print(f"❌ Order Failed: {order['error']['message']}")
    else:
        print("\n🎉 TRADE SUCCESSFUL!")
        print(f"Contract ID: {order['buy']['contract_id']}")
        print(f"Buy Price:   {order['buy']['buy_price']} {info.get('currency')}")
        print("Check your Deriv app now to see the open position!")

if __name__ == "__main__":
    asyncio.run(test_live_trade())
