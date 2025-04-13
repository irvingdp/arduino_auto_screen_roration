# 螢幕自動旋轉控制器 (Screen Auto-Rotation Controller)

這是一個基於 Flask 的網頁應用程式，用於自動控制螢幕旋轉。它通過串口與 Arduino 設備通信，接收角度數據，並使用 `displayplacer` 命令來旋轉指定的顯示器。

## 功能特點

- 網頁界面，易於使用
- 自動檢測可用的串口和顯示器
- 實時顯示連接狀態和接收到的數據
- 除錯模式，方便排查問題
- 響應式設計，適配不同設備

## 系統需求

- Python 3.6+
- Flask 和相關依賴
- `displayplacer` 命令行工具 (用於控制顯示器)
- 支援的作業系統: macOS (需要 `displayplacer`)

## 安裝

1. 克隆或下載此專案到本地

2. 安裝所需的 Python 依賴:

```bash
pip install -r requirements.txt
```

3. 安裝 `displayplacer` (如果尚未安裝):

```bash
brew install displayplacer
```

## 使用方法

### 啟動應用程式

1. 在終端機中導航到專案目錄

2. 運行 Flask 應用程式:

```bash
python web_screen_rotator.py
```

3. 打開瀏覽器，訪問:

```
http://localhost:8098
```

### 使用界面

1. 從下拉選單中選擇 Arduino 串口
2. 從下拉選單中選擇要控制的顯示器
3. 點擊「開始監聽」按鈕開始監控串口
4. 當 Arduino 發送角度數據 (0, 90, 180, 270) 時，應用程式會自動旋轉選定的顯示器
5. 點擊「停止監聽」按鈕停止監控

## 除錯指南

### 啟用除錯模式

1. 在網頁界面中，找到「除錯日誌」面板
2. 切換「除錯模式」開關以啟用除錯功能
3. 除錯日誌會顯示詳細的操作和錯誤信息

### 常見問題排查

#### 找不到串口

- 確保 Arduino 已正確連接到電腦
- 點擊「重新整理」按鈕更新串口列表
- 檢查 Arduino 驅動程式是否正確安裝

#### 找不到顯示器

- 確保 `displayplacer` 已正確安裝
- 點擊「重新整理」按鈕更新顯示器列表
- 在終端機中運行 `displayplacer list` 檢查是否能列出顯示器

#### 無法旋轉顯示器

- 檢查 `displayplacer` 是否有足夠的權限 (macOS 可能需要授予輔助功能權限)
- 查看除錯日誌中的錯誤信息
- 嘗試在終端機中手動運行 `displayplacer` 命令

#### 連接問題

- 檢查 Arduino 是否正確發送數據
- 確認串口波特率設置為 9600
- 檢查串口連接是否穩定

### 進階除錯

#### 查看 Flask 日誌

Flask 應用程式在運行時會在終端機中輸出日誌信息，包括請求和錯誤。這些信息對於排查問題非常有用。

#### 檢查 WebSocket 連接

如果實時更新不工作，可能是 WebSocket 連接問題。打開瀏覽器的開發者工具，查看控制台是否有相關錯誤。

#### 測試串口通信

可以使用串口監視工具 (如 `screen` 或 `minicom`) 來測試與 Arduino 的通信:

```bash
screen /dev/tty.usbmodem* 9600
```

## 專案結構

```
auto_screen_detection/
├── web_screen_rotator.py  # Flask 應用程式主文件
├── requirements.txt       # Python 依賴
├── templates/             # HTML 模板
│   └── index.html        # 主頁面
└── static/               # 靜態文件
    ├── css/              # CSS 樣式
    │   └── style.css     # 主樣式表
    └── js/               # JavaScript 文件
        └── app.js        # 前端邏輯
```

## 授權

此專案採用 MIT 授權條款。詳見 LICENSE 文件。

## 貢獻

歡迎提交問題報告和改進建議！ 