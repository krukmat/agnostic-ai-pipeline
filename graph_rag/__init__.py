"""
Graph RAG Module - LightRAG Integration

Provides knowledge graph-based retrieval for the agnostic-ai-pipeline.
Combines semantic graph traversal with vector similarity for context-aware retrieval.

F1 Phase: Graph RAG with LightRAG (EMNLP 2025 paper, HKUDS)
- Knowledge Graph (NetworkX): Entities and relationships from artifacts
- Vector Store (NanoVectorDB): Chunk embeddings via bge-m3
- Retrieval Modes: naive, local, global, hybrid, mix (recommended)
- Ollama Integration: Native support for LLMs and embeddings
"""

from graph_rag.engine import GraphRAGEngine
from graph_rag.ingestion import PipelineIngestion
from graph_rag.retrieval import AgentRetriever

__all__ = [
    "GraphRAGEngine",
    "PipelineIngestion",
    "AgentRetriever",
]
