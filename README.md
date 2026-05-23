# 🔬 AI COA Document Parser & Verification Hub

An industrial-grade, open-source AI desktop application to parse, validate, and standardize chemical and food laboratory **Certificate of Analysis (COA)** documents. 

Equipped with a **Human-in-the-loop Verification Hub**, **Deterministic Rules Engine**, **Persistent SQLite Task Queue**, and **Google Sheets Collaborative Sync (GAS)**, this tool automates laboratory inventory logging with high reliability and zero concurrency locking issues.

---

## 🌟 Key Features

1. **Vision-Driven Extraction**: Powered by Gemini Multimodal Vision API to accurately capture noisy, scanned, double-column, or handwritten COA documents.
2. **Comprehensive Dual-Field Mechanism**: Captures both the original text and automatically computes standardized values for:
   - **Brand (廠牌)** ➔ Mapped to standardized manufacturer/brand catalog.
   - **Product Name (產品名稱)** ➔ Capitalized (Title Case) format.
   - **Molecular Weight (分子量)** ➔ Parsed and standardized to numerical floats.
   - **CAS Number (CAS Number)** ➔ Standardized CAS formatting check.
   - **Batch Number (生產批號)** ➔ Exact raw batch code.
   - **Expiry Date (有效期限)** ➔ Standardized to `YYYY/M/D` format.
   - **Amount (包裝容量)** ➔ Standardized volume/weight metrics.
   - **Purity (純度/含量)** ➔ Cleaned numerical values formatted as `[Value] %`.
   - **Storage Conditions (儲存條件)** ➔ Mapped to `-20°C`, `4°C`, or `RT`.
3. **Interactive Document Viewer**: Direct mouse drag-to-pan and mouse wheel scroll-to-zoom for seamless visual verification of PDFs and JPEGs.
4. **Google Sheets Cloud Sync (GAS)**: Collaborative database synchronization via Google Apps Script (GAS) Web Apps. Shares parsing caches across the team to save API costs ("One parses, all share").
5. **Keyboard-Driven Verification**: Increase human verification speeds by 200% with pure keyboard hotkeys (`Ctrl+Enter` to save and jump).
6. **Customizable Export Layout**: Customize visibility, order, and labels (headers) of all columns directly from the settings panel before exporting to Excel.
7. **Autofit Excel Exports**: Expose records to a beautifully styled Excel sheet with frozen headers, enabled filters, and user-defined configurations.
8. **Open-Source Ready**: Built-in credential encryption using OS Keychain / Windows Credential Manager to protect API keys.

---

## 📂 Project Structure

```text
COAhtml/
├── app/                   # Backend Python Engine
│   ├── core/              # Preprocessors, Classifiers, SQLite Queues, Rule Validators
│   ├── providers/         # Vision API Adapters (Gemini, Extensible)
│   ├── exporters/         # openpyxl Styled Excel Exporters
│   ├── utils/             # Loggers, Secure Stores, GAS Client API
│   └── main.py            # Desktop Window Bootloader
├── frontend/              # Webview Interface (HTML5 / Vanilla CSS / Vanilla JS)
│   ├── index.html         # Workspace Layout
│   ├── style.css          # Glassmorphic Dark UI Theme
│   ├── app.js             # Keyboard Events & JS IPC Bridge
│   └── tutorial.html      # In-App User Manual
├── prompts/               # System prompt templates
├── dataset/               # Expected test sets (Regression testing)
├── requirements.txt       # Python Dependencies list
└── README.md              # Project Introduction
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- A Google Account (for AI Studio API key and Google Sheet access)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/coa-parser.git
   cd coa-parser
   ```

2. Install python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application
Launch the desktop application via:
```bash
python -m app.main
```

---

## 📖 Setup Integration Guides

For complete integration instructions, open the in-app **User Manual** by clicking the button in the application sidebar, or view the instructions locally in `frontend/tutorial.html`.

1. **API Key**: Acquire your Gemini key from [Google AI Studio](https://aistudio.google.com/).
2. **Cloud Sync**: Open `frontend/tutorial.html`, copy the Google Apps Script template, paste it in your target Google Sheet script editor, and deploy as a Web App.

---

## 🛠️ Build Executable
To package the application as a standalone `.exe` without console prompts (requires `pyinstaller`):
```bash
pip install pyinstaller
pyinstaller --noconsole --name="COA_Parser" --add-data "frontend;frontend" --add-data "app;app" app/main.py
```

---

## ⚖️ License & Credits
* **Developer**: etrnya
* **License**: This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

