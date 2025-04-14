document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO connection
    const socket = io();
    
    // DOM elements
    const portSelect = document.getElementById('port-select');
    const displaySelect = document.getElementById('display-select');
    const refreshPortsBtn = document.getElementById('refresh-ports');
    const refreshDisplaysBtn = document.getElementById('refresh-displays');
    const debugDisplaysBtn = document.getElementById('debug-displays');
    const toggleMonitoringBtn = document.getElementById('toggle-monitoring');
    const connectionStatus = document.getElementById('connection-status');
    const receivedData = document.getElementById('received-data');
    const actionStatus = document.getElementById('action-status');
    const debugToggle = document.getElementById('debug-toggle');
    const clearLogBtn = document.getElementById('clear-log');
    const debugLog = document.getElementById('debug-log');
    
    // Status variables
    let isMonitoring = false;
    let debugMode = false;
    
    // Initialize
    fetchPorts();
    fetchDisplays();
    
    // Event listeners
    refreshPortsBtn.addEventListener('click', fetchPorts);
    refreshDisplaysBtn.addEventListener('click', fetchDisplays);
    debugDisplaysBtn.addEventListener('click', debugDisplays);
    toggleMonitoringBtn.addEventListener('click', toggleMonitoring);
    debugToggle.addEventListener('change', toggleDebugMode);
    clearLogBtn.addEventListener('click', clearDebugLog);
    
    // Show error message
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.color = 'black';
        errorDiv.style.padding = '10px';
        errorDiv.style.margin = '10px 0';
        errorDiv.style.backgroundColor = '#ffeeee';
        errorDiv.style.borderRadius = '4px';
        errorDiv.style.border = '1px solid #ffcccc';
        
        // Add to status panel
        const statusPanel = document.querySelector('.status-panel');
        statusPanel.appendChild(errorDiv);
        
        // Automatically remove after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
        
        // Also log to debug log
        logDebug(`Error: ${message}`);
    }
    
    // Fetch serial port list
    function fetchPorts() {
        fetch('/api/ports')
            .then(response => response.json())
            .then(data => {
                portSelect.innerHTML = '<option value="">-- Please select a serial port --</option>';
                data.forEach(port => {
                    const option = document.createElement('option');
                    option.value = port.device;
                    option.textContent = `${port.device} (${port.description})`;
                    portSelect.appendChild(option);
                });
                logDebug('Serial port list updated');
            })
            .catch(error => {
                console.error('Error fetching serial port list:', error);
                showError(`Error fetching serial port list: ${error.message}`);
            });
    }
    
    // Fetch display list
    function fetchDisplays() {
        fetch('/api/displays')
            .then(response => response.json())
            .then(data => {
                displaySelect.innerHTML = '<option value="">-- Please select a display --</option>';
                data.forEach(display => {
                    const option = document.createElement('option');
                    option.value = display.id;
                    option.textContent = display.desc;
                    displaySelect.appendChild(option);
                });
                logDebug('Display list updated');
            })
            .catch(error => {
                console.error('Error fetching display list:', error);
                showError(`Error fetching display list: ${error.message}`);
            });
    }
    
    // Toggle monitoring status
    function toggleMonitoring() {
        if (isMonitoring) {
            stopMonitoring();
        } else {
            startMonitoring();
        }
    }
    
    // Start monitoring
    function startMonitoring() {
        const port = portSelect.value;
        const displayId = displaySelect.value;
        
        if (!port) {
            showError('Please select a serial port');
            return;
        }
        
        if (!displayId) {
            showError('Please select a display to control');
            return;
        }
        
        fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                port: port,
                display_id: displayId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isMonitoring = true;
                toggleMonitoringBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Monitoring';
                toggleMonitoringBtn.classList.remove('btn-primary');
                toggleMonitoringBtn.classList.add('btn-danger');
                portSelect.disabled = true;
                displaySelect.disabled = true;
                logDebug(`Started monitoring serial port: ${port}`);
            } else {
                showError(data.message);
            }
        })
        .catch(error => {
            console.error('Error starting monitoring:', error);
            showError(`Error starting monitoring: ${error.message}`);
        });
    }
    
    // Stop monitoring
    function stopMonitoring() {
        fetch('/api/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isMonitoring = false;
                toggleMonitoringBtn.innerHTML = '<i class="fas fa-play"></i> Start Monitoring';
                toggleMonitoringBtn.classList.remove('btn-danger');
                toggleMonitoringBtn.classList.add('btn-primary');
                portSelect.disabled = false;
                displaySelect.disabled = false;
                logDebug('Stopped monitoring');
            } else {
                showError(data.message);
            }
        })
        .catch(error => {
            console.error('Error stopping monitoring:', error);
            showError(`Error stopping monitoring: ${error.message}`);
        });
    }
    
    // Toggle debug mode
    function toggleDebugMode() {
        debugMode = debugToggle.checked;
        logDebug(`Debug mode ${debugMode ? 'enabled' : 'disabled'}`);
    }
    
    // Clear debug log
    function clearDebugLog() {
        debugLog.innerHTML = '';
        logDebug('Log cleared');
    }
    
    // Log debug message
    function logDebug(message) {
        if (debugMode) {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.textContent = `[${timestamp}] ${message}`;
            debugLog.appendChild(logEntry);
            debugLog.scrollTop = debugLog.scrollHeight;
        }
    }
    
    // Socket.IO event handlers
    socket.on('connect', () => {
        logDebug('Connected to server');
    });
    
    socket.on('disconnect', () => {
        logDebug('Disconnected from server');
    });
    
    socket.on('connection', (data) => {
        connectionStatus.textContent = data.status;
        connectionStatus.style.color = data.color;
        logDebug(`Connection status: ${data.status}`);
    });
    
    socket.on('received', (data) => {
        receivedData.textContent = data.data;
        logDebug(`Received angle: ${data.data}`);
    });
    
    socket.on('action', (data) => {
        actionStatus.textContent = data.status;
        logDebug(`Action: ${data.status}`);
    });
    
    socket.on('error', (data) => {
        showError(data.message);
    });
    
    // Debug displays
    function debugDisplays() {
        fetch('/api/debug/displays')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Create a modal to display detailed information
                    const modal = document.createElement('div');
                    modal.className = 'modal';
                    modal.style.position = 'fixed';
                    modal.style.top = '0';
                    modal.style.left = '0';
                    modal.style.width = '100%';
                    modal.style.height = '100%';
                    modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
                    modal.style.display = 'flex';
                    modal.style.justifyContent = 'center';
                    modal.style.alignItems = 'center';
                    modal.style.zIndex = '1000';
                    
                    const modalContent = document.createElement('div');
                    modalContent.className = 'modal-content';
                    modalContent.style.backgroundColor = 'white';
                    modalContent.style.padding = '20px';
                    modalContent.style.borderRadius = '5px';
                    modalContent.style.maxWidth = '80%';
                    modalContent.style.maxHeight = '80%';
                    modalContent.style.overflow = 'auto';
                    
                    const closeBtn = document.createElement('button');
                    closeBtn.textContent = 'Close';
                    closeBtn.style.marginBottom = '10px';
                    closeBtn.style.padding = '5px 10px';
                    closeBtn.onclick = () => modal.remove();
                    
                    const pre = document.createElement('pre');
                    pre.style.whiteSpace = 'pre-wrap';
                    pre.style.fontFamily = 'monospace';
                    pre.textContent = `displayplacer output:\n\n${data.stdout}\n\nError output:\n${data.stderr}\n\nReturn code: ${data.returncode}`;
                    
                    modalContent.appendChild(closeBtn);
                    modalContent.appendChild(pre);
                    modal.appendChild(modalContent);
                    document.body.appendChild(modal);
                    
                    // Click background to close modal
                    modal.onclick = (e) => {
                        if (e.target === modal) {
                            modal.remove();
                        }
                    };
                } else {
                    showError(`Debug failed: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error in debug displays:', error);
                showError(`Error in debug displays: ${error.message}`);
            });
    }
}); 