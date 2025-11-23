"""Repository classes for CRUD operations on each entity."""
import json
from datetime import datetime
from typing import Optional, Any
from .storage import Database


class BaseRepository:
    """Base class with common DB operations."""

    def __init__(self, db: Database):
        self.db = db

    def _to_dict(self, row) -> Optional[dict]:
        if row is None:
            return None
        return dict(row)

    def _to_list(self, rows) -> list[dict]:
        return [dict(r) for r in rows]


class ProjectRepository(BaseRepository):
    """CRUD for projects table."""

    def create(self, name: str, concept: str) -> int:
        cursor = self.db.execute(
            "INSERT INTO projects (name, concept) VALUES (?, ?)",
            (name, concept),
        )
        return cursor.lastrowid

    def get(self, project_id: int) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone("SELECT * FROM projects WHERE id = ?", (project_id,))
        )

    def get_by_name(self, name: str) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone("SELECT * FROM projects WHERE name = ?", (name,))
        )

    def list_all(self, status: str = None) -> list[dict]:
        if status:
            return self._to_list(
                self.db.fetchall("SELECT * FROM projects WHERE status = ?", (status,))
            )
        return self._to_list(self.db.fetchall("SELECT * FROM projects"))

    def update_status(self, project_id: int, status: str) -> None:
        self.db.execute(
            "UPDATE projects SET status = ? WHERE id = ?", (status, project_id)
        )


class IterationRepository(BaseRepository):
    """CRUD for iterations table."""

    def create(
        self, project_id: int, loops_requested: int = 1, config_snapshot: dict = None
    ) -> int:
        config_json = json.dumps(config_snapshot) if config_snapshot else None
        cursor = self.db.execute(
            "INSERT INTO iterations (project_id, loops_requested, config_snapshot) VALUES (?, ?, ?)",
            (project_id, loops_requested, config_json),
        )
        return cursor.lastrowid

    def get(self, iteration_id: int) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone("SELECT * FROM iterations WHERE id = ?", (iteration_id,))
        )

    def get_latest(self, project_id: int) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone(
                "SELECT * FROM iterations WHERE project_id = ? ORDER BY id DESC LIMIT 1",
                (project_id,),
            )
        )

    def update_status(self, iteration_id: int, status: str) -> None:
        self.db.execute(
            "UPDATE iterations SET status = ?, finished_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), iteration_id),
        )

    def increment_loops(self, iteration_id: int) -> None:
        self.db.execute(
            "UPDATE iterations SET loops_completed = loops_completed + 1 WHERE id = ?",
            (iteration_id,),
        )


class StoryRepository(BaseRepository):
    """CRUD for stories table."""

    def create(
        self,
        iteration_id: int,
        story_id: str,
        title: str,
        description: str = None,
        priority: str = None,
        estimate: str = None,
        acceptance_criteria: list = None,
        depends_on: list = None,
    ) -> int:
        cursor = self.db.execute(
            """INSERT INTO stories
               (iteration_id, story_id, title, description, priority, estimate, acceptance_criteria, depends_on)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                iteration_id,
                story_id,
                title,
                description,
                priority,
                estimate,
                json.dumps(acceptance_criteria) if acceptance_criteria else None,
                json.dumps(depends_on) if depends_on else None,
            ),
        )
        return cursor.lastrowid

    def get(self, id: int) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone("SELECT * FROM stories WHERE id = ?", (id,))
        )

    def get_by_story_id(self, iteration_id: int, story_id: str) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone(
                "SELECT * FROM stories WHERE iteration_id = ? AND story_id = ?",
                (iteration_id, story_id),
            )
        )

    def list_by_iteration(self, iteration_id: int) -> list[dict]:
        return self._to_list(
            self.db.fetchall(
                "SELECT * FROM stories WHERE iteration_id = ? ORDER BY story_id",
                (iteration_id,),
            )
        )

    def list_by_status(self, iteration_id: int, status: str) -> list[dict]:
        return self._to_list(
            self.db.fetchall(
                "SELECT * FROM stories WHERE iteration_id = ? AND status = ?",
                (iteration_id, status),
            )
        )

    def update_status(self, id: int, status: str) -> None:
        self.db.execute(
            "UPDATE stories SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), id),
        )

    def update_metadata(self, id: int, metadata: dict) -> None:
        self.db.execute(
            "UPDATE stories SET metadata = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metadata), datetime.now().isoformat(), id),
        )

    def count_by_status(self, iteration_id: int) -> dict[str, int]:
        rows = self.db.fetchall(
            "SELECT status, COUNT(*) as cnt FROM stories WHERE iteration_id = ? GROUP BY status",
            (iteration_id,),
        )
        return {r["status"]: r["cnt"] for r in rows}


class StoryAttemptRepository(BaseRepository):
    """CRUD for story_attempts table."""

    def create(
        self,
        story_id: int,
        attempt_number: int,
        role: str,
        provider: str,
        model: str,
        status: str,
        duration_ms: int = None,
        tokens_in: int = None,
        tokens_out: int = None,
        cost_usd: float = None,
        error_message: str = None,
        error_category: str = None,
        artifacts_path: str = None,
        raw_response_path: str = None,
    ) -> int:
        cursor = self.db.execute(
            """INSERT INTO story_attempts
               (story_id, attempt_number, role, provider, model, status,
                duration_ms, tokens_in, tokens_out, cost_usd,
                error_message, error_category, artifacts_path, raw_response_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                story_id,
                attempt_number,
                role,
                provider,
                model,
                status,
                duration_ms,
                tokens_in,
                tokens_out,
                cost_usd,
                error_message,
                error_category,
                artifacts_path,
                raw_response_path,
            ),
        )
        return cursor.lastrowid

    def list_by_story(self, story_id: int) -> list[dict]:
        return self._to_list(
            self.db.fetchall(
                "SELECT * FROM story_attempts WHERE story_id = ? ORDER BY attempt_number",
                (story_id,),
            )
        )

    def get_last_attempt(self, story_id: int) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone(
                "SELECT * FROM story_attempts WHERE story_id = ? ORDER BY attempt_number DESC LIMIT 1",
                (story_id,),
            )
        )

    def count_attempts(self, story_id: int, role: str = None) -> int:
        if role:
            row = self.db.fetchone(
                "SELECT COUNT(*) as cnt FROM story_attempts WHERE story_id = ? AND role = ?",
                (story_id, role),
            )
        else:
            row = self.db.fetchone(
                "SELECT COUNT(*) as cnt FROM story_attempts WHERE story_id = ?",
                (story_id,),
            )
        return row["cnt"] if row else 0


class RoleArtifactRepository(BaseRepository):
    """CRUD for role_artifacts table."""

    def create(
        self,
        project_id: int,
        role: str,
        artifact_type: str,
        content: Any,
        iteration_id: int = None,
    ) -> int:
        # Get next version
        row = self.db.fetchone(
            "SELECT MAX(version) as v FROM role_artifacts WHERE project_id = ? AND role = ? AND artifact_type = ?",
            (project_id, role, artifact_type),
        )
        version = (row["v"] or 0) + 1

        content_str = json.dumps(content) if not isinstance(content, str) else content
        cursor = self.db.execute(
            """INSERT INTO role_artifacts (project_id, iteration_id, role, artifact_type, content, version)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, iteration_id, role, artifact_type, content_str, version),
        )
        return cursor.lastrowid

    def get_latest(
        self, project_id: int, role: str, artifact_type: str
    ) -> Optional[dict]:
        return self._to_dict(
            self.db.fetchone(
                """SELECT * FROM role_artifacts
                   WHERE project_id = ? AND role = ? AND artifact_type = ?
                   ORDER BY version DESC LIMIT 1""",
                (project_id, role, artifact_type),
            )
        )

    def list_by_project(self, project_id: int) -> list[dict]:
        return self._to_list(
            self.db.fetchall(
                "SELECT * FROM role_artifacts WHERE project_id = ? ORDER BY created_at",
                (project_id,),
            )
        )


class EventLogRepository(BaseRepository):
    """CRUD for event_log table."""

    def log(
        self,
        event_type: str,
        message: str = None,
        project_id: int = None,
        iteration_id: int = None,
        story_id: int = None,
        role: str = None,
        severity: str = "info",
        payload: dict = None,
    ) -> int:
        cursor = self.db.execute(
            """INSERT INTO event_log
               (project_id, iteration_id, story_id, event_type, role, severity, message, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                iteration_id,
                story_id,
                event_type,
                role,
                severity,
                message,
                json.dumps(payload) if payload else None,
            ),
        )
        return cursor.lastrowid

    def list_recent(self, limit: int = 100, project_id: int = None) -> list[dict]:
        if project_id:
            return self._to_list(
                self.db.fetchall(
                    "SELECT * FROM event_log WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (project_id, limit),
                )
            )
        return self._to_list(
            self.db.fetchall(
                "SELECT * FROM event_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        )

    def list_by_type(
        self, event_type: str, project_id: int = None, limit: int = 100
    ) -> list[dict]:
        if project_id:
            return self._to_list(
                self.db.fetchall(
                    "SELECT * FROM event_log WHERE event_type = ? AND project_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (event_type, project_id, limit),
                )
            )
        return self._to_list(
            self.db.fetchall(
                "SELECT * FROM event_log WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            )
        )

    def list_errors(self, project_id: int = None, limit: int = 50) -> list[dict]:
        if project_id:
            return self._to_list(
                self.db.fetchall(
                    "SELECT * FROM event_log WHERE severity = 'error' AND project_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (project_id, limit),
                )
            )
        return self._to_list(
            self.db.fetchall(
                "SELECT * FROM event_log WHERE severity = 'error' ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        )
