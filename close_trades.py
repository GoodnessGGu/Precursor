import asyncio
from ctrader_engine import CTraderBot
import os
from dotenv import load_dotenv

load_dotenv()

async def close_all():
    print("--- CLOSING ALL OPEN POSITIONS ---")
    bot = CTraderBot()
    
    # Ensure trade connection
    success = await bot.connect_trade()
    if not success:
        print("❌ Handshake Failed")
        return

    results = await bot.close_all_positions()
    
    if not results:
        print("No trades were found or closed.")
    else:
        print(f"✅ Successfully processed {len(results)} close requests.")
        for res in results:
            if "error" in res:
                print(f"❌ Error: {res['error']}")
            else:
                print(f"✅ Close Event: {res.get('payloadType')}")

if __name__ == "__main__":
    asyncio.run(close_all())
