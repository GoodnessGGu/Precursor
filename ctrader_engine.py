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
        
        # cTrader JSON WebSocket Endpoints
        if self.env == 'live':
            self.uri = "wss://live.ctraderapi.com:5036"
        else:
            self.uri = "wss://demo.ctraderapi.com:5036"
            
        self.ws = None
        self.is_authenticated = False

    async def connect(self):
        """Establishes WebSocket connection and authenticates"""
        try:
            print(f"Connecting to cTrader {self.env} (JSON)...")
            self.ws = await websockets.connect(self.uri)
            
            # 1. Application Authentication
            auth_req = {
                "payloadType": 2100, # ProtoOAApplicationAuthReq
                "payload": {
                    "clientId": self.client_id,
                    "clientSecret": self.secret
                }
            }
            await self.ws.send(json.dumps(auth_req))
            res = await self.ws.recv()
            data = json.loads(res)
            
            if data.get('payloadType') == 2101: # ProtoOAApplicationAuthRes
                print("✅ cTrader Application Authorized.")
            else:
                return False, f"App Auth Failed: {res}"

            # 2. Account Authentication
            acc_auth_req = {
                "payloadType": 2102, # ProtoOAAccountAuthReq
                "payload": {
                    "ctidTraderAccountId": int(self.account_id),
                    "accessToken": self.access_token
                }
            }
            await self.ws.send(json.dumps(acc_auth_req))
            res = await self.ws.recv()
            data = json.loads(res)
            
            if data.get('payloadType') == 2103: # ProtoOAAccountAuthRes
                print(f"✅ cTrader Account {self.account_id} Authorized.")
                self.is_authenticated = True
                # Start Heartbeat
                asyncio.create_task(self.heartbeat())
                return True, "Success"
            else:
                return False, f"Account Auth Failed: {res}"

        except Exception as e:
            return False, str(e)

    async def heartbeat(self):
        """Keep-alive loop (cTrader requires a ping every 25s)"""
        while self.ws:
            try:
                # Shorter sleep for stability
                await asyncio.sleep(15) 
                
                # Check if closed
                if not hasattr(self.ws, 'closed') or self.ws.closed:
                    break
                
                ping = {"payloadType": 2104, "payload": {}} 
                await self.ws.send(json.dumps(ping))
            except Exception as e:
                print(f"Heartbeat Loop Stopped: {e}")
                break

    async def get_account_info(self):
        # ... (existing rest api logic)
        
    async def get_open_positions(self):
        """Fetches all active positions to calculate live PnL"""
        if not self.is_authenticated:
            success, err = await self.connect()
            if not success: return []
            
        req = {
            "payloadType": 2121, # ProtoOAReconcileReq
            "payload": {
                "ctidTraderAccountId": int(self.account_id)
            }
        }
        await self.ws.send(json.dumps(req))
        res = await self.ws.recv()
        data = json.loads(res)
        return data.get('payload', {}).get('position', [])

    async def get_symbol_id(self, symbol_name):
        """Fetches the internal numeric ID for a symbol name"""
        if not self.is_authenticated:
            success, err = await self.connect()
            if not success: return None
        
        # Mapping for common assets to avoid discovery failures
        # BTC is 31, XAU is 17, USD is 15
        f_id, l_id = (17, 15) 
        if "BTC" in symbol_name.upper():
            f_id, l_id = (31, 15)
        
        req = {
            "payloadType": 2118, 
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "firstAssetId": f_id, 
                "lastAssetId": l_id
            }
        }
        await self.ws.send(json.dumps(req))
        res = await self.ws.recv()
        data = json.loads(res)
        
        symbols = data.get('payload', {}).get('symbol', [])
        for s in symbols:
            if s.get('symbolName').upper() == symbol_name.upper():
                return s.get('symbolId')
                
        return None

    async def place_order(self, symbol, side, qty, sl_price=None, tp_price=None):
        """Places a Market Order"""
        if not self.is_authenticated:
            success, err = await self.connect()
            if not success: return {"error": err}

        symbol_id = await self.get_symbol_id(symbol)
        if not symbol_id:
            return {"error": f"Symbol {symbol} not found."}

        volume = int(float(qty) * 100000) 
        order_side = 1 if side.upper() in ["LONG", "BUY"] else 2 
        
        order_req = {
            "payloadType": 2106, # ProtoOANewOrderReq
            "payload": {
                "ctidTraderAccountId": int(self.account_id),
                "symbolId": symbol_id,
                "orderType": 1, # MARKET
                "tradeSide": order_side,
                "volume": volume,
                "comment": "Gushtec AI Co-Pilot"
            }
        }
        
        if sl_price: order_req['payload']['stopLoss'] = float(sl_price)
        if tp_price: order_req['payload']['takeProfit'] = float(tp_price)

        print(f"Sending cTrader Order: {qty} Lots of {symbol} (ID: {symbol_id})...")
        await self.ws.send(json.dumps(order_req))
        
        # Listen for the execution result
        for _ in range(5):
            res = await self.ws.recv()
            data = json.loads(res)
            pt = data.get('payloadType')
            
            if pt == 2126: # ProtoOAExecutionEvent
                payload = data.get('payload', {})
                etype = payload.get('executionType') 
                if etype == 3: # REJECTED
                    return {"error": f"Order Rejected: {payload.get('errorCode')}"}
                if etype in [1, 2]: # ACCEPTED or FILLED
                    return {"status": "success", "data": payload}
            
            if pt == 2142: # ERROR
                return {"error": f"cTrader Error: {data.get('payload', {}).get('description')}"}

        return {"error": f"Order sent but no confirmation received."}
