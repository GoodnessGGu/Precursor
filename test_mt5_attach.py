import MetaTrader5 as mt5

def test_attach():
    print("Attempting to attach to running MT5 terminal...")
    
    mt5_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=mt5_path, timeout=60000):
        print(f"❌ Failed to attach, error code = {mt5.last_error()}")
        return

    print("✅ Successfully attached to MT5!")
    
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
        print("Note: Make sure you are actually logged into an account in MT5.")

    mt5.shutdown()

if __name__ == "__main__":
    test_attach()
