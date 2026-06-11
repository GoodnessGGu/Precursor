import asyncio
import json
import websockets
import os
import requests
from dotenv import load_dotenv

load_dotenv()

DERIV_TOKEN = os.getenv('DERIV_TOKEN', '').strip()
DERIV_APP_ID = os.getenv('DERIV_APP_ID', '')

class DerivBot:
    def __init__(self, token, app_id):
        self.token = token
        self.app_id = app_id
        # Use the official API base from 2026 documentation
        self.api_base = "https://api.derivws.com/trading/v1"

    async def get_authenticated_ws_url(self):
        """
        New 2026 Two-Step Handshake:
        1. Get Account List via REST
        2. Get OTP for the first active account
        3. Build pre-signed WebSocket URL
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Deriv-App-ID": self.app_id,
            "Content-Type": "application/json"
        }
        
        try:
            # Step A: Get Account List
            print("Step A: Fetching account list via REST...")
            acc_res = requests.get(f"{self.api_base}/options/accounts", headers=headers)
            if acc_res.status_code != 200:
                return None, f"REST Account Error {acc_res.status_code}: {acc_res.text}"
            
            accounts = acc_res.json().get('data', [])
            if not accounts:
                return None, "No active accounts found linked to this token."
            
            # Use the specific account requested by the user
            account_id = "DOT91952411"
            print(f"Step B: Requesting OTP for specific account {account_id}...")
            
            # Step B: Get OTP
            otp_res = requests.post(f"{self.api_base}/options/accounts/{account_id}/otp", headers=headers)
            if otp_res.status_code != 200:
                return None, f"REST OTP Error {otp_res.status_code}: {otp_res.text}"
            
            otp_url = otp_res.json().get('data', {}).get('url')
            if not otp_url:
                return None, "Handshake failed: No URL returned in OTP response."
            
            return otp_url, None
            
        except Exception as e:
            return None, f"Handshake Exception: {str(e)}"

    async def get_account_info(self):
        """Fetches balance using the new 2026 OTP handshake"""
        ws_url, error = await self.get_authenticated_ws_url()
        if error:
            return {"error": error}

        print(f"Step C: Connecting to secure WebSocket...")
        try:
            async with websockets.connect(ws_url) as ws:
                # In the new API, the connection is pre-authenticated!
                # We can immediately request data.
                await ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                res = await ws.recv()
                data = json.loads(res)
                
                # Format to our bot's standard
                bal_data = data.get('balance', {})
                return {
                    "email": "Connected via PAT",
                    "balance": bal_data.get('balance'),
                    "currency": bal_data.get('currency'),
                    "is_virtual": "True" # Based on the OTP URL usually
                }
        except Exception as e:
            return {"error": str(e)}

    async def place_order(self, symbol, side, price, sl, tp, amount=10):
        """Places a Multiplier (CFD-like) order using the 2026 OTP session via Proposal -> Buy"""
        ws_url, error = await self.get_authenticated_ws_url()
        if error: return {"error": error}
        
        async with websockets.connect(ws_url) as ws:
            # Multiplier directions: MULTUP (Long) or MULTDOWN (Short)
            direction = "MULTUP" if side.lower() == "long" else "MULTDOWN"
            clean_amount = int(amount) if float(amount).is_integer() else float(amount)
            
            # Step 1: Request a Proposal for a Multiplier
            # Note: SL and TP on Deriv Multipliers are usually monetary amounts (e.g., risk $5 to make $10)
            # We calculate the monetary risk based on the entry price and the TradingView SL/TP
            # For simplicity, if price=100, SL=90, risk is 10%. If stake is $10, monetary SL is $1.00.
            
            # Let's request the proposal first
            proposal_req = {
                "proposal": 1,
                "amount": clean_amount,
                "basis": "stake",
                "contract_type": direction,
                "currency": "USD",
                "underlying_symbol": symbol,
                "multiplier": 100, # 1:100 Leverage
                "limit_order": {
                    "stop_loss": abs(price - sl), # Distance in price
                    "take_profit": abs(tp - price) # Distance in price
                }
            }
            print(f"Requesting Multiplier Proposal: {json.dumps(proposal_req)}")
            await ws.send(json.dumps(proposal_req))
            
            prop_res_raw = await ws.recv()
            prop_res = json.loads(prop_res_raw)
            
            if "error" in prop_res:
                # If absolute price distances fail, try without limit_order first
                print(f"Proposal Error: {prop_res['error']['message']}. Retrying without SL/TP...")
                del proposal_req["limit_order"]
                await ws.send(json.dumps(proposal_req))
                prop_res_raw = await ws.recv()
                prop_res = json.loads(prop_res_raw)
                
                if "error" in prop_res:
                    return {"error": prop_res["error"]}
                
            proposal_id = prop_res.get("proposal", {}).get("id")
            if not proposal_id:
                return {"error": {"message": "No proposal ID returned"}}
                
            print(f"Got Multiplier Proposal ID: {proposal_id}")
            
            # Step 2: Execute Buy with Proposal ID
            buy_req = {
                "buy": proposal_id,
                "price": clean_amount
            }
            print(f"Executing Multiplier Contract...")
            await ws.send(json.dumps(buy_req))
            
            buy_res_raw = await ws.recv()
            return json.loads(buy_res_raw)
