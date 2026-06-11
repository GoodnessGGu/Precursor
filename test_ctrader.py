import asyncio
from ctrader_engine import CTraderBot
import os
from dotenv import load_dotenv

load_dotenv()

async def verify():
    print("--- CTRADER CONNECTION VERIFIER ---")
    bot = CTraderBot()
    
    # Check if credentials exist
    if not all([bot.client_id, bot.secret, bot.access_token, bot.account_id]):
        print("❌ Error: Missing credentials in .env file.")
        print("Please ensure the following are set:")
        print(" - CTRADER_CLIENT_ID")
        print(" - CTRADER_SECRET")
        print(" - CTRADER_ACCESS_TOKEN")
        print(" - CTRADER_ACCOUNT_ID")
        return

    success, msg = await bot.connect()
    
    if success:
        print("✅ SUCCESS: Connected and Authorized!")
        
        # Test Symbol ID fetching
        print("Fetching XAUUSD Symbol ID...")
        symbol_id = await bot.get_symbol_id("XAUUSD")
        if symbol_id:
            print(f"✅ XAUUSD Symbol ID: {symbol_id}")
        else:
            print("⚠️ Warning: Could not find XAUUSD in your symbol list.")
            
    else:
        print(f"❌ CONNECTION FAILED: {msg}")
        print("\nTroubleshooting:")
        print("1. Check if your Access Token has 'trade' permissions.")
        print("2. Ensure your Account ID is numeric.")
        print("3. Check if you are using the correct Environment (demo/live).")

if __name__ == "__main__":
    asyncio.run(verify())
