# stock_analysis
LLM股價資訊平台

# 股票技術分析平台

## 簡介
Flask 建構之股票技術分析平台，允許使用者查詢的歷史股價並生成技術指標和買賣訊號，同時使用 GPT 分析以提供投資建議。

## 功能
1. 提供多種股票技術指標：MA、KD、MACD、RSI。
2. 計算年化波動率和區間報酬率。
3. 提供過去30天的收盤價和成交量圖表。
4. 整合 GPT 分析，生成投資建議。

## 環境需求
- Python 3.10
- Windows x64 環境

## 安裝步驟

### 1. clone專案
```bash
$ git clone <repository_url>
$ cd <project_directory>
```

### 2. 安裝相依套件
#### 方法 1：直接使用 requirements.txt
```bash
$ pip install -r requirements.txt
```

#### 方法 2：安裝 TA-Lib
由於 TA-Lib 的特殊依賴，請另外下載並安裝：
- 將 `TA_Lib-0.4.24-cp310-cp310-win_amd64.whl` 放入專案目錄。
- 安裝該檔案：
```bash
$ pip install TA_Lib-0.4.24-cp310-cp310-win_amd64.whl
```

### 3. 設置環境變數
創建一個 `.env` 檔案並填入以下內容：
```env
OPENAI_API_KEY=OpenAI金鑰
```

### 4. 啟動伺服器
```bash
$ python app.py
```
伺服器啟動後，打開瀏覽器並訪問 `http://127.0.0.1:5000/`。

## 文件結構
```
|-- app.py                 # 後端程式
|-- requirements.txt       # Python 相依套件
|-- templates/
|   |-- index.html         # 前端 HTML
|-- static/
    |-- css/
    |   |-- style.css      # 前端css
    |-- js/
        |-- app.js         # 前端js
```
## 使用方法
1. 在首頁輸入股票代碼（例如：AAPL, TSLA, 2330.TW）。
2. 可選擇起始與結束日期，否則預設查詢過去180天。
3. 點擊查詢後，查看技術分析結果及 GPT 投資建議。

## 注意事項
1. 請確保 `.env` 文件中的 OpenAI API Key 

## 貢獻
歡迎提交 Issue 和 Pull Request，共同優化專案。

## 授權
MIT
