# 🔬 AI COA Parser 資訊安全架構與審查說明書 (IT Security Audit & Architecture Specification)

本文件旨在為政府機關、國營事業或企業內部之**資訊安全人員 (IT Security Auditors)** 提供本系統的架構審查資料。本系統設計之初即將「資安合規」與「最小權限原則」作為核心考量，不含任何木馬、後門或隱蔽外連通訊，源碼完全開源可供審查。

---

## 1. 系統基本資訊 (System Information)
* **軟體名稱**：AI COA Parser & Verification Hub (實驗室智慧文件處理系統)
* **開發架構**：Python 3.10+ (後端引擎) + pywebview (桌面視窗容器) + HTML5/CSS3/Vanilla JS (前端介面)。
* **架構類型**：本機端桌面應用程式 (Standard Desktop Client-Side Application)。本系統**非 Web 伺服器**，本機不監聽任何外部通訊埠 (Ports)，亦不向任何非授權之第三方主機發送資料。

---

## 2. 網路通訊安全性 (Network Security & Domain Whitelisting)
本程式僅在執行文件解析與雲端同步時發送出境網路流量。所有網路通訊均強制使用 **HTTPS (Port 443) 加密傳輸**，拒絕任何非加密的 HTTP 連線。

### 📌 網域白名單 (Required Domains for Whitelisting)
若機關內部設有防火牆或 Proxy 限制，僅需放行以下兩個官方安全網域：
1. **Gemini API 服務** (`https://generativelanguage.googleapis.com`)：用於發送影像並取得結構化欄位結果。
2. **Google Sheets 同步服務** (`https://script.google.com` & `https://script.googleusercontent.com`)：用於與同組人員共用快取資料庫（由使用者自行配置之 GAS 網址，若不使用可於設定中關閉）。

> [!NOTE]
> **無第三方遙測 (No Telemetry)**：本軟體不包含任何第三方數據統計、廣告載入、自動更新檢查或匿名日誌回傳機制，確保公務機關文件隱私不外洩。

---

## 3. 敏感資訊保護與金鑰加密 (Credential & Key Protection)
本程式絕不以「明文」形式在硬碟儲存敏感的 API Key。

* **Windows 憑證管理器整合 (Keyring DPAPI)**：
  本軟體整合了 Windows 系統內建的**憑證管理員 (Credential Manager)**，透過微軟官方之 **DPAPI (Data Protection API)** 進行金鑰加密保護。金鑰僅綁定於該 Windows 登入帳戶，即使電腦遺失或硬碟被拆解，其他使用者帳戶亦無法讀取該憑證。
* **本地加密備份**：
  若本機系統因特殊安全原則停用憑證管理器，軟體會透過機器硬體特徵碼（UUID 與 MAC 雜湊）作為鹽值 (Salt)，利用 **PBKDF2** 演算法衍生出對稱金鑰，以 **AES-256-GCM** 演算法將 API Key 加密後寫入 `config.json`，防範未授權的明文讀取。

---

## 4. 資料儲存與暫存檔生命週期 (Data Storage & Local Cache Lifecycle)
* **本地 SQLite 資料庫**：
  本程式將任務狀態、解析後之文字欄位與警告儲存於使用者設定目錄下的 `queue.db` 中。資料庫開啟了 **WAL (Write-Ahead Logging)** 模式以防異常斷電導致的損毀。
* **暫存圖片安全清理**：
  當使用者匯入 PDF 進行解析時，系統會調用 `PyMuPDF` 於本機記憶體中渲染頁面為 JPEG 位元流。若需產生暫存檔，檔案將寫入使用者暫存資料夾 `%TEMP%` 中，並在解析任務結束或視窗關閉時**強制調用 Python 垃圾回收 (`gc.collect`) 與 OS 檔案移除機制**徹底刪除暫存影像，防止殘留敏感實驗室文件。

---

## 5. 系統執行權限 (Execution Permissions)
* **非管理員權限執行 (No Administrator Privilege Required)**：
  本程式不需變更任何系統登錄檔 (Registry)、不需安裝核心驅動程式、亦不需提升至管理員權限 (`Administrator`)。
* **安裝目錄隔離**：
  軟體預設安裝於使用者的 `%USERPROFILE%\AppData\Local\COA_Parser` 內，確保執行時受到 Windows 使用者帳戶控制 (UAC) 限制，無法寫入系統目錄 (如 `C:\Windows` 或 `C:\Program Files`)，將潛在的安全風險降至最低。

---

## 6. 安裝與卸載包裝 (Installer & Uninstaller Integrity)
* **安裝包打包技術**：使用標準之 **Inno Setup** 進行安裝包製作。
* **靜態檔案清單**：安裝程式所釋出的所有檔案皆有明確雜湊，不包含動態下載外部二進位檔案之行為。
* **乾淨卸載 (Clean Uninstallation)**：
  使用者透過 Windows「新增或移除程式」解除安裝時，卸載程式會將釋出的所有二進位檔案、捷徑完全清除，不留下任何系統常駐服務或背景執行程序。
