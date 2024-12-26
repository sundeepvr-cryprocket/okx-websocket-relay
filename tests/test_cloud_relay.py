import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

# Import the main relay class
from cloud_relay import CloudWebSocketRelay

@pytest.mark.asyncio
async def test_read_trading_pairs():
    """Test reading trading pairs from file"""
    relay = CloudWebSocketRelay()
    
    # Test with a mock file
    with patch('builtins.open', AsyncMock()) as mock_file:
        mock_file.return_value.__enter__.return_value.readlines.return_value = [
            'BTC-USDT\n', 
            'ETH-USDT\n'
        ]
        
        pairs = relay.read_trading_pairs('mock_pairs.txt')
        
        assert len(pairs) == 2
        assert 'BTC-USDT' in pairs
        assert 'ETH-USDT' in pairs

@pytest.mark.asyncio
async def test_subscribe_okx():
    """Test OKX subscription message generation"""
    relay = CloudWebSocketRelay()
    
    # Mock reading pairs
    with patch.object(relay, 'read_trading_pairs', return_value=['BTC-USDT', 'ETH-USDT']):
        subscribe_message = await relay.subscribe_okx()
        
        assert 'op' in subscribe_message
        assert subscribe_message['op'] == 'subscribe'
        assert 'args' in subscribe_message
        
        # Check args contain correct pairs
        pair_ids = [arg['instId'] for arg in subscribe_message['args']]
        assert 'BTC-USDT' in pair_ids
        assert 'ETH-USDT' in pair_ids
        assert len(subscribe_message['args']) == 2

@pytest.mark.asyncio
async def test_broadcast_to_clients():
    """Test broadcasting messages to WebSocket clients"""
    relay = CloudWebSocketRelay()
    
    # Create mock WebSocket clients
    mock_clients = [
        AsyncMock(),
        AsyncMock(),
        AsyncMock()
    ]
    relay.connected_clients = set(mock_clients)
    
    test_message = json.dumps({"test": "message"})
    await relay.broadcast_to_clients(test_message)
    
    # Verify each mock client received the message
    for client in mock_clients:
        client.send.assert_called_once_with(test_message)

@pytest.mark.asyncio
async def test_publish_to_pubsub():
    """Test Pub/Sub message publishing"""
    relay = CloudWebSocketRelay()
    
    # Mock Pub/Sub publisher
    mock_publisher = AsyncMock()
    relay.publisher = mock_publisher
    relay.topic_path = 'projects/test/topics/test-topic'
    
    test_message = {"test": "pubsub_message"}
    await relay.publish_to_pubsub(test_message)
    
    # Verify publish method was called
    mock_publisher.publish.assert_called_once()

def test_error_handling():
    """Test basic error handling mechanisms"""
    relay = CloudWebSocketRelay()
    
    # Simulate various error scenarios
    with pytest.raises(Exception):
        # Force an error by passing invalid data
        asyncio.run(relay.publish_to_pubsub(None))

# Performance and load testing
@pytest.mark.asyncio
async def test_connection_limit():
    """Test maximum connection handling"""
    relay = CloudWebSocketRelay()
    
    # Exceed max connections
    for _ in range(200):  # Assuming max is 100
        mock_client = AsyncMock()
        relay.connected_clients.add(mock_client)
    
    assert len(relay.connected_clients) <= 100
