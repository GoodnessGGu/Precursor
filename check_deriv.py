import asyncio
import websockets
import json
import os

DERIV_TOKEN = "6U2R0Y3B38J8X3Q"

async def check_account():
    api_url = "wss://re.derivws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(api_url) as ws:
            await ws.send(json.dumps({"authorize": DERIV_TOKEN}))
            res = await ws.recv()
            data = json.loads(res)
            
            if "error" in data:
                print(f"Error: {data['error']['message']}")
                return

            auth = data.get("authorize", {})
            print(f"Account: {auth.get('email')}")
            print(f"Currency: {auth.get('currency')}")
            print(f"Is Virtual: {auth.get('is_virtual')}")
            print(f"Balance: {auth.get('balance')}")
            print(f"Login ID: {auth.get('loginid')}")

    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_account())
