import requests
import os
from dotenv import load_dotenv
import json
import asyncio
import websockets

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN", "").strip()
APP_ID = os.getenv("DERIV_APP_ID", "").strip()
ACCOUNT_ID = "DOT91952411"

async def test_deriv_otp():
    # Step 1: Get OTP URL
    url = f"https://api.derivws.com/trading/v1/options/accounts/{ACCOUNT_ID}/otp"
    
    headers = {
        "Authorization": f"Bearer {DERIV_TOKEN}",
        "Deriv-App-ID": APP_ID,
        "Content-Type": "application/json"
    }
    
    print(f"Requesting OTP for Account {ACCOUNT_ID}...")
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            ws_url = data.get("data", {}).get("url")
            print(f"Got WebSocket URL: {ws_url}")
            
            if ws_url:
                print("\nConnecting to WebSocket...")
                async with websockets.connect(ws_url) as ws:
                    # Request balance to verify connection
                    await ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                    res = await ws.recv()
                    print("WebSocket Response:", json.dumps(json.loads(res), indent=2))
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_deriv_otp())
