import asyncio
import json
import logging
from typing import Set
import websockets
import aiohttp
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('relay_server.log')
    ]
)
logger = logging.getLogger(__name__)

# OKX WebSocket URL
OKX_WSS_URL = "wss://ws.okx.com:8443/ws/v5/public"

# Set to store all connected clients
connected_clients: Set[websockets.WebSocketServerProtocol] = set()

def read_trading_pairs(filename="pairs.txt"):
    """Read trading pairs from file"""
    try:
        with open(filename, 'r') as f:
            # Read lines and remove empty lines and whitespace
            pairs = [line.strip() for line in f.readlines() if line.strip()]
        logger.info(f"Loaded {len(pairs)} trading pairs")
        return pairs
    except Exception as e:
        logger.error(f"Error reading pairs file: {e}")
        return ["BTC-USDT"]  # Default to BTC-USDT if file reading fails

async def subscribe_okx():
    """Subscribe to OKX ticker data for all pairs"""
    pairs = read_trading_pairs()
    return {
        "op": "subscribe",
        "args": [
            {
                "channel": "tickers",
                "instId": pair
            } for pair in pairs
        ]
    }

async def handle_client_connection(websocket):
    """Handle individual client connections"""
    try:
        # Add client to connected clients set
        connected_clients.add(websocket)
        client_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'Unknown'
        logger.info(f"New client connected from {client_address}. Total clients: {len(connected_clients)}")
        
        try:
            async for message in websocket:
                logger.debug(f"Received message from client: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_address} connection closed normally")
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
    finally:
        connected_clients.remove(websocket)
        logger.info(f"Client disconnected. Total clients: {len(connected_clients)}")

async def broadcast_to_clients(message: str):
    """Broadcast message to all connected clients"""
    if not connected_clients:
        return
    
    # Create tasks for sending message to all clients
    disconnected_clients = set()
    for client in connected_clients:
        try:
            await client.send(message)
        except websockets.exceptions.ConnectionClosed:
            disconnected_clients.add(client)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            disconnected_clients.add(client)
    
    # Remove disconnected clients
    for client in disconnected_clients:
        connected_clients.remove(client)

async def connect_okx_and_relay():
    """Connect to OKX WebSocket and relay messages to clients"""
    retry_count = 0
    max_retries = 5
    retry_delay = 5

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(OKX_WSS_URL) as ws:
                    logger.info("Connected to OKX WebSocket")
                    retry_count = 0  # Reset retry count on successful connection
                    
                    # Subscribe to ticker data
                    subscribe_message = await subscribe_okx()
                    await ws.send_json(subscribe_message)
                    logger.info("Subscribed to OKX ticker data")
                    
                    # Handle incoming messages
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await broadcast_to_clients(msg.data)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.warning("OKX WebSocket connection closed")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error("OKX WebSocket connection error")
                            break
                            
        except aiohttp.ClientError as e:
            logger.error(f"OKX connection error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in OKX connection: {e}")
        
        retry_count += 1
        if retry_count >= max_retries:
            logger.error(f"Failed to connect after {max_retries} attempts. Waiting longer before retrying...")
            await asyncio.sleep(retry_delay * 2)
            retry_count = 0
        else:
            logger.info(f"Attempting to reconnect in {retry_delay} seconds... (Attempt {retry_count}/{max_retries})")
            await asyncio.sleep(retry_delay)

async def main():
    """Main function to start the WebSocket server and OKX connection"""
    server = None
    try:
        # Start the WebSocket server
        server = await websockets.serve(
            handle_client_connection,
            "localhost",
            8765,
            ping_interval=30,
            ping_timeout=10
        )
        
        logger.info("WebSocket server started on ws://localhost:8765")
        
        # Start the OKX connection and relay
        okx_task = asyncio.create_task(connect_okx_and_relay())
        
        # Keep the server running
        await asyncio.Future()  # run forever
        
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        if server:
            server.close()
            await server.wait_closed()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
