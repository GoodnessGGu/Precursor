import requests
import os
from dotenv import load_dotenv

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")

def test_rest():
    url = "https://api.deriv.com/api/v1/authorize"
    headers = {
        "Authorization": f"Bearer {DERIV_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"authorize": DERIV_TOKEN}
    
    print(f"Testing REST Auth with token: {DERIV_TOKEN[:10]}...")
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_rest()
