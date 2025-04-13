document.addEventListener('DOMContentLoaded', function() {
    // 初始化 Socket.IO 連接
    const socket = io();
    
    // DOM 元素
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
    
    // 狀態變數
    let isMonitoring = false;
    let debugMode = false;
    
    // 初始化
    fetchPorts();
    fetchDisplays();
    
    // 事件監聽器
    refreshPortsBtn.addEventListener('click', fetchPorts);
    refreshDisplaysBtn.addEventListener('click', fetchDisplays);
    debugDisplaysBtn.addEventListener('click', debugDisplays);
    toggleMonitoringBtn.addEventListener('click', toggleMonitoring);
    debugToggle.addEventListener('change', toggleDebugMode);
    clearLogBtn.addEventListener('click', clearDebugLog);
    
    // 顯示錯誤訊息
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.color = 'red';
        errorDiv.style.padding = '10px';
        errorDiv.style.margin = '10px 0';
        errorDiv.style.backgroundColor = '#ffeeee';
        errorDiv.style.borderRadius = '4px';
        errorDiv.style.border = '1px solid #ffcccc';
        
        // 添加到狀態面板
        const statusPanel = document.querySelector('.status-panel');
        statusPanel.appendChild(errorDiv);
        
        // 5秒後自動移除
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
        
        // 同時記錄到除錯日誌
        logDebug(`錯誤: ${message}`);
    }
    
    // 獲取序列埠列表
    function fetchPorts() {
        fetch('/api/ports')
            .then(response => response.json())
            .then(data => {
                portSelect.innerHTML = '<option value="">-- 請選擇序列埠 --</option>';
                data.forEach(port => {
                    const option = document.createElement('option');
                    option.value = port.device;
                    option.textContent = `${port.device} (${port.description})`;
                    portSelect.appendChild(option);
                });
                logDebug('已更新序列埠列表');
            })
            .catch(error => {
                console.error('獲取序列埠列表時出錯:', error);
                showError(`獲取序列埠列表時出錯: ${error.message}`);
            });
    }
    
    // 獲取顯示器列表
    function fetchDisplays() {
        fetch('/api/displays')
            .then(response => response.json())
            .then(data => {
                displaySelect.innerHTML = '<option value="">-- 請選擇顯示器 --</option>';
                data.forEach(display => {
                    const option = document.createElement('option');
                    option.value = display.id;
                    option.textContent = display.desc;
                    displaySelect.appendChild(option);
                });
                logDebug('已更新顯示器列表');
            })
            .catch(error => {
                console.error('獲取顯示器列表時出錯:', error);
                showError(`獲取顯示器列表時出錯: ${error.message}`);
            });
    }
    
    // 切換監聽狀態
    function toggleMonitoring() {
        if (isMonitoring) {
            stopMonitoring();
        } else {
            startMonitoring();
        }
    }
    
    // 開始監聽
    function startMonitoring() {
        const port = portSelect.value;
        const displayId = displaySelect.value;
        
        if (!port) {
            showError('請選擇一個序列埠');
            return;
        }
        
        if (!displayId) {
            showError('請選擇一個要控制的顯示器');
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
                toggleMonitoringBtn.innerHTML = '<i class="fas fa-stop"></i> 停止監聽';
                toggleMonitoringBtn.classList.remove('btn-primary');
                toggleMonitoringBtn.classList.add('btn-danger');
                portSelect.disabled = true;
                displaySelect.disabled = true;
                logDebug(`開始監聽序列埠: ${port}`);
            } else {
                showError(data.message);
            }
        })
        .catch(error => {
            console.error('啟動監聽時出錯:', error);
            showError(`啟動監聽時出錯: ${error.message}`);
        });
    }
    
    // 停止監聽
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
                toggleMonitoringBtn.innerHTML = '<i class="fas fa-play"></i> 開始監聽';
                toggleMonitoringBtn.classList.remove('btn-danger');
                toggleMonitoringBtn.classList.add('btn-primary');
                portSelect.disabled = false;
                displaySelect.disabled = false;
                logDebug('停止監聽');
            } else {
                showError(data.message);
            }
        })
        .catch(error => {
            console.error('停止監聽時出錯:', error);
            showError(`停止監聽時出錯: ${error.message}`);
        });
    }
    
    // 切換除錯模式
    function toggleDebugMode() {
        debugMode = debugToggle.checked;
        logDebug(`除錯模式已${debugMode ? '啟用' : '停用'}`);
    }
    
    // 清除除錯日誌
    function clearDebugLog() {
        debugLog.innerHTML = '';
        logDebug('日誌已清除');
    }
    
    // 記錄除錯訊息
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
    
    // Socket.IO 事件處理
    socket.on('connect', () => {
        logDebug('已連接到伺服器');
    });
    
    socket.on('disconnect', () => {
        logDebug('與伺服器斷開連接');
    });
    
    socket.on('connection', (data) => {
        connectionStatus.textContent = data.status;
        connectionStatus.style.color = data.color;
        logDebug(`連線狀態: ${data.status}`);
    });
    
    socket.on('received', (data) => {
        receivedData.textContent = data.data;
        logDebug(`收到角度: ${data.data}`);
    });
    
    socket.on('action', (data) => {
        actionStatus.textContent = data.status;
        logDebug(`操作: ${data.status}`);
    });
    
    socket.on('error', (data) => {
        showError(data.message);
    });
    
    // 除錯顯示器
    function debugDisplays() {
        fetch('/api/debug/displays')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 創建一個模態框來顯示詳細信息
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
                    closeBtn.textContent = '關閉';
                    closeBtn.style.marginBottom = '10px';
                    closeBtn.style.padding = '5px 10px';
                    closeBtn.onclick = () => modal.remove();
                    
                    const pre = document.createElement('pre');
                    pre.style.whiteSpace = 'pre-wrap';
                    pre.style.fontFamily = 'monospace';
                    pre.textContent = `displayplacer 輸出:\n\n${data.stdout}\n\n錯誤輸出:\n${data.stderr}\n\n返回碼: ${data.returncode}`;
                    
                    modalContent.appendChild(closeBtn);
                    modalContent.appendChild(pre);
                    modal.appendChild(modalContent);
                    document.body.appendChild(modal);
                    
                    // 點擊背景關閉模態框
                    modal.onclick = (e) => {
                        if (e.target === modal) {
                            modal.remove();
                        }
                    };
                } else {
                    showError(`除錯失敗: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('除錯顯示器時出錯:', error);
                showError(`除錯顯示器時出錯: ${error.message}`);
            });
    }
}); 