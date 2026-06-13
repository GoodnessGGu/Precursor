import asyncio
import json
import websockets
import os
import time
from dotenv import load_dotenv

load_dotenv()

class CTraderBot:
    def __init__(self):
        self.client_id = os.getenv('CTRADER_CLIENT_ID')
        self.secret = os.getenv('CTRADER_SECRET')
        self.access_token = os.getenv('CTRADER_ACCESS_TOKEN')
        self.account_id = os.getenv('CTRADER_ACCOUNT_ID')
        self.env = os.getenv('CTRADER_ENVIRONMENT', 'demo').lower()
        
        if self.env == 'live':
            self.uri = "wss://live.ctraderapi.com:5036"
        else:
            self.uri = "wss://demo.ctraderapi.com:5036"
            
        self.ws_trade = None
        self.ws_price = None
        self.is_authenticated = False

    async def connect_trade(self):
        """Dedicated connection for trading and account info"""
        print(f"Connecting Trade WebSocket to {self.env}...")
        self.ws_trade = await websockets.connect(self.uri)
        success = await self._authenticate(self.ws_trade)
        if success:
            asyncio.create_task(self.heartbeat(self.ws_trade))
        return success

    async def connect_price(self):
        """Dedicated connection for live price feed"""
        print(f"Connecting Price WebSocket to {self.env}...")
        self.ws_price = await websockets.connect(self.uri)
        success = await self._authenticate(self.ws_price)
        if success:
            asyncio.create_task(self.heartbeat(self.ws_price))
        return success

    async def _authenticate(self, ws):
        try:
            # 1. App Auth
            await ws.send(json.dumps({
                "payloadType": 2100,
                "payload": {"clientId": self.client_id, "clientSecret": self.secret}
            }))
            res = await ws.recv()
            
            # 2. Account Auth
            await ws.send(json.dumps({
                "payloadType": 2102,
                "payload": {"ctidTraderAccountId": int(self.account_id), "accessToken": self.access_token}
            }))
            res = await ws.recv()
            data = json.loads(res)
            if data.get('payloadType') == 2103:
                self.is_authenticated = True
                return True
        except Exception as e:
            print(f"Auth Error: {e}")
        return False

    async def heartbeat(self, ws):
        while ws:
            try:
                await asyncio.sleep(15)
                if not hasattr(ws, 'closed') or ws.closed: break
                await ws.send(json.dumps({"payloadType": 2104, "payload": {}}))
            except:
                break

    async def get_account_info(self):
        """REST API based account info (more reliable)"""
        try:
            import requests
            url = "https://api.spotware.com/connect/tradingaccounts"
            res = requests.get(url, params={"access_token": self.access_token})
            if res.status_code == 200:
                accounts = res.json().get('data', [])
                for acc in accounts:
                    if str(acc.get('accountId')) == str(self.account_id):
                        digits = acc.get('moneyDigits', 2)
                        return {
                            "balance": acc.get('balance', 0) / (10**digits),
                            "currency": acc.get('depositCurrency'),
                            "account_id": self.account_id
                        }
        except: pass
        return {"error": "Could not fetch account info"}

    async def get_open_positions(self):
        if not self.ws_trade or self.ws_trade.closed:
            await self.connect_trade()
            
        await self.ws_trade.send(json.dumps({
            "payloadType": 2121,
            "payload": {"ctidTraderAccountId": int(self.account_id)}
        }))
        res = await self.ws_trade.recv()
        return json.loads(res).get('payload', {}).get('position', [])

    async def subscribe_live_prices(self, symbol_name, callback):
        if not self.ws_price or self.ws_price.closed:
            await self.connect_price()
            
        symbol_id = await self.get_symbol_id(self.ws_price, symbol_name)
        await self.ws_price.send(json.dumps({
            "payloadType": 2127,
            "payload": {"ctidTraderAccountId": int(self.account_id), "symbolId": [symbol_id]}
        }))
        
        print(f"📡 Price Feed Live for {symbol_name}")
        async for message in self.ws_price:
            data = json.loads(message)
            if data.get('payloadType') == 2131: # Spot Event
                await callback(data.get('payload', {}))

    async def get_symbol_id(self, ws, symbol_name):
        f_id, l_id = (31, 15) if "BTC" in symbol_name.upper() else (17, 15)
        await ws.send(json.dumps({
            "payloadType": 2118,
            "payload": {"ctidTraderAccountId": int(self.account_id), "firstAssetId": f_id, "lastAssetId": l_id}
        }))
        res = await ws.recv()
        symbols = json.loads(res).get('payload', {}).get('symbol', [])
        for s in symbols:
            if s.get('symbolName').upper() == symbol_name.upper():
                return s.get('symbolId')
        return None

    async def place_order(self, symbol, side, qty, sl_price=None, tp_price=None):
        if not self.ws_trade or self.ws_trade.closed:
            await self.connect_trade()

        symbol_id = await self.get_symbol_id(self.ws_trade, symbol)
        volume = int(float(qty) * 100000)
        
        req = {
            "payloadType": 2106,
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "symbolId": symbol_id,
                "orderType": 1,
                "tradeSide": 1 if side.upper() in ["BUY", "LONG"] else 2,
                "volume": volume
            }
        }
        if sl_price: req['payload']['stopLoss'] = float(sl_price)
        if tp_price: req['payload']['takeProfit'] = float(tp_price)

        await self.ws_trade.send(json.dumps(req))
        for _ in range(5):
            data = json.loads(await self.ws_trade.recv())
            if data.get('payloadType') == 2126:
                payload = data.get('payload', {})
                if payload.get('executionType') == 3:
                    return {"error": f"Rejected: {payload.get('errorCode')}"}
                return {"status": "success", "data": payload}
        return {"error": "Timeout"}
