import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test_order():
    client_id = os.getenv('CTRADER_CLIENT_ID')
    secret = os.getenv('CTRADER_SECRET')
    access_token = os.getenv('CTRADER_ACCESS_TOKEN')
    account_id = os.getenv('CTRADER_ACCOUNT_ID')
    
    uri = "wss://demo.ctraderapi.com:5036"
    
    async with websockets.connect(uri) as ws:
        # Auth
        await ws.send(json.dumps({"payloadType": 2100, "payload": {"clientId": client_id, "clientSecret": secret}}))
        await ws.recv()
        await ws.send(json.dumps({"payloadType": 2102, "payload": {"ctidTraderAccountId": int(account_id), "accessToken": access_token}}))
        await ws.recv()
        
        # Place BTC Order (ID 101)
        # Try Volume = 1 (which is 0.01 units - the minimum)
        print("Sending BTC BUY order (Vol: 1)...")
        await ws.send(json.dumps({
            "payloadType": 2106,
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "symbolId": 101,
                "orderType": 1,
                "tradeSide": 1,
                "volume": 1,
                "comment": "Bot Test Min Vol"
            }
        }))
        
        # Read next 10 messages to see EXACT rejection reason
        print("Reading responses...")
        for _ in range(10):
            res = await ws.recv()
            data = json.loads(res)
            print(f"MSG: {data}")
            if data.get('payloadType') == 2126:
                print("--- FINAL RESULT ---")
                print(json.dumps(data, indent=4))
                return

if __name__ == "__main__":
    asyncio.run(test_order())
