import requests
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
DERIV_APP_ID = os.getenv("DERIV_APP_ID")

def find_demo_10k():
    url = "https://api.derivws.com/trading/v1/options/accounts"
    headers = {
        "Authorization": f"Bearer {DERIV_TOKEN}",
        "Deriv-App-ID": DERIV_APP_ID,
        "Content-Type": "application/json"
    }
    
    print(f"Searching for the $10,000 Demo account...")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            accounts = response.json().get('data', [])
            print(f"Found {len(accounts)} accounts in total.")
            
            for acc in accounts:
                acc_id = acc.get('account_id')
                balance_raw = acc.get('balance', 0)
                # Ensure balance is a float for comparison
                try:
                    balance = float(balance_raw)
                except:
                    balance = 0.0
                    
                is_demo = acc.get('is_virtual', False)
                
                print(f" - {acc_id}: ${balance} (Demo: {is_demo})")
                
                if balance >= 9000 and is_demo:
                    print(f"\n🎯 FOUND IT! Account ID: {acc_id}")
                    return acc_id
            
            print("\n⚠️ No account with ~$10,000 found. Please double-check your account list in the Deriv dashboard.")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    return None

if __name__ == "__main__":
    find_demo_10k()
