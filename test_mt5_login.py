import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER", "Deriv-Demo")

def test_login():
    print("Initializing MT5...")
    if not MT5_LOGIN or not MT5_PASSWORD:
        print("Error: MT5_LOGIN or MT5_PASSWORD missing from .env file.")
        return

    print(f"Loaded credentials from .env: Login={MT5_LOGIN}, Server={MT5_SERVER}, Password={'*' * len(MT5_PASSWORD)}")
    
    print("Initializing MT5 from cold start...")
    mt5_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    
    # Initialize path only
    if not mt5.initialize(path=mt5_path):
        print(f"initialize() failed, error code = {mt5.last_error()}")
        return
        
    print(f"Attempting login to account {MT5_LOGIN} on server {MT5_SERVER}...")
    authorized = mt5.login(int(MT5_LOGIN), password=MT5_PASSWORD, server=MT5_SERVER)

    if authorized:
        print("✅ SUCCESS: Connected to MT5 Account!")
        account_info = mt5.account_info()
        print(f"Login: {account_info.login}")
        print(f"Server: {account_info.server}")
        print(f"Balance: {account_info.balance} {account_info.currency}")
        print(f"Equity: {account_info.equity}")
        print(f"Margin Free: {account_info.margin_free}")
    else:
        print(f"❌ FAILED: Could not retrieve account info. Error code: {mt5.last_error()}")
        print("This usually means the Password or Server name in your .env is incorrect.")
        
    mt5.shutdown()

if __name__ == "__main__":
    test_login()
