import requests
import os
from dotenv import load_dotenv

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")

def test_rest_v2():
    # Trying the new 2026 REST endpoint
    url = "https://api.deriv.com/trading/v1/accounts"
    headers = {
        "Authorization": f"Bearer {DERIV_TOKEN}",
        "Content-Type": "application/json",
        "Deriv-App-ID": "1"
    }
    
    print(f"Testing NEW REST Auth with token: {DERIV_TOKEN[:10]}...")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_rest_v2()
