"""Database singleton with WAL mode and transaction helpers."""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

_DB_PATH = Path("data/pipeline.db")
_lock = threading.Lock()
_instance: Optional["Database"] = None


class Database:
    """SQLite database singleton with WAL mode."""

    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None,  # autocommit, we manage transactions manually
            )
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for concurrent reads
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA busy_timeout=5000")
        return self._conn

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_connection()

    @contextmanager
    def transaction(self):
        """Context manager for transactional operations."""
        conn = self.conn
        conn.execute("BEGIN")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single SQL statement."""
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """Execute SQL for multiple parameter sets."""
        return self.conn.executemany(sql, params_list)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute and fetch one result."""
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute and fetch all results."""
        return self.conn.execute(sql, params).fetchall()

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


def get_db(db_path: Optional[Path] = None) -> Database:
    """Get or create the database singleton."""
    global _instance
    with _lock:
        if _instance is None:
            _instance = Database(db_path or _DB_PATH)
        return _instance


def reset_db():
    """Reset the singleton (for testing)."""
    global _instance
    with _lock:
        if _instance:
            _instance.close()
        _instance = None
