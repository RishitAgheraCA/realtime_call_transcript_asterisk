// Create a new WebSocket connection
const websocket = new WebSocket('ws://localhost:8765');

// Event listener for when the connection is established
websocket.onopen = () => {
    console.log('Connected to WebSocket server');

    // Send initial message with call_id
    const call_id = '54321';  // Replace with a unique call_id
    websocket.send(JSON.stringify({ call_id }));
    console.log(`Sent call_id: ${call_id}`);
};

// Event listener for incoming messages from the server
websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`Received transcript: ${data.transcript}`);
};

// Event listener for errors
websocket.onerror = (error) => {
    console.error('WebSocket error:', error);
};

// Event listener for when the connection is closed
websocket.onclose = () => {
    console.log('WebSocket connection closed');
};
