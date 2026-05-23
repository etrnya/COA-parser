import os
import sqlite3
import json
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger("QueueDB")

# Base directory for database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "queue.db")

def get_connection():
    """Create a database connection and enable WAL mode for safety and concurrency."""
    conn = sqlite3.connect(DB_PATH)
    # Use WAL mode to prevent locking conflicts
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """Initialize the persistent queue database schema."""
    logger.info(f"Initializing SQLite Queue Database at: {DB_PATH}")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                file_name TEXT NOT NULL,
                status TEXT NOT NULL, -- Pending, Processing, Validating, ReviewNeeded, Completed, Failed
                extracted_data TEXT,  -- JSON string of parsed payload
                validation_errors TEXT, -- JSON string of warning details
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create a index on status for smart filtering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status);")
        # Create index on file_hash
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON tasks(file_hash);")
        conn.commit()
        logger.info("SQLite database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite: {e}")
    finally:
        conn.close()

def add_task(file_path: str, file_hash: str, file_name: str) -> bool:
    """Add a new COA task to the queue if it doesn't already exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Insert or ignore to prevent duplicates
        cursor.execute("""
            INSERT OR IGNORE INTO tasks (file_path, file_hash, file_name, status)
            VALUES (?, ?, ?, 'Pending')
        """, (file_path, file_hash, file_name))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to add task {file_name} to SQLite: {e}")
        return False
    finally:
        conn.close()

def update_task_status(
    file_path: str, 
    status: str, 
    extracted_data: dict = None, 
    validation_errors: list = None
) -> bool:
    """Update status, extracted data, and validation errors of a COA task."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        data_str = json.dumps(extracted_data) if extracted_data is not None else None
        errors_str = json.dumps(validation_errors) if validation_errors is not None else None
        
        cursor.execute("""
            UPDATE tasks 
            SET status = ?, extracted_data = ?, validation_errors = ?, updated_at = CURRENT_TIMESTAMP
            WHERE file_path = ?
        """, (status, data_str, errors_str, file_path))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update task status in SQLite for {file_path}: {e}")
        return False
    finally:
        conn.close()

def get_all_tasks() -> list:
    """Get all tasks currently in the queue, sorted by risk index and updated_at."""
    conn = get_connection()
    tasks_list = []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path, file_hash, file_name, status, extracted_data, validation_errors, updated_at
            FROM tasks
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        for r in rows:
            tasks_list.append({
                "id": r[0],
                "file_path": r[1],
                "file_hash": r[2],
                "file_name": r[3],
                "status": r[4],
                "extracted_data": json.loads(r[5]) if r[5] else None,
                "validation_errors": json.loads(r[6]) if r[6] else None,
                "updated_at": r[7]
            })
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}")
    finally:
        conn.close()
    return tasks_list

def get_task_by_path(file_path: str) -> dict:
    """Retrieve a single task record by its path."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path, file_hash, file_name, status, extracted_data, validation_errors, updated_at
            FROM tasks WHERE file_path = ?
        """, (file_path,))
        r = cursor.fetchone()
        if r:
            return {
                "id": r[0],
                "file_path": r[1],
                "file_hash": r[2],
                "file_name": r[3],
                "status": r[4],
                "extracted_data": json.loads(r[5]) if r[5] else None,
                "validation_errors": json.loads(r[6]) if r[6] else None,
                "updated_at": r[7]
            }
    except Exception as e:
        logger.error(f"Failed to query task: {e}")
    finally:
        conn.close()
    return None

def clear_queue() -> bool:
    """Delete all records from the queue database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks")
        conn.commit()
        logger.info("Cleared all tasks from SQLite Queue.")
        return True
    except Exception as e:
        logger.error(f"Failed to clear queue: {e}")
        return False
    finally:
        conn.close()

def delete_task(file_path: str) -> bool:
    """Remove a single task from the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE file_path = ?", (file_path,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        return False
    finally:
        conn.close()
