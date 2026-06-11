import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()
DERIV_TOKEN = os.getenv("DERIV_TOKEN")

async def test_v3_direct():
    # Attempting to connect to the new V3 WebSocket directly with the token in the message
    # using different common App IDs
    app_ids = ["1", "1089", "31063"]
    
    for app_id in app_ids:
        url = f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"
        print(f"Testing App ID {app_id} on {url}...")
        try:
            async with websockets.connect(url) as ws:
                # The 2026 way might be 'authorize' or just a direct Bearer payload
                await ws.send(json.dumps({"authorize": DERIV_TOKEN}))
                res = await ws.recv()
                print(f"Result for {app_id}: {res}")
        except Exception as e:
            print(f"Failed {app_id}: {e}")

if __name__ == "__main__":
    asyncio.run(test_v3_direct())
