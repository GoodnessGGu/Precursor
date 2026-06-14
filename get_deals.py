import asyncio
import json
import websockets
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def get_deals():
    client_id = os.getenv('CTRADER_CLIENT_ID')
    secret = os.getenv('CTRADER_SECRET')
    access_token = os.getenv('CTRADER_ACCESS_TOKEN')
    account_id = os.getenv('CTRADER_ACCOUNT_ID')
    
    uri = "wss://demo.ctraderapi.com:5036"
    
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"payloadType": 2100, "payload": {"clientId": client_id, "clientSecret": secret}}))
        await ws.recv()
        await ws.send(json.dumps({"payloadType": 2102, "payload": {"ctidTraderAccountId": int(account_id), "accessToken": access_token}}))
        await ws.recv()
        
        # Request deals for last 24h
        from_date = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        to_date = int(datetime.now().timestamp() * 1000)
        
        print("Fetching deals for the last hour...")
        await ws.send(json.dumps({
            "payloadType": 2137, # ProtoOADealListReq
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "fromTimestamp": from_date,
                "toTimestamp": to_date,
                "symbolId": 41, # GOLD
                "period": 1 # M1
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        if data.get('payloadType') == 2138:
            deals = data.get('payload', {}).get('deal', [])
            print(f"\n--- RECENT DEALS ({len(deals)}) ---")
            for d in deals:
                pnl = d.get('netProfit', 0) / 100.0
                print(f"ID: {d.get('dealId')} | Symbol: {d.get('symbolId')} | PnL: ${pnl:.2f}")
            print("--------------------\n")
        else:
            print(f"Error: {data}")

if __name__ == "__main__":
    asyncio.run(get_deals())
