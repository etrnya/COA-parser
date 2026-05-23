# AI COA 文件自動建檔系統 (COA Parser) - RPD

Version: v1.7  
Author: 彥廷  
Type: Desktop AI Document Processing Tool (Open Source Friendly & Enterprise Grade)

---

# 1. 專案願景 (Vision)

建立一套可於本機端運作的開源 **AI 文件自動化處理管線系統 (IDP Platform)**。

使用者可填入自備的 Gemini API Key，選擇包含多頁 PDF 或圖片的資料夾。系統將利用 **多供應商視覺架構 (Vision Provider Architecture)** 進行自動文檔分類、圖片預處理、資訊擷取、與規則驗證。為解決 AI 幻覺與錯誤率，系統內置了**持續性佇列 (Persistent Queue)、SHA256 快取、動態欄位驗證與標準化引擎、黃金資料集基準測試 (Ground Truth) 以及智慧優先級人機校正佇列**。最終，使用者能利用極速鍵盤捷徑完成雙欄校對，自訂欄位排序與更名，並將校對後的資料輸出為 Excel / CSV。

為支援團隊協作，系統具備 **Google Sheets & GAS (Google Apps Script) 雲端同步機制**。本軟體作為 **「COA 實驗室智慧管理家族軟體」** 的第一塊拼圖，將為後續的自動命名歸檔 (COA Organizer)、實體藥瓶入庫管理 (COA Stocker) 及標準液配製記錄 (COA Formulator) 奠定核心的資料與架構基礎。

---

# 2. 背景問題與痛點 (Pain Points)

- **AI 幻覺與出錯代價高**：實驗室資料若輸入錯誤純度或批號，可能導致後續實驗失敗或法規合規性漏洞。AI 必須與人類校對無縫結合。
- **多頁與文件混雜**：資料夾內常混有非 COA 文件（如 SDS、發票、出貨單）。若強行擷取，AI 將產生大量無效或誤導資料。
- **缺乏測試依據 (Prompt Drift)**：API 更新或 Prompt 調整後，缺乏科學量化方法評估成功率是否倒退 (Regression)。
- **斷電當機風險**：批次處理 200+ 份檔案時若遇軟體崩潰或網路瞬斷，在沒有持續性佇列的情況下，必須整批重來。
- **現行表格對接繁瑣**：各實驗室的 Excel 登記表欄位順序、名稱各異。若系統輸出格式固定，使用者還需要手動在 Excel 中剪下、貼上並調整欄位順序，無法直接複製貼上使用。
- **審核介面效率低**：若每確認一個檔案，都需要用滑鼠點擊「確認」、再點擊「下一個」，當面對 200 份文件時，頻繁的滑鼠點擊會使效率大打折扣。
- **同組同事重複工作 (資料孤島)**：同一個實驗小組的同事常需要分析相同批號的 COA。若每人都在各自的電腦上儲存快取，會導致重複呼叫 API，浪費 Token 費用。
- **局網 SQLite 共用鎖定痛點**：若使用區域網路共享資料夾 (NAS/Z 槽) 共用 SQLite 檔案，當多人同時寫入時，極易觸發 SQLite 的 **`database is locked`** 衝突，導致寫入失敗或資料損毀。

---

# 3. 專案核心設計原則 (Architecture Principles)

- **Provider Agnostic (平台無關)**：底層 AI 引擎可動態切換，不鎖死於特定雲端服務。
- **Fail-Safe & Recoverable (安全失敗與續跑)**：任務持久化儲存，具備錯誤防護與自動續傳。
- **Human-in-the-Loop (人機協作)**：AI 負責結構化提取，人類負責終審。所有數據在寫入最終報表前，必須通過前端校對佇列的確認狀態。
- **Traceable (可追溯性)**：保留每個擷取欄位的來源頁數與原始上下文，滿足實驗室稽核需求。
- **Cache First (快取優先)**：基於 SHA256 檔案雜湊，避免重複運算已處理過的文件，節省費用。
- **Dual-Field Output (原始與標準值並存)**：對重要欄位同時保留「原始文字」與「標準化後的值」，兼顧文件真實性與資料易用性。
- **Alignment Friendly (對接友善)**：支援自訂欄位排序與輸出欄位選取，方便直接複製貼上至實驗室現行表格。
- **Google Sheets Cloud Sync (雲端試算表同步)**：使用 Google Sheets 作為多用戶共享的雲端資料庫，避免本地資料庫寫入衝突，且同事可用瀏覽器直接查閱最新庫存。
- **Keyboard-First Interaction (鍵盤優先導航)**：專為高強度核對設計的無滑鼠快捷鍵流，提升 200% 的人工審查效率。

---

# 4. 系統架構：管道化設計 (Pipeline Architecture)

系統處理每個檔案的資料流，必須遵循以下 Pipeline：

```text
[檔案輸入]
   │
   ▼
[1. 預處理 Preprocess]
   ├─ 計算檔案二進位 SHA256 值
   ├─ 比對本地與 Google Sheet 雲端快取。若命中，載入已核對答案，直接跳至 [7. 輸出]
   └─ 使用 PyMuPDF 轉圖並進行 Resize (最大寬度 1200px)、灰階化與 JPEG 壓縮
   │
   ▼
[2. 文件分類 Classifier]
   └─ 辨識 DocType。非 COA 檔案則分流或警告
   │
   ▼
[3. 視覺理解 Vision Provider]
   └─ 調用當前啟用之 Vision 適配器 (如 Gemini 1.5/2.0 Flash) 擷取資料與信心度
   │
   ▼
[4. 規則驗證與標準化 Validation & Standardization]
   ├─ 載入 `config.json` 中的標準化規則 (大小寫轉換、日期與溫度對照規則)
   ├─ 雙軌化欄位處理：保存原始文字，並計算標準化格式
   └─ 執行 Range Check、Regex 匹配。若失敗，標記為「Review Needed」並寫入原因
   │
   ▼
[5. 持久化任務佇列 Persistent Queue]
   └─ 狀態寫入 SQLite (`queue.db`)，標記處理狀態與追溯資訊
   │
   ▼
[6. 智慧審核佇列 Smart Review Queue]
   ├─ UI 雙欄對比，左右同步切換，並依風險高低排序
   └─ 使用者利用鍵盤捷徑 (Enter / 方向鍵下) 進行秒級核對，並「聯動切換」至下一筆
   │
   ▼
[7. 進階匯出與雲端同步 Export & Cloud Sync]
   ├─ 將核對完的資料非同步寫入 (POST) 雲端 Google Sheet，實現團隊資料同步
   └─ 依據 UI 欄位順序設定，Pandas 排序輸出包含顏色標記、凍結視窗的 Excel 與 CSV
```

---

# 5. 詳細功能規格 (System Specifications)

## 5.1 雙軌欄位與標準化規則定義 (Dual-Field & Standardization)
後端與 AI 協同工作的欄位定義如下：

| 欄位 ID | 輸出欄位名稱 | 類型 | 說明 / 標準化邏輯 | 範例 |
|---|---|---|---|---|
| `product_raw` | Product Name (Original) | 原始值 | COA 上的原始標準品名稱。 | `SULFABENZAMIDE` |
| `product_std` | Product Name (Standardized)| 標準值 | 統一轉換為 **Title Case**（首字大寫，其餘小寫）。 | **`Sulfabenzamide`** |
| `batch_no` | Batch No | 原始值 | 批號。 | `A12345` |
| `storage_raw` | Storage Condition (Original) | 原始值 | COA 上原始標示的儲存條件文字。 | `2-8°C, Avoid light exposure...` |
| `storage_std` | Storage Condition (Standardized)| 標準值 | 根據配置規則判定並歸類為下列三者之一：<br>1. **`-20°C`** (冷凍)<br>2. **`4°C`** (冷藏)<br>3. **`RT`** (室溫) | **`4°C`** |
| `expiry_raw` | Expiry Date (Original) | 原始值 | COA 上原始標示的有效期限文字。 | `August 22, 2027` |
| `expiry_std` | Expiry Date (Standardized) | 標準值 | 將各式日期改寫並標準化為 **`YYYY/M/D`** 格式。 | **`2027/8/22`** |
| `purity_raw` | Purity (Original) | 原始值 | COA 上原始標示的純度文字。 | `98.0 % (g/g)` |
| `purity_std` | Purity (Standardized) | 標準值 | 清理多餘的文字與空格，標準化改寫為 **`[數值] %`** 格式。 | **`98.0 %`** |

## 5.2 標準化規則與欄位排序配置 UI (Configurator UI)
- **標準化規則編輯面板**：
  - 提供設定區，讓使用者設定：
    * **日期格式**：可選擇下拉選單（如 `YYYY/M/D`、`YYYY-MM-DD` 等）定義標準化輸出格式。
    * **儲存溫度映射對照**：自訂 `4°C`、`-20°C`、`RT` 的關鍵字映射。
    * **名稱轉換格式**：可選 Title Case、UPPERCASE 或 lowercase。
  - 設定內容寫入本機 `config.json`，後端 validator 自動載入套用。
- **欄位排序與開關面板**：
  - 使用者能上/下拖曳調整欄位順序，並能勾選是否啟用，這些設定也將存入 `config.json` 用於匯出排序。

## 5.3 智慧人工核對與極速切換 (Smart Review & Fast Switch)
- **雙欄聯動對照**：
  - UI 左側為 COA 原始檔案預覽區（支援 PDF / JPG），右側為 AI 擷取欄位輸入框。
  - 當切換到新檔案時，**左側的預覽與右側的輸入框必須「同步重新載入」**。
- **無滑鼠極速切換捷徑**：
  - 使用者修改完右側的輸入框後，可使用鍵盤操作：
    - **`Enter` 鍵** (在輸入框按 Enter) 或 **`方向鍵(下) (Down Arrow)`** (或點擊右下角的「下一筆 / Next」按鈕)。
    - **觸發動作**：系統自動**儲存當前修改後的數值**、將當前檔案的狀態改為 `Completed`，並**瞬間切換並加載下一個待核對檔案**的原始文件與輸入框。
    - **`方向鍵(上) (Up Arrow)`** 則可返回上一個檔案。

## 5.4 Google Sheets & GAS 雲端同步機制 (Google Sheets & GAS Sync)
為解決區域網路磁碟多人同時寫入 SQLite 導致的資料庫鎖定問題，本系統引入 Google 雲端試算表同步：
- **Google Apps Script (GAS) 部署**：
  - 專案內置提供一段 GAS 程式碼。使用者在自己的 Google Sheet 中開啟 Apps Script，將此程式碼貼上並部署為「網頁應用程式 (Web App)」，取得一串 GAS Web App URL。
- **API 橋接設定**：
  - 使用者在軟體的設定頁面填入該 GAS Web App URL。
- **雲端快取共享 (GET)**：
  - 當處理新 COA 時，軟體會先以該檔案的 SHA256 雜湊向 GAS Web App 發送請求。如果 Google Sheet 中已經有同組同仁核對過該檔案的紀錄，軟體會直接拉回該數據，**標記為「雲端快取載入」，免除重複呼叫 Gemini API，省下 Token 費用**。
- **即時入庫儲存 (POST)**：
  - 當使用者在 GUI 按下確認校對後，軟體會自動非同步向 GAS 發送 POST 請求，將欄位資料追加 (Append) 到雲端的 Google Sheet 中。
  - 這樣同組的所有同仁都能透過網頁瀏覽器，在同一張 Google Sheet 上共同查閱、篩選最新的 COA 庫存。

## 5.5 多供應商適配架構與文檔分類
- 定義統一介面 `VisionProvider`。MVP 實作 `GeminiProvider` 並留出 `OpenAIProvider` 與 `LocalOCRProvider` 的適配介面。
- 視覺辨識判斷檔案是否為 COA。非 COA 檔案標記為 `Invalid Document` 並自動跳過。

## 5.6 持久化任務佇列 (Persistent Queue)
- 使用本地 SQLite 資料庫檔案 `queue.db` 保存每個處理檔案的狀態，重啟後自動讀取隊列續跑未完成項目。

## 5.7 黃金資料集基準測試 (Ground Truth & Regression Testing)
- 在軟體根目錄建立 `dataset/` 目錄，提供 `python run_benchmark.py` 工具，計算提取精確率與召回率。

---

# 6. 系統設定與非同步架構

- **金鑰安全 (Credential Management)**：優先儲存於作業系統內建的憑證管理器中。
- **開源安全備置 (Open Source Readiness)**：提供 `.gitignore` 與中英文 `README.md`。
- **非同步與執行緒安全 (Asyncio Architecture)**：Python 後端採用 `asyncio` 事件循環。
- **獨立匯出層 (Export Layer)**：
  - 封裝成 `ExcelExporter` 模組，支援凍結首行、啟用篩選器、列寬自動適應，並將人工修改過的儲存格以淡黃色底色標記，方便審查。

---

# 7. 效能與資源目標

- **軟體包大小**：PyInstaller 打包後控制在 **80MB** 以內。
- **單頁處理成本**：經過預處理後，單頁圖片 Payload < 150KB，Gemini API 處理延遲 < 3 秒。
- **記憶體上限**：批次處理 200+ 檔案時，主行程實體記憶體佔用不超過 **300MB**。
- **快取命中率目標**：重複掃描相同資料夾時，快取命中率應達到 100%，耗時 < 1 秒。

---

# 8. 未來實驗室智慧化軟體家族規劃 (COA Family Suite Roadmap)

本專案 `COA Parser` 所產生的資料，將在 `local.db` 與 Google Sheet 中保留延伸介面，供未來以下家族軟體擴充對接：

1. **COA Organizer (自動改名歸檔工具)**：
   * **方案**：讀取 `local.db` 或 Google Sheet 中核對完成的資訊，自動將 PDF 重新命名並按年份或廠牌歸檔，格式如：`[產品名稱]_[批號]_[效期].pdf`。
2. **COA Stocker (標準品入庫管理系統)**：
   * **方案**：提供庫位對照，核對完 COA 後一鍵入庫，產生包含 QR Code 的實體標籤。掃描實體標籤即可立即在電腦調閱該瓶標準品的原始 COA 文件與開瓶記錄。
3. **COA Formulator (標準溶液配製記錄助手)**：
   * **方案**：配製溶液時，直接在軟體中點選 Google Sheet 的標準品，系統自動載入其「批號」、「廠牌」與「標準化純度 (Purity)」，使用者僅需輸入本次稱重重量與目標體積，系統即自動計算精準濃度並輸出符合 GMP/ISO 規範的配製表格。
