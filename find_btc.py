import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def find_btc():
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
        
        # Search for BTC to USD conversion symbols (most reliable)
        # We know from previous run: BTC Asset ID = 31, USD Asset ID = 15
        print("Searching for BTC (31) to USD (15)...")
        await ws.send(json.dumps({
            "payloadType": 2118, 
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "firstAssetId": 31, 
                "lastAssetId": 15
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        symbols = data.get('payload', {}).get('symbol', [])
        print("\n--- BTC SYMBOL DISCOVERY ---")
        for s in symbols:
            print(f"✅ MATCH: {s.get('symbolName')} (ID: {s.get('symbolId')})")
        print("----------------------------\n")

if __name__ == "__main__":
    asyncio.run(find_btc())
