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

    def is_ws_open(self, ws):
        if ws is None: return False
        return getattr(ws, "open", False)

    async def connect_trade(self):
        """Fresh connection for trading"""
        print(f"🔄 Opening Fresh Trade Connection to {self.env}...")
        try:
            if self.ws_trade:
                try: await self.ws_trade.close()
                except: pass
            
            # Using shorter ping timeouts to detect dead links faster
            self.ws_trade = await websockets.connect(self.uri, ping_interval=10, ping_timeout=10)
            success = await self._authenticate(self.ws_trade)
            if success:
                asyncio.create_task(self.heartbeat(self.ws_trade))
            return success
        except Exception as e:
            print(f"Trade Connection Error: {e}")
            return False

    async def connect_price(self):
        """Dedicated connection for live price feed"""
        print(f"📡 Opening Price Feed to {self.env}...")
        try:
            self.ws_price = await websockets.connect(self.uri, ping_interval=10, ping_timeout=10)
            success = await self._authenticate(self.ws_price)
            if success:
                asyncio.create_task(self.heartbeat(self.ws_price))
            return success
        except Exception as e:
            print(f"Price Connection Error: {e}")
            return False

    async def _authenticate(self, ws):
        try:
            await ws.send(json.dumps({
                "payloadType": 2100,
                "payload": {"clientId": self.client_id, "clientSecret": self.secret}
            }))
            await ws.recv()
            await ws.send(json.dumps({
                "payloadType": 2102,
                "payload": {"ctidTraderAccountId": int(self.account_id), "accessToken": self.access_token}
            }))
            res = await ws.recv()
            data = json.loads(res)
            if data.get('payloadType') == 2103:
                return True
        except Exception as e:
            print(f"Auth Error: {e}")
        return False

    async def heartbeat(self, ws):
        while True:
            try:
                await asyncio.sleep(15)
                if not self.is_ws_open(ws): break
                await ws.send(json.dumps({"payloadType": 2104, "payload": {}}))
            except:
                break

    async def get_account_info(self):
        try:
            import requests
            url = "https://api.spotware.com/connect/tradingaccounts"
            res = requests.get(url, params={"access_token": self.access_token}, timeout=10)
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
        if not self.is_ws_open(self.ws_trade):
            await self.connect_trade()
            
        try:
            await self.ws_trade.send(json.dumps({
                "payloadType": 2121,
                "payload": {"ctidTraderAccountId": int(self.account_id)}
            }))
            res = await self.ws_trade.recv()
            return json.loads(res).get('payload', {}).get('position', [])
        except:
            # If fail, try once more with fresh connect
            await self.connect_trade()
            try:
                await self.ws_trade.send(json.dumps({
                    "payloadType": 2121,
                    "payload": {"ctidTraderAccountId": int(self.account_id)}
                }))
                res = await self.ws_trade.recv()
                return json.loads(res).get('payload', {}).get('position', [])
            except:
                return []

    async def subscribe_live_prices(self, symbol_name, callback):
        if not self.is_ws_open(self.ws_price):
            await self.connect_price()
            
        # Hardcoded ID for speed
        symbol_id = 101 if "BTC" in symbol_name.upper() else 41
        
        await self.ws_price.send(json.dumps({
            "payloadType": 2127,
            "payload": {"ctidTraderAccountId": int(self.account_id), "symbolId": [symbol_id]}
        }))
        
        async for message in self.ws_price:
            try:
                data = json.loads(message)
                if data.get('payloadType') == 2131:
                    await callback(data.get('payload', {}))
            except: continue

    async def place_order(self, symbol, side, qty, sl_price=None, tp_price=None, retry=True):
        """Places a Market Order with dynamic retry logic"""
        if not self.is_ws_open(self.ws_trade):
            await self.connect_trade()

        symbol_id = 101 if "BTC" in symbol.upper() else 41
        volume = int(float(qty) * 100000)
        
        req = {
            "payloadType": 2106,
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "symbolId": symbol_id,
                "orderType": 1,
                "tradeSide": 1 if side.upper() in ["BUY", "LONG"] else 2,
                "volume": volume,
                "comment": "Gushtec Cloud"
            }
        }
        if sl_price: req['payload']['stopLoss'] = float(sl_price)
        if tp_price: req['payload']['takeProfit'] = float(tp_price)

        try:
            await self.ws_trade.send(json.dumps(req))
            # Wait for confirm
            for _ in range(5):
                res = await self.ws_trade.recv()
                data = json.loads(res)
                if data.get('payloadType') == 2126:
                    payload = data.get('payload', {})
                    if payload.get('executionType') == 3:
                        return {"error": f"Rejected: {payload.get('errorCode')}"}
                    return {"status": "success", "data": payload}
        except Exception as e:
            if retry:
                print(f"⚠️ Trade send failed ({e}), retrying with fresh connection...")
                await self.connect_trade()
                return await self.place_order(symbol, side, qty, sl_price, tp_price, retry=False)
            return {"error": f"Execution Error: {e}"}
            
        return {"error": "Timeout waiting for confirmation"}
