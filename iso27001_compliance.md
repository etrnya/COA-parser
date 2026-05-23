# 🔬 AI COA Parser 符合 ISO/IEC 27001:2022 資安控制規範對照表

本文件針對 **ISO/IEC 27001:2022 資訊安全管理系統 (ISMS)** 附錄 A (Annex A) 的控制措施進行對照與分析。提供公務機關與企業內部的資安稽核人員 (Auditors) 評估本系統導入時的資安合規性。

---

## 1. ISO/IEC 27001:2022 控制措施對照 (Control Mapping)

| ISO 27001 控制編號 | 控制名稱 (Control Name) | 系統具體實作與防護機制 (System Implementation) | 稽核佐證說明 (Audit Evidence) |
| :--- | :--- | :--- | :--- |
| **A.8.24** | **密碼學之使用**<br>(Use of cryptography) | 1. **憑證安全儲存**：API Key 不以明文存於硬碟，預設呼叫作業系統微軟官方之 **DPAPI (Data Protection API)** 進行硬體級加密保護，寫入 Windows 憑證管理員。<br>2. **本機備份加密**：若憑證管理員停用，系統會讀取本機 UUID 雜湊，以 **PBKDF2** 衍生金鑰，並透過 **AES-256-GCM** 加密演算法將 Key 加密後寫入 `config.json`。 | 參閱代碼：<br>[secure_store.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/utils/secure_store.py) |
| **A.8.20** | **網路安全控制**<br>(Network security) | 1. **傳輸加密 (Transit Security)**：強制所有外連網路連線（Gemini API 與 Google Apps Script）均採用 **HTTPS (TLS 1.2 或 TLS 1.3)** 加密通道。<br>2. **零隱蔽外連**：軟體不含任何隱藏的外聯遙測 (Telemetry) 或分析伺服器，僅與官方白名單網域進行資料傳輸。 | 參閱代碼：<br>[gemini.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/providers/gemini.py)<br>[gas_client.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/utils/gas_client.py) |
| **A.8.11** | **資料遮罩**<br>(Data masking) | 1. **金鑰遮罩 (UI Masking)**：在設定介面 (Settings Pane) 中，API Key 的輸入框會自動遮蔽（例如顯示 `****`），且調用後端遮罩 API 來防止旁路窺視 (Shoulder Surfing)。 | 參閱代碼：<br>[bridge.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/bridge.py#L65-L74) |
| **A.8.28** | **安全編碼**<br>(Secure coding) | 1. **防範 SQL 注入**：本地 SQLite 佇列資料庫全面使用參數化查詢 (Parameterized Queries)，防止惡意檔名或文字造成 SQL 注入攻擊。<br>2. **前端 XSS 防護**：在 Python 透過 `evaluate_js` 傳遞數據給網頁介面時，均對字串進行特殊字元逸出 (Escape)，防範 Cross-Site Scripting (XSS)。 | 參閱代碼：<br>[queue_db.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/core/queue_db.py)<br>[bridge.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/bridge.py#L32-L42) |
| **A.8.12** | **防範資料外洩**<br>(Data leakage prevention) | 1. **本地沙箱處理**：COA 文件圖片僅存在記憶體或本機暫存資料夾中。解析完成後立即觸發 `gc.collect()` 強制資源回收，清空記憶體緩衝區以防暫存洩漏。 | 參閱代碼：<br>[preprocessor.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/core/preprocessor.py#L40-L65) |
| **A.8.9** | **組態管理**<br>(Configuration management) | 1. **設定檔隔離**：系統將用戶端組態 (`config.json`) 與本機快取資料庫 (`queue.db`) 儲存於 Windows 使用者專屬的安全 AppData 目錄，避免不同作業系統帳戶間互相存取。 | 參閱代碼：<br>[config_manager.py](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/app/utils/config_manager.py) |
| **A.8.25** | **安全開發生命週期**<br>(Secure development life cycle) | 1. **排除敏感原始碼提交**：配置防護性的 `.gitignore` 阻擋金鑰、個人測試資料庫上傳至開源 Git 庫。<br>2. **套件相依性安全**：`requirements.txt` 指定明確套件版本，防止在編譯時引入未知的惡意套件版本。 | 參閱檔案：<br>[.gitignore](file:///c:/Users/etrny/.gemini/antigravity/scratch/COAhtml/.gitignore) |

---

## 2. 導入與作業環境注意事項 (Operational Recommendations)

除了系統代碼層級的防護，依據 ISO 27001 規範，機關在**作業管理層面**應實施以下程序：

### 🔑 2.1 API 金鑰生命週期管理 (A.8.24)
* **定期金鑰變更 (Rotation)**：建議每 90 天至 180 天至 Google AI Studio 撤銷舊的金鑰並更換新金鑰。
* **人員離職程序**：當有權接觸 Settings 介面設定金鑰的同仁調職或離職時，必須立刻在 Google AI Studio 廢止該 API Key，並重新發行新 Key 供在職人員設定。

### 👥 2.2 Google Sheets 存取權限控制 (A.5.15 & A.8.2)
* **GAS 權限限制**：雖然部署 GAS 時設定為「Anyone」，但這指的是 Web App Webhook 接收端。**後端的 Google 試算表本身必須嚴格限縮共用對象**。
* **權限最小化**：試算表僅能共享給同組負責 COA 建檔的同仁（唯讀或寫入權限），禁止設定為「任何知道連結的人皆可檢視/編輯」。

### 🖥️ 2.3 用戶端本機權限防護 (A.8.2)
* **鎖定電腦原則**：軟體因為採用 Windows 憑證管理員 (DPAPI)，是與目前登入的 Windows 帳戶綁定的。同仁離開座位時必須習慣按下 <kbd>Win</kbd> + <kbd>L</kbd> 鎖定螢幕，以防他人操作已登入帳戶的 COA 系統。
* **防毒軟體排除與安全掃描**：封裝後的 `.exe` 可在送交資訊部門前，使用內部的企業防毒軟體或上傳至 [VirusTotal](https://www.virustotal.com/) 進行多引擎掃描，並保留掃描報告作為資安佐證文件。
