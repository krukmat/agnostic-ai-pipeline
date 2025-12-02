"""Tests for dual-write functionality."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.db.storage import Database, reset_db
from src.db.schema import create_schema
from src.db.dual_write import (
    DualWriteContext,
    db_enabled,
    get_current_context,
    set_current_context,
    get_or_create_adhoc_context,
)
from src.db.repository import (
    ProjectRepository,
    IterationRepository,
    StoryRepository,
    StoryAttemptRepository,
    RoleArtifactRepository,
    EventLogRepository,
)


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    reset_db()
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = Database(db_path)
        create_schema(database)
        yield database
        database.close()
    reset_db()


@pytest.fixture
def mock_db_enabled():
    """Mock db_enabled to return True."""
    with patch("src.db.dual_write.is_db_enabled", return_value=True):
        with patch("src.db.dual_write.get_db") as mock_get_db:
            yield mock_get_db


class TestDualWriteContext:
    """Tests for DualWriteContext class."""

    def test_context_creates_project(self, db, mock_db_enabled):
        """Test that entering context creates a project."""
        mock_db_enabled.return_value = db

        ctx = DualWriteContext("test-project", "Test concept")
        ctx.__enter__()

        assert ctx.enabled
        assert ctx.project_id is not None

        # Verify project exists in DB
        projects = ProjectRepository(db)
        project = projects.get(ctx.project_id)
        assert project["name"] == "test-project"
        assert project["concept"] == "Test concept"

        ctx.__exit__(None, None, None)

    def test_context_reuses_existing_project(self, db, mock_db_enabled):
        """Test that context reuses existing project by name."""
        mock_db_enabled.return_value = db

        # Create first context
        ctx1 = DualWriteContext("same-project", "Concept 1")
        ctx1.__enter__()
        project_id_1 = ctx1.project_id
        ctx1.__exit__(None, None, None)

        # Create second context with same name
        ctx2 = DualWriteContext("same-project", "Concept 2")
        ctx2.__enter__()
        project_id_2 = ctx2.project_id
        ctx2.__exit__(None, None, None)

        assert project_id_1 == project_id_2

    def test_start_iteration(self, db, mock_db_enabled):
        """Test starting an iteration."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            iteration_id = ctx.start_iteration(loops_requested=5)

            assert iteration_id is not None
            assert ctx.iteration_id == iteration_id

            # Verify iteration in DB
            iterations = IterationRepository(db)
            iteration = iterations.get(iteration_id)
            assert iteration["loops_requested"] == 5
            assert iteration["status"] == "running"

    def test_end_iteration(self, db, mock_db_enabled):
        """Test ending an iteration."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            ctx.end_iteration("completed")

            iterations = IterationRepository(db)
            iteration = iterations.get(ctx.iteration_id)
            assert iteration["status"] == "completed"

    def test_log_event(self, db, mock_db_enabled):
        """Test logging events."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            event_id = ctx.log_event(
                "role_start",
                "BA started processing",
                role="ba",
                severity="info"
            )

            assert event_id is not None

            events = EventLogRepository(db)
            # Get recent events - start_iteration also logs, so check for our specific event
            recent = events.list_by_type("role_start", project_id=ctx.project_id, limit=1)
            assert len(recent) == 1
            assert recent[0]["event_type"] == "role_start"
            assert recent[0]["role"] == "ba"

    def test_save_artifact(self, db, mock_db_enabled):
        """Test saving role artifacts."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            artifact_id = ctx.save_artifact(
                "ba",
                "requirements",
                {"functional": ["req1", "req2"]}
            )

            assert artifact_id is not None

            artifacts = RoleArtifactRepository(db)
            latest = artifacts.get_latest(ctx.project_id, "ba", "requirements")
            assert latest is not None
            assert '"functional"' in latest["content"]

    def test_artifact_versioning(self, db, mock_db_enabled):
        """Test that artifacts are versioned."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.save_artifact("ba", "requirements", {"v": 1})
            ctx.save_artifact("ba", "requirements", {"v": 2})

            artifacts = RoleArtifactRepository(db)
            latest = artifacts.get_latest(ctx.project_id, "ba", "requirements")
            assert latest["version"] == 2

    def test_create_story(self, db, mock_db_enabled):
        """Test creating a single story."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            story_db_id = ctx.create_story(
                story_id="S1",
                title="First Story",
                description="Description",
                priority="P1",
                estimate="M"
            )

            assert story_db_id is not None

            stories = StoryRepository(db)
            story = stories.get(story_db_id)
            assert story["story_id"] == "S1"
            assert story["title"] == "First Story"
            assert story["priority"] == "P1"

    def test_create_stories_from_list(self, db, mock_db_enabled):
        """Test creating multiple stories from a list."""
        mock_db_enabled.return_value = db

        stories_list = [
            {"id": "S1", "title": "Story 1", "priority": "P1"},
            {"id": "S2", "title": "Story 2", "priority": "P2"},
            {"id": "S3", "title": "Story 3", "description": "Desc"},
        ]

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            mapping = ctx.create_stories_from_list(stories_list)

            assert len(mapping) == 3
            assert "S1" in mapping
            assert "S2" in mapping
            assert "S3" in mapping

            stories = StoryRepository(db)
            all_stories = stories.list_by_iteration(ctx.iteration_id)
            assert len(all_stories) == 3

    def test_update_story_status(self, db, mock_db_enabled):
        """Test updating story status."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            ctx.create_story("S1", "Story 1")

            ctx.update_story_status("S1", "done")

            stories = StoryRepository(db)
            story = stories.get_by_story_id(ctx.iteration_id, "S1")
            assert story["status"] == "done"

    def test_log_attempt(self, db, mock_db_enabled):
        """Test logging a story attempt."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            ctx.create_story("S1", "Story 1")

            attempt_id = ctx.log_attempt(
                story_id="S1",
                role="dev",
                provider="vertex_sdk",
                model="gemini-2.5-pro",
                status="success",
                duration_ms=5000,
                tokens_in=100,
                tokens_out=500
            )

            assert attempt_id is not None

            db_story_id = ctx.get_story_db_id("S1")
            attempts = StoryAttemptRepository(db)
            story_attempts = attempts.list_by_story(db_story_id)
            assert len(story_attempts) == 1
            assert story_attempts[0]["provider"] == "vertex_sdk"
            assert story_attempts[0]["tokens_in"] == 100

    def test_log_multiple_attempts(self, db, mock_db_enabled):
        """Test logging multiple attempts increments attempt_number."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            ctx.create_story("S1", "Story 1")

            ctx.log_attempt("S1", "dev", "ollama", "mistral", "error", error_message="Parse error")
            ctx.log_attempt("S1", "dev", "vertex_sdk", "gemini", "success")

            db_story_id = ctx.get_story_db_id("S1")
            attempts = StoryAttemptRepository(db)
            story_attempts = attempts.list_by_story(db_story_id)

            assert len(story_attempts) == 2
            assert story_attempts[0]["attempt_number"] == 1
            assert story_attempts[1]["attempt_number"] == 2

    def test_get_story_counts(self, db, mock_db_enabled):
        """Test getting story counts by status."""
        mock_db_enabled.return_value = db

        with DualWriteContext("test-project", "Test") as ctx:
            ctx.start_iteration()
            ctx.create_story("S1", "Story 1")
            ctx.create_story("S2", "Story 2")
            ctx.create_story("S3", "Story 3")

            ctx.update_story_status("S1", "done")
            ctx.update_story_status("S2", "done")

            counts = ctx.get_story_counts()
            assert counts.get("done") == 2
            assert counts.get("todo") == 1

    def test_context_disabled_when_db_not_enabled(self):
        """Test that context is disabled when DB is not enabled."""
        with patch("src.db.dual_write.is_db_enabled", return_value=False):
            ctx = DualWriteContext("test", "test")
            ctx.__enter__()

            assert not ctx.enabled
            assert ctx.project_id is None

            # Operations should be no-ops
            assert ctx.save_artifact("ba", "req", {}) is None
            assert ctx.log_event("test", "msg") is None

            ctx.__exit__(None, None, None)


class TestGlobalContext:
    """Tests for global context management."""

    def test_set_and_get_context(self, db, mock_db_enabled):
        """Test setting and getting the global context."""
        mock_db_enabled.return_value = db

        assert get_current_context() is None

        ctx = DualWriteContext("test", "test")
        ctx.__enter__()
        set_current_context(ctx)

        assert get_current_context() is ctx

        set_current_context(None)
        ctx.__exit__(None, None, None)

        assert get_current_context() is None


class TestDbEnabled:
    """Tests for db_enabled function."""

    def test_db_enabled_returns_config_value(self):
        """Test db_enabled reads from config."""
        with patch("src.db.dual_write.is_db_enabled", return_value=True):
            assert db_enabled() is True

        with patch("src.db.dual_write.is_db_enabled", return_value=False):
            assert db_enabled() is False


class TestAdhocContext:
    """Tests for get_or_create_adhoc_context helper."""

    def test_returns_none_when_db_disabled(self):
        with patch("src.db.dual_write.is_db_enabled", return_value=False):
            ctx = get_or_create_adhoc_context(role="dev", concept="c")
            assert ctx is None

    def test_reuses_existing_context(self):
        dummy_ctx = object()
        with patch("src.db.dual_write.get_current_context", return_value=dummy_ctx):
            ctx = get_or_create_adhoc_context(role="dev", concept="c")
            assert ctx is dummy_ctx

    def test_creates_new_context_and_starts_iteration(self):
        mock_ctx = MagicMock()
        mock_ctx.iteration_id = None
        with patch("src.db.dual_write.is_db_enabled", return_value=True), patch(
            "src.db.dual_write.DualWriteContext", return_value=mock_ctx
        ) as mock_cls:
            ctx = get_or_create_adhoc_context(role="dev", concept="c")
            mock_cls.assert_called_once_with("adhoc-dev", "c")
            mock_ctx.__enter__.assert_called_once()
            mock_ctx.start_iteration.assert_called_once()
            assert ctx is mock_ctx
