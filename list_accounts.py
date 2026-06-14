import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def list_accounts():
    client_id = os.getenv('CTRADER_CLIENT_ID')
    secret = os.getenv('CTRADER_SECRET')
    access_token = os.getenv('CTRADER_ACCESS_TOKEN')
    env = os.getenv('CTRADER_ENVIRONMENT', 'demo').lower()
    
    uri = "wss://live.ctraderapi.com:5036" if env == 'live' else "wss://demo.ctraderapi.com:5036"
    
    print(f"Connecting to {env} to list accounts...")
    
    async with websockets.connect(uri) as ws:
        # 1. App Auth
        await ws.send(json.dumps({
            "payloadType": 2100,
            "payload": {"clientId": client_id, "clientSecret": secret}
        }))
        await ws.recv()
        
        # 2. Get Account List by Access Token
        await ws.send(json.dumps({
            "payloadType": 2149, # ProtoOAGetAccountListByAccessTokenReq
            "payload": {"accessToken": access_token}
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        if data.get('payloadType') == 2150: # ProtoOAGetAccountListByAccessTokenRes
            print(f"RAW PAYLOAD: {json.dumps(data.get('payload'), indent=2)}")
            accounts = data.get('payload', {}).get('ctidTraderAccount', [])
            print("\n--- FOUND ACCOUNTS ---")
            for acc in accounts:
                print(f"ID: {acc.get('ctidTraderAccountId')} | Live: {not acc.get('isLive') == False} | Broker: {acc.get('traderLogin')}")
            print("----------------------\n")
        else:
            print(f"Failed to get accounts: {res}")

if __name__ == "__main__":
    asyncio.run(list_accounts())
