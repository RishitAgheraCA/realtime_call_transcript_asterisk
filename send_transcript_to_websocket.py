import asyncio
import websockets
import json

async def send_transcript_to_server():
    uri = "ws://0.0.0.0:8765"  # WebSocket server URI

    try:
        # Connect to the WebSocket server
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")

            # Send initial message with call_id
            call_id = "12345"  # Replace with the desired call_id
            await websocket.send(json.dumps({"received_from": "Transcript side","call_id":"12345"}))
            print(f"Sent call_id: {call_id}")

            # Simulate sending a transcript after a delay
            transcript = "This is a test transcript from the client"
            await asyncio.sleep(2)  # Optional delay
            await websocket.send(json.dumps({"transcript": transcript}))
            print(f"Sent transcript: {transcript}")
            # await websocket.close()
            # Optionally, listen for any response from the server
            response = await websocket.recv()
            print(f"Received response from server: {response}")

    except Exception as e:
        print(f"Error: {e}")

# Run the client
asyncio.run(send_transcript_to_server())
