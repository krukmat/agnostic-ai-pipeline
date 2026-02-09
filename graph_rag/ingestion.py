"""
PipelineIngestion - Ingest pipeline artifacts into Knowledge Graph.

Pipeline artifact ingestion with MD5 deduplication.
Only ingests new/modified files to reduce ingestion cost.

LightRAG automatically extracts entities and relationships from documents.
Example: ingesting stories.yaml automatically extracts:
  - Entities: S1, S3, AuthService, Database
  - Relations: S3 --depends_on--> S1, S3 --tested_by--> test_auth.py
"""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PipelineIngestion:
    """
    Manages ingestion of pipeline artifacts into LightRAG Knowledge Graph.

    Handles:
    - Incremental ingestion (only new/modified files via MD5 hashing)
    - Multiple content types: YAML, Python, markdown, JSON
    - Metadata tagging: [Source: path] [Type: content_type]
    - Automatic entity extraction via LightRAG
    """

    CONTENT_TYPES = {
        "planning": ["*.yaml", "*.md"],  # Requirements, stories, architecture, ADRs
        "code": ["*.py", "*.js", "*.ts"],  # Generated and test code
        "artifacts": ["*.json", "*.yaml", "*.md"],  # QA reports, iteration summaries
        "docs": ["*.md"],  # Distillation reports, plans
    }

    INGESTION_STATE_FILE = ".graph_rag_ingestion_state.json"

    def __init__(self, engine, state_dir: Optional[Path] = None):
        """
        Initialize PipelineIngestion.

        Args:
            engine: GraphRAGEngine instance
            state_dir: Directory to store ingestion state (default: engine.working_dir)
        """
        self.engine = engine
        self.state_dir = state_dir or engine.working_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / self.INGESTION_STATE_FILE
        self.ingested_hashes: Dict[str, str] = self._load_ingested_hashes()

    def _load_ingested_hashes(self) -> Dict[str, str]:
        """Load previously ingested file hashes."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load ingestion state: {e}. Starting fresh.")
        return {}

    def _save_ingested_hashes(self):
        """Persist ingested file hashes."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.ingested_hashes, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ingestion state: {e}")

    async def ingest_all(self):
        """
        Ingest all pipeline sources in order:
        1. planning/ - Requirements, stories, architecture
        2. project/ - Generated code and tests
        3. artifacts/ - QA reports, iteration snapshots
        4. docs/ - Plans and reports

        Returns:
            Dict with ingestion statistics
        """
        stats = {
            "planning": await self._ingest_directory("planning/", "planning"),
            "code": await self._ingest_directory("project/", "code"),
            "artifacts": await self._ingest_directory("artifacts/", "artifacts"),
            "docs": await self._ingest_directory("docs/", "docs"),
        }

        total_new = sum(s["new_files"] for s in stats.values())
        total_skipped = sum(s["skipped_files"] for s in stats.values())

        logger.info(
            f"✓ Ingestion complete: {total_new} new files, {total_skipped} skipped"
        )
        self._save_ingested_hashes()

        return stats

    def _should_ingest_file(self, file: Path) -> bool:
        """
        Determine if a file should be ingested (not directory, not duplicate).

        Extracted helper to reduce _ingest_directory CC.

        Args:
            file: File path to check

        Returns:
            True if file should be ingested, False if directory or already ingested
        """
        # Skip directories
        if not file.is_file():
            return False

        # Check if already ingested (via MD5 hash)
        try:
            content = file.read_text(errors="ignore")
            file_hash = hashlib.md5(content.encode()).hexdigest()
            if file_hash in self.ingested_hashes:
                return False
            return True
        except Exception as e:
            logger.warning(f"Could not read {file}: {e}")
            return False

    def _build_file_metadata(self, file: Path, content: str, content_type: str) -> str:
        """
        Build tagged content with source and type metadata.

        Extracted helper to reduce _ingest_directory CC.

        Args:
            file: Source file path
            content: File content
            content_type: Type of content (planning, code, artifacts, docs)

        Returns:
            Content with [Source: path] and [Type: content_type] tags prepended
        """
        tagged_content = (
            f"[Source: {file}] [Type: {content_type}]\n\n"
            f"{content}"
        )
        return tagged_content

    async def _process_single_file(self, file: Path, content_type: str, stats: Dict) -> None:
        """Process a single file for ingestion with dedup check.

        Args:
            file: File path to process
            content_type: Type of content (planning, code, artifacts, docs)
            stats: Mutable stats dict to update in-place
        """
        if not self._should_ingest_file(file):
            if file.is_file():
                stats["skipped_files"] += 1
            return

        try:
            content = file.read_text(errors="ignore")
            file_hash = hashlib.md5(content.encode()).hexdigest()
            tagged_content = self._build_file_metadata(file, content, content_type)
            await self.engine.ingest(tagged_content)
            self.ingested_hashes[file_hash] = str(file)
            stats["new_files"] += 1
            logger.debug(f"  ✓ {file}")
        except Exception as e:
            logger.error(f"  ✗ Failed to ingest {file}: {e}")
            stats["errors"] += 1

    async def _ingest_directory(self, path: str, content_type: str) -> Dict:
        """
        Ingest all matching files in directory with deduplication.

        Args:
            path: Directory path relative to repo root
            content_type: Type of content (planning, code, artifacts, docs)

        Returns:
            Dict with {new_files, skipped_files, errors}
        """
        patterns = self.CONTENT_TYPES.get(content_type, ["*"])
        base = Path(path)
        stats = {"new_files": 0, "skipped_files": 0, "errors": 0}

        if not base.exists():
            logger.debug(f"  Skipping {path} (not found)")
            return stats

        logger.info(f"Ingesting {path}...")
        for pattern in patterns:
            for file in base.rglob(pattern):
                await self._process_single_file(file, content_type, stats)

        return stats

    async def ingest_artifact(self, artifact_text: str, metadata: dict):
        """
        Ingest a single agent artifact immediately after generation.

        Called after BA, PO, Architect, Dev, QA steps complete.

        Args:
            artifact_text: Generated artifact content
            metadata: Dict with {role, step, iteration, timestamp}

        Example:
            await ingestion.ingest_artifact(
                artifact_text=stories_yaml,
                metadata={
                    "role": "architect",
                    "step": "stories_generation",
                    "iteration": 1,
                    "timestamp": "2026-02-06T19:50:00Z"
                }
            )
        """
        try:
            role = metadata.get("role", "unknown")
            step = metadata.get("step", "unknown")
            iteration = metadata.get("iteration", 0)

            tagged_content = (
                f"[Agent: {role}] [Step: {step}] [Iteration: {iteration}]\n\n"
                f"{artifact_text}"
            )

            await self.engine.ingest(tagged_content)
            logger.info(f"✓ Ingested artifact: {role}/{step} (iteration {iteration})")

        except Exception as e:
            logger.error(f"✗ Failed to ingest artifact: {e}")
            raise

    async def ingest_text(self, text: str, source: str, content_type: str):
        """
        Ingest raw text with source tagging.

        Args:
            text: Content to ingest
            source: Source identifier (e.g., "requirements.yaml", "test_suite")
            content_type: Content type (planning, code, artifacts, docs)
        """
        try:
            tagged_content = (
                f"[Source: {source}] [Type: {content_type}]\n\n"
                f"{text}"
            )
            await self.engine.ingest(tagged_content)
            logger.debug(f"✓ Ingested text from {source}")
        except Exception as e:
            logger.error(f"✗ Failed to ingest text from {source}: {e}")
            raise


async def ingest_pipeline_artifacts(
    engine, state_dir: Optional[Path] = None
) -> Dict:
    """
    Convenience function for one-shot ingestion of all pipeline artifacts.

    Smoke test for ingestion (used in setup_graph_rag.py).

    Args:
        engine: GraphRAGEngine instance
        state_dir: Optional directory for ingestion state

    Returns:
        Ingestion statistics
    """
    ingestion = PipelineIngestion(engine, state_dir)
    return await ingestion.ingest_all()


# ============================================================================
# Auto-Ingest Hook Listener
# ============================================================================


async def _ingest_single_artifact(artifact, ingestion, metadata) -> bool:
    """Ingest a single artifact file. Returns True if ingested successfully."""
    if not isinstance(artifact, (str, Path)):
        return False
    artifact_path = Path(artifact)
    if not artifact_path.exists():
        logger.debug(f"[auto-ingest] Skipped (not found): {artifact_path}")
        return False
    content = artifact_path.read_text(errors="ignore")
    await ingestion.ingest_artifact(content, metadata)
    return True


async def _setup_ingestion(cfg):
    """Setup engine and PipelineIngestion from config."""
    from graph_rag.engine import GraphRAGEngine
    from graph_rag.config import GraphRAGConfig

    graph_cfg = GraphRAGConfig(cfg.get("graph_rag", {}))
    engine = await GraphRAGEngine.get_instance(graph_cfg.config)
    return PipelineIngestion(engine)


async def _ingest_artifacts_batch(ingestion, artifacts, metadata) -> int:
    """Ingest a batch of artifacts, returns count of successfully ingested."""
    ingested_count = 0
    for artifact in artifacts:
        try:
            if await _ingest_single_artifact(artifact, ingestion, metadata):
                ingested_count += 1
        except Exception as e:
            logger.warning(f"[auto-ingest] Failed to ingest {artifact}: {e}")
    return ingested_count


async def auto_ingest_hook(
    step_name: str,
    artifacts: list,
    metadata: Dict[str, any]
) -> None:
    """
    Post-step hook for automatic ingestion of artifacts.

    Called after pipeline steps (dev, architect, qa, ba) complete.
    Respects auto_ingest config flag - does nothing if disabled.
    Does NOT raise exceptions - pipeline continues even if ingestion fails.

    Args:
        step_name: Name of completed step (ba, architect, dev, qa)
        artifacts: List of artifact file paths (Path objects)
        metadata: Dict with {role, iteration, timestamp, story_id, ...}
    """
    from common import load_config

    try:
        cfg = load_config()
    except Exception as e:
        logger.error(f"✗ Auto-ingest: Could not load config: {e}")
        return

    if not cfg.get("graph_rag", {}).get("auto_ingest", False):
        logger.debug(f"[auto-ingest] Skipped: auto_ingest=false (step={step_name})")
        return

    try:
        ingestion = await _setup_ingestion(cfg)
        count = await _ingest_artifacts_batch(ingestion, artifacts, metadata)
        logger.info(f"✓ Auto-ingest: {count}/{len(artifacts)} artifacts from {step_name}")
    except Exception as e:
        logger.error(f"✗ Auto-ingest failed for {step_name}: {e}")
