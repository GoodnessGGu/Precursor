import MetaTrader5 as mt5
import time

class MT5Bot:
    def __init__(self, login=None, password=None, server=None):
        # Establish connection to the MetaTrader 5 terminal
        if not mt5.initialize():
            print(f"MT5 Initialization failed, error code = {mt5.last_error()}")
            self.connected = False
            return
            
        # Attempt login if credentials are provided
        if login and password and server:
            authorized = mt5.login(int(login), password=password, server=server)
            if authorized:
                print(f"MT5 Successfully Logged into Account: {login}")
                self.connected = True
            else:
                print(f"MT5 Login failed, error code: {mt5.last_error()}")
                self.connected = False
        else:
            # Assume already logged in
            print("MT5 Connected (using active terminal session)")
            self.connected = True

    def get_account_info(self):
        if not self.connected: return {"error": "MT5 not connected"}
        
        account_info = mt5.account_info()
        if account_info is None:
            return {"error": f"Failed to retrieve MT5 account info, error code: {mt5.last_error()}"}
        
        return {
            "login": account_info.login,
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin_free": account_info.margin_free,
            "currency": account_info.currency,
            "server": account_info.server
        }

    def place_order(self, symbol, side, qty, sl, tp):
        """
        Places an exact market order on MT5 with specified lot size, SL, and TP.
        """
        if not self.connected: return {"error": "MT5 not connected"}

        # Select the symbol
        if not mt5.symbol_select(symbol, True):
            return {"error": f"Failed to select symbol {symbol}. Is it correct for your account type?"}

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"error": f"Symbol {symbol} not found"}

        # Define order type based on side
        if side.lower() == "long":
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid

        # Create the MT5 request dictionary
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(qty),          # EXACT Lot size (e.g., 0.01)
            "type": order_type,
            "price": price,
            "sl": float(sl),               # EXACT Price level for Stop Loss
            "tp": float(tp),               # EXACT Price level for Take Profit
            "deviation": 20,               # Max slippage in points
            "magic": 100,                  # Magic number to identify bot trades
            "comment": "Gushtec AI Pilot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC, # Usually required for Deriv MT5
        }

        print(f"Sending MT5 Order: {qty} lots of {symbol} ({side.upper()})")
        
        # Send order to MT5
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Order failed, retcode={result.retcode}")
            # Analyze the error
            result_dict = result._asdict()
            return {"error": f"MT5 Error: {result.comment} (Code: {result.retcode})"}
        
        print(f"✅ MT5 TRADE OPENED! Ticket: {result.order}")
        return {"status": "success", "ticket": result.order, "price": result.price}

    def shutdown(self):
        if self.connected:
            mt5.shutdown()

if __name__ == "__main__":
    bot = MT5Bot()
    info = bot.get_account_info()
    print("\n--- MT5 ACCOUNT INFO ---")
    print(info)
    bot.shutdown()
