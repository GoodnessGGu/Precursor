import asyncio
import json
import os
from dotenv import load_dotenv
from deriv_engine import DerivBot

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
DERIV_APP_ID = os.getenv("DERIV_APP_ID")

async def run_diagnostic():
    print(f"--- 2026 DERIV DIAGNOSTIC ---")
    print(f"Token:  {DERIV_TOKEN[:10]}...")
    print(f"App ID: {DERIV_APP_ID}")
    
    bot = DerivBot(DERIV_TOKEN, DERIV_APP_ID)
    info = await bot.get_account_info()
    
    if "error" in info:
        print("\n❌ CONNECTION FAILED")
        print(f"Error: {info['error']}")
        if "code" in info:
            print(f"Code:  {info['code']}")
    else:
        print("\n✅ CONNECTION SUCCESSFUL!")
        print(f"Account:  {info.get('email')}")
        print(f"Balance:  {info.get('balance')} {info.get('currency')}")
        print(f"Is Demo:   {info.get('is_virtual')}")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
