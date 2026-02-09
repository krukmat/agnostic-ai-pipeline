"""
Graph RAG Configuration Management.

Loads graph_rag settings from config.yaml or environment.

Single source of truth for all Graph RAG configuration.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GraphRAGConfig:
    """Manages Graph RAG configuration from YAML or defaults."""

    DEFAULT_CONFIG = {
        "enabled": True,
        "working_dir": "./artifacts/graph_rag",
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "chunk_token_size": 1200,
        "top_k": 60,
        "default_mode": "mix",
        "auto_ingest": False,
        "context_budget_chars": 4000,
        "context_truncation_strategy": "hierarchical",
        "sources": [
            "planning/",
            "project/",
            "artifacts/",
            "docs/",
        ],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with config dict.

        Args:
            config: Dict with graph_rag settings (merged with defaults)
        """
        self.config = {**self.DEFAULT_CONFIG}
        if config:
            self.config.update(config)

    def to_dict(self) -> Dict[str, Any]:
        """Return config as dict."""
        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key."""
        return self.config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Dict-like access."""
        return self.config[key]

    def __repr__(self) -> str:
        return f"GraphRAGConfig({self.config})"

    # Property accessors for type-safe access
    @property
    def enabled(self) -> bool:
        """Get enabled flag."""
        return self.config.get("enabled", True)

    @property
    def working_dir(self) -> str:
        """Get working directory path."""
        return self.config.get("working_dir", "./artifacts/graph_rag")

    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return self.config.get("llm_model", "qwen2.5:7b-instruct")

    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        return self.config.get("embedding_model", "bge-m3")

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension."""
        return self.config.get("embedding_dim", 1024)

    @property
    def top_k(self) -> int:
        """Get default top_k for retrieval."""
        return self.config.get("top_k", 60)

    @property
    def default_mode(self) -> str:
        """Get default retrieval mode."""
        return self.config.get("default_mode", "mix")

    @property
    def context_budget_chars(self) -> int:
        """Get context budget in characters."""
        return self.config.get("context_budget_chars", 4000)

    @property
    def context_truncation_strategy(self) -> str:
        """Get context truncation strategy."""
        return self.config.get("context_truncation_strategy", "hierarchical")

    def _check_int_range(self, name: str, value, lo: int, hi: int = None) -> None:
        """Validate an integer field is in range [lo, hi].

        Args:
            name: Field name for error messages
            value: Value to check
            lo: Minimum allowed value (inclusive)
            hi: Maximum allowed value (inclusive), None for no upper bound
        """
        if not isinstance(value, int):
            raise ValueError(f"'{name}' must be integer")
        if value < lo:
            raise ValueError(f"'{name}' must be >= {lo}, got {value}")
        if hi is not None and value > hi:
            raise ValueError(f"'{name}' must be <= {hi}, got {value}")

    def _validate_types(self) -> None:
        """Validate boolean and string field types."""
        if not isinstance(self.config.get("enabled", True), bool):
            raise ValueError("'enabled' must be boolean")
        for name in ["llm_model", "embedding_model"]:
            val = getattr(self, name)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"'{name}' must be non-empty string")

    def _validate_ranges(self) -> None:
        """Validate numeric fields are in acceptable ranges."""
        self._check_int_range("embedding_dim", self.embedding_dim, 1)
        self._check_int_range("top_k", self.top_k, 1, 100)
        self._check_int_range("context_budget_chars", self.context_budget_chars, 1)

    def _validate_enums(self) -> None:
        """Validate enum fields have allowed values."""
        enums = {
            "default_mode": ["naive", "local", "global", "hybrid", "mix"],
            "context_truncation_strategy": ["hierarchical", "truncate"],
        }
        for name, valid_values in enums.items():
            val = getattr(self, name)
            if val not in valid_values:
                raise ValueError(f"'{name}' must be one of {valid_values}, got '{val}'")

    def validate_schema(self) -> None:
        """
        Validate configuration schema and constraints.

        Raises:
            ValueError: If config is invalid (invalid types, out-of-range values)
        """
        self._validate_types()
        self._validate_ranges()
        self._validate_enums()
        logger.info(
            f"✓ GraphRAGConfig validated: "
            f"model={self.llm_model}, mode={self.default_mode}, top_k={self.top_k}"
        )


def load_from_yaml(yaml_dict: Dict[str, Any]) -> GraphRAGConfig:
    """
    Load GraphRAG config from parsed YAML dict.

    Expected structure:
    ```yaml
    graph_rag:
      enabled: true
      working_dir: ./artifacts/graph_rag
      llm_model: qwen2.5-coder:7b
      embedding_model: bge-m3
      embedding_dim: 1024
      chunk_token_size: 1200
      top_k: 60
      default_mode: mix
      auto_ingest: true
      sources:
        - planning/
        - project/
        - artifacts/
        - docs/
    ```

    Args:
        yaml_dict: Dict from yaml.safe_load() of config.yaml

    Returns:
        GraphRAGConfig instance
    """
    graph_rag_config = yaml_dict.get("graph_rag", {})
    return GraphRAGConfig(graph_rag_config)
