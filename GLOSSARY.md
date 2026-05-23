# AI COA 文件自動建檔系統 - 術語表與架構規範 (GLOSSARY & Architectural Standards)

Version: v1.7  
Date: 2026-05-23  

---

## 1. 術語表 (Glossary)

| 術語 (Term) | 縮寫/別名 | 定義與在專案中的角色 |
|---|---|---|
| **Certificate of Analysis** | COA | **分析證明書**。化學、食品或醫藥實驗室用以證明產品純度、成分、批號及效期的原廠規格文件。本系統的處理對象。 |
| **Intelligent Document Processing** | IDP | **智慧文件處理**。結合 AI 技術（如大語言模型、電腦視覺）對非結構化文件（PDF/圖片）進行分類、擷取與結構化輸出的技術。 |
| **Provider Architecture** | 供應商架構 | **多引擎適配器模式**。定義統一的 `VisionProvider` 介面，使系統能靈活插拔切換 AI 引擎（如 Gemini, OpenAI, Claude, Azure 或本地離線 OCR），避免單一廠商鎖定 (Vendor Lock-in)。 |
| **Document Classification** | 文檔分類器 | **前置分類引擎**。在提取資料前，先判斷文件是否為 COA。若混入 SDS、發票、出貨單或未知文件，自動分類並分流，防止 AI 亂套用 Schema 造成資料污染。 |
| **Rule-based Validation** | 欄位規則驗證 | **規則校準引擎**。利用預設或自訂規則對 AI 提取的數值進行二次驗證。例如：純度必須在 `0% ~ 100%`、有效期限不可大於「今天 + 20年」、批號格式需符合特定 Regex 等。 |
| **Ground Truth Dataset**| 黃金資料集 | **基準測試集**。存放於 `dataset/` 底下的一組標準 COA 圖片/PDF 與其對應的真實 JSON 結果 (`expected.json`)，用於進行 AI 的自動化迴歸測試 (Regression Testing)，防止 Prompt 漂移 (Prompt Drift)。 |
| **Persistent Queue** | 持續性佇列 | **防中斷任務隊列**。使用本機 SQLite (`queue.db`) 記錄佇列狀態（`Pending` / `Processing` / `Completed` / `Failed`），若遇當機或關機，重啟後可從中斷點自動續跑。 |
| **Traceability & Audit** | 稽核溯源性 | 符合 ISO17025/GMP 規範的安全機制。AI 擷取欄位時需回傳該資訊在文件中的 **原始上下文** 與 **來源頁碼**（未來可擴充為 Bounding Box 座標），以供合規稽核。 |
| **Smart Review Queue** | 智慧審核佇列 | **校對優先級排序**。系統根據「欄位風險度（如 Expiry Date, Purity）」與「AI 信心評分」進行權重加權，自動將高風險或高機率出錯的檔案排在審核佇列最前列。 |
| **Prompt Versioning** | 提示詞版本控制| 將 System Prompts 獨立於代碼之外，以文字檔形式（如 `prompts/v1/`）進行版控，結合黃金資料集，定量評估 Prompt 更新後的提取率變化。 |
| **Fitz Pixmap Stream** | 記憶體流處理 | 在 PDF 轉圖片與預處理時，將轉出的字節流限制在記憶體緩衝區（如 `BytesIO`）或單一暫存檔中，每執行完一頁即釋放資源，預防批次處理導致的 Out of Memory (OOM) 崩潰。 |
| **Dual-Field Extraction** | 雙軌欄位擷取 | **原始值與標準值對應機制**。針對容易因廠牌不同而寫法相異的欄位（產品名稱、有效期限、純度、保存條件），系統同時保留並輸出「COA 上的原始文字」以及「標準化後的統一格式（如 首字大寫其餘小寫、YYYY/MM/DD、-20°C/4°C/RT 等）」。 |
| **Standardization Rules Configurator** | 標準化規則編輯器 | **規則配置介面**。提供 UI 設定頁面，讓使用者自訂標準化對應規則（例如：設定哪些關鍵字對應到 `4°C`，設定日期輸出是要 `YYYY/M/D` 還是 `YYYY-MM-DD` 等），無須修改程式代碼。 |
| **Custom Column Order** | 自訂欄位排序 | **導出對接機制**。使用者可在匯出前，於 UI 介面藉由拖曳或下拉選單調整 Excel/CSV 輸出的欄位順序與中英文欄位名稱，以便直接複製貼上對接現行的實驗室登記表。 |
| **COA Family Suite** | COA 家族系列軟體 | 本專案未來擴充規劃的智慧化實驗室軟體家族，包含：<br>1. **COA Parser**：本專案（核心文件結構化擷取與校對）。<br>2. **COA Organizer**：依據擷取之元數據自動將檔名混亂之 PDF 重新命名並分類歸檔（如：`標準品_批號_效期.pdf`）。<br>3. **COA Stocker (入庫助手)**：結合 QR 碼與本機資料庫進行實體藥瓶與 COA 電子檔之入庫定位管理。<br>4. **COA Formulator (配製記錄器)**：自動產生「一標/二標」配製記錄表，自動依據 COA 擷取之純度與取樣重量計算目標配製濃度。 |
| **Google Sheets & GAS Sync** | Google 表格與 GAS 同步 | **雲端協同機制**。使用者可將 Google Apps Script (GAS) 部署為網頁應用程式 (Web App) 作為 API 橋樑。軟體可透過此 API 將核對完的 COA 資料即時寫入雲端 Google Sheet，同組同仁能共用同一個雲端 Sheet 快取，解決 SQLite 區域網路鎖定與權限問題。 |
| **Keyboard-Driven Review** | 鍵盤極速校對 | **高效率審核操作**。在 UI 雙欄對比中，使用者可透過 `Enter` 鍵或 `方向鍵(下)` 直接保存當前資料，並「聯動切換」至下一個檔案的 PDF 與表單，達到無滑鼠純鍵盤操作。 |

---

## 2. 系統架構規範 (Architectural Standards)

### 2.1 目錄結構規範 (Directory Layout)
系統依循以下模組化插件設計，所有與 AI 平台相關之調用皆抽象化：

```text
COAhtml/
├── GLOSSARY.md            # 本術語表與架構規範
├── RPD.md                 # 專案需求文件 (Requirements Product Document)
├── requirements.txt       # Python 依賴包定義
├── config.json            # 本機一般設定檔 (定義動態 Schema、欄位順序、GAS Web App URL)
├── .gitignore             # 排除敏感金鑰、資料庫與暫存圖片，為 GitHub 開源做準備
├── README.md              # 專案開源說明文件
│
├── prompts/               # 提示詞版本庫
│   ├── current/           # 當前使用中的提示詞模板
│   └── v1_0/              # 歷史版本提示詞
│
├── dataset/               # 迴歸測試集 (Ground Truth)
│   ├── expected.json      # 標準答案對照表
│   └── pdf/               # 測試用標準 COA 檔案
│
├── app/                   # 後端 Python 核心
│   ├── __init__.py
│   ├── main.py            # 程式啟動與 GUI 橋接
│   ├── bridge.py          # 前後端非同步通訊 (IPC Handlers)
│   ├── pipeline.py        # 核心 Pipeline 控制
│   │
│   ├── providers/         # AI/OCR 引擎適配器
│   │   ├── base.py
│   │   └── gemini.py      # Gemini Vision 適配器
│   │
│   ├── core/
│   │   ├── classifier.py  # 文檔分類模組
│   │   ├── preprocessor.py# 圖片預處理
│   │   ├── validator.py   # 規則驗證與標準化引擎
│   │   ├── cache.py       # 本地快取與雲端同步調用介面
│   │   └── queue_db.py    # SQLite 持續性任務隊列 (Persistent Queue)
│   │
│   ├── exporters/         # 匯出層
│   │   ├── base.py
│   │   └── excel.py       # 進階 Excel 格式化
│   │
│   └── utils/
│       ├── secure_store.py# 金鑰安全儲存
│       ├── logger.py      # 滾動日誌
│       ├── gas_client.py  # Google Apps Script 雲端同步客端 (GET/POST 實作)
│       └── metrics.py     # 指標收集系統
│
└── frontend/              # 前端網頁介面
    ├── index.html         # 主介面
    ├── style.css          # UI 樣式
    └── app.js             # 狀態控制與 Bridge 綁定 (鍵盤快捷鍵事件監聽)
```

### 2.2 核心架構原則 (Architecture Principles)
1. **供應商無關 (Provider Agnostic)**：後端核心邏輯與 AI 引擎抽象化分離。
2. **容錯與續跑 (Fail-Safe & Recoverable)**：所有任務持久化儲存，具備錯誤防護與自動續傳。
3. **人機協作 (Human-in-the-Loop)**：AI 負責結構化提取，人類負責終審。
4. **雙軌值輸出 (Dual-Field Output)**：同時保留「原始文字」與「標準值」。
5. **可配置標準化 (Configurable Standardization)**：標準化對應規則支援使用者自訂。
6. **可自訂輸出 (User-Defined Export)**：支援自訂欄位排序與別名更名。
7. **Google 雲端同步 (Google Sheet & GAS Cloud Sync)**：
   * 藉由 GAS Web App 將資料寫入雲端試算表，解決傳統 SQLite 在區域網路磁碟多人同時寫入時容易發生的 **資料庫鎖定 (Database Locked)** 問題。
   * 同組同事可共享同一個 Google Sheet 快取，達到「一人解析，全組共用」並能即時在瀏覽器上共同查看建檔資料。
8. **鍵盤快速鍵導航 (Keyboard-Shortcut Friendly)**：UI 核對面設計高效率鍵盤事件監聽，支援無滑鼠操作。
