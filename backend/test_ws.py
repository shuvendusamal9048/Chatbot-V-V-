import asyncio
import websockets

async def main():
    async with websockets.connect('ws://127.0.0.1:8000/chat') as ws:
        await ws.send('hello')
        for i in range(4):
            print(await ws.recv())

asyncio.run(main())
