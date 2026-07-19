import logging
import os
import sqlite3
from typing import Any

logger = logging.getLogger("phishing_backend")

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
DB_PATH = os.path.join(DB_DIR, "predictions.db")


def init_db() -> None:
    """Initializes the SQLite database and creates the prediction history table if not present."""
    try:
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text TEXT NOT NULL,
                input_type TEXT NOT NULL,
                prediction_label TEXT NOT NULL,
                confidence REAL NOT NULL,
                is_phishing INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"Database initialized successfully at '{DB_PATH}'")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


def log_prediction(
    input_text: str,
    input_type: str,
    prediction_label: str,
    confidence: float,
    is_phishing: bool,
    reason: str,
) -> None:
    """Logs a single inference prediction to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prediction_history (input_text, input_type, prediction_label, confidence, is_phishing, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (input_text, input_type, prediction_label, confidence, 1 if is_phishing else 0, reason),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log prediction to DB: {e}")


def get_history(limit: int = 100) -> list[dict[str, Any]]:
    """Retrieves recent prediction log history."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, input_text, input_type, prediction_label, confidence, is_phishing, reason, timestamp
            FROM prediction_history
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to retrieve prediction history: {e}")
        return []


def clear_history() -> bool:
    """Deletes all records from the prediction history table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prediction_history")
        conn.commit()
        conn.close()
        logger.info("Prediction history cleared from database.")
        return True
    except Exception as e:
        logger.error(f"Failed to clear prediction history: {e}")
        return False
