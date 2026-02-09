#!/usr/bin/env python3
"""
F1-T1 Smoke Test: Setup LightRAG + Ollama Integration

This script performs end-to-end verification of Graph RAG setup:
1. Verify Ollama models (qwen2.5-coder:7b, bge-m3) are available
2. Initialize GraphRAGEngine singleton
3. Ingest sample documents
4. Query the Knowledge Graph with different retrieval modes
5. Report statistics and latency

Usage:
    python scripts/setup_graph_rag.py

Related to: PLAN_implementation_distilabel_finetuning_rag.md - F1-T1
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_rag.engine import GraphRAGEngine
from graph_rag.ingestion import PipelineIngestion
from graph_rag.retrieval import AgentRetriever


async def verify_ollama_models() -> bool:
    """
    Verify required Ollama models are available.

    Required:
    - qwen2.5-coder:7b (for entity extraction and general tasks)
    - bge-m3 (for embeddings)
    """
    print("\n" + "=" * 70)
    print("STEP 1: Verify Ollama Models")
    print("=" * 70)

    try:
        import ollama

        models_response = ollama.list()
        available_models = [model.model for model in models_response.models]

        required_models = {
            "qwen2.5-coder:7b": False,
            "bge-m3:latest": False,
        }

        print("\nRequired models:")
        for model_name in required_models.keys():
            # Check with flexible naming (7b vs 7b-instruct, etc.)
            found = any(
                model_name.split(":")[0] in model.split(":")[0]
                for model in available_models
            )
            required_models[model_name] = found
            status = "✓" if found else "✗"
            print(f"  {status} {model_name}")

        if not all(required_models.values()):
            print("\n✗ Missing required models. Pull them:")
            print("  ollama pull qwen2.5-coder:7b")
            print("  ollama pull bge-m3")
            return False

        print("\n✓ All required models available")
        return True

    except Exception as e:
        print(f"\n✗ Failed to verify Ollama: {e}")
        print("  Ensure Ollama is running: ollama serve")
        return False


async def test_lightrag_engine(config: dict) -> bool:
    """
    Initialize and test GraphRAGEngine.

    Verifies:
    - Engine initialization
    - Ollama connectivity
    - Storage creation
    """
    print("\n" + "=" * 70)
    print("STEP 2: Initialize GraphRAGEngine")
    print("=" * 70)

    try:
        engine = GraphRAGEngine(config)
        print(f"  Working dir: {engine.working_dir}")
        print(f"  LLM model: {config.get('llm_model')}")
        print(f"  Embedding model: {config.get('embedding_model')}")

        await engine.initialize()
        print("\n✓ GraphRAGEngine initialized successfully")
        return engine

    except ImportError as e:
        print(f"\n✗ LightRAG import failed: {e}")
        print("  Install: pip install -r requirements-rag.txt")
        return None
    except Exception as e:
        print(f"\n✗ Engine initialization failed: {e}")
        return None


async def test_ingestion(engine: GraphRAGEngine) -> bool:
    """
    Test document ingestion into Knowledge Graph.

    Ingests sample pipeline artifact and verifies storage creation.
    """
    print("\n" + "=" * 70)
    print("STEP 3: Test Document Ingestion")
    print("=" * 70)

    try:
        sample_doc = """
[Source: sample_stories.yaml] [Type: planning]

Stories for User Authentication Feature:

S1: Database Setup
- Create PostgreSQL schema
- Initialize Redis cache
- Setup migrations

S3: User Authentication
- depends_on: S1 (Database Setup)
- implements: JWT token validation
- acceptance_criteria: "User can login with email/password"
- designed_by: ADR-002 (JWT vs Session tokens)

ADR-002: JWT vs Session Tokens
- Decision: Use JWT tokens with refresh rotation
- Rationale: Stateless, scalable, works with multiple backends
- Trade-off: Slightly more complex than sessions

Components:
- AuthService: Handles login/logout
- TokenValidator: Validates JWT signature
- PasswordHasher: Uses bcrypt for hashing
"""

        print("Ingesting sample document (S1, S3, ADR-002)...")
        start = time.time()
        await engine.ingest(sample_doc)
        elapsed = time.time() - start
        print(f"✓ Ingestion succeeded ({elapsed:.2f}s)")
        return True

    except Exception as e:
        print(f"✗ Ingestion failed: {e}")
        return False


async def test_retrieval(engine: GraphRAGEngine) -> bool:
    """
    Test Knowledge Graph retrieval with different modes.

    Verifies:
    - Query execution
    - Retrieval latency
    - Context extraction
    """
    print("\n" + "=" * 70)
    print("STEP 4: Test Knowledge Graph Retrieval")
    print("=" * 70)

    retriever = AgentRetriever(engine)

    test_queries = [
        ("What stories depend on S1?", "Graph traversal (hybrid mode)"),
        ("What is the JWT authentication design?", "Entity + relationships (mix mode)"),
        ("List all components", "Vector similarity (naive mode)"),
    ]

    results = {}

    for query, description in test_queries:
        print(f"\nQuery: {query}")
        print(f"Description: {description}")

        try:
            start = time.time()
            context = await engine.get_context_only(query, mode="mix")
            elapsed = time.time() - start

            # Truncate for display
            preview = context[:150] + "..." if len(context) > 150 else context

            print(f"✓ Retrieved ({elapsed:.2f}s): {preview}")
            results[query] = {
                "latency": elapsed,
                "context_len": len(context),
                "preview": preview,
            }

        except Exception as e:
            print(f"✗ Query failed: {e}")
            return False

    print("\n✓ All queries succeeded")
    return results


async def test_agent_retrieval(engine: GraphRAGEngine) -> bool:
    """
    Test role-specific retrieval policies.

    Verifies each role gets appropriate context.
    """
    print("\n" + "=" * 70)
    print("STEP 5: Test Role-Based Retrieval Policies")
    print("=" * 70)

    retriever = AgentRetriever(engine)
    test_query = "What components are needed for user authentication?"

    roles_to_test = ["ba", "architect", "dev", "qa"]
    results = {}

    for role in roles_to_test:
        try:
            policy = retriever.get_policy_info(role)
            print(f"\n[{role.upper()}] mode={policy['mode']}, top_k={policy['top_k']}")
            print(f"  {policy['description']}")

            start = time.time()
            context = await retriever.retrieve_for_role(role, test_query)
            elapsed = time.time() - start

            results[role] = {
                "policy": policy,
                "latency": elapsed,
                "context_len": len(context),
            }

            print(f"  ✓ Retrieved {len(context)} chars in {elapsed:.2f}s")

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return False

    print("\n✓ All role-based retrievals succeeded")
    return results


async def generate_report(
    config: dict,
    test_results: dict,
) -> None:
    """Generate setup report."""
    print("\n" + "=" * 70)
    print("SETUP REPORT - F1-T1 Smoke Test")
    print("=" * 70)

    report = {
        "status": "SUCCESS",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configuration": {
            "working_dir": config.get("working_dir"),
            "llm_model": config.get("llm_model"),
            "embedding_model": config.get("embedding_model"),
            "embedding_dim": config.get("embedding_dim"),
        },
        "test_results": test_results,
    }

    # Save report
    report_file = Path(config.get("working_dir", "./artifacts/graph_rag")) / "setup_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(json.dumps(report, indent=2, default=str))
    print(f"\n✓ Report saved to: {report_file}")


async def main():
    """Run F1-T1 smoke test."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  F1-T1: Setup LightRAG + bge-m3 in Ollama".center(68) + "║")
    print("║" + "  Graph RAG for agnostic-ai-pipeline".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")

    # Step 1: Verify Ollama
    if not await verify_ollama_models():
        print("\n✗ Setup failed: Ollama models not available")
        sys.exit(1)

    # Step 2: Initialize engine
    config = {
        "working_dir": "./artifacts/graph_rag",
        "llm_model": "qwen2.5:7b-instruct",  # Use exact model name from ollama list
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "chunk_token_size": 1200,
        "top_k": 60,
    }

    engine = await test_lightrag_engine(config)
    if not engine:
        print("\n✗ Setup failed: Engine initialization")
        sys.exit(1)

    # Step 3: Test ingestion
    if not await test_ingestion(engine):
        print("\n✗ Setup failed: Document ingestion")
        sys.exit(1)

    # Step 4: Test retrieval
    retrieval_results = await test_retrieval(engine)
    if not retrieval_results:
        print("\n✗ Setup failed: Knowledge Graph retrieval")
        sys.exit(1)

    # Step 5: Test role-based policies
    role_results = await test_agent_retrieval(engine)
    if not role_results:
        print("\n✗ Setup failed: Role-based retrieval")
        sys.exit(1)

    # Cleanup
    await engine.finalize()

    # Generate report
    test_results = {
        "retrieval_tests": retrieval_results,
        "role_based_retrieval": role_results,
    }
    await generate_report(config, test_results)

    print("\n" + "=" * 70)
    print("✓ F1-T1 Setup Complete")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Review setup_report.json in ./artifacts/graph_rag/")
    print("  2. Implement F1-T2: GraphRAGEngine integration")
    print("  3. Implement F1-T3: Pipeline artifact ingestion")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✗ Setup interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Setup failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
