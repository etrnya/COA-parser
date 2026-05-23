import os
import logging
from logging.handlers import RotatingFileHandler

# Define logs directory in workspace
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "coa_parser.log")

# Setup formatting
log_formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Rotate files (Max 5MB per file, keeping up to 5 back-ups)
file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG)

# Get root logger
logger = logging.getLogger("COAParser")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger(module_name: str) -> logging.Logger:
    """Helper to return a child logger for a specific module."""
    return logger.getChild(module_name)

class UIForwardingHandler(logging.Handler):
    """Custom log handler that forwards records to a frontend UI callback function."""
    def __init__(self, forward_fn):
        super().__init__()
        self.forward_fn = forward_fn
        self.setFormatter(log_formatter)
        self.setLevel(logging.INFO)

    def emit(self, record):
        try:
            msg = self.format(record)
            # Call pywebview bridged frontend function
            self.forward_fn(msg)
        except Exception:
            pass

def register_ui_logger(forward_fn):
    """Enables the frontend UI log panel to receive log updates."""
    ui_handler = UIForwardingHandler(forward_fn)
    logger.addHandler(ui_handler)
    logger.info("UI Logging Handler registered successfully.")
