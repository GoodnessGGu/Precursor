import asyncio
import json
import websockets
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def get_transactions():
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
        
        # Pull last 48h (including future)
        from_ts = int((datetime.now() - timedelta(days=2)).timestamp() * 1000)
        to_ts = int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
        
        print(f"\n--- ACCOUNT TRANSACTIONS (Last 24h) ---")
        
        await ws.send(json.dumps({
            "payloadType": 2133, # ProtoOATransactionListReq
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "fromTimestamp": from_ts,
                "toTimestamp": to_ts
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        if data.get('payloadType') == 2134:
            txs = data.get('payload', {}).get('transaction', [])
            print(f"Total Transactions: {len(txs)}")
            for tx in txs:
                amount = tx.get('delta', 0) / 100.0
                balance = tx.get('balance', 0) / 100.0
                comment = tx.get('comment', 'No comment')
                dt = datetime.fromtimestamp(tx.get('timestamp')/1000)
                print(f" • [{dt.strftime('%H:%M')}] Amt: ${amount:+.2f} | Bal: ${balance:,.2f} | {comment}")
        else:
            print(f"Error: {data}")

if __name__ == "__main__":
    asyncio.run(get_transactions())
