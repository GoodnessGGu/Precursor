import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def check_positions():
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
        
        # Request Open Positions (2111 can return them if specified, but better use 2121)
        print(f"Requesting open positions for Account {account_id}...")
        await ws.send(json.dumps({
            "payloadType": 2121, # ProtoOAReconcileReq
            "payload": {
                "ctidTraderAccountId": int(account_id)
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        if data.get('payloadType') == 2122: # ProtoOAReconcileRes
            positions = data.get('payload', {}).get('position', [])
            print(f"\n--- OPEN POSITIONS ({len(positions)}) ---")
            for p in positions:
                trade_data = p.get('tradeData', {})
                print(f"ID: {p.get('positionId')} | Symbol ID: {trade_data.get('symbolId')} | Side: {'BUY' if trade_data.get('tradeSide') == 1 else 'SELL'} | Vol: {trade_data.get('volume')}")
            print("--------------------------\n")
        else:
            print(f"Error fetching positions: {res}")

if __name__ == "__main__":
    asyncio.run(check_positions())
