import asyncio
import json
import websockets
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def get_history():
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
        
        # Request Deals for the last 24 hours
        from_date = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        to_date = int(datetime.now().timestamp() * 1000)
        
        print(f"Requesting trade history for Account {account_id}...")
        await ws.send(json.dumps({
            "payloadType": 2137, # ProtoOADealListReq
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "fromTimestamp": from_date,
                "toTimestamp": to_date
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        if data.get('payloadType') == 2138: # ProtoOADealListRes
            deals = data.get('payload', {}).get('deal', [])
            print(f"\n--- RECENT TRADE HISTORY ({len(deals)} deals) ---")
            for d in deals:
                print(f"ID: {d.get('dealId')} | Symbol ID: {d.get('symbolId')} | PnL: ${d.get('netProfit', 0)/100.0} | Time: {datetime.fromtimestamp(d.get('executionTimestamp')/1000)}")
            print("----------------------------------\n")
        else:
            print(f"Error fetching history: {res}")

if __name__ == "__main__":
    asyncio.run(get_history())
