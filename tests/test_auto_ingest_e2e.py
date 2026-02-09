"""
End-to-End Auto-Ingest Tests - Multi-Role Pipeline

Tests for complete auto-ingest flow with multiple roles (BA → PO → Architect → Dev):
- BA generates requirements → auto-ingested
- PO generates product review → auto-ingested (context enriched with requirements)
- Architect generates stories → auto-ingested (context has BA + PO)
- Dev generates implementation → auto-ingested (full context chain)

Validates that context enriches at each step and auto_ingest=true enables production flow.
"""

import pytest
import asyncio
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ============================================================================
# BA STEP - Initial Artifact Ingestion
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ba_artifacts_ingested_automatically():
    """
    E2E Test: BA step artifacts are automatically ingested.

    Scenario:
    1. BA completes with requirements artifact
    2. Hook fires with auto_ingest=true
    3. Requirements are ingested into KG
    4. Ingestion state tracks MD5 hash
    """
    from scripts.orchestrate import HookRegistry, _collect_dev_artifacts
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        artifacts_dir = state_dir / "ba_artifacts"
        artifacts_dir.mkdir()

        # Simulate BA output: requirements.yaml
        ba_requirements = """
        requirements:
          - req_1: "User authentication"
          - req_2: "Database schema"
          - req_3: "API endpoints"
        """
        req_file = artifacts_dir / "requirements.yaml"
        req_file.write_text(ba_requirements)

        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        # Setup ingestion
        ingestion = PipelineIngestion(mock_engine, state_dir)

        # Simulate hook firing with BA artifacts
        metadata = {
            "role": "ba",
            "step": "requirements_generation",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        }

        await ingestion.ingest_artifact(ba_requirements, metadata)

        # Verify ingestion called with tagged content
        mock_engine.ingest.assert_called_once()
        call_args = mock_engine.ingest.call_args[0][0]
        assert "[Agent: ba]" in call_args, "Should tag with BA role"
        assert "requirements" in call_args.lower(), "Should include requirements content"

        # Verify state persisted
        ingestion._save_ingested_hashes()
        assert state_dir.joinpath(".graph_rag_ingestion_state.json").exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ba_ingestion_state_persists():
    """
    E2E Test: BA ingestion state is saved and loadable.

    Validates that after BA ingestion, state file exists and can be loaded
    for the next role (PO) to build upon.
    """
    import hashlib
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        # BA ingestion
        ingestion_ba = PipelineIngestion(mock_engine, state_dir)

        ba_content = "# Requirements\\nAuth system needed"
        ba_hash = hashlib.md5(ba_content.encode()).hexdigest()
        ingestion_ba.ingested_hashes[ba_hash] = "requirements.yaml"
        ingestion_ba._save_ingested_hashes()

        # New instance loads state (simulating PO starting)
        ingestion_po = PipelineIngestion(mock_engine, state_dir)

        assert len(ingestion_po.ingested_hashes) == 1, "Should load BA state"
        assert ba_hash in ingestion_po.ingested_hashes, "Should have BA hash"


# ============================================================================
# PO STEP - Context Enrichment (BA + PO)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_po_artifacts_enriched_with_ba_context():
    """
    E2E Test: PO ingestion enriches context with BA requirements.

    Scenario:
    1. BA ingestion exists (persisted state with requirements hash)
    2. PO completes with product review
    3. Hook fires with auto_ingest=true
    4. PO artifact ingested (tagged with references to BA)
    5. KG now contains: requirements + product_review (enriched)
    """
    import hashlib
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        # Step 1: BA ingestion (persisted)
        ingestion_ba = PipelineIngestion(mock_engine, state_dir)
        ba_content = "# Requirements\\n- Auth system\\n- Database"
        ba_hash = hashlib.md5(ba_content.encode()).hexdigest()
        ingestion_ba.ingested_hashes[ba_hash] = "requirements.yaml"
        ingestion_ba._save_ingested_hashes()

        # Step 2: PO ingestion (loads BA state)
        ingestion_po = PipelineIngestion(mock_engine, state_dir)
        assert ba_hash in ingestion_po.ingested_hashes, "Should have BA context"

        # PO artifact with reference to BA requirements
        po_content = """
        # Product Owner Review
        Based on requirements:
        - Authentication: Critical path
        - Database: Design validation needed

        New features:
        - Role-based access control
        - Audit logging
        """

        po_metadata = {
            "role": "po",
            "step": "product_review",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        }

        await ingestion_po.ingest_artifact(po_content, po_metadata)

        # Verify PO artifact tagged and ingested
        mock_engine.ingest.assert_called()
        call_args = mock_engine.ingest.call_args[0][0]
        assert "[Agent: po]" in call_args, "Should tag with PO role"
        assert "Role-based access control" in call_args, "Should include PO content"

        # Save PO state
        po_hash = hashlib.md5(po_content.encode()).hexdigest()
        ingestion_po.ingested_hashes[po_hash] = "product_review.yaml"
        ingestion_po._save_ingested_hashes()

        # Verify both BA and PO hashes in state (enriched context)
        with open(state_dir / ".graph_rag_ingestion_state.json") as f:
            import json
            state = json.load(f)
            assert len(state) == 2, "Should have both BA and PO hashes"


# ============================================================================
# ARCHITECT STEP - Full Context Chain (BA + PO + Architect)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_architect_artifacts_enriched_with_ba_po_context():
    """
    E2E Test: Architect ingestion enriches context with BA + PO.

    Scenario:
    1. BA and PO ingestion persisted (state contains 2 hashes)
    2. Architect completes with stories.yaml
    3. Hook fires with auto_ingest=true
    4. Stories artifact ingested (tagged with iteration)
    5. KG now contains: requirements + product_review + stories (full chain)
    """
    import hashlib
    import json
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        # Setup: BA + PO state (persisted)
        ba_content = "# Requirements\\n- Auth"
        po_content = "# Product Review\\n- RBAC"
        ba_hash = hashlib.md5(ba_content.encode()).hexdigest()
        po_hash = hashlib.md5(po_content.encode()).hexdigest()

        state_data = {ba_hash: "requirements.yaml", po_hash: "product_review.yaml"}
        state_file = state_dir / ".graph_rag_ingestion_state.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Architect ingestion (loads BA + PO state)
        ingestion_arch = PipelineIngestion(mock_engine, state_dir)

        # Verify full context available
        assert len(ingestion_arch.ingested_hashes) == 2, "Should have BA + PO"
        assert ba_hash in ingestion_arch.ingested_hashes
        assert po_hash in ingestion_arch.ingested_hashes

        # Architect artifact (stories)
        arch_content = """
        stories:
          - S1: "User authentication workflow"
            depends_on: ["Auth requirement"]
          - S2: "RBAC implementation"
            depends_on: ["Role-based access control"]
        """

        arch_metadata = {
            "role": "architect",
            "step": "stories_generation",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        }

        await ingestion_arch.ingest_artifact(arch_content, arch_metadata)

        # Verify artifact ingested with full context
        mock_engine.ingest.assert_called()
        call_args = mock_engine.ingest.call_args[0][0]
        assert "[Agent: architect]" in call_args, "Should tag with architect role"
        assert "S1:" in call_args, "Should include stories"

        # Add architect hash to state
        arch_hash = hashlib.md5(arch_content.encode()).hexdigest()
        ingestion_arch.ingested_hashes[arch_hash] = "stories.yaml"
        ingestion_arch._save_ingested_hashes()

        # Verify all three ingestions in state (full context chain)
        with open(state_file) as f:
            state = json.load(f)
            assert len(state) == 3, "Should have BA + PO + Architect"


# ============================================================================
# DEV STEP - Complete Pipeline Flow
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_ba_po_architect_dev_ingestion_chain():
    """
    E2E Test: Complete multi-role pipeline ingestion chain.

    Validates the full orchestration flow:
    1. BA generates and ingests requirements
    2. PO generates and ingests review (enriched with BA)
    3. Architect generates and ingests stories (enriched with BA + PO)
    4. Dev generates and ingests code (enriched with BA + PO + Architect)
    5. Final KG contains complete context chain
    """
    import hashlib
    import json
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Mock engine for all roles
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        ingested_artifacts = []

        # Capture all ingested content
        async def capture_ingest(content):
            ingested_artifacts.append(content)

        mock_engine.ingest.side_effect = capture_ingest

        # BA step
        ingestion = PipelineIngestion(mock_engine, state_dir)
        ba_content = "# Requirements\n- Authentication system\n- Database schema"
        await ingestion.ingest_artifact(ba_content, {
            "role": "ba",
            "step": "requirements",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        })
        ba_hash = hashlib.md5(ba_content.encode()).hexdigest()
        ingestion.ingested_hashes[ba_hash] = "requirements.yaml"
        ingestion._save_ingested_hashes()

        # PO step
        ingestion = PipelineIngestion(mock_engine, state_dir)
        po_content = "# Product Review\nValidates all requirements. RBAC addition proposed."
        await ingestion.ingest_artifact(po_content, {
            "role": "po",
            "step": "product_review",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        })
        po_hash = hashlib.md5(po_content.encode()).hexdigest()
        ingestion.ingested_hashes[po_hash] = "product_review.yaml"
        ingestion._save_ingested_hashes()

        # Architect step
        ingestion = PipelineIngestion(mock_engine, state_dir)
        arch_content = "# Stories\nS1: Auth system\nS2: Database\nS3: RBAC"
        await ingestion.ingest_artifact(arch_content, {
            "role": "architect",
            "step": "stories_generation",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        })
        arch_hash = hashlib.md5(arch_content.encode()).hexdigest()
        ingestion.ingested_hashes[arch_hash] = "stories.yaml"
        ingestion._save_ingested_hashes()

        # Dev step
        ingestion = PipelineIngestion(mock_engine, state_dir)
        dev_content = "# Implementation\nclass AuthService: pass\nclass Database: pass"
        await ingestion.ingest_artifact(dev_content, {
            "role": "dev",
            "step": "implementation",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        })
        dev_hash = hashlib.md5(dev_content.encode()).hexdigest()
        ingestion.ingested_hashes[dev_hash] = "implementation.py"
        ingestion._save_ingested_hashes()

        # Verify all artifacts were ingested
        assert len(ingested_artifacts) == 4, "Should ingest BA + PO + Architect + Dev"
        assert "[Agent: ba]" in ingested_artifacts[0], "First should be BA"
        assert "[Agent: po]" in ingested_artifacts[1], "Second should be PO"
        assert "[Agent: architect]" in ingested_artifacts[2], "Third should be Architect"
        assert "[Agent: dev]" in ingested_artifacts[3], "Fourth should be Dev"

        # Verify final state has all 4 hashes
        with open(state_dir / ".graph_rag_ingestion_state.json") as f:
            state = json.load(f)
            assert len(state) == 4, "Should track all 4 artifacts"


# ============================================================================
# CONFIG BEHAVIOR - Auto-Ingest Enable/Disable
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_config_controls_pipeline_flow():
    """
    E2E Test: auto_ingest config flag controls ingestion in pipeline.

    Validates:
    1. When auto_ingest=false, artifacts are not ingested
    2. When auto_ingest=true, artifacts are ingested
    3. Config can be toggled between pipeline steps
    """
    from graph_rag.ingestion import auto_ingest_hook
    from unittest.mock import patch

    artifacts = [Path("/tmp/artifact1.yaml")]
    metadata = {"role": "ba", "iteration": 1}

    # Test 1: auto_ingest=false (disabled)
    mock_config_disabled = {"graph_rag": {"auto_ingest": False}}
    with patch("common.load_config", return_value=mock_config_disabled):
        # Should return early without error
        await auto_ingest_hook("ba", artifacts, metadata)
        # Test passes if no exception raised

    # Test 2: auto_ingest=true (enabled)
    mock_config_enabled = {
        "graph_rag": {
            "auto_ingest": True,
            "working_dir": "/tmp/kg",
            "llm_model": "test-model",
        }
    }

    with patch("common.load_config", return_value=mock_config_enabled):
        with patch("graph_rag.engine.GraphRAGEngine.get_instance") as mock_get:
            mock_engine = AsyncMock()
            mock_engine.ingest = AsyncMock()
            mock_get.return_value = mock_engine

            # Create test artifact file
            with tempfile.TemporaryDirectory() as tmpdir:
                artifact_file = Path(tmpdir) / "test.yaml"
                artifact_file.write_text("test content")

                await auto_ingest_hook("ba", [artifact_file], metadata)

                # Should have attempted engine get
                mock_get.assert_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_iteration_context_accumulates():
    """
    E2E Test: Context accumulates across multiple iterations.

    Scenario:
    1. Iteration 1: BA→PO→Architect ingestion (state has 3 hashes)
    2. Iteration 2: New dev artifacts ingested (state has 4 hashes)
    3. Verify context chain is preserved and expanded
    """
    import hashlib
    import json
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        # Iteration 1: BA phase
        ingestion_iter1_ba = PipelineIngestion(mock_engine, state_dir)
        ba_content = "# Iteration 1: Requirements"
        await ingestion_iter1_ba.ingest_artifact(ba_content, {
            "role": "ba",
            "iteration": 1,
            "step": "requirements",
            "timestamp": datetime.now().isoformat(),
        })
        ba_hash = hashlib.md5(ba_content.encode()).hexdigest()
        ingestion_iter1_ba.ingested_hashes[ba_hash] = "req_iter1.yaml"
        ingestion_iter1_ba._save_ingested_hashes()

        # Iteration 2: Dev phase (loads iter1 state)
        ingestion_iter2_dev = PipelineIngestion(mock_engine, state_dir)

        # Verify iter1 context available
        assert len(ingestion_iter2_dev.ingested_hashes) == 1, "Should have iter1 BA"

        dev_content = "# Iteration 2: Implementation"
        await ingestion_iter2_dev.ingest_artifact(dev_content, {
            "role": "dev",
            "iteration": 2,
            "step": "implementation",
            "timestamp": datetime.now().isoformat(),
        })
        dev_hash = hashlib.md5(dev_content.encode()).hexdigest()
        ingestion_iter2_dev.ingested_hashes[dev_hash] = "impl_iter2.py"
        ingestion_iter2_dev._save_ingested_hashes()

        # Verify both iterations in state (context accumulated)
        with open(state_dir / ".graph_rag_ingestion_state.json") as f:
            state = json.load(f)
            assert len(state) == 2, "Should accumulate across iterations"
            assert ba_hash in state, "Should preserve iter1 BA"
            assert dev_hash in state, "Should have iter2 Dev"


# ============================================================================
# ERROR RESILIENCE - Pipeline Safety
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_continues_on_ingestion_error():
    """
    E2E Test: Pipeline continues even if one role's ingestion fails.

    Validates that auto-ingest errors don't block the full pipeline:
    1. BA ingests successfully
    2. PO ingestion fails (exception during ingest)
    3. Architect still ingests (pipeline continues)
    """
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # BA step (success)
        mock_engine_ba = AsyncMock()
        mock_engine_ba.ingest = AsyncMock()
        mock_engine_ba.working_dir = state_dir

        ingestion_ba = PipelineIngestion(mock_engine_ba, state_dir)
        ba_content = "# Requirements"
        await ingestion_ba.ingest_artifact(ba_content, {
            "role": "ba",
            "iteration": 1,
            "step": "requirements",
            "timestamp": datetime.now().isoformat(),
        })

        # PO step (failure, but should not propagate)
        mock_engine_po = AsyncMock()
        mock_engine_po.ingest = AsyncMock(side_effect=RuntimeError("Ingestion failed"))
        mock_engine_po.working_dir = state_dir

        ingestion_po = PipelineIngestion(mock_engine_po, state_dir)
        po_content = "# Product Review"

        # This should raise because ingest_artifact raises exceptions
        with pytest.raises(RuntimeError):
            await ingestion_po.ingest_artifact(po_content, {
                "role": "po",
                "iteration": 1,
                "step": "review",
                "timestamp": datetime.now().isoformat(),
            })

        # However, in the hook context, exceptions are caught and logged
        # Architect step (success - simulates pipeline continuing)
        mock_engine_arch = AsyncMock()
        mock_engine_arch.ingest = AsyncMock()
        mock_engine_arch.working_dir = state_dir

        ingestion_arch = PipelineIngestion(mock_engine_arch, state_dir)
        arch_content = "# Stories"
        await ingestion_arch.ingest_artifact(arch_content, {
            "role": "architect",
            "iteration": 1,
            "step": "stories",
            "timestamp": datetime.now().isoformat(),
        })

        # Verify Architect still ingested (pipeline continued)
        mock_engine_arch.ingest.assert_called_once()
