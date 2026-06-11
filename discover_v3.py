import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
APP_ID = "1" # Default to 1

def discover_v3_accounts():
    """
    Step 1 of the 2026 API: List all accounts linked to the PAT
    """
    url = "https://api.deriv.com/api/v1/accounts"
    headers = {
        "Authorization": f"Bearer {DERIV_TOKEN}",
        "Deriv-App-ID": APP_ID,
        "Content-Type": "application/json"
    }
    
    print(f"Discovering accounts via v3 API with token: {DERIV_TOKEN[:10]}...")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("--- ACCOUNTS FOUND ---")
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

if __name__ == "__main__":
    discover_v3_accounts()
