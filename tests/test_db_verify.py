"""Tests for db_verify.py - Fase 3: Verificación dual-write."""
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.db.storage import Database, reset_db
from src.db.schema import create_schema
from src.db.repository import (
    ProjectRepository,
    IterationRepository,
    StoryRepository,
    StoryAttemptRepository,
    RoleArtifactRepository,
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
def temp_planning_dir():
    """Create a temporary planning directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestVerifyStories:
    """Tests for story verification between YAML and DB."""

    def test_verify_matching_stories(self, db, temp_planning_dir):
        """Test verification passes when YAML and DB match."""
        from scripts.db_verify import verify_stories

        # Create project and iteration in DB
        projects = ProjectRepository(db)
        iterations = IterationRepository(db)
        stories_repo = StoryRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)

        # Create stories in DB
        stories_repo.create(iteration_id, "S1", "Story 1", "Desc 1", "P1", "M")
        stories_repo.create(iteration_id, "S2", "Story 2", "Desc 2", "P2", "S")

        # Create matching YAML
        stories_yaml = {
            "stories": [
                {"id": "S1", "title": "Story 1", "description": "Desc 1", "priority": "P1", "estimate": "M"},
                {"id": "S2", "title": "Story 2", "description": "Desc 2", "priority": "P2", "estimate": "S"},
            ]
        }
        yaml_path = temp_planning_dir / "stories.yaml"
        yaml_path.write_text(yaml.safe_dump(stories_yaml), encoding="utf-8")

        # Verify should pass
        result = verify_stories(db, iteration_id, yaml_path)
        assert result["status"] == "ok"
        assert result["yaml_count"] == 2
        assert result["db_count"] == 2
        assert len(result["discrepancies"]) == 0

    def test_verify_missing_in_db(self, db, temp_planning_dir):
        """Test verification detects stories in YAML but not in DB."""
        from scripts.db_verify import verify_stories

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)
        stories_repo = StoryRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)

        # Only one story in DB
        stories_repo.create(iteration_id, "S1", "Story 1")

        # Two stories in YAML
        stories_yaml = {
            "stories": [
                {"id": "S1", "title": "Story 1"},
                {"id": "S2", "title": "Story 2"},
            ]
        }
        yaml_path = temp_planning_dir / "stories.yaml"
        yaml_path.write_text(yaml.safe_dump(stories_yaml), encoding="utf-8")

        result = verify_stories(db, iteration_id, yaml_path)
        assert result["status"] == "mismatch"
        assert "S2" in result["missing_in_db"]

    def test_verify_missing_in_yaml(self, db, temp_planning_dir):
        """Test verification detects stories in DB but not in YAML."""
        from scripts.db_verify import verify_stories

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)
        stories_repo = StoryRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)

        # Two stories in DB
        stories_repo.create(iteration_id, "S1", "Story 1")
        stories_repo.create(iteration_id, "S2", "Story 2")

        # Only one in YAML
        stories_yaml = {
            "stories": [
                {"id": "S1", "title": "Story 1"},
            ]
        }
        yaml_path = temp_planning_dir / "stories.yaml"
        yaml_path.write_text(yaml.safe_dump(stories_yaml), encoding="utf-8")

        result = verify_stories(db, iteration_id, yaml_path)
        assert result["status"] == "mismatch"
        assert "S2" in result["missing_in_yaml"]

    def test_verify_status_mismatch(self, db, temp_planning_dir):
        """Test verification detects status differences."""
        from scripts.db_verify import verify_stories

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)
        stories_repo = StoryRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)

        # Story in DB with status "done"
        story_db_id = stories_repo.create(iteration_id, "S1", "Story 1")
        stories_repo.update_status(story_db_id, "done")

        # Same story in YAML with status "todo"
        stories_yaml = {
            "stories": [
                {"id": "S1", "title": "Story 1", "status": "todo"},
            ]
        }
        yaml_path = temp_planning_dir / "stories.yaml"
        yaml_path.write_text(yaml.safe_dump(stories_yaml), encoding="utf-8")

        result = verify_stories(db, iteration_id, yaml_path)
        assert result["status"] == "mismatch"
        assert len(result["discrepancies"]) > 0
        assert any(d["field"] == "status" for d in result["discrepancies"])

    def test_verify_yaml_not_found(self, db, temp_planning_dir):
        """Test verification handles missing YAML file."""
        from scripts.db_verify import verify_stories

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)

        yaml_path = temp_planning_dir / "nonexistent.yaml"

        result = verify_stories(db, iteration_id, yaml_path)
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


class TestVerifyArtifacts:
    """Tests for artifact verification between files and DB."""

    def test_verify_matching_artifacts(self, db, temp_planning_dir):
        """Test artifact verification when files match DB."""
        from scripts.db_verify import verify_artifacts

        projects = ProjectRepository(db)
        artifacts_repo = RoleArtifactRepository(db)

        project_id = projects.create("test-project", "Test concept")

        # Save artifact in DB
        content = {"functional": ["req1", "req2"]}
        artifacts_repo.create(project_id, "ba", "requirements", yaml.safe_dump(content))

        # Create matching file
        req_path = temp_planning_dir / "requirements.yaml"
        req_path.write_text(yaml.safe_dump(content), encoding="utf-8")

        result = verify_artifacts(
            db, project_id,
            artifact_files={"ba:requirements": req_path}
        )
        assert result["status"] == "ok"
        assert result["verified_count"] == 1

    def test_verify_content_mismatch(self, db, temp_planning_dir):
        """Test artifact verification detects content differences."""
        from scripts.db_verify import verify_artifacts

        projects = ProjectRepository(db)
        artifacts_repo = RoleArtifactRepository(db)

        project_id = projects.create("test-project", "Test concept")

        # Save one version in DB
        db_content = {"version": 1}
        artifacts_repo.create(project_id, "ba", "requirements", yaml.safe_dump(db_content))

        # Different version in file
        file_content = {"version": 2}
        req_path = temp_planning_dir / "requirements.yaml"
        req_path.write_text(yaml.safe_dump(file_content), encoding="utf-8")

        result = verify_artifacts(
            db, project_id,
            artifact_files={"ba:requirements": req_path}
        )
        assert result["status"] == "mismatch"
        assert len(result["discrepancies"]) > 0


class TestVerifyIntegrity:
    """Tests for referential integrity verification."""

    def test_verify_fk_integrity(self, db):
        """Test foreign key integrity check."""
        from scripts.db_verify import verify_integrity

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)
        stories_repo = StoryRepository(db)
        attempts_repo = StoryAttemptRepository(db)

        # Create valid chain
        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)
        story_db_id = stories_repo.create(iteration_id, "S1", "Story 1")
        # StoryAttemptRepository.create requires: story_id, attempt_number, role, provider, model, status
        attempts_repo.create(story_db_id, 1, "dev", "ollama", "mistral", "success")

        result = verify_integrity(db)
        assert result["status"] == "ok"
        assert result["orphan_iterations"] == 0
        assert result["orphan_stories"] == 0
        assert result["orphan_attempts"] == 0

    def test_detect_orphan_records(self, db):
        """Test detection of orphan records (manual DB corruption simulation)."""
        from scripts.db_verify import verify_integrity

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iterations.create(project_id, loops_requested=1)

        # Temporarily disable FK enforcement to create orphan
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        db.execute("PRAGMA foreign_keys = ON")

        result = verify_integrity(db)
        assert result["status"] == "error"
        assert result["orphan_iterations"] > 0


class TestFullVerification:
    """Tests for complete verification workflow."""

    def test_full_verify_report(self, db, temp_planning_dir):
        """Test complete verification generates proper report."""
        from scripts.db_verify import run_verification

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)
        stories_repo = StoryRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)
        stories_repo.create(iteration_id, "S1", "Story 1")

        # Create matching YAML
        stories_yaml = {"stories": [{"id": "S1", "title": "Story 1", "status": "todo"}]}
        yaml_path = temp_planning_dir / "stories.yaml"
        yaml_path.write_text(yaml.safe_dump(stories_yaml), encoding="utf-8")

        report = run_verification(
            db,
            project_id=project_id,
            iteration_id=iteration_id,
            stories_yaml_path=yaml_path,
        )

        assert "stories" in report
        assert "integrity" in report
        assert report["overall_status"] in ["ok", "mismatch", "error"]

    def test_verify_empty_iteration(self, db, temp_planning_dir):
        """Test verification handles empty iteration gracefully."""
        from scripts.db_verify import verify_stories

        projects = ProjectRepository(db)
        iterations = IterationRepository(db)

        project_id = projects.create("test-project", "Test concept")
        iteration_id = iterations.create(project_id, loops_requested=1)

        # Empty YAML
        stories_yaml = {"stories": []}
        yaml_path = temp_planning_dir / "stories.yaml"
        yaml_path.write_text(yaml.safe_dump(stories_yaml), encoding="utf-8")

        result = verify_stories(db, iteration_id, yaml_path)
        assert result["status"] == "ok"
        assert result["yaml_count"] == 0
        assert result["db_count"] == 0
