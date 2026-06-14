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

    def is_ws_open(self, ws):
        if ws is None: return False
        return getattr(ws, "open", False)

    async def connect_trade(self):
        """Dedicated connection for trading and account info"""
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
            # 1. App Auth
            print("   - Sending App Auth...")
            await ws.send(json.dumps({
                "payloadType": 2100,
                "payload": {"clientId": self.client_id, "clientSecret": self.secret}
            }))
            await ws.recv()
            print("   - App Auth OK.")
            
            # 2. Account Auth
            print(f"   - Sending Account Auth for {self.account_id}...")
            await ws.send(json.dumps({
                "payloadType": 2102,
                "payload": {"ctidTraderAccountId": int(self.account_id), "accessToken": self.access_token}
            }))
            res = await ws.recv()
            data = json.loads(res)
            if data.get('payloadType') == 2103:
                print("   - Account Auth OK.")
                return True
            else:
                print(f"   - Account Auth FAILED: {res}")
        except Exception as e:
            print(f"   - Auth Exception: {e}")
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
        """REST API based account info (more reliable)"""
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
        except Exception as e:
            print(f"REST Account Info Error: {e}")
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
        except Exception as e:
            print(f"Get Positions Error: {e}")
            # Try to reconnect for next call
            self.ws_trade = None
            return []

    async def subscribe_live_prices(self, symbol_name, callback):
        if not self.is_ws_open(self.ws_price):
            await self.connect_price()
            
        symbol_id = 101 if "BTC" in symbol_name.upper() else 41
        
        try:
            await self.ws_price.send(json.dumps({
                "payloadType": 2127,
                "payload": {"ctidTraderAccountId": int(self.account_id), "symbolId": [symbol_id]}
            }))
            
            print(f"📡 Price Feed Live for {symbol_name} (ID: {symbol_id})")
            async for message in self.ws_price:
                data = json.loads(message)
                if data.get('payloadType') == 2131: # Spot Event
                    await callback(data.get('payload', {}))
        except Exception as e:
            print(f"Price Subscription Loop Error: {e}")
            self.ws_price = None 

    async def get_symbol_id(self, ws, symbol_name):
        """Hardcoded IDs for speed and reliability"""
        MAPPING = {"BTCUSD": 101, "XAUUSD": 41}
        name_up = symbol_name.upper()
        if name_up in MAPPING: return MAPPING[name_up]
        return None

    async def place_order(self, symbol, side, qty, sl_price=None, tp_price=None, retry=True):
        """Places a Market Order with dynamic retry logic and error decoding"""
        
        # 1. Ensure connection is alive
        if not self.is_ws_open(self.ws_trade):
            print("   - Trade WS closed/missing, performing fresh handshake...")
            success = await self.connect_trade()
            if not success: return {"error": "Handshake Failed before order"}

        symbol_id = 101 if "BTC" in symbol.upper() else 41
        
        # 2. Dynamic Volume Calculation
        # cTrader 'volume' is units. 
        # For BTC: 100 units = 1.00 lot in Deriv cTrader? 
        # Actually in cTrader 1 unit = 0.01 lot usually.
        # Let's try Volume = 100 for 0.01 BTC (1 unit) to be safe.
        if "BTC" in symbol.upper():
            volume = int(float(qty) * 10000) # 0.01 -> 100 units
        else:
            volume = int(float(qty) * 100000) # 0.01 -> 1000 units (Gold)

        req = {
            "payloadType": 2106,
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "symbolId": symbol_id,
                "orderType": 1,
                "tradeSide": 1 if side.upper() in ["BUY", "LONG"] else 2,
                "volume": volume,
                "comment": "Gushtec Immortal"
            }
        }
        if sl_price: req['payload']['stopLoss'] = float(sl_price)
        if tp_price: req['payload']['takeProfit'] = float(tp_price)

        print(f"   - Sending Order: {side} {qty} {symbol} (Vol: {volume})...")
        try:
            await self.ws_trade.send(json.dumps(req))
            
            # 3. Read loop with specific error decoding
            for _ in range(10): # Listen up to 10 messages
                res = await self.ws_trade.recv()
                data = json.loads(res)
                pt = data.get('payloadType')
                
                if pt == 2126: # Execution Event
                    payload = data.get('payload', {})
                    etype = payload.get('executionType')
                    if etype == 3: # REJECTED
                        err_code = payload.get('errorCode', 'UNKNOWN')
                        print(f"   - cTrader REJECTION: {err_code}")
                        return {"error": f"Broker Rejected: {err_code}"}
                    if etype in [1, 2]:
                        return {"status": "success", "data": payload}
                
                if pt == 2142: # Error Res
                    err_msg = data.get('payload', {}).get('description', 'Unknown Error')
                    print(f"   - cTrader PROTOCOL ERROR: {err_msg}")
                    return {"error": f"Protocol Error: {err_msg}"}

        except Exception as e:
            if retry:
                print(f"⚠️ Trade link dropped ({e}), retrying once...")
                self.ws_trade = None
                return await self.place_order(symbol, side, qty, sl_price, tp_price, retry=False)
            return {"error": f"Critical Execution Error: {e}"}
            
        return {"error": "Timeout waiting for confirmation"}
