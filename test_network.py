import asyncio
import websockets
import time

async def test():
    uri = "wss://demo.ctraderapi.com:5036"
    print(f"Attempting to connect to {uri}...")
    try:
        async with websockets.connect(uri, open_timeout=10) as ws:
            print("✅ CONNECTION SUCCESSFUL!")
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test())
