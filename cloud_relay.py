import os
import asyncio
import json
import logging
import sys
from typing import Set, Dict, Any

import websockets
import aiohttp
from google.cloud import pubsub_v1
from google.cloud import logging as cloud_logging

# Configure Google Cloud Logging
def setup_cloud_logging():
    """Set up logging to Google Cloud Logging"""
    try:
        client = cloud_logging.Client()
        cloud_handler = client.get_default_handler()
        cloud_handler.setLevel(logging.INFO)
        logger = logging.getLogger()
        logger.addHandler(cloud_handler)
        logger.setLevel(logging.INFO)
        return logger
    except Exception as e:
        print(f"Could not set up Cloud Logging: {e}")
        return logging.getLogger(__name__)

# Initialize logger
logger = setup_cloud_logging()

# Configuration from environment variables
CONFIG = {
    'OKX_WSS_URL': os.getenv('OKX_WSS_URL', "wss://ws.okx.com:8443/ws/v5/public"),
    'PUBSUB_TOPIC': os.getenv('PUBSUB_TOPIC', 'trading-data-stream'),
    'PROJECT_ID': os.getenv('GCP_PROJECT_ID', ''),
    'PORT': int(os.getenv('PORT', 8080)),  # Cloud Run default
    'MAX_CONNECTIONS': int(os.getenv('MAX_CONNECTIONS', 100)),
    'PAIRS_FILE': os.getenv('PAIRS_FILE', 'pairs.txt')
}

class CloudWebSocketRelay:
    def __init__(self):
        # Set of connected WebSocket clients
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Pub/Sub publisher client
        self.publisher = pubsub_v1.PublisherClient() if CONFIG['PROJECT_ID'] else None
        self.topic_path = (
            self.publisher.topic_path(CONFIG['PROJECT_ID'], CONFIG['PUBSUB_TOPIC']) 
            if self.publisher else None
        )

    def read_trading_pairs(self, filename=None):
        """Read trading pairs from file or environment"""
        filename = filename or CONFIG['PAIRS_FILE']
        try:
            with open(filename, 'r') as f:
                pairs = [line.strip() for line in f.readlines() if line.strip()]
            logger.info(f"Loaded {len(pairs)} trading pairs from {filename}")
            return pairs
        except Exception as e:
            logger.error(f"Error reading pairs file: {e}")
            return ["BTC-USDT"]  # Default fallback

    async def publish_to_pubsub(self, message: Dict[str, Any]):
        """Publish message to Google Cloud Pub/Sub"""
        if not self.publisher or not self.topic_path:
            return

        try:
            # Convert message to JSON string
            data = json.dumps(message).encode('utf-8')
            future = self.publisher.publish(self.topic_path, data)
            future.result(timeout=5)  # Wait for publish confirmation
            logger.debug(f"Published message to {CONFIG['PUBSUB_TOPIC']}")
        except Exception as e:
            logger.error(f"Pub/Sub publish error: {e}")

    async def broadcast_to_clients(self, message: str):
        """Broadcast message to all connected WebSocket clients"""
        if not self.connected_clients:
            return
        
        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.connected_clients.remove(client)

    async def handle_client_connection(self, websocket, path):
        """Handle individual WebSocket client connections"""
        try:
            # Limit maximum number of connections
            if len(self.connected_clients) >= CONFIG['MAX_CONNECTIONS']:
                await websocket.close(code=1008, reason="Server at maximum capacity")
                return

            # Add client to connected clients
            self.connected_clients.add(websocket)
            client_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'Unknown'
            logger.info(f"New client connected from {client_address}. Total clients: {len(self.connected_clients)}")
            
            async for message in websocket:
                logger.debug(f"Received message from client: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_address} connection closed normally")
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            self.connected_clients.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")

    async def subscribe_okx(self):
        """Create OKX subscription message for all pairs"""
        pairs = self.read_trading_pairs()
        return {
            "op": "subscribe",
            "args": [
                {
                    "channel": "tickers",
                    "instId": pair
                } for pair in pairs
            ]
        }

    async def connect_okx_and_relay(self):
        """Connect to OKX WebSocket and relay messages"""
        retry_count = 0
        max_retries = 5
        retry_delay = 5

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(CONFIG['OKX_WSS_URL']) as ws:
                        logger.info("Connected to OKX WebSocket")
                        retry_count = 0  # Reset retry count
                        
                        # Subscribe to ticker data
                        subscribe_message = await self.subscribe_okx()
                        await ws.send_json(subscribe_message)
                        logger.info("Subscribed to OKX ticker data")
                        
                        # Handle incoming messages
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                message_data = msg.data
                                
                                # Broadcast to WebSocket clients
                                await self.broadcast_to_clients(message_data)
                                
                                # Optionally publish to Pub/Sub
                                try:
                                    parsed_message = json.loads(message_data)
                                    await self.publish_to_pubsub(parsed_message)
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not parse message: {message_data}")
                            
                            elif msg.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                                logger.warning("OKX WebSocket connection issue")
                                break
                                
            except aiohttp.ClientError as e:
                logger.error(f"OKX connection error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in OKX connection: {e}")
            
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Failed to connect after {max_retries} attempts")
                await asyncio.sleep(retry_delay * 2)
                retry_count = 0
            else:
                logger.info(f"Attempting to reconnect in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)

    async def start_server(self):
        """Start WebSocket server and OKX connection"""
        server = await websockets.serve(
            self.handle_client_connection,
            "0.0.0.0",  # Listen on all interfaces for Cloud Run
            CONFIG['PORT'],
            ping_interval=30,
            ping_timeout=10
        )
        
        logger.info(f"WebSocket server started on port {CONFIG['PORT']}")
        
        # Create tasks for server and OKX connection
        okx_task = asyncio.create_task(self.connect_okx_and_relay())
        
        # Keep server running
        await server.wait_closed()

def main():
    """Main entry point for the Cloud WebSocket Relay"""
    relay = CloudWebSocketRelay()
    
    try:
        asyncio.run(relay.start_server())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
