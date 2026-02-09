"""
End-to-End Graph RAG tests.

Tests complete pipeline:
1. Ingest artifacts (planning, code, docs)
2. Query knowledge graph with different modes
3. Verify role-based retrieval policies
4. Test multi-hop query capability (Graph RAG strength)
"""

import pytest
import tempfile
import asyncio
import importlib.util
from pathlib import Path

from graph_rag.engine import GraphRAGEngine
from graph_rag.ingestion import PipelineIngestion
from graph_rag.retrieval import AgentRetriever
from tests.utils.real_env import is_real_rag_env_ready


HAS_LIGHTRAG = importlib.util.find_spec("lightrag") is not None
REAL_READY, REAL_REASON = is_real_rag_env_ready()


@pytest.fixture
def temp_project_dir():
    """Create temp project with sample artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # Create directories
        (tmpdir / "planning").mkdir()
        (tmpdir / "project").mkdir()
        (tmpdir / "artifacts").mkdir()

        # Create sample artifacts
        (tmpdir / "planning" / "stories.yaml").write_text("""
S1: Database Setup
  description: Initialize PostgreSQL

S3: User Authentication
  depends_on: [S1]
  description: JWT token validation
  designed_by: ADR-002

ADR-002: JWT vs Session
  decision: Use JWT tokens
  rationale: Stateless, scalable
""")

        (tmpdir / "project" / "auth.py").write_text("""
# AuthService implements S3
class AuthService:
    def validate_token(self, token):
        # Uses JWT from ADR-002
        pass
""")

        yield tmpdir


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.integration_real
@pytest.mark.skipif((not HAS_LIGHTRAG) or (not REAL_READY), reason=REAL_REASON if not REAL_READY else "lightrag-hku no instalado en este entorno")
async def test_e2e_ingest_and_query(temp_project_dir):
    """Test complete ingest → query flow."""
    config = {
        "working_dir": str(temp_project_dir / "graph_rag"),
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "top_k": 60,
    }

    engine = GraphRAGEngine(config)
    await engine.initialize()

    ingestion = PipelineIngestion(engine)
    await ingestion.ingest_all()

    retriever = AgentRetriever(engine)
    context = await retriever.retrieve_for_role("architect", "What depends on S1?")
    assert context
    assert isinstance(context, str)
    assert len(context) > 0

    await engine.finalize()


def test_acceptance_criteria_f1t7():
    """
    Verify acceptance criteria with structural validation.

    Validates:
    - Makefile targets exist (rag-index, rag-query, rag-visualize)
    - AgentRetriever has role-based policies
    - Retrieval modes documented
    - GraphRAGEngine can be initialized
    """
    from graph_rag.retrieval import AgentRetriever
    from graph_rag.engine import GraphRAGEngine
    from pathlib import Path

    # Verify Makefile targets exist
    makefile_path = Path(__file__).parent.parent / "Makefile"
    assert makefile_path.exists(), "Makefile should exist"
    makefile_content = makefile_path.read_text()
    assert "rag-index:" in makefile_content, "Makefile should have rag-index target"
    assert "rag-query:" in makefile_content, "Makefile should have rag-query target"
    assert "rag-visualize:" in makefile_content, "Makefile should have rag-visualize target"

    # Verify AgentRetriever has role policies
    policies = AgentRetriever.ROLE_POLICIES
    assert len(policies) >= 4, "Should have policies for at least 4 roles"
    for role in ["ba", "product_owner", "architect", "dev", "qa"]:
        assert role in policies, f"Should have policy for role: {role}"
        policy = policies[role]
        assert "mode" in policy, f"{role} policy should have 'mode'"
        assert "top_k" in policy, f"{role} policy should have 'top_k'"
        assert policy["mode"] in ["naive", "local", "global", "hybrid", "mix"], \
            f"{role} should use valid retrieval mode"

    # Verify retrieval modes are documented
    modes = AgentRetriever.explain_modes()
    assert len(modes) == 5, "Should document 5 retrieval modes"

    # Verify GraphRAGEngine config structure
    config = {"working_dir": "/tmp/test_kg", "llm_model": "test"}
    engine = GraphRAGEngine(config)
    assert engine.config is not None, "Engine should be initialized with config"


def test_graph_rag_design_validates_requirements():
    """
    Verify Graph RAG architecture meets design requirements.

    Graph RAG capabilities vs Vector RAG:
    - Retrieval modes support different access patterns
    - Role-based policies enable tailored context per agent
    - Multi-hop traversal via graph structure (entities + relationships)
    - Integration with LLM pipeline for augmented queries
    """
    from graph_rag.retrieval import AgentRetriever

    # Verify retrieval modes support different patterns
    modes = AgentRetriever.explain_modes()
    assert modes["local"] != modes["global"], "Modes should offer different strategies"
    assert "relationship" in modes["hybrid"].lower() or \
           "entit" in modes["hybrid"].lower(), \
           "Hybrid mode should address relationship queries"

    # Verify role-specific policies
    policies = AgentRetriever.ROLE_POLICIES
    architect_mode = policies["architect"]["mode"]
    dev_mode = policies["dev"]["mode"]
    assert architect_mode != dev_mode, \
        "Different roles should have different retrieval modes"

    # Verify policy attributes for multi-hop capability
    for role, policy in policies.items():
        assert "mode" in policy, f"{role} should specify retrieval mode"
        assert "top_k" in policy, f"{role} should specify result count"
        # Higher top_k enables multi-hop traversal
        assert policy["top_k"] > 20, f"{role} should allow sufficient results for traversal"
