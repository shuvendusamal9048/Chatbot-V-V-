import asyncio
import websockets


async def main():

    ws = await websockets.connect(
        "ws://localhost:8000/chat"
    )

    await ws.send(
        "What is the candidate name?"
    )

    full_response = ""

    while True:

        msg = await ws.recv()

        if msg == "[END]":
            print("\n")
            print("Final Response:")
            print(full_response)
            break

        full_response += msg

        print(msg, end="", flush=True)


asyncio.run(main())