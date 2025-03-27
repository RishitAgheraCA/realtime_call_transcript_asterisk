import asyncio
import websockets
import json

# Store active agent connections (call_id -> websocket)
active_connections = {}

async def handler(websocket):
    call_id = "0"
    try:
        # Wait for the agent to send their call_id for identification
        while True:
            initial_message = await websocket.recv()
            data = json.loads(initial_message)
            print(data)
            if "received_from" in data.keys():
                if data.get('received_from') == "Transcript side":
                    transcript_for_call_id = data.get('call_id')
                    print("received check for callid:",transcript_for_call_id)
                    if transcript_for_call_id in active_connections.keys():
                        await websocket.send("Found Call-ID")
                        agent_socket = active_connections.get(transcript_for_call_id)
                        print("transcript received from server:",data.get("transcript"))
                        await agent_socket.send(json.dumps({"transcript":data.get("transcript")}))
                        await agent_socket.wait_closed()
                    else:
                        await websocket.send("Not found Call-ID")
                    # await websocket.wait_closed()
                    
            try:
                call_id = data.get("call_id")
                # Register the agent with their call_id
                active_connections[call_id] = websocket
                print(f"Agent connected with call_id: {call_id}: websokcet:{websocket}")
                await websocket.wait_closed()
            except Exception as e:
                pass
            # Keep the connection open
            await websocket.wait_closed()
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup after disconnection
        # if call_id in active_connections:
        #     del active_connections[call_id]
        #     print(f"Agent with call_id {call_id} disconnected")
        pass

# Function to send transcript to the correct agent
async def send_transcript(call_id, transcript):
    if call_id in active_connections:
        agent_socket = active_connections[call_id]
        message = json.dumps({"transcript": transcript})
        await agent_socket.send(message)
        print(f"Sent transcript to call_id {call_id}")
    else:
        print(f"No active agent for call_id {call_id}")

# Start the WebSocket server
async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket Server Started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

asyncio.run(main())