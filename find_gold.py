import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def find_gold():
    client_id = os.getenv('CTRADER_CLIENT_ID')
    secret = os.getenv('CTRADER_SECRET')
    access_token = os.getenv('CTRADER_ACCESS_TOKEN')
    account_id = os.getenv('CTRADER_ACCOUNT_ID')
    env = os.getenv('CTRADER_ENVIRONMENT', 'demo').lower()
    
    uri = "wss://live.ctraderapi.com:5036" if env == 'live' else "wss://demo.ctraderapi.com:5036"
    
    async with websockets.connect(uri) as ws:
        # 1. App Auth
        await ws.send(json.dumps({
            "payloadType": 2100,
            "payload": {"clientId": client_id, "clientSecret": secret}
        }))
        await ws.recv()
        
        # 2. Account Auth
        await ws.send(json.dumps({
            "payloadType": 2102,
            "payload": {"ctidTraderAccountId": int(account_id), "accessToken": access_token}
        }))
        await ws.recv()
        
        # 3. Get Symbols for Conversion (XAU to USD)
        print("Fetching conversion symbols for XAU(17) to USD(15)...")
        await ws.send(json.dumps({
            "payloadType": 2118, # ProtoOASymbolsForConversionReq
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "firstAssetId": 17, 
                "lastAssetId": 15
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        print(f"DEBUG: Conversion Response: {data}")
        
        symbols = data.get('payload', {}).get('symbol', [])
        found = False
        for s in symbols:
            name = s.get('symbolName', '')
            print(f"✅ FOUND MATCH: {name} (ID: {s.get('symbolId')})")
            found = True
        print("--------------------------\n")

if __name__ == "__main__":
    asyncio.run(find_gold())
