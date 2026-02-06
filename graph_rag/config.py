"""
Graph RAG Configuration Management.

Loads graph_rag settings from config.yaml or environment.

Related to: PLAN_implementation_distilabel_finetuning_rag.md - F1-T5 (config.yaml)
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GraphRAGConfig:
    """Manages Graph RAG configuration from YAML or defaults."""

    DEFAULT_CONFIG = {
        "enabled": True,
        "working_dir": "./artifacts/graph_rag",
        "llm_model": "qwen2.5-coder:7b",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "chunk_token_size": 1200,
        "top_k": 60,
        "default_mode": "mix",
        "auto_ingest": True,
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
