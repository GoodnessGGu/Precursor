import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
DERIV_APP_ID = os.getenv("DERIV_APP_ID")

def test_new_handshake():
    # Trying the official 2026 REST endpoint with Alphanumeric App ID in Header
    url = "https://api.deriv.com/api/v1/authorize"
    headers = {
        "Authorization": f"Bearer {DERIV_TOKEN}",
        "Deriv-App-ID": DERIV_APP_ID,
        "Content-Type": "application/json"
    }
    
    print(f"Handshaking with token: {DERIV_TOKEN[:10]}...")
    print(f"App ID: {DERIV_APP_ID}")
    
    try:
        # Try POST authorize
        res = requests.post(url, headers=headers, json={"authorize": DERIV_TOKEN})
        print(f"REST POST Status: {res.status_code}")
        print(f"REST POST Response: {res.text[:500]}")
        
        # Try GET accounts
        res_get = requests.get("https://api.deriv.com/api/v1/accounts", headers=headers)
        print(f"REST GET Status: {res_get.status_code}")
        print(f"REST GET Response: {res_get.text[:500]}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_new_handshake()
