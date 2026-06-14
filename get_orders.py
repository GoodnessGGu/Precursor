import asyncio
import json
import websockets
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def get_orders():
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
        
        from_date = int((datetime.now() - timedelta(hours=6)).timestamp() * 1000)
        to_date = int(datetime.now().timestamp() * 1000)
        
        print("\n--- CTRADER ORDER HISTORY (Last 6h) ---")
        
        # Request Order List
        await ws.send(json.dumps({
            "payloadType": 2139, # ProtoOAOrderListReq
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "fromTimestamp": from_date,
                "toTimestamp": to_date,
                "symbolId": 101
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        if data.get('payloadType') == 2140:
            orders = data.get('payload', {}).get('order', [])
            print(f"Total Orders: {len(orders)}")
            for o in orders:
                status = o.get('orderStatus') # 1=Accepted, 2=Filled, 3=Rejected, etc.
                side = "BUY" if o.get('tradeData', {}).get('tradeSide') == 1 else "SELL"
                vol = o.get('tradeData', {}).get('volume', 0)
                print(f" • ID: {o.get('orderId')} | {side} | Status: {status} | Vol: {vol}")
        else:
            print(f"Error: {data}")

if __name__ == "__main__":
    asyncio.run(get_orders())
