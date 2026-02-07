"""
Test Graph RAG config consolidation and validation.

Validates that GraphRAGConfig provides single source of truth with schema validation.
Before fix: Defaults duplicados entre engine, config.yaml, config.py
After fix: GraphRAGConfig.validate_schema() ensures correctness

TDD: Este test FALLA antes de la implementación.
"""

import pytest
from pathlib import Path


def test_graphrag_config_exists():
    """
    Verify that GraphRAGConfig class exists and can be imported.
    """
    from graph_rag.config import GraphRAGConfig
    assert GraphRAGConfig is not None, "GraphRAGConfig should exist"


def test_graphrag_config_initialization():
    """
    Verify GraphRAGConfig can be initialized from dict.
    """
    from graph_rag.config import GraphRAGConfig

    config_dict = {
        "enabled": True,
        "working_dir": "./artifacts/graph_rag",
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "top_k": 60,
        "default_mode": "mix",
        "context_budget_chars": 4000,
    }

    cfg = GraphRAGConfig(config_dict)
    assert cfg.enabled == True
    assert cfg.working_dir == "./artifacts/graph_rag"
    assert cfg.llm_model == "qwen2.5:7b-instruct"
    assert cfg.top_k == 60


def test_graphrag_config_validation_succeeds_with_valid():
    """
    Verify that validate_schema() passes for valid config.
    """
    from graph_rag.config import GraphRAGConfig

    valid_config = {
        "enabled": True,
        "working_dir": "./artifacts/graph_rag",
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "top_k": 60,
        "default_mode": "mix",
        "context_budget_chars": 4000,
        "context_truncation_strategy": "hierarchical",
    }

    cfg = GraphRAGConfig(valid_config)
    # Should not raise
    cfg.validate_schema()


def test_graphrag_config_validation_fails_with_invalid_mode():
    """
    Verify that validate_schema() fails for invalid retrieval mode.
    """
    from graph_rag.config import GraphRAGConfig

    invalid_config = {
        "enabled": True,
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "default_mode": "invalid_mode",  # Invalid!
        "top_k": 60,
    }

    cfg = GraphRAGConfig(invalid_config)
    with pytest.raises(ValueError, match="invalid_mode"):
        cfg.validate_schema()


def test_graphrag_config_validation_fails_with_invalid_top_k():
    """
    Verify that validate_schema() fails for out-of-range top_k.
    """
    from graph_rag.config import GraphRAGConfig

    invalid_config = {
        "enabled": True,
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "default_mode": "mix",
        "top_k": 150,  # Out of range (should be 1-100)
    }

    cfg = GraphRAGConfig(invalid_config)
    with pytest.raises(ValueError, match="top_k"):
        cfg.validate_schema()


def test_graphrag_config_provides_defaults():
    """
    Verify that GraphRAGConfig provides sensible defaults.
    """
    from graph_rag.config import GraphRAGConfig

    # Minimal config
    cfg = GraphRAGConfig({"enabled": True})

    # Should have defaults
    assert cfg.top_k == 60 or cfg.top_k is not None, "Should have default top_k"
    assert cfg.default_mode in ["naive", "local", "global", "hybrid", "mix"], \
        "Should have valid default mode"
    assert cfg.context_budget_chars == 4000 or cfg.context_budget_chars is not None, \
        "Should have default budget"


def test_llm_client_uses_graphrag_config():
    """
    Verify that LLM client can use GraphRAGConfig for initialization.
    """
    from scripts.llm import load_config
    from graph_rag.config import GraphRAGConfig

    # Load config
    cfg = load_config()
    graph_cfg_dict = cfg.get("graph_rag", {})

    # Initialize GraphRAGConfig
    graph_cfg = GraphRAGConfig(graph_cfg_dict)

    # Validate
    graph_cfg.validate_schema()

    # Verify accessible
    assert graph_cfg.enabled == graph_cfg_dict.get("enabled")
