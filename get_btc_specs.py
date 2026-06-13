import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def get_btc_specs():
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
        
        # 1. Get Symbols List for account to see active symbols (2116)
        print("Fetching full symbol data for ID 101...")
        await ws.send(json.dumps({
            "payloadType": 2116, 
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "includeSymbolEntities": True
            }
        }))
        
        # 2. Get Trading Parameters (to find lot size, etc)
        # We'll read multiple messages
        for _ in range(20):
            res = await ws.recv()
            data = json.loads(res)
            pt = data.get('payloadType')
            
            if pt == 2117: # ProtoOASymbolsListRes
                symbols = data.get('payload', {}).get('symbol', [])
                for s in symbols:
                    if s.get('symbolId') == 101:
                        print("\n--- BTCUSD FULL SPECS ---")
                        print(json.dumps(s, indent=4))
                        print("-------------------------\n")
                        return

        print("Symbol 101 specs not found in the first 20 messages.")

if __name__ == "__main__":
    asyncio.run(get_btc_specs())
