# OKX WebSocket Relay

## Overview
This application provides a WebSocket relay for OKX trading pair data, with a real-time frontend dashboard.

## Prerequisites
- Python 3.8+
- pip

## Setup
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application
Open two terminal windows:

1. Start the WebSocket Relay Server:
   ```bash
   python websocket_relay.py
   ```

2. Start the Frontend Server:
   ```bash
   python server.py
   ```

3. Open a web browser and navigate to `http://localhost:5000`

## Configuration
- Modify `pairs.txt` to add or remove trading pairs
- Check `relay_server.log` for server logs

## Features
- Real-time OKX trading pair data
- WebSocket connection status
- Message logging
- Automatic reconnection

## Dependencies
- websockets
- aiohttp
- flask
