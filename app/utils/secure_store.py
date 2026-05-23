import os
import sys
import platform
import hashlib
import base64
import json
from app.utils.logger import get_logger

logger = get_logger("SecureStore")

# Service name for OS Credential Manager
SERVICE_NAME = "COAParserService"
KEY_NAME = "GeminiAPIKey"

# Safe import for keyring
HAS_KEYRING = False
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    logger.warning("Keyring package not installed. Falling back to local encrypted storage.")

# Fallback crypto imports
HAS_CRYPTOGRAPHY = False
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTOGRAPHY = True
except ImportError:
    logger.warning("Cryptography package not installed. Falling back to weak local encoding.")

# Get config.json path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def _get_machine_uuid() -> str:
    """Retrieve a unique identifier based on hardware characteristics."""
    system = platform.system()
    node = platform.node()
    proc = platform.processor()
    # Combine some hardware/OS metrics to create a stable machine fingerprint
    fingerprint = f"{system}-{node}-{proc}-{sys.platform}"
    
    # Try OS specific identifiers
    try:
        if system == "Windows":
            import winreg
            registry_key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, 
                r"SOFTWARE\Microsoft\Cryptography", 
                0, 
                winreg.KEY_READ
            )
            value, regtype = winreg.QueryValueEx(registry_key, "MachineGuid")
            winreg.CloseKey(registry_key)
            return str(value)
    except Exception:
        pass
        
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

def _get_encryption_key() -> bytes:
    """Generate a stable Fernet key derived from hardware characteristics."""
    if not HAS_CRYPTOGRAPHY:
        return b""
    machine_id = _get_machine_uuid()
    salt = b"COA_Parser_Salt_1984" # Stable salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode("utf-8")))
    return key

def save_api_key(api_key: str) -> bool:
    """Save the Gemini API Key securely using Windows Credential Manager or encrypted config fallback."""
    if not api_key:
        logger.error("API Key cannot be empty.")
        return False
        
    # Method 1: Try Keyring (Windows Credential Manager)
    if HAS_KEYRING:
        try:
            logger.info("Attempting to store key in system credential manager...")
            keyring.set_password(SERVICE_NAME, KEY_NAME, api_key)
            logger.info("API Key successfully stored in Credential Manager.")
            # Clear any fallback keys if they exist in config.json
            _remove_fallback_key()
            return True
        except Exception as e:
            logger.warning(f"Failed to use Credential Manager: {e}. Falling back to encrypted config.")

    # Method 2: Fallback to Encrypted Config
    if HAS_CRYPTOGRAPHY:
        try:
            logger.info("Encrypting key and storing locally in config.json...")
            fernet = Fernet(_get_encryption_key())
            encrypted_bytes = fernet.encrypt(api_key.encode("utf-8"))
            encrypted_str = encrypted_bytes.decode("utf-8")
            _write_to_config("encrypted_api_key", encrypted_str)
            return True
        except Exception as e:
            logger.error(f"Failed to encrypt and store API key: {e}")
    else:
        # Method 3: Weak fallback (Base64 encoding)
        logger.warning("Weak security: encoding key in base64 and saving to config.json...")
        encoded_str = base64.b64encode(api_key.encode("utf-8")).decode("utf-8")
        _write_to_config("encoded_api_key", encoded_str)
        return True
        
    return False

def get_api_key() -> str:
    """Retrieve the Gemini API Key from secure storage."""
    # Method 1: Try Keyring
    if HAS_KEYRING:
        try:
            api_key = keyring.get_password(SERVICE_NAME, KEY_NAME)
            if api_key:
                return api_key
        except Exception as e:
            logger.warning(f"Failed to read from Credential Manager: {e}")

    # Method 2: Check Cryptography Fallback in config.json
    try:
        config = _read_config()
        if "encrypted_api_key" in config and HAS_CRYPTOGRAPHY:
            encrypted_str = config["encrypted_api_key"]
            fernet = Fernet(_get_encryption_key())
            decrypted_bytes = fernet.decrypt(encrypted_str.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        elif "encoded_api_key" in config:
            encoded_str = config["encoded_api_key"]
            return base64.b64decode(encoded_str.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to load fallback API key: {e}")
        
    return ""

def delete_api_key() -> bool:
    """Delete the saved API Key."""
    success = False
    if HAS_KEYRING:
        try:
            keyring.delete_password(SERVICE_NAME, KEY_NAME)
            success = True
        except Exception:
            pass
            
    _remove_fallback_key()
    logger.info("API Key removed from secure storage.")
    return success

# Helper functions to manage config.json
def _read_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_to_config(key: str, value):
    config = _read_config()
    config[key] = value
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to write configuration file: {e}")

def _remove_fallback_key():
    config = _read_config()
    changed = False
    for k in ["encrypted_api_key", "encoded_api_key"]:
        if k in config:
            del config[k]
            changed = True
    if changed:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
