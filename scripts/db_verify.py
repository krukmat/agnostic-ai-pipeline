"""
Fase 3: Script de verificación dual-write.

Compara datos entre YAML files y base de datos SQLite para validar
consistencia durante el período de dual-write.

Usage:
    python scripts/db_verify.py                    # Verificar última iteración
    python scripts/db_verify.py --iteration-id 5   # Verificar iteración específica
    python scripts/db_verify.py --project test-proj # Verificar proyecto específico
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.db.storage import Database, get_db, is_db_enabled
from src.db.repository import (
    ProjectRepository,
    IterationRepository,
    StoryRepository,
    StoryAttemptRepository,
    RoleArtifactRepository,
)
from logger import logger


def verify_stories(
    db: Database,
    iteration_id: int,
    yaml_path: Path,
) -> Dict[str, Any]:
    """
    Compare stories between YAML file and database.

    Task: database-layer - Fase 3 verification

    Args:
        db: Database connection
        iteration_id: ID of iteration to verify
        yaml_path: Path to stories.yaml file

    Returns:
        Dict with verification results
    """
    result = {
        "status": "ok",
        "yaml_count": 0,
        "db_count": 0,
        "missing_in_db": [],
        "missing_in_yaml": [],
        "discrepancies": [],
        "error": None,
    }

    # Load YAML stories
    if not yaml_path.exists():
        result["status"] = "error"
        result["error"] = f"YAML file not found: {yaml_path}"
        return result

    try:
        yaml_content = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        result["status"] = "error"
        result["error"] = f"YAML parse error: {e}"
        return result

    # Handle both formats: {"stories": [...]} or just [...]
    if isinstance(yaml_content, list):
        yaml_stories = yaml_content
    else:
        yaml_stories = yaml_content.get("stories", [])
    result["yaml_count"] = len(yaml_stories)

    # Build YAML story map
    yaml_map: Dict[str, Dict] = {}
    for story in yaml_stories:
        story_id = story.get("id")
        if story_id:
            yaml_map[story_id] = story

    # Load DB stories
    stories_repo = StoryRepository(db)
    db_stories = stories_repo.list_by_iteration(iteration_id)
    result["db_count"] = len(db_stories)

    # Build DB story map
    db_map: Dict[str, Dict] = {}
    for story in db_stories:
        db_map[story["story_id"]] = story

    # Find missing in DB
    for story_id in yaml_map:
        if story_id not in db_map:
            result["missing_in_db"].append(story_id)

    # Find missing in YAML
    for story_id in db_map:
        if story_id not in yaml_map:
            result["missing_in_yaml"].append(story_id)

    # Priority normalization map (same as in dual_write.py)
    def normalize_priority(p):
        if not p:
            return None
        p = str(p).strip().upper()
        if p in ("P0", "P1", "P2", "P3"):
            return p
        if p in ("0", "1", "2", "3"):
            return f"P{p}"
        priority_map = {
            "HIGH": "P1", "ALTA": "P1",
            "MEDIUM": "P2", "MED": "P2", "MEDIA": "P2",
            "LOW": "P3", "BAJA": "P3",
            "CRITICAL": "P0", "CRITICA": "P0",
        }
        return priority_map.get(p)

    # Status normalization
    def normalize_status(s):
        if not s:
            return "todo"
        s = str(s).strip().lower().replace(" ", "")
        # Map common variations
        status_map = {
            "todo": "todo", "to_do": "todo",
            "doing": "doing", "in_progress": "doing", "inprogress": "doing",
            "done": "done", "completed": "done",
            "dev_ok": "dev_ok", "devok": "dev_ok",
            "in_review": "in_review", "inreview": "in_review",
            "blocked_dev": "blocked_dev", "blockeddev": "blocked_dev",
        }
        return status_map.get(s, s)

    # Compare common stories
    common_ids = set(yaml_map.keys()) & set(db_map.keys())
    for story_id in common_ids:
        yaml_story = yaml_map[story_id]
        db_story = db_map[story_id]

        # Compare fields
        fields_to_compare = [
            ("title", "title"),
            ("description", "description"),
            ("priority", "priority"),
            ("estimate", "estimate"),
            ("status", "status"),
        ]

        for yaml_field, db_field in fields_to_compare:
            yaml_val = yaml_story.get(yaml_field)
            db_val = db_story.get(db_field)

            # Normalize None vs empty string
            if yaml_val is None:
                yaml_val = ""
            if db_val is None:
                db_val = ""

            # Normalize priority for comparison
            if yaml_field == "priority":
                yaml_val = normalize_priority(yaml_val) or ""
                db_val = normalize_priority(db_val) or ""

            # Normalize status for comparison
            if yaml_field == "status":
                yaml_val = normalize_status(yaml_val)
                db_val = normalize_status(db_val)

            if str(yaml_val) != str(db_val):
                result["discrepancies"].append({
                    "story_id": story_id,
                    "field": yaml_field,
                    "yaml_value": yaml_val,
                    "db_value": db_val,
                })

    # Set status
    if result["missing_in_db"] or result["missing_in_yaml"] or result["discrepancies"]:
        result["status"] = "mismatch"

    return result


def verify_artifacts(
    db: Database,
    project_id: int,
    artifact_files: Dict[str, Path],
) -> Dict[str, Any]:
    """
    Compare artifacts between files and database.

    Task: database-layer - Fase 3 verification

    Args:
        db: Database connection
        project_id: Project ID to verify
        artifact_files: Dict mapping "role:type" to file paths

    Returns:
        Dict with verification results
    """
    result = {
        "status": "ok",
        "verified_count": 0,
        "discrepancies": [],
        "errors": [],
    }

    artifacts_repo = RoleArtifactRepository(db)

    for key, file_path in artifact_files.items():
        role, artifact_type = key.split(":", 1)

        # Load file content
        if not file_path.exists():
            result["errors"].append(f"File not found: {file_path}")
            continue

        try:
            file_content = file_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            result["errors"].append(f"Error reading {file_path}: {e}")
            continue

        # Get DB artifact
        db_artifact = artifacts_repo.get_latest(project_id, role, artifact_type)

        if not db_artifact:
            result["discrepancies"].append({
                "artifact": key,
                "issue": "missing_in_db",
                "file_path": str(file_path),
            })
            continue

        db_content = db_artifact["content"].strip()

        # Compare content (normalize whitespace)
        if file_content != db_content:
            # Try parsing as YAML/JSON for semantic comparison
            try:
                file_data = yaml.safe_load(file_content)
                db_data = yaml.safe_load(db_content)

                if file_data != db_data:
                    result["discrepancies"].append({
                        "artifact": key,
                        "issue": "content_mismatch",
                        "file_path": str(file_path),
                    })
            except:
                # Raw comparison failed
                result["discrepancies"].append({
                    "artifact": key,
                    "issue": "content_mismatch",
                    "file_path": str(file_path),
                })

        result["verified_count"] += 1

    if result["discrepancies"] or result["errors"]:
        result["status"] = "mismatch"

    return result


def verify_integrity(db: Database) -> Dict[str, Any]:
    """
    Verify referential integrity of database.

    Task: database-layer - Fase 3 verification

    Returns:
        Dict with integrity check results
    """
    result = {
        "status": "ok",
        "orphan_iterations": 0,
        "orphan_stories": 0,
        "orphan_attempts": 0,
        "orphan_artifacts": 0,
        "details": [],
    }

    # Check orphan iterations (iteration without valid project)
    orphan_iterations = db.fetchall("""
        SELECT i.id, i.project_id
        FROM iterations i
        LEFT JOIN projects p ON i.project_id = p.id
        WHERE p.id IS NULL
    """)
    result["orphan_iterations"] = len(orphan_iterations)
    if orphan_iterations:
        result["details"].append(f"Orphan iterations: {[r['id'] for r in orphan_iterations]}")

    # Check orphan stories (story without valid iteration)
    orphan_stories = db.fetchall("""
        SELECT s.id, s.iteration_id, s.story_id
        FROM stories s
        LEFT JOIN iterations i ON s.iteration_id = i.id
        WHERE i.id IS NULL
    """)
    result["orphan_stories"] = len(orphan_stories)
    if orphan_stories:
        result["details"].append(f"Orphan stories: {[r['story_id'] for r in orphan_stories]}")

    # Check orphan attempts (attempt without valid story)
    orphan_attempts = db.fetchall("""
        SELECT sa.id, sa.story_id
        FROM story_attempts sa
        LEFT JOIN stories s ON sa.story_id = s.id
        WHERE s.id IS NULL
    """)
    result["orphan_attempts"] = len(orphan_attempts)
    if orphan_attempts:
        result["details"].append(f"Orphan attempts: {[r['id'] for r in orphan_attempts]}")

    # Check orphan artifacts (artifact without valid project)
    orphan_artifacts = db.fetchall("""
        SELECT ra.id, ra.project_id, ra.role, ra.artifact_type
        FROM role_artifacts ra
        LEFT JOIN projects p ON ra.project_id = p.id
        WHERE p.id IS NULL
    """)
    result["orphan_artifacts"] = len(orphan_artifacts)
    if orphan_artifacts:
        result["details"].append(f"Orphan artifacts: {[r['id'] for r in orphan_artifacts]}")

    # Set status
    if any([
        result["orphan_iterations"],
        result["orphan_stories"],
        result["orphan_attempts"],
        result["orphan_artifacts"],
    ]):
        result["status"] = "error"

    return result


def run_verification(
    db: Database,
    project_id: int,
    iteration_id: int,
    stories_yaml_path: Path,
    artifact_files: Optional[Dict[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Run complete verification.

    Task: database-layer - Fase 3 verification

    Args:
        db: Database connection
        project_id: Project to verify
        iteration_id: Iteration to verify
        stories_yaml_path: Path to stories.yaml
        artifact_files: Optional dict of artifact files to verify

    Returns:
        Complete verification report
    """
    report = {
        "project_id": project_id,
        "iteration_id": iteration_id,
        "stories": None,
        "artifacts": None,
        "integrity": None,
        "overall_status": "ok",
    }

    # Verify stories
    report["stories"] = verify_stories(db, iteration_id, stories_yaml_path)

    # Verify artifacts if provided
    if artifact_files:
        report["artifacts"] = verify_artifacts(db, project_id, artifact_files)

    # Verify integrity
    report["integrity"] = verify_integrity(db)

    # Determine overall status
    statuses = []
    if report["stories"]:
        statuses.append(report["stories"]["status"])
    if report["artifacts"]:
        statuses.append(report["artifacts"]["status"])
    if report["integrity"]:
        statuses.append(report["integrity"]["status"])

    if "error" in statuses:
        report["overall_status"] = "error"
    elif "mismatch" in statuses:
        report["overall_status"] = "mismatch"
    else:
        report["overall_status"] = "ok"

    return report


def get_latest_iteration(db: Database) -> Optional[Dict[str, int]]:
    """Get the most recent iteration with its project ID."""
    row = db.fetchone("""
        SELECT i.id as iteration_id, i.project_id, p.name as project_name
        FROM iterations i
        JOIN projects p ON i.project_id = p.id
        ORDER BY i.started_at DESC
        LIMIT 1
    """)
    return dict(row) if row else None


def main():
    """CLI entry point for db_verify."""
    parser = argparse.ArgumentParser(
        description="Verify dual-write consistency between YAML and database"
    )
    parser.add_argument(
        "--iteration-id", "-i",
        type=int,
        help="Iteration ID to verify (default: latest)"
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="Project name to verify"
    )
    parser.add_argument(
        "--stories-yaml",
        type=Path,
        default=BASE_DIR / "planning" / "stories.yaml",
        help="Path to stories.yaml (default: planning/stories.yaml)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Check if DB is enabled
    if not is_db_enabled():
        logger.error("[VERIFY] Database is not enabled. Set database.enabled: true in config.yaml")
        sys.exit(1)

    db = get_db()

    # Determine what to verify
    iteration_id = args.iteration_id
    project_id = None

    if args.project:
        # Find project by name
        projects = ProjectRepository(db)
        project = projects.get_by_name(args.project)
        if not project:
            logger.error(f"[VERIFY] Project not found: {args.project}")
            sys.exit(1)
        project_id = project["id"]

        # Get latest iteration for this project
        if not iteration_id:
            iterations = IterationRepository(db)
            latest = iterations.get_latest(project_id)
            if latest:
                iteration_id = latest["id"]

    if not iteration_id:
        # Get latest iteration overall
        latest = get_latest_iteration(db)
        if not latest:
            logger.error("[VERIFY] No iterations found in database")
            sys.exit(1)
        iteration_id = latest["iteration_id"]
        project_id = latest["project_id"]
        if args.verbose:
            logger.info(f"[VERIFY] Using latest iteration: {iteration_id} (project: {latest.get('project_name')})")

    if not project_id:
        # Get project from iteration
        iterations = IterationRepository(db)
        iteration = iterations.get(iteration_id)
        if not iteration:
            logger.error(f"[VERIFY] Iteration not found: {iteration_id}")
            sys.exit(1)
        project_id = iteration["project_id"]

    # Build artifact files map
    planning_dir = BASE_DIR / "planning"
    artifact_files = {}

    artifact_mapping = [
        ("ba", "requirements", "requirements.yaml"),
        ("po", "product_vision", "product_vision.yaml"),
        ("po", "product_owner_review", "product_owner_review.yaml"),
        ("architect", "architecture", "architecture.yaml"),
        ("architect", "stories", "stories.yaml"),
    ]

    for role, artifact_type, filename in artifact_mapping:
        file_path = planning_dir / filename
        if file_path.exists():
            artifact_files[f"{role}:{artifact_type}"] = file_path

    # Run verification
    report = run_verification(
        db,
        project_id=project_id,
        iteration_id=iteration_id,
        stories_yaml_path=args.stories_yaml,
        artifact_files=artifact_files if artifact_files else None,
    )

    # Output
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print(f"DUAL-WRITE VERIFICATION REPORT")
        print(f"{'='*60}")
        print(f"Project ID: {project_id}")
        print(f"Iteration ID: {iteration_id}")
        print(f"Overall Status: {report['overall_status'].upper()}")
        print()

        # Stories section
        stories = report.get("stories", {})
        print(f"STORIES:")
        print(f"  Status: {stories.get('status', 'N/A')}")
        print(f"  YAML count: {stories.get('yaml_count', 0)}")
        print(f"  DB count: {stories.get('db_count', 0)}")

        if stories.get("missing_in_db"):
            print(f"  Missing in DB: {stories['missing_in_db']}")
        if stories.get("missing_in_yaml"):
            print(f"  Missing in YAML: {stories['missing_in_yaml']}")
        if stories.get("discrepancies"):
            print(f"  Discrepancies: {len(stories['discrepancies'])}")
            if args.verbose:
                for d in stories["discrepancies"]:
                    print(f"    - {d['story_id']}.{d['field']}: YAML={d['yaml_value']} DB={d['db_value']}")
        print()

        # Integrity section
        integrity = report.get("integrity", {})
        print(f"INTEGRITY:")
        print(f"  Status: {integrity.get('status', 'N/A')}")
        print(f"  Orphan iterations: {integrity.get('orphan_iterations', 0)}")
        print(f"  Orphan stories: {integrity.get('orphan_stories', 0)}")
        print(f"  Orphan attempts: {integrity.get('orphan_attempts', 0)}")
        print()

        # Artifacts section
        artifacts = report.get("artifacts")
        if artifacts:
            print(f"ARTIFACTS:")
            print(f"  Status: {artifacts.get('status', 'N/A')}")
            print(f"  Verified: {artifacts.get('verified_count', 0)}")
            if artifacts.get("discrepancies"):
                print(f"  Discrepancies: {len(artifacts['discrepancies'])}")

        print(f"\n{'='*60}")

        # Exit code
        if report["overall_status"] == "error":
            sys.exit(2)
        elif report["overall_status"] == "mismatch":
            sys.exit(1)


if __name__ == "__main__":
    main()
