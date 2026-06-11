import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
DERIV_APP_ID = os.getenv("DERIV_APP_ID", "1")

async def check_account():
    api_url = f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"
    print(f"Testing token: {DERIV_TOKEN[:10]}... on {api_url}")
    try:
        async with websockets.connect(api_url) as ws:
            await ws.send(json.dumps({"authorize": DERIV_TOKEN}))
            res = await ws.recv()
            data = json.loads(res)
            
            if "error" in data:
                print(f"Error: {data['error']['message']} (Code: {data['error']['code']})")
                return

            auth = data.get("authorize", {})
            print("--- SUCCESS ---")
            print(f"Account: {auth.get('email')}")
            print(f"Balance: {auth.get('balance')} {auth.get('currency')}")
            print(f"Is Virtual: {auth.get('is_virtual')}")

    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_account())
