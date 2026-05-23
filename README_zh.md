# 🔬 AI COA 證書解析與驗證中心 (AI COA Document Parser & Verification Hub)

一個專為化學、生物及食品實驗室設計的工業級開源桌面應用程式，用於自動解析、驗證並標準化 **分析證明書 (Certificate of Analysis, COA)** 文件。

本系統配備了**人機協同驗證中心 (Human-in-the-loop Verification Hub)**、**確定性規則引擎**、**持久性 SQLite 任務排程佇列**以及 **Google Sheets 團隊協同快取同步 (GAS)**，可自動化登錄實驗室庫存，並具備優異的可靠度與零併發鎖定（Concurrency Locking）特性。

---

## 🌟 核心特色

1. **視覺驅動提取**：基於 Gemini 多模態視覺 API，精準擷取掃描件、雙欄格式、手寫文字或多頁 PDF/JPG 文件。
2. **全面的雙欄位對照機制**：同時擷取原始文件文字，並自動轉換標準化值：
   - **廠牌 (Brand)** ➔ 對應標準製造商名稱。
   - **產品名稱 (Product Name)** ➔ 轉換為英文首字母大寫（Title Case）格式。
   - **分子量 (Molecular Weight)** ➔ 提取為標準浮點數。
   - **CAS Number (CAS Number)** ➔ 進行格式檢查並對齊。
   - **生產批號 (Batch Number)** ➔ 擷取精確原始批號。
   - **有效期限 (Expiry Date)** ➔ 統一格式化為 `YYYY/M/D`。
   - **包裝容量 (Amount)** ➔ 解析容量數值與標準化單位（如 g, mL）。
   - **純度/含量 (Purity)** ➔ 清除雜質符號，格式化為 `[數值] %`。
   - **儲存條件 (Storage Conditions)** ➔ 自動模糊映射對應至 `-20°C`、`4°C` 或 `RT` (室溫)。
3. **互動式文件預覽**：支援滑鼠左鍵拖曳平移 (Drag-to-Pan) 與滑鼠滾輪縮放 (Scroll-to-Zoom)，讓人工核對 PDF 與圖片時更加直觀高效。
4. **Google Sheets 雲端協同快取 (GAS)**：透過 Google Apps Script 將資料上傳至雲端試算表。「一人解析，全隊共享快取」，大幅降低 Gemini API 的呼叫次數與使用成本。
5. **純鍵盤極速驗證**：支援快捷鍵（`Ctrl+Enter` 儲存並跳至下一筆），核對效率提升 200% 以上。
6. **自訂匯出配置**：在設定面板中，可任意拖動調整欄位順序、開啟/關閉欄位匯出，甚至**直接修改匯出 Excel 的表頭名稱**。
7. **專業格式 Excel 匯出**：自動計算列寬自適應、凍結首列、啟用篩選器，並套用商用深藍質感配色。
8. **憑證安全加密**：整合 Windows 憑證管理員 (Credential Manager) 加密儲存 API Key，金鑰絕不以明文存存放在設定檔中。

---

## 📂 專案架構

```text
COAhtml/
├── app/                   # 後端 Python 引擎
│   ├── core/              # 前處理器、分類器、SQLite 佇列、規則驗證引擎
│   ├── providers/         # Vision API 轉接器 (Gemini 驅動)
│   ├── exporters/         # openpyxl 質感 Excel 匯出模組
│   ├── utils/             # 日誌、憑證安全儲存、GAS 雲端客戶端
│   └── main.py            # Pywebview 視窗啟動點
├── frontend/              # Webview 前端介面 (HTML5 / Vanilla CSS / Vanilla JS)
│   ├── index.html         # 儀表板版面配置
│   ├── style.css          # 精美毛玻璃深色/淺色主題 CSS
│   ├── app.js             # 鍵盤事件、平移縮放及 JS-Python IPC 橋接
│   └── tutorial.html      # 內建操作說明手冊
├── prompts/               # AI 提示詞範本
├── dataset/               # 測試用 COA 數據集 (回歸測試)
├── requirements.txt       # Python 依賴套件清單
└── README.md              # 專案說明書 (英文版)
```

---

## 🚀 快速上手

### 系統需求
- Python 3.10 或更高版本
- Google 帳號（用於申請 Gemini API 金鑰及部署 Google 試算表）

### 安裝步驟
1. 複製 GitHub 儲存庫：
   ```bash
   git clone https://github.com/yourusername/coa-parser.git
   cd coa-parser
   ```

2. 安裝必要的 Python 套件：
   ```bash
   pip install -r requirements.txt
   ```

### 執行程式
雙擊專案目錄下的 `run.bat`，程式會自動建立虛擬環境、下載依賴，並啟動桌面應用程式。
或者手動執行：
```bash
python -m app.main
```

---

## 📖 雲端整合設定

關於詳細的部署說明，請點選軟體側邊欄的 **「操作說明手冊」** 按鈕，或直接在本機開啟 `frontend/tutorial.html`。

1. **Gemini API 金鑰**：請前往 [Google AI Studio](https://aistudio.google.com/) 申請免費的金鑰，並在程式設定中貼上儲存。
2. **Google Sheet 協同快取**：複製 `frontend/tutorial.html` 內附的 Google Apps Script 程式碼，貼入您 Google 試算表的指令碼編輯器中，並部署為「網頁應用程式 (Web App)」即可獲取串接網址。

---

## 🛠️ 打包安裝檔與編譯

若要將專案打包為沒有主控台視窗的獨立 `.exe` 執行檔（需安裝 `pyinstaller`）：
```bash
pip install pyinstaller
pyinstaller --noconsole --name="COA_Parser" --add-data "frontend;frontend" app/main.py
```
您也可以執行專案根目錄下的 `build.bat` 自動完成 PyInstaller 編譯，並參照 `installer_setup.iss` 透過 Inno Setup 編譯成 Windows Setup 安裝精靈。

---

## ⚖️ 授權條款與開發者
* **開發者**：etrnya
* **授權協議**：本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案。

