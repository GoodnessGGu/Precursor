import requests
import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

# THE CORE CONFIG
DERIV_TOKEN = os.getenv("DERIV_TOKEN", "").strip()
APP_ID = os.getenv("DERIV_APP_ID", "1") # Need to get this from user

class DerivV3:
    def __init__(self, token, app_id):
        self.token = token
        self.app_id = app_id
        self.base_url = "https://api.deriv.com"
        self.ws_base = "wss://ws.derivws.com/websockets/v3"

    async def get_accounts(self):
        """Lists all accounts using the new v3 Bearer Auth"""
        url = f"{self.base_url}/trading/v1/accounts"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Deriv-App-ID": self.app_id,
            "Content-Type": "application/json"
        }
        
        print(f"Requesting Account List via V3 REST...")
        try:
            # We must use the correct subdomain for REST v3
            # Some docs say api.deriv.com, others say api.derivws.com
            for domain in ["https://api.deriv.com", "https://api.derivws.com"]:
                print(f"Trying domain: {domain}")
                try:
                    res = requests.get(f"{domain}/trading/v1/accounts", headers=headers, timeout=5)
                    if res.status_code == 200:
                        return res.json(), None
                except:
                    continue
            return None, "All V3 REST domains failed."
        except Exception as e:
            return None, str(e)

    async def get_otp_url(self, account_id):
        """Gets a pre-signed WebSocket URL for a specific account"""
        url = f"{self.base_url}/trading/v1/accounts/{account_id}/otp"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Deriv-App-ID": self.app_id
        }
        res = requests.post(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("ws_url"), None
        return None, res.text

async def diagnostic():
    bot = DerivV3(DERIV_TOKEN, APP_ID)
    accounts, err = await bot.get_accounts()
    if err:
        print(f"DIAGNOSTIC ERROR: {err}")
    else:
        print("DIAGNOSTIC SUCCESS!")
        print(json.dumps(accounts, indent=2))

if __name__ == "__main__":
    asyncio.run(diagnostic())
