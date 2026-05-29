import asyncio
import json
import websockets
import os
import requests

DERIV_TOKEN = os.getenv('DERIV_TOKEN', '').strip()
APP_ID = 1089  # Using default stable ID for the handshake

class DerivBot:
    def __init__(self, token):
        self.token = token
        self.rest_url = "https://api.derivws.com/v2" # New V2/V3 REST endpoint
        self.app_id = APP_ID

    async def get_authenticated_url(self):
        """
        Step 1: The New Handshake
        Uses REST to get an OTP-authenticated WebSocket URL
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        # First, we need to get the account ID by calling 'authorize' via REST
        # or simply try to get an OTP for the default account
        try:
            # Note: For some accounts, you need the specific account loginid in the URL
            # but usually 'authorize' via REST works first.
            response = requests.post(
                f"https://api.derivws.com/api/v1/authorize", 
                headers=headers,
                json={"authorize": self.token}
            )
            auth_data = response.json()
            if "error" in auth_data:
                return None, auth_data["error"]["message"]
            
            # Now we have the session, we use the standard WebSocket but the handshake is done
            # Actually, modern Deriv PATs often work directly if passed in the INITIAL WS message
            # but must be EXACTLY correct.
            return f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}", None
        except Exception as e:
            return None, str(e)

    async def place_order(self, symbol, side, price, sl, tp, amount=1):
        ws_url, error = await self.get_authenticated_url()
        if error:
            return {"error": error}

        async with websockets.connect(ws_url) as websocket:
            # Step 2: Immediate Authorization
            await websocket.send(json.dumps({"authorize": self.token}))
            auth_res = await websocket.recv()
            
            direction = "CALL" if side.lower() == "long" else "PUT"
            order_payload = {
                "buy": 1,
                "subscribe": 1,
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
            await websocket.send(json.dumps(order_payload))
            order_res = await websocket.recv()
            return json.loads(order_res)

    async def get_account_info(self):
        ws_url, error = await self.get_authenticated_url()
        if error: return {"error": error}

        async with websockets.connect(ws_url) as websocket:
            await websocket.send(json.dumps({"authorize": self.token}))
            auth_res = await websocket.recv()
            data = json.loads(auth_res)
            if "error" in data: return {"error": data['error']['message']}
            
            auth = data.get("authorize", {})
            return {
                "email": auth.get("email"),
                "currency": auth.get("currency"),
                "balance": auth.get("balance"),
                "is_virtual": auth.get("is_virtual")
            }

async def test_engine():
    bot = DerivBot(DERIV_TOKEN)
    # Placeholder values for testing
    await bot.place_order("frxXAUUSD", "long", 2340.50, 2335.00, 2350.00)

if __name__ == "__main__":
    if DERIV_TOKEN:
        asyncio.run(test_engine())
    else:
        print("Set DERIV_TOKEN env var first.")
