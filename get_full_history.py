import asyncio
import json
import websockets
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def get_all_deals():
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
        
        # We'll check for BTC (101) and Gold (41)
        symbols = [101, 41]
        from_date = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        to_date = int(datetime.now().timestamp() * 1000)
        
        print(f"\n--- CTRADER TRADE HISTORY (Last 24h) ---")
        
        for sid in symbols:
            await ws.send(json.dumps({
                "payloadType": 2137, # ProtoOADealListReq
                "payload": {
                    "ctidTraderAccountId": int(account_id),
                    "fromTimestamp": from_date,
                    "toTimestamp": to_date,
                    "symbolId": sid,
                    "period": 1 # M1
                }
            }))
            
            res = await ws.recv()
            data = json.loads(res)
            
            if data.get('payloadType') == 2138:
                deals = data.get('payload', {}).get('deal', [])
                sym_name = "BTCUSD" if sid == 101 else "XAUUSD"
                print(f"\nAsset: {sym_name} ({len(deals)} deals)")
                for d in deals:
                    pnl = d.get('netProfit', 0) / 100.0
                    side = "BUY" if d.get('tradeSide') == 1 else "SELL"
                    time_str = datetime.fromtimestamp(d.get('executionTimestamp')/1000).strftime('%Y-%m-%d %H:%M')
                    print(f" • ID: {d.get('dealId')} | {side} | PnL: ${pnl:,.2f} | {time_str}")
            else:
                print(f"Error fetching for ID {sid}: {data.get('payload', {}).get('description')}")
        
        print("\n----------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(get_all_deals())
