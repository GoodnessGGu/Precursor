import asyncio
import json
import websockets
import os

DERIV_TOKEN = os.getenv('DERIV_TOKEN', '').strip()
APP_ID = 1089  # Reverting to default stable ID

class DerivBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}"

    async def place_order(self, symbol, side, price, sl, tp, amount=1):
        """
        Places an order on Deriv.
        Note: For Gold on Financial accounts, symbol is usually 'frxXAUUSD' 
        or similar depending on account type.
        """
        async with websockets.connect(self.api_url) as websocket:
            # 1. Authorize
            await websocket.send(json.dumps({"authorize": self.token}))
            auth_res = await websocket.recv()
            print(f"Auth Response: {auth_res}")

            # 2. Prepare Contract
            # For Spot Gold/Forex style trading, we use 'buy' for a 'call' or 'put'
            # OR 'buy' for a CFD if using MT5 API. 
            # This implementation assumes Deriv API V3 Buy Contract.
            
            direction = "CALL" if side.lower() == "long" else "PUT"
            
            # Simple binary/digital option example for Deriv API
            # For true CFD/Forex execution, one usually uses the MT5 manager.
            # Here we implement the 'Buy Contract' logic.
            
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
                    "limit_order": {
                        "stop_loss": sl,
                        "take_profit": tp
                    }
                }
            }
            
            await websocket.send(json.dumps(order_payload))
            order_res = await websocket.recv()
            print(f"Order Response: {order_res}")
            return json.loads(order_res)

    async def get_account_info(self):
        """Fetches current balance and account type"""
        async with websockets.connect(self.api_url) as websocket:
            print(f"Connecting to Deriv with token: {self.token[:10]}...")
            await websocket.send(json.dumps({"authorize": self.token}))
            auth_res = await websocket.recv()
            print(f"Raw Auth Response: {auth_res}")
            data = json.loads(auth_res)
            
            if "error" in data:
                return {"error": data['error']['message'], "details": data['error']}
            
            auth = data.get("authorize", {})
            return {
                "email": auth.get("email"),
                "currency": auth.get("currency"),
                "balance": auth.get("balance"),
                "is_virtual": auth.get("is_virtual"),
                "loginid": auth.get("loginid")
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
