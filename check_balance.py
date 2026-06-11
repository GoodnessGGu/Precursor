import asyncio
import json
import websockets
import os
import time
from dotenv import load_dotenv
from ctrader_engine import CTraderBot

load_dotenv()

async def check():
    bot = CTraderBot()
    # Step 1: App Auth
    print("Connecting...")
    bot.ws = await websockets.connect(bot.uri)
    await bot.ws.send(json.dumps({
        "payloadType": 2100,
        "payload": {"clientId": bot.client_id, "clientSecret": bot.secret}
    }))
    await bot.ws.recv()
    
    # Step 2: Account Auth
    print(f"Authorizing Account {bot.account_id}...")
    await bot.ws.send(json.dumps({
        "payloadType": 2102,
        "payload": {"ctidTraderAccountId": int(bot.account_id), "accessToken": bot.access_token}
    }))
    res = await bot.ws.recv()
    data = json.loads(res)
    print(f"AUTH RESPONSE: {data}")
    
    # Step 3: Try Trader Req again with a more explicit payload
    print("Requesting Trader Details...")
    await bot.ws.send(json.dumps({
        "payloadType": 2111,
        "payload": {"ctidTraderAccountId": int(bot.account_id)},
        "clientMsgId": "check_1"
    }))
    res = await bot.ws.recv()
    print(f"TRADER RESPONSE: {res}")

if __name__ == "__main__":
    asyncio.run(check())
