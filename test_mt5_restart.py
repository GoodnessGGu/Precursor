import MetaTrader5 as mt5
import time

def restart_and_attach():
    print("Initializing MT5 from a clean state...")
    mt5_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    
    # Initialize will launch the terminal if it's not running
    if not mt5.initialize(path=mt5_path, timeout=60000):
        print(f"❌ Failed to initialize, error code = {mt5.last_error()}")
        return

    print("✅ Successfully initialized MT5!")
    print("Waiting for MT5 to complete its own auto-login process (10 seconds)...")
    time.sleep(10)
    
    account_info = mt5.account_info()
    if account_info is not None:
        print("\n--- ACTIVE ACCOUNT INFO ---")
        print(f"Login: {account_info.login}")
        print(f"Server: {account_info.server}")
        print(f"Balance: {account_info.balance} {account_info.currency}")
        print(f"Equity: {account_info.equity}")
        print(f"Margin Free: {account_info.margin_free}")
    else:
        print(f"❌ Could not retrieve account info. Error code: {mt5.last_error()}")
        print("This usually means MT5 didn't auto-login successfully.")

    mt5.shutdown()

if __name__ == "__main__":
    restart_and_attach()
