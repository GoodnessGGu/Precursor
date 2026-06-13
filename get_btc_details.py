import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def get_details():
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
        
        # Get Symbol by ID (BTC is 101)
        print("Requesting full details for Symbol ID 101 (BTCUSD) via direct ID req...")
        await ws.send(json.dumps({
            "payloadType": 2114, # ProtoOASymbolByIdReq
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "symbolId": [101]
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        print(f"DEBUG: RAW RESPONSE: {data}")
        
        symbols = data.get('payload', {}).get('symbol', [])
        for s in symbols:
            print("\n--- BTCUSD SPECIFICATIONS ---")
            print(json.dumps(s, indent=4))
            print("----------------------------\n")
            return

if __name__ == "__main__":
    asyncio.run(get_details())
