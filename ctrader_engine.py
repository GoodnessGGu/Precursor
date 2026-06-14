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
            
            self.ws_trade = await websockets.connect(self.uri, ping_interval=10, ping_timeout=10)
            success = await self._authenticate(self.ws_trade)
            if success:
                # CRITICAL: Tiny delay to let broker process the auth
                await asyncio.sleep(0.5)
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
                await asyncio.sleep(0.5)
                asyncio.create_task(self.heartbeat(self.ws_price))
            return success
        except Exception as e:
            print(f"Price Connection Error: {e}")
            return False

    async def _authenticate(self, ws):
        try:
            # 1. App Auth
            await ws.send(json.dumps({
                "payloadType": 2100,
                "payload": {"clientId": self.client_id, "clientSecret": self.secret}
            }))
            await ws.recv()
            
            # 2. Account Auth
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

    async def get_symbol_specs(self, symbol_name):
        """Fetches full trading parameters for a symbol"""
        if not self.is_ws_open(self.ws_trade):
            await self.connect_trade()
            
        symbol_id = 101 if "BTC" in symbol_name.upper() else 41
        
        req = {
            "payloadType": 2114, # ProtoOASymbolByIdReq
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "symbolId": [symbol_id]
            }
        }
        try:
            await self.ws_trade.send(json.dumps(req))
            res = await self.ws_trade.recv()
            data = json.loads(res)
            
            if data.get('payloadType') == 2115: # ProtoOASymbolByIdRes
                symbols = data.get('payload', {}).get('symbol', [])
                for s in symbols:
                    if s.get('symbolId') == symbol_id:
                        return s
        except: pass
        return None

    async def place_order(self, symbol, side, qty, sl_price=None, tp_price=None, retry=True):
        """Places a Market Order with hardened speed-calibration and 15s timeout protection"""
        
        if not self.is_ws_open(self.ws_trade):
            success = await self.connect_trade()
            if not success: return {"error": "Handshake Failed"}

        symbol_id = 101 if "BTC" in symbol.upper() else 41
        
        # 1. Fetch Specs for Dynamic Volume Correction
        specs = await self.get_symbol_specs(symbol)
        
        # Default volume based on previous knowledge
        if "BTC" in symbol.upper():
            volume = int(float(qty) * 100) # 0.01 -> 1
        else:
            volume = int(float(qty) * 100000) # 0.01 -> 1000 units (Gold)

        # Apply broker's minimum if discovered
        if specs:
            min_vol = specs.get('minVolume', 1)
            if volume < min_vol:
                print(f"   - Auto-Adjusting volume from {volume} to broker minimum {min_vol}")
                volume = min_vol

        req = {
            "payloadType": 2106,
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "symbolId": symbol_id,
                "orderType": 1,
                "tradeSide": 1 if side.upper() in ["BUY", "LONG"] else 2,
                "volume": int(volume),
                "comment": "Gushtec DeepDiscovery"
            }
        }
        if sl_price: req['payload']['stopLoss'] = float(sl_price)
        if tp_price: req['payload']['takeProfit'] = float(tp_price)

        print(f"   - Sending {side} Order (Vol: {volume})...")
        try:
            await self.ws_trade.send(json.dumps(req))
            
            # Start timer for confirmation
            start_time = time.time()
            while time.time() - start_time < 15: # 15 second total patience
                try:
                    res = await asyncio.wait_for(self.ws_trade.recv(), timeout=2.0)
                    data = json.loads(res)
                    pt = data.get('payloadType')
                    
                    # LOG EVERY MESSAGE during wait for debugging
                    print(f"   - [TRACE] Received Type {pt}")
                    
                    if pt == 2126: # Execution Event (Success)
                        payload = data.get('payload', {})
                        etype = payload.get('executionType')
                        if etype == 3: # REJECTED
                            return {"error": f"Broker Rejected: {payload.get('errorCode')}"}
                        print(f"✅ Order Confirmed: {etype}")
                        return {"status": "success", "data": payload}
                    
                    if pt == 2132: # Order Error Event (Explicit Rejection)
                        payload = data.get('payload', {})
                        err_code = payload.get('errorCode', 'UNKNOWN_ERROR')
                        err_desc = payload.get('description', 'No description provided')
                        print(f"   - [TRACE] Order Error: {err_code} ({err_desc})")
                        return {"error": f"Broker Error: {err_code} - {err_desc}"}

                    if pt == 2142: # Protocol Error
                        return {"error": f"cTrader Error: {data.get('payload', {}).get('description')}"}
                except asyncio.TimeoutError:
                    continue 

            if retry:
                print("⚠️ Confirmation Timeout, resetting connection and retrying...")
                self.ws_trade = None
                return await self.place_order(symbol, side, qty, sl_price, tp_price, retry=False)
            
            return {"error": "Execution Confirmation Timeout"}

        except Exception as e:
            if retry:
                self.ws_trade = None
                return await self.place_order(symbol, side, qty, sl_price, tp_price, retry=False)
            return {"error": f"Execution Error: {e}"}

    async def close_position(self, position_id, volume):
        """Closes a specific position by ID and volume"""
        if not self.is_ws_open(self.ws_trade):
            await self.connect_trade()

        req = {
            "payloadType": 2110, # ProtoOAClosePositionReq
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "positionId": int(position_id),
                "volume": int(volume)
            }
        }
        try:
            await self.ws_trade.send(json.dumps(req))
            res = await self.ws_trade.recv()
            return json.loads(res)
        except Exception as e:
            return {"error": str(e)}

    async def close_all_positions(self):
        """Closes all currently open positions for the account"""
        positions = await self.get_open_positions()
        if not positions:
            print("No open positions to close.")
            return []

        results = []
        for p in positions:
            p_id = p.get('positionId')
            vol = p.get('tradeData', {}).get('volume', 0)
            print(f"   - Closing Position ID: {p_id} (Vol: {vol})...")
            res = await self.close_position(p_id, vol)
            results.append(res)
        return results
