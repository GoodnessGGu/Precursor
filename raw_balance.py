import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def get_balance():
    client_id = os.getenv('CTRADER_CLIENT_ID')
    secret = os.getenv('CTRADER_SECRET')
    access_token = os.getenv('CTRADER_ACCESS_TOKEN')
    account_id = os.getenv('CTRADER_ACCOUNT_ID')
    
    uri = "wss://demo.ctraderapi.com:5036"
    
    print(f"Connecting to cTrader...")
    async with websockets.connect(uri) as ws:
        # 1. App Auth
        await ws.send(json.dumps({
            "payloadType": 2100,
            "payload": {"clientId": client_id, "clientSecret": secret}
        }))
        await ws.recv()
        print("App Authorized.")
        
        # 2. Account Auth
        await ws.send(json.dumps({
            "payloadType": 2102,
            "payload": {"ctidTraderAccountId": int(account_id), "accessToken": access_token}
        }))
        await ws.recv()
        print(f"Account {account_id} Authorized.")
        
        # 3. Trader Req (ROOT VERSION)
        print("Sending Trader Req (2111) ROOT version...")
        await ws.send(json.dumps({
            "payloadType": 2111,
            "ctidTraderAccountId": int(account_id),
            "clientMsgId": "check_bal_root"
        }))
        
        while True:
            res = await ws.recv()
            data = json.loads(res)
            print(f"Received: Type {data.get('payloadType')} (ID: {data.get('clientMsgId')})")
            
            if data.get('clientMsgId') == "check_bal_root":
                print(f"FULL RESPONSE: {data}")
                return

if __name__ == "__main__":
    asyncio.run(get_balance())
