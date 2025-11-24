"""Database singleton with WAL mode and transaction helpers."""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import yaml

_lock = threading.Lock()
_instance: Optional["Database"] = None
_config: Optional[dict] = None


def _load_config() -> dict:
    """Load database config from config.yaml."""
    global _config
    if _config is None:
        config_path = Path("config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                full_config = yaml.safe_load(f)
                _config = full_config.get("database", {})
        else:
            _config = {}
    return _config


def get_db_config() -> dict:
    """Get database configuration with defaults."""
    config = _load_config()
    return {
        "enabled": config.get("enabled", False),
        "path": Path(config.get("path", "data/pipeline.db")),
        "wal_mode": config.get("wal_mode", True),
        "busy_timeout_ms": config.get("busy_timeout_ms", 5000),
        "backup_on_iteration_end": config.get("backup_on_iteration_end", True),
    }


def is_db_enabled() -> bool:
    """Check if database is enabled in config."""
    return get_db_config()["enabled"]


class Database:
    """SQLite database singleton with WAL mode."""

    def __init__(self, db_path: Path = None, wal_mode: bool = True, busy_timeout_ms: int = 5000):
        config = get_db_config()
        self.db_path = db_path or config["path"]
        self.wal_mode = wal_mode if db_path else config["wal_mode"]
        self.busy_timeout_ms = busy_timeout_ms if db_path else config["busy_timeout_ms"]
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
            # Enable WAL mode for concurrent reads (if configured)
            if self.wal_mode:
                self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
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
            _instance = Database(db_path)
        return _instance


def reset_db():
    """Reset the singleton (for testing)."""
    global _instance, _config
    with _lock:
        if _instance:
            _instance.close()
        _instance = None
        _config = None
