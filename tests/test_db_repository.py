"""Tests for database repository layer."""
import pytest
import tempfile
from pathlib import Path

from src.db.storage import Database, reset_db
from src.db.schema import create_schema
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


class TestProjectRepository:
    def test_create_and_get(self, db):
        repo = ProjectRepository(db)
        pid = repo.create("test-project", "A test concept")
        assert pid > 0

        project = repo.get(pid)
        assert project["name"] == "test-project"
        assert project["concept"] == "A test concept"
        assert project["status"] == "active"

    def test_get_by_name(self, db):
        repo = ProjectRepository(db)
        repo.create("my-project", "concept")

        project = repo.get_by_name("my-project")
        assert project is not None
        assert project["name"] == "my-project"

    def test_list_all(self, db):
        repo = ProjectRepository(db)
        repo.create("p1", "c1")
        repo.create("p2", "c2")

        projects = repo.list_all()
        assert len(projects) == 2

    def test_update_status(self, db):
        repo = ProjectRepository(db)
        pid = repo.create("proj", "concept")
        repo.update_status(pid, "completed")

        project = repo.get(pid)
        assert project["status"] == "completed"


class TestIterationRepository:
    def test_create_and_get(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid, loops_requested=5)

        iteration = iter_repo.get(iid)
        assert iteration["project_id"] == pid
        assert iteration["loops_requested"] == 5
        assert iteration["status"] == "running"

    def test_get_latest(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)

        pid = proj_repo.create("proj", "concept")
        iter_repo.create(pid, loops_requested=1)
        iid2 = iter_repo.create(pid, loops_requested=3)

        latest = iter_repo.get_latest(pid)
        assert latest["id"] == iid2

    def test_increment_loops(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid)

        iter_repo.increment_loops(iid)
        iter_repo.increment_loops(iid)

        iteration = iter_repo.get(iid)
        assert iteration["loops_completed"] == 2


class TestStoryRepository:
    def test_create_and_get(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)
        story_repo = StoryRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid)
        sid = story_repo.create(
            iid, "S1", "First story",
            description="Description",
            priority="P1",
            estimate="M",
        )

        story = story_repo.get(sid)
        assert story["story_id"] == "S1"
        assert story["title"] == "First story"
        assert story["priority"] == "P1"

    def test_list_by_iteration(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)
        story_repo = StoryRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid)
        story_repo.create(iid, "S1", "Story 1")
        story_repo.create(iid, "S2", "Story 2")
        story_repo.create(iid, "S3", "Story 3")

        stories = story_repo.list_by_iteration(iid)
        assert len(stories) == 3

    def test_update_status(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)
        story_repo = StoryRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid)
        sid = story_repo.create(iid, "S1", "Story")

        story_repo.update_status(sid, "done")
        story = story_repo.get(sid)
        assert story["status"] == "done"

    def test_count_by_status(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)
        story_repo = StoryRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid)

        s1 = story_repo.create(iid, "S1", "Story 1")
        s2 = story_repo.create(iid, "S2", "Story 2")
        story_repo.create(iid, "S3", "Story 3")

        story_repo.update_status(s1, "done")
        story_repo.update_status(s2, "done")

        counts = story_repo.count_by_status(iid)
        assert counts.get("done") == 2
        assert counts.get("todo") == 1


class TestStoryAttemptRepository:
    def test_create_and_list(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)
        story_repo = StoryRepository(db)
        attempt_repo = StoryAttemptRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid)
        sid = story_repo.create(iid, "S1", "Story")

        attempt_repo.create(
            sid, 1, "dev", "vertex_sdk", "gemini-2.5-flash", "error",
            duration_ms=5000, tokens_in=100, tokens_out=500,
            error_message="Parse error"
        )
        attempt_repo.create(
            sid, 2, "dev", "openai", "gpt-4", "success",
            duration_ms=3000, tokens_in=100, tokens_out=800
        )

        attempts = attempt_repo.list_by_story(sid)
        assert len(attempts) == 2
        assert attempts[0]["status"] == "error"
        assert attempts[1]["status"] == "success"

    def test_count_attempts(self, db):
        proj_repo = ProjectRepository(db)
        iter_repo = IterationRepository(db)
        story_repo = StoryRepository(db)
        attempt_repo = StoryAttemptRepository(db)

        pid = proj_repo.create("proj", "concept")
        iid = iter_repo.create(pid)
        sid = story_repo.create(iid, "S1", "Story")

        attempt_repo.create(sid, 1, "dev", "ollama", "mistral", "error")
        attempt_repo.create(sid, 2, "dev", "openai", "gpt-4", "success")
        attempt_repo.create(sid, 1, "qa", "ollama", "mistral", "success")

        assert attempt_repo.count_attempts(sid) == 3
        assert attempt_repo.count_attempts(sid, role="dev") == 2


class TestRoleArtifactRepository:
    def test_create_with_versioning(self, db):
        proj_repo = ProjectRepository(db)
        artifact_repo = RoleArtifactRepository(db)

        pid = proj_repo.create("proj", "concept")

        artifact_repo.create(pid, "ba", "requirements", {"reqs": ["r1"]})
        artifact_repo.create(pid, "ba", "requirements", {"reqs": ["r1", "r2"]})

        latest = artifact_repo.get_latest(pid, "ba", "requirements")
        assert latest["version"] == 2

    def test_list_by_project(self, db):
        proj_repo = ProjectRepository(db)
        artifact_repo = RoleArtifactRepository(db)

        pid = proj_repo.create("proj", "concept")

        artifact_repo.create(pid, "ba", "requirements", {})
        artifact_repo.create(pid, "po", "product_vision", {})
        artifact_repo.create(pid, "architect", "stories", {})

        artifacts = artifact_repo.list_by_project(pid)
        assert len(artifacts) == 3


class TestEventLogRepository:
    def test_log_and_list(self, db):
        proj_repo = ProjectRepository(db)
        event_repo = EventLogRepository(db)

        pid = proj_repo.create("proj", "concept")

        event_repo.log("role_start", "BA started", project_id=pid, role="ba")
        event_repo.log("role_end", "BA finished", project_id=pid, role="ba")
        event_repo.log("error", "Something failed", project_id=pid, severity="error")

        events = event_repo.list_recent(project_id=pid)
        assert len(events) == 3

    def test_list_errors(self, db):
        proj_repo = ProjectRepository(db)
        event_repo = EventLogRepository(db)

        pid = proj_repo.create("proj", "concept")

        event_repo.log("info", "All good", project_id=pid)
        event_repo.log("error", "Failed 1", project_id=pid, severity="error")
        event_repo.log("error", "Failed 2", project_id=pid, severity="error")

        errors = event_repo.list_errors(project_id=pid)
        assert len(errors) == 2
