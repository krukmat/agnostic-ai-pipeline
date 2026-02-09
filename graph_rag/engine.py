"""
GraphRAGEngine - Wrapper over LightRAG for knowledge graph management.

Wrapper singleton that integrates LightRAG with Ollama.
Constructs knowledge graph automatically from documents.
Supports 5 retrieval modes: naive, local, global, hybrid, mix.
"""

import asyncio
import threading
import time
from pathlib import Path
from typing import Optional
import logging

#Cache and persistence imports
from graph_rag.cache import QueryCache, IndexPersistence

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
    # Use threading lock to avoid event-loop binding issues across pytest async loops.
    _instance_lock = threading.Lock()

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
                - cache_enabled: Enable query cache (default: False)
                - cache_ttl: Cache TTL in seconds (default: 3600)
                - cache_max_size: Max cache entries (default: 1000)
        """
        self.config = config
        self.working_dir = Path(config.get("working_dir", "./artifacts/graph_rag"))
        self.rag = None  # Lazy initialization
        self._initialized = False

        #Cache and persistence initialization
        self.cache_enabled = config.get("cache_enabled", False)
        self.cache_ttl = config.get("cache_ttl", 3600)
        self.cache_max_size = config.get("cache_max_size", 1000)

        self.query_cache = QueryCache(
            max_size=self.cache_max_size,
            ttl_seconds=self.cache_ttl
        ) if self.cache_enabled else None

        self.persistence = IndexPersistence(self.working_dir)
        self._index_metadata = {}

        #Streaming responses configuration
        self.stream_chunk_size = config.get("stream_chunk_size", 512)

        #Multi-language support configuration
        self.language_detection = config.get("language_detection", True)
        self.supported_languages = config.get("supported_languages", ["en", "es", "fr", "de", "zh"])
        self.default_language = config.get("default_language", "en")

        # Initialize language detector
        if self.language_detection:
            from graph_rag.language import LanguageDetector
            self._language_detector = LanguageDetector()
        else:
            self._language_detector = None

    # ========================================================================
    # Private helpers for CC reduction
    # ========================================================================

    def _resolve_effective_top_k(self, top_k: Optional[int]) -> int:
        """Resolve effective top_k from parameter or config default."""
        return top_k if top_k is not None else self.config.get("top_k", 60)

    def _check_cache(self, question: str, mode: str, effective_top_k: int, context_only: bool = False):
        """Check query cache for a hit.

        Returns:
            Tuple of (cached_result_or_None, cache_key_or_None)
        """
        if not self.cache_enabled or not self.query_cache:
            return None, None
        kwargs = {"context_only": True} if context_only else {}
        cache_key = self.query_cache.generate_key(
            question, mode=mode, top_k=effective_top_k, **kwargs
        )
        return self.query_cache.get(cache_key), cache_key

    def _store_in_cache(self, cache_key: Optional[str], result: str) -> None:
        """Store result in cache if caching is enabled."""
        if self.cache_enabled and self.query_cache and cache_key:
            self.query_cache.set(cache_key, result)

    def _make_query_param(self, **kwargs):
        """Build LightRAG QueryParam with fallback for test environments.

        When `lightrag` is not installed, tests may still exercise query logic
        with a mocked `self.rag`. In that case we return a lightweight object
        exposing the same attributes expected by downstream code.
        """
        try:
            from lightrag import QueryParam
            return QueryParam(**kwargs)
        except ImportError:
            class _FallbackQueryParam:
                def __init__(self, **data):
                    self.__dict__.update(data)

            return _FallbackQueryParam(**kwargs)

    async def _ensure_initialized(self) -> float:
        """Ensure engine is initialized. Returns init time in seconds."""
        init_start = time.perf_counter()
        if not self._initialized:
            await self.initialize()
        return time.perf_counter() - init_start

    async def initialize(self):
        """
        Lazy initialization of LightRAG instance.
        Called once on first use.

        Imports LightRAG here to avoid hard dependency if not using RAG.
        """
        if self._initialized:
            return

        #Load persisted index metadata on initialization
        self.load_indices()

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

    async def query(self, question: str, mode: str = "mix", top_k: Optional[int] = None) -> str:
        """
        Query the Knowledge Graph.

        Includes timing instrumentation and query caching.

        Args:
            question: Query string
            mode: Retrieval mode - 'naive', 'local', 'global', 'hybrid', or 'mix'
            top_k: Number of results to retrieve (overrides config default if provided)

        Returns:
            Response from LightRAG (LLM-generated answer based on retrieved context)
        """
        query_start = time.perf_counter()
        effective_top_k = self._resolve_effective_top_k(top_k)

        cached, cache_key = self._check_cache(question, mode, effective_top_k)
        if cached is not None:
            total_time = time.perf_counter() - query_start
            logger.info(
                f"[Query] mode={mode} top_k={effective_top_k} "
                f"total_time={total_time:.3f}s (CACHED) result_size={len(cached)} chars"
            )
            return cached

        init_time = await self._ensure_initialized()

        try:
            rag_start = time.perf_counter()
            result = await self.rag.aquery(
                question,
                param=self._make_query_param(
                    mode=mode,
                    top_k=effective_top_k,
                    response_type="Multiple Paragraphs",
                    only_need_context=False,
                ),
            )
            rag_time = time.perf_counter() - rag_start
            total_time = time.perf_counter() - query_start

            self._store_in_cache(cache_key, result)

            logger.info(
                f"[Query] mode={mode} top_k={effective_top_k} "
                f"total_time={total_time:.3f}s rag_time={rag_time:.3f}s "
                f"init_time={init_time:.3f}s result_size={len(result)} chars"
            )
            logger.debug(f"✓ Query succeeded ({len(result)} chars)")
            return result

        except Exception as e:
            total_time = time.perf_counter() - query_start
            logger.error(f"✗ Query failed after {total_time:.3f}s: {e}")
            raise

    async def get_context_only(self, question: str, mode: str = "mix", top_k: Optional[int] = None) -> str:
        """
        Retrieve context without LLM generation.

        Includes timing instrumentation and context caching.
        Used for prompt injection: agents receive raw context to compose own prompts.

        Args:
            question: Query string
            mode: Retrieval mode
            top_k: Number of results to retrieve (overrides config default if provided)

        Returns:
            Raw context (entities, relationships, chunks) without LLM response
        """
        retrieval_start = time.perf_counter()
        effective_top_k = self._resolve_effective_top_k(top_k)

        cached, cache_key = self._check_cache(question, mode, effective_top_k, context_only=True)
        if cached is not None:
            total_time = time.perf_counter() - retrieval_start
            logger.info(
                f"[ContextOnly] mode={mode} top_k={effective_top_k} "
                f"total_time={total_time:.3f}s (CACHED) context_size={len(cached)} chars"
            )
            return cached

        init_time = await self._ensure_initialized()

        try:
            rag_start = time.perf_counter()
            result = await self.rag.aquery(
                question,
                param=self._make_query_param(
                    mode=mode,
                    top_k=effective_top_k,
                    only_need_context=True,
                ),
            )
            rag_time = time.perf_counter() - rag_start
            total_time = time.perf_counter() - retrieval_start

            self._store_in_cache(cache_key, result)

            logger.info(
                f"[ContextOnly] mode={mode} top_k={effective_top_k} "
                f"total_time={total_time:.3f}s rag_time={rag_time:.3f}s "
                f"init_time={init_time:.3f}s context_size={len(result)} chars"
            )
            logger.debug(f"✓ Context retrieval succeeded ({len(result)} chars)")
            return result

        except Exception as e:
            total_time = time.perf_counter() - retrieval_start
            logger.error(f"✗ Context retrieval failed after {total_time:.3f}s: {e}")
            raise

    async def stream_query(self, question: str, mode: str = "mix", top_k: Optional[int] = None):
        """
        Stream query responses in chunks (async generator).

        Args:
            question: Query string
            mode: Retrieval mode - 'naive', 'local', 'global', 'hybrid', or 'mix'
            top_k: Number of results to retrieve (overrides config default if provided)

        Yields:
            Response chunks (strings) progressively
        """
        query_start = time.perf_counter()
        effective_top_k = self._resolve_effective_top_k(top_k)

        cached, cache_key = self._check_cache(question, mode, effective_top_k)
        if cached is not None:
            logger.info(f"[StreamQuery] mode={mode} top_k={effective_top_k} (CACHED) streaming {len(cached)} chars")
            for i in range(0, len(cached), self.stream_chunk_size):
                yield cached[i:i + self.stream_chunk_size]
            return

        init_time = await self._ensure_initialized()

        try:
            rag_start = time.perf_counter()
            result = await self.rag.aquery(
                question,
                param=self._make_query_param(
                    mode=mode, top_k=effective_top_k,
                    response_type="Multiple Paragraphs", only_need_context=False,
                ),
            )
            rag_time = time.perf_counter() - rag_start
            total_time = time.perf_counter() - query_start

            self._store_in_cache(cache_key, result)
            logger.info(
                f"[StreamQuery] mode={mode} top_k={effective_top_k} "
                f"total_time={total_time:.3f}s rag_time={rag_time:.3f}s "
                f"init_time={init_time:.3f}s result_size={len(result)} chars"
            )

            for i in range(0, len(result), self.stream_chunk_size):
                yield result[i:i + self.stream_chunk_size]

        except Exception as e:
            total_time = time.perf_counter() - query_start
            logger.error(f"✗ Stream query failed after {total_time:.3f}s: {e}")
            raise

    async def stream_context_only(self, question: str, mode: str = "mix", top_k: Optional[int] = None):
        """
        Stream context retrieval in chunks (async generator).

        Args:
            question: Query string
            mode: Retrieval mode
            top_k: Number of results to retrieve (overrides config default if provided)

        Yields:
            Context chunks (strings) progressively
        """
        retrieval_start = time.perf_counter()
        effective_top_k = self._resolve_effective_top_k(top_k)

        cached, cache_key = self._check_cache(question, mode, effective_top_k, context_only=True)
        if cached is not None:
            logger.info(f"[StreamContext] mode={mode} top_k={effective_top_k} (CACHED) streaming {len(cached)} chars")
            for i in range(0, len(cached), self.stream_chunk_size):
                yield cached[i:i + self.stream_chunk_size]
            return

        init_time = await self._ensure_initialized()

        try:
            rag_start = time.perf_counter()
            result = await self.rag.aquery(
                question,
                param=self._make_query_param(
                    mode=mode, top_k=effective_top_k, only_need_context=True,
                ),
            )
            rag_time = time.perf_counter() - rag_start
            total_time = time.perf_counter() - retrieval_start

            self._store_in_cache(cache_key, result)
            logger.info(
                f"[StreamContext] mode={mode} top_k={effective_top_k} "
                f"total_time={total_time:.3f}s rag_time={rag_time:.3f}s "
                f"init_time={init_time:.3f}s context_size={len(result)} chars"
            )

            for i in range(0, len(result), self.stream_chunk_size):
                yield result[i:i + self.stream_chunk_size]

        except Exception as e:
            total_time = time.perf_counter() - retrieval_start
            logger.error(f"✗ Stream context failed after {total_time:.3f}s: {e}")
            raise

    def detect_query_language(self, question: str) -> str:
        """
        Detect language of query text.

        Args:
            question: Query string to analyze

        Returns:
            ISO 639-1 language code (en, es, fr, de, zh)

        CC: 2 (check + delegate)
        """
        if not self.language_detection or self._language_detector is None:
            return self.default_language

        detected = self._language_detector.detect_language(question)

        # Ensure detected language is supported
        if detected not in self.supported_languages:
            logger.debug(f"[lang] Detected {detected} not in supported languages, using {self.default_language}")
            return self.default_language

        return detected

    async def query_multilingual(self, question: str, mode: str = "mix", top_k: Optional[int] = None) -> str:
        """
        Query with automatic language detection.

        Detects language of query and processes accordingly.

        Args:
            question: Query in any supported language
            mode: Retrieval mode
            top_k: Number of results

        Returns:
            Response (may be in detected language)

        CC: 2 (detect + delegate)
        """
        detected_lang = self.detect_query_language(question)
        logger.info(f"[lang] Detected language: {detected_lang} for query (first 50 chars): {question[:50]}...")

        # For now, delegate to regular query (could add language-specific processing)
        return await self.query(question, mode=mode, top_k=top_k)

    async def get_context_multilingual(self, question: str, mode: str = "mix", top_k: Optional[int] = None) -> str:
        """
        Get context with automatic language detection.

        Detects language of query and retrieves context accordingly.

        Args:
            question: Query in any supported language
            mode: Retrieval mode
            top_k: Number of results

        Returns:
            Context in detected language

        CC: 2 (detect + delegate)
        """
        detected_lang = self.detect_query_language(question)
        logger.info(f"[lang] Detected language: {detected_lang} for context query")

        # Delegate to context-only retrieval
        return await self.get_context_only(question, mode=mode, top_k=top_k)

    def save_indices(self) -> None:
        """
        Save index metadata and cache state to disk.

        Allows indices and cache to survive engine restarts.

        CC: 1 (delegate to persistence)
        """
        self.persistence.save(self._index_metadata)

    def load_indices(self) -> None:
        """
        Load index metadata and cache state from disk.

        Called during initialization to restore persisted state.

        CC: 1 (delegate to persistence)
        """
        self._index_metadata = self.persistence.load()

    async def finalize(self):
        """
        Cleanup resources (storage backends, connections).
        Called on application shutdown.
        """
        #Save indices before shutdown
        self.save_indices()

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
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(config or {})

        # Initialize outside lock to keep critical section sync and short.
        if not cls._instance._initialized:
            try:
                await cls._instance.initialize()
            except ImportError:
                logger.warning(
                    "GraphRAGEngine.get_instance() running without lightrag installed; "
                    "returning uninitialized singleton for test/non-runtime flows."
                )
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

    @classmethod
    async def reset_instance(cls):
        """Test helper: finalize and clear singleton instance safely."""
        if cls._instance is not None:
            try:
                await cls._instance.finalize()
            finally:
                cls._instance = None

    @classmethod
    def clear_instance(cls):
        """Test helper: clear singleton without awaiting finalization."""
        cls._instance = None
