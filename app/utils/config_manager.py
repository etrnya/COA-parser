import os
import json
from app.utils.logger import get_logger

logger = get_logger("ConfigManager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "gas_web_app_url": "",
    "output_format": "xlsx",
    "fields_order": [
        "brand_raw",
        "product_raw",
        "mw_raw",
        "cas_no_raw",
        "batch_no",
        "expiry_raw",
        "amount_raw",
        "purity_raw",
        "storage_raw",
        "brand_std",
        "product_std",
        "mw_std",
        "cas_no_std",
        "expiry_std",
        "amount_std",
        "purity_std",
        "storage_std"
    ],
    "fields_visibility": {
        "brand_raw": True,
        "product_raw": True,
        "mw_raw": True,
        "cas_no_raw": True,
        "batch_no": True,
        "expiry_raw": True,
        "amount_raw": True,
        "purity_raw": True,
        "storage_raw": True,
        "brand_std": True,
        "product_std": True,
        "mw_std": True,
        "cas_no_std": True,
        "expiry_std": True,
        "amount_std": True,
        "purity_std": True,
        "storage_std": True
    },
    "column_headers": {
        "brand_raw": "廠牌 (原始)",
        "product_raw": "產品名稱 (原始)",
        "mw_raw": "分子量 (原始)",
        "cas_no_raw": "CAS Number (原始)",
        "batch_no": "生產批號",
        "expiry_raw": "有效期限 (原始)",
        "amount_raw": "包裝容量 (原始)",
        "purity_raw": "純度/含量 (原始)",
        "storage_raw": "儲存條件 (原始)",
        "brand_std": "廠牌 (標準化)",
        "product_std": "產品名稱 (標準化)",
        "mw_std": "分子量 (標準化)",
        "cas_no_std": "CAS Number (標準化)",
        "expiry_std": "有效期限 (標準化)",
        "amount_std": "包裝容量 (標準化)",
        "purity_std": "純度/含量 (標準化)",
        "storage_std": "儲存條件 (標準化對應)"
    },
    "standardization_rules": {
        "date_format": "YYYY/M/D",
        "name_format": "Title Case",
        "temp_mappings": {
            "4°C": ["2-8°C", "4°C", "refrigerate", "cold", "2-8 degree", "refrigerator", "2-8", "2 - 8"],
            "-20°C": ["-20", "freeze", "frozen", "deep freeze", "-20°C"],
            "RT": ["room temperature", "RT", "15-25", "ambient", "room temp", "20-25", "20 - 25"]
        }
    }
}

def load_config() -> dict:
    """Load configuration dictionary from config.json. Creates default if missing."""
    if not os.path.exists(CONFIG_PATH):
        logger.info("config.json not found. Initializing default config.")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
        
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            
            # Migrate to new sorting order and customize column headers if upgrading
            updated = False
            if "column_headers" not in config:
                config["column_headers"] = DEFAULT_CONFIG["column_headers"]
                config["fields_order"] = DEFAULT_CONFIG["fields_order"]
                config["fields_visibility"] = DEFAULT_CONFIG["fields_visibility"]
                updated = True
                
            # Ensure all default keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
                    updated = True
                elif k == "fields_order":
                    for field in v:
                        if field not in config[k]:
                            config[k].append(field)
                            updated = True
                elif k == "fields_visibility":
                    for field, visible in v.items():
                        if field not in config[k]:
                            config[k][field] = visible
                            updated = True
                elif k == "column_headers":
                    for field, label in v.items():
                        if field not in config[k]:
                            config[k][field] = label
                            updated = True
            if updated:
                save_config(config)
            return config
    except Exception as e:
        logger.error(f"Failed to read config.json: {e}. Returning default config.")
        return DEFAULT_CONFIG.copy()

def save_config(config: dict) -> bool:
    """Save configuration dictionary to config.json."""
    try:
        # Never store plaintext API Key inside config.json
        # If it somehow got into config, delete it. SecureStore handles API key!
        if "gemini_api_key" in config:
            del config["gemini_api_key"]
            
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to write to config.json: {e}")
        return False
