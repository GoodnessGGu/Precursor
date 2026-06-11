import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN", "").strip()
APP_ID = os.getenv("DERIV_APP_ID", "").strip()

def test_deriv_rest():
    url = "https://api.derivws.com/trading/v1/options/accounts"
    
    headers = {
        "Authorization": f"Bearer {DERIV_TOKEN}",
        "Deriv-App-ID": APP_ID,
        "Content-Type": "application/json"
    }
    
    print(f"Testing Deriv REST API v3...")
    print(f"Token: {DERIV_TOKEN[:10]}...")
    print(f"App ID: {APP_ID}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        try:
            print("Response:", json.dumps(response.json(), indent=2))
        except:
            print("Response:", response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_deriv_rest()
