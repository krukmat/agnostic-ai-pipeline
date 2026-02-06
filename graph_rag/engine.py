"""
GraphRAGEngine - Wrapper over LightRAG for knowledge graph management.

F1-T2: GraphRAGEngine wrapper singleton that integrates LightRAG with Ollama.
Constructs knowledge graph automatically from documents.
Supports 5 retrieval modes: naive, local, global, hybrid, mix.

Related to: PLAN_implementation_distilabel_finetuning_rag.md - F1-T2
"""

import asyncio
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GraphRAGEngine:
    """
    Wrapper over LightRAG configured for the agnostic-ai-pipeline.

    Constructs a Knowledge Graph automatically from documents:
    - Entities: Pipeline artifacts (S1, S3, AuthService, ADR-002, etc.)
    - Relationships: depends_on, designed_by, implements, tested_by, etc.
    - Vector embeddings: via bge-m3 (1024-dim, multilingual)

    Retrieval Modes:
    - naive:   Vector similarity only (like ChromaDB)
    - local:   Nearby entities in the graph
    - global:  Community/cluster summaries
    - hybrid:  local + global combined
    - mix:     graph + vector combined (RECOMMENDED)

    Singleton pattern: Only one instance per application lifecycle.
    """

    _instance: Optional["GraphRAGEngine"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: dict):
        """
        Initialize GraphRAGEngine with configuration.

        Args:
            config: Dictionary with keys:
                - working_dir: Path to store KG and vector store (default: ./artifacts/graph_rag)
                - llm_model: Model name for entity extraction (default: qwen2.5-coder:7b)
                - embedding_model: Model name for embeddings (default: bge-m3)
                - embedding_dim: Embedding dimension (default: 1024 for bge-m3)
                - chunk_token_size: Tokens per chunk (default: 1200)
                - max_gleaning: Entity extraction iterations (default: 1)
                - top_k: Results to retrieve (default: 60)
        """
        self.config = config
        self.working_dir = Path(config.get("working_dir", "./artifacts/graph_rag"))
        self.rag = None  # Lazy initialization
        self._initialized = False

    async def initialize(self):
        """
        Lazy initialization of LightRAG instance.
        Called once on first use (F1-T1 smoke test).

        Imports LightRAG here to avoid hard dependency if not using RAG.
        """
        if self._initialized:
            return

        try:
            from functools import partial
            from lightrag import LightRAG, QueryParam
            from lightrag.llm.ollama import ollama_model_complete, ollama_embed
            from lightrag.utils import EmbeddingFunc

            self.working_dir.mkdir(parents=True, exist_ok=True)

            llm_model_name = self.config.get("llm_model", "qwen2.5:7b-instruct")
            embedding_model_name = self.config.get("embedding_model", "bge-m3")

            # Use ollama_model_complete directly - LightRAG handles llm_model_name binding
            llm_func = ollama_model_complete

            # Prepare embedding function (ollama_embed.func gives us the raw function)
            # Use the raw function to customize model/host
            embedding_func = partial(
                ollama_embed.func,
                embed_model=embedding_model_name,
                host="http://localhost:11434"
            )

            # Wrap embedding function with dimension info
            embedding_func_wrapped = EmbeddingFunc(
                embedding_dim=self.config.get("embedding_dim", 1024),
                func=embedding_func,
                max_token_size=8192,
                model_name=embedding_model_name,
            )

            self.rag = LightRAG(
                working_dir=str(self.working_dir),
                llm_model_func=llm_func,
                llm_model_name=llm_model_name,
                llm_model_max_async=4,
                embedding_func=embedding_func_wrapped,
                chunk_token_size=self.config.get("chunk_token_size", 1200),
                entity_extract_max_gleaning=self.config.get("max_gleaning", 1),
                enable_llm_cache=True,  # Reduce costs of re-extraction
            )

            # Initialize storage backends (NetworkX + NanoVectorDB)
            await self.rag.initialize_storages()
            self._initialized = True

            logger.info(
                f"✓ GraphRAGEngine initialized: "
                f"KG at {self.working_dir}, "
                f"LLM={llm_model_name}, "
                f"Embedding={embedding_model_name}"
            )

        except ImportError as e:
            logger.error(
                f"✗ Failed to import LightRAG. "
                f"Ensure lightrag-hku[api] is installed: pip install -r requirements-rag.txt. "
                f"Error: {e}"
            )
            raise

    async def ingest(self, text: str):
        """
        Insert document into the Knowledge Graph.
        LightRAG automatically extracts entities and relationships.

        Args:
            text: Document text (may include metadata header [Source:...] [Type:...])
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self.rag.ainsert(text)
            logger.debug(f"✓ Ingested document ({len(text)} chars)")
        except Exception as e:
            logger.error(f"✗ Ingestion failed: {e}")
            raise

    async def query(self, question: str, mode: str = "mix") -> str:
        """
        Query the Knowledge Graph.

        Args:
            question: Query string
            mode: Retrieval mode - 'naive', 'local', 'global', 'hybrid', or 'mix'

        Returns:
            Response from LightRAG (LLM-generated answer based on retrieved context)
        """
        if not self._initialized:
            await self.initialize()

        try:
            from lightrag import QueryParam

            result = await self.rag.aquery(
                question,
                param=QueryParam(
                    mode=mode,
                    top_k=self.config.get("top_k", 60),
                    response_type="Multiple Paragraphs",
                    only_need_context=False,  # Return full response (not just context)
                ),
            )
            logger.debug(f"✓ Query succeeded ({len(result)} chars)")
            return result

        except Exception as e:
            logger.error(f"✗ Query failed: {e}")
            raise

    async def get_context_only(self, question: str, mode: str = "mix") -> str:
        """
        Retrieve context without LLM generation.

        Used for prompt injection: agents receive raw context to compose own prompts.

        Args:
            question: Query string
            mode: Retrieval mode

        Returns:
            Raw context (entities, relationships, chunks) without LLM response
        """
        if not self._initialized:
            await self.initialize()

        try:
            from lightrag import QueryParam

            result = await self.rag.aquery(
                question,
                param=QueryParam(
                    mode=mode,
                    top_k=self.config.get("top_k", 60),
                    only_need_context=True,  # Return only context, no generation
                ),
            )
            logger.debug(f"✓ Context retrieval succeeded ({len(result)} chars)")
            return result

        except Exception as e:
            logger.error(f"✗ Context retrieval failed: {e}")
            raise

    async def finalize(self):
        """
        Cleanup resources (storage backends, connections).
        Called on application shutdown.
        """
        if self.rag and self._initialized:
            try:
                await self.rag.finalize_storages()
                self._initialized = False
                logger.info("✓ GraphRAGEngine finalized")
            except Exception as e:
                logger.error(f"✗ Finalization failed: {e}")

    @classmethod
    async def get_instance(cls, config: dict = None) -> "GraphRAGEngine":
        """
        Get or create singleton instance with async-safe locking.

        Args:
            config: Configuration dict (only used on first call)

        Returns:
            GraphRAGEngine singleton instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config or {})
                    await cls._instance.initialize()
        return cls._instance

    @classmethod
    def instance(cls, config: dict = None) -> "GraphRAGEngine":
        """
        Synchronous access to singleton (for backwards compatibility).
        Note: Must call initialize() manually if not using get_instance().
        """
        if cls._instance is None:
            cls._instance = cls(config or {})
        return cls._instance
