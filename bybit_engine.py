from pybit.unified_trading import HTTP
import os

class BybitBot:
    def __init__(self, api_key, api_secret, testnet=False):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )

    def place_order(self, symbol, side, qty, sl, tp):
        """
        Places a USDT Perpetual Market Order on Bybit with TP/SL
        """
        # Ensure side is correct for Bybit (Buy/Sell)
        bybit_side = "Buy" if side.lower() == "long" else "Sell"
        
        try:
            # 1. Set Position Mode to Isolated (Safest for $100)
            # This is optional if already set in app
            
            # 2. Place Order
            response = self.session.place_order(
                category="linear",
                symbol=symbol,
                side=bybit_side,
                orderType="Market",
                qty=str(qty),
                takeProfit=str(tp),
                stopLoss=str(sl),
                tpTriggerBy="MarkPrice",
                slTriggerBy="MarkPrice",
                tpslMode="Full"
            )
            print(f"Bybit Order Response: {response}")
            return response
        except Exception as e:
            print(f"Bybit API Error: {e}")
            return {"error": str(e)}

    def get_balance(self):
        """Fetches available USDT balance"""
        try:
            res = self.session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            balance = res['result']['list'][0]['totalAvailableBalance']
            return balance
        except:
            return "0.00"
