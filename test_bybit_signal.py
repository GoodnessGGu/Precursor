import requests
import json

def send_test_signal():
    url = "http://localhost:8000/webhook"
    
    # Simulate a Bitcoin 1-minute Long signal
    payload = {
        "action": "long",
        "symbol": "BTCUSDT",
        "price": 66700,
        "sl": 66500,
        "tp": 67100,
        "qty": 0.001
    }
    
    print(f"Sending test signal to local bot at {url}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send_test_signal()
