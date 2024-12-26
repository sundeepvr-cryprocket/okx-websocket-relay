document.addEventListener('DOMContentLoaded', () => {
    const statusIndicator = document.getElementById('status-indicator');
    const connectionText = document.getElementById('connection-text');
    const connectionDetails = document.getElementById('connection-details');
    const tickTableBody = document.getElementById('tick-table-body');
    const messageContainer = document.getElementById('message-container');
    const clearLogButton = document.getElementById('clear-log');

    const WS_URL = 'ws://localhost:8765';
    let socket = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    const RECONNECT_DELAY = 5000; // 5 seconds

    // Tracking for each trading pair
    const pairData = {};

    function formatNumber(num, decimals = 2) {
        return num ? Number(num).toFixed(decimals) : '-';
    }

    function getChangeClass(change) {
        const numChange = Number(change);
        if (numChange > 0) return 'positive';
        if (numChange < 0) return 'negative';
        return 'neutral';
    }

    function updatePairRow(pair, data) {
        let row = document.getElementById(`pair-${pair.replace('/', '-')}`);
        
        // Create row if it doesn't exist
        if (!row) {
            row = document.createElement('tr');
            row.id = `pair-${pair.replace('/', '-')}`;
            row.innerHTML = `
                <td>${pair}</td>
                <td class="last-price">-</td>
                <td class="change">-</td>
                <td class="high">-</td>
                <td class="low">-</td>
                <td class="volume">-</td>
                <td class="status">-</td>
            `;
            tickTableBody.appendChild(row);
        }

        // Update row data
        const lastPriceCell = row.querySelector('.last-price');
        const changeCell = row.querySelector('.change');
        const highCell = row.querySelector('.high');
        const lowCell = row.querySelector('.low');
        const volumeCell = row.querySelector('.volume');
        const statusCell = row.querySelector('.status');

        // Update last price
        if (data.last) {
            lastPriceCell.textContent = formatNumber(data.last);
        }

        // Update 24h change
        if (data.sodChg) {
            const changeClass = getChangeClass(data.sodChg);
            changeCell.textContent = `${formatNumber(data.sodChg)}%`;
            changeCell.className = `change ${changeClass}`;
        }

        // Update 24h high and low
        if (data.high24h) highCell.textContent = formatNumber(data.high24h);
        if (data.low24h) lowCell.textContent = formatNumber(data.low24h);

        // Update volume
        if (data.vol24h) volumeCell.textContent = formatNumber(data.vol24h, 4);

        // Update status based on price change
        if (data.sodChg) {
            const status = Number(data.sodChg) > 0 ? 'Bullish' : 'Bearish';
            statusCell.textContent = status;
            statusCell.className = `status ${getChangeClass(data.sodChg)}`;
        }
    }

    function formatTimestamp() {
        return new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    }

    function updateStatus(isConnected, details = '') {
        if (isConnected) {
            statusIndicator.classList.add('connected');
            connectionText.textContent = 'Connected';
            connectionDetails.textContent = details || 'WebSocket connection established';
        } else {
            statusIndicator.classList.remove('connected');
            connectionText.textContent = 'Disconnected';
            connectionDetails.textContent = details || 'No active connection';
        }
    }

    function addMessage(message, type = 'info') {
        const messageItem = document.createElement('div');
        messageItem.classList.add('message-item');
        
        // Add type-specific styling
        if (type === 'error') {
            messageItem.classList.add('error');
        } else if (type === 'success') {
            messageItem.classList.add('success');
        }

        // Parse and format the message
        try {
            const parsedMessage = JSON.parse(message);
            
            // Special handling for OKX ticker data
            if (parsedMessage.data && parsedMessage.arg) {
                const tickerData = parsedMessage.data[0];
                const pair = parsedMessage.arg.instId;
                
                // Update pair data
                updatePairRow(pair, tickerData);

                // Log message
                messageItem.innerHTML = `
                    <div class="d-flex justify-content-between">
                        <strong>${pair} Update</strong>
                        <small class="text-muted">${formatTimestamp()}</small>
                    </div>
                `;
            } else {
                // Fallback for other message types
                messageItem.innerHTML = `
                    <div class="d-flex justify-content-between">
                        <strong>Raw Message</strong>
                        <small class="text-muted">${formatTimestamp()}</small>
                    </div>
                    <pre class="mt-2 mb-0">${JSON.stringify(parsedMessage, null, 2)}</pre>
                `;
            }
        } catch {
            // For non-JSON messages
            messageItem.innerHTML = `
                <div class="d-flex justify-content-between">
                    <strong>System Message</strong>
                    <small class="text-muted">${formatTimestamp()}</small>
                </div>
                <div class="mt-2">${message}</div>
            `;
        }

        messageContainer.prepend(messageItem);
        
        // Limit message log to last 100 messages
        if (messageContainer.children.length > 100) {
            messageContainer.removeChild(messageContainer.lastChild);
        }
    }

    function readPairs() {
        fetch('pairs.txt')
            .then(response => response.text())
            .then(text => {
                const pairs = text.split('\n')
                    .filter(pair => pair.trim() !== '')
                    .map(pair => pair.trim());
                
                // Clear existing table rows
                tickTableBody.innerHTML = '';
                
                // Prepare rows for each pair
                pairs.forEach(pair => {
                    const row = document.createElement('tr');
                    row.id = `pair-${pair.replace('/', '-')}`;
                    row.innerHTML = `
                        <td>${pair}</td>
                        <td class="last-price">-</td>
                        <td class="change">-</td>
                        <td class="high">-</td>
                        <td class="low">-</td>
                        <td class="volume">-</td>
                        <td class="status">-</td>
                    `;
                    tickTableBody.appendChild(row);
                });
            })
            .catch(error => {
                addMessage(`Error reading pairs: ${error}`, 'error');
            });
    }

    function connectWebSocket() {
        const startTime = Date.now();
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
            const connectionTime = ((Date.now() - startTime) / 1000).toFixed(2);
            updateStatus(true, `Connected in ${connectionTime}s`);
            reconnectAttempts = 0;
            addMessage('WebSocket connection established', 'success');
            readPairs();
        };

        socket.onmessage = (event) => {
            addMessage(event.data);
        };

        socket.onclose = (event) => {
            updateStatus(false, `Connection closed: ${event.reason}`);
            
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                addMessage(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`, 'info');
                setTimeout(connectWebSocket, RECONNECT_DELAY);
            } else {
                addMessage('Max reconnection attempts reached. Please refresh the page.', 'error');
            }
        };

        socket.onerror = (error) => {
            addMessage(`WebSocket error: ${error}`, 'error');
        };
    }

    // Clear log button functionality
    clearLogButton.addEventListener('click', () => {
        messageContainer.innerHTML = '';
        addMessage('Log cleared', 'info');
    });

    // Initial connection
    connectWebSocket();
});
