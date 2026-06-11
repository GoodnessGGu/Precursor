import asyncio
import json
import websockets
import os
import requests
from dotenv import load_dotenv

load_dotenv()

DERIV_TOKEN = os.getenv('DERIV_TOKEN', '').strip()
DERIV_APP_ID = os.getenv('DERIV_APP_ID', '1')

class DerivBot:
    def __init__(self, token, app_id):
        self.token = token
        self.app_id = app_id
        # The new 2026 REST base
        self.api_base = "https://api.deriv.com"

    async def get_authenticated_ws(self):
        """
        New 2026 Protocol:
        1. Call REST to get a secure WebSocket URL
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Deriv-App-ID": str(self.app_id),
            "Content-Type": "application/json"
        }
        
        # Endpoint to get a one-time WebSocket session
        # This is the modern replacement for the 'authorize' WS call
        url = f"{self.api_base}/trading/v1/ws-url"
        
        print(f"Requesting secure WS URL from {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("ws_url"), None
            else:
                return None, f"REST Error {response.status_code}: {response.text}"
        except Exception as e:
            return None, str(e)

    async def get_account_info(self):
        """Fetches balance using the new secure handshake"""
        ws_url, error = await self.get_authenticated_ws()
        if error:
            # Fallback to direct REST if WS-URL isn't ready
            print(f"WS-URL failed, trying direct REST...")
            url = f"{self.api_base}/trading/v1/accounts"
            headers = {"Authorization": f"Bearer {self.token}", "Deriv-App-ID": str(self.app_id)}
            res = requests.get(url, headers=headers)
            return res.json()

        try:
            async with websockets.connect(ws_url) as ws:
                # In 2026, the WS is often pre-authorized by the URL
                await ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                res = await ws.recv()
                return json.loads(res)
        except Exception as e:
            return {"error": str(e)}

    async def place_order(self, symbol, side, price, sl, tp, amount=1):
        # Implementation for order placement using the new secure handshake
        ws_url, error = await self.get_authenticated_ws()
        if error: return {"error": error}
        
        async with websockets.connect(ws_url) as ws:
            direction = "CALL" if side.lower() == "long" else "PUT"
            payload = {
                "buy": 1,
                "price": amount,
                "parameters": {
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": direction,
                    "currency": "USD",
                    "symbol": symbol,
                    "duration": 15,
                    "duration_unit": "m",
                    "limit_order": {"stop_loss": sl, "take_profit": tp}
                }
            }
            await ws.send(json.dumps(payload))
            res = await ws.recv()
            return json.loads(res)

async def test_v4_locally():
    bot = DerivBot(DERIV_TOKEN, DERIV_APP_ID)
    print("--- RUNNING LOCAL TEST ---")
    info = await bot.get_account_info()
    print(json.dumps(info, indent=2))

if __name__ == "__main__":
    asyncio.run(test_v4_locally())
