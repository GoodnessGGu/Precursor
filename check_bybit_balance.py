from bybit_engine import BybitBot
import os
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

def check_balance():
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    testnet = os.getenv('BYBIT_TESTNET', 'False').lower() == 'true'

    if not api_key or not api_secret:
        print("Error: BYBIT_API_KEY or BYBIT_API_SECRET not found in .env")
        return

    print(f"Connecting to Bybit {'Testnet' if testnet else 'Mainnet'}...")
    bot = BybitBot(api_key, api_secret, testnet=testnet)
    balance = bot.get_balance()
    
    print("\n" + "="*30)
    print(f"BYBIT ACCOUNT BALANCE")
    print("="*30)
    print(f"Available USDT: ${balance}")
    print("="*30)

if __name__ == "__main__":
    check_balance()
