"""Database schema definitions (DDL)."""

SCHEMA_VERSION = 1

TABLES = {
    "projects": """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            concept TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'archived'))
        )
    """,
    "iterations": """
        CREATE TABLE IF NOT EXISTS iterations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            loops_requested INTEGER DEFAULT 1,
            loops_completed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running' CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
            config_snapshot TEXT
        )
    """,
    "role_artifacts": """
        CREATE TABLE IF NOT EXISTS role_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            iteration_id INTEGER REFERENCES iterations(id),
            role TEXT NOT NULL CHECK(role IN ('ba', 'po', 'architect', 'dev', 'qa')),
            artifact_type TEXT NOT NULL,
            content TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, role, artifact_type, version)
        )
    """,
    "stories": """
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            iteration_id INTEGER NOT NULL REFERENCES iterations(id),
            story_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'todo' CHECK(status IN (
                'todo', 'doing', 'in_progress', 'dev_ok',
                'done', 'in_review', 'blocked_dev', 'done_force_architect'
            )),
            priority TEXT CHECK(priority IN ('P0', 'P1', 'P2', 'P3')),
            estimate TEXT,
            acceptance_criteria TEXT,
            depends_on TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(iteration_id, story_id)
        )
    """,
    "story_attempts": """
        CREATE TABLE IF NOT EXISTS story_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL REFERENCES stories(id),
            attempt_number INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('dev', 'qa', 'architect_review')),
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('success', 'error', 'timeout')),
            duration_ms INTEGER,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            error_message TEXT,
            error_category TEXT,
            artifacts_path TEXT,
            raw_response_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "event_log": """
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id),
            iteration_id INTEGER REFERENCES iterations(id),
            story_id INTEGER REFERENCES stories(id),
            event_type TEXT NOT NULL,
            role TEXT,
            severity TEXT DEFAULT 'info' CHECK(severity IN ('debug', 'info', 'warning', 'error')),
            message TEXT,
            payload TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "model_stats": """
        CREATE TABLE IF NOT EXISTS model_stats (
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            role TEXT NOT NULL,
            total_attempts INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            avg_duration_ms REAL,
            total_tokens INTEGER DEFAULT 0,
            total_cost_usd REAL DEFAULT 0,
            PRIMARY KEY (provider, model, role)
        )
    """,
    "schema_version": """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_event_log_timestamp ON event_log(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_event_log_project ON event_log(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_event_log_type ON event_log(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_stories_iteration ON stories(iteration_id)",
    "CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status)",
    "CREATE INDEX IF NOT EXISTS idx_story_attempts_story ON story_attempts(story_id)",
    "CREATE INDEX IF NOT EXISTS idx_role_artifacts_project ON role_artifacts(project_id)",
]


def create_schema(db) -> None:
    """Create all tables and indexes."""
    with db.transaction():
        for table_name, ddl in TABLES.items():
            db.execute(ddl)
        for index_ddl in INDEXES:
            db.execute(index_ddl)
        # Record schema version
        db.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )


def get_schema_version(db) -> int:
    """Get current schema version."""
    try:
        row = db.fetchone("SELECT MAX(version) as v FROM schema_version")
        return row["v"] if row and row["v"] else 0
    except Exception:
        return 0
