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
        
        # Pull last 24h
        from_ts = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        to_ts = int(datetime.now().timestamp() * 1000)
        
        # We must request deals symbol by symbol
        symbols = {"BTCUSD": 101, "GOLD": 41}
        
        print(f"\n--- CTRADER DEAL HISTORY (Last 24h) ---")
        
        for name, sid in symbols.items():
            try:
                await ws.send(json.dumps({
                    "payloadType": 2137,
                    "payload": {
                        "ctidTraderAccountId": int(account_id),
                        "fromTimestamp": from_ts,
                        "toTimestamp": to_ts,
                        "symbolId": sid,
                        "period": 1 # M1
                    }
                }))
                
                res = await ws.recv()
                data = json.loads(res)
                
                if data.get('payloadType') == 2138:
                    deals = data.get('payload', {}).get('deal', [])
                    print(f"\nAsset: {name} ({len(deals)} deals)")
                    for d in deals:
                        pnl = d.get('netProfit', 0) / 100.0
                        side = "BUY" if d.get('tradeSide') == 1 else "SELL"
                        dt = datetime.fromtimestamp(d.get('executionTimestamp')/1000)
                        print(f" • ID: {d.get('dealId')} | {side} | PnL: ${pnl:,.2f} | {dt.strftime('%H:%M')} UTC")
                else:
                    print(f"Error for {name}: {data.get('payload', {}).get('description')}")
            except Exception as e:
                print(f"Fetch failed for {name}: {e}")

if __name__ == "__main__":
    asyncio.run(get_deals())
