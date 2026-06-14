import asyncio
import json
import websockets
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def get_pos_history():
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
        
        from_date = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
        to_date = int(datetime.now().timestamp() * 1000)
        
        print("\n--- CTRADER POSITION HISTORY (Last 24h) ---")
        
        await ws.send(json.dumps({
            "payloadType": 2135, # ProtoOAPositionHistoryListReq
            "payload": {
                "ctidTraderAccountId": int(account_id),
                "fromTimestamp": from_date,
                "toTimestamp": to_date,
                "symbolId": 101,
                "period": 1
            }
        }))
        
        res = await ws.recv()
        data = json.loads(res)
        
        if data.get('payloadType') == 2136:
            positions = data.get('payload', {}).get('position', [])
            print(f"Total Closed Positions: {len(positions)}")
            for p in positions:
                p_id = p.get('positionId')
                pnl = p.get('netProfit', 0) / 100.0
                print(f" • ID: {p_id} | Symbol: {p.get('tradeData', {}).get('symbolId')} | PnL: ${pnl:,.2f}")
        else:
            print(f"Error: {data}")

if __name__ == "__main__":
    asyncio.run(get_pos_history())
