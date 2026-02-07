"""
AgentRetriever - Role-based retrieval adapter for pipeline agents.

Retrieval adapter with per-role policies.
Each role gets a configured retrieval strategy optimized for its task.

Policies are defined by:
- mode: Retrieval strategy (naive, local, global, hybrid, mix)
- top_k: Number of results to retrieve
- context_only: If True, return raw context (for prompt injection); if False, use LLM

Role-specific examples:
- Architect: mode="hybrid" (graph-heavy for design relationships)
- Dev: mode="local" (nearby entities for code specifics)
- BA/PO/QA: mode="mix" (balanced graph + vector)
"""

from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)


class AgentRetriever:
    """
    Retrieval adapter for pipeline agents.

    Manages per-role retrieval policies and context budgets.
    Ensures each agent gets the right context type for its role.
    """

    # Role-specific retrieval policies
    # Tuned based on each role's information needs
    ROLE_POLICIES = {
        "ba": {
            "mode": "mix",  # Balanced: find similar requirements + graph context
            "top_k": 30,  # Fewer results for concise requirements
            "context_only": True,  # BA composes own prompts
            "description": "Requirements gathering - need existing patterns",
        },
        "product_owner": {
            "mode": "mix",  # Balanced: existing PRD + validation notes
            "top_k": 40,  # Medium results for product vision
            "context_only": True,  # PO reviews in own format
            "description": "Vision validation - need product context",
        },
        "architect": {
            "mode": "hybrid",  # Graph-heavy: dependencies, relationships, ADRs
            "top_k": 60,  # Many results for comprehensive architecture
            "context_only": True,  # Architect designs in own format
            "description": "Design - need relationships, dependencies, decisions",
        },
        "dev": {
            "mode": "local",  # Local entities: code modules, classes, functions
            "top_k": 40,  # Medium results for focused implementation
            "context_only": True,  # Dev writes code directly
            "description": "Implementation - need specific code context",
        },
        "qa": {
            "mode": "mix",  # Balanced: test cases + acceptance criteria
            "top_k": 50,  # Many results for comprehensive test coverage
            "context_only": True,  # QA writes test cases
            "description": "Testing - need acceptance criteria + edge cases",
        },
    }

    def __init__(self, engine):
        """
        Initialize AgentRetriever.

        Args:
            engine: GraphRAGEngine instance
        """
        self.engine = engine

    def _resolve_policy(self, role: str, override_policy: Optional[dict]) -> dict:
        """
        Resolve policy for a role with optional overrides.

        Extracted helper to reduce retrieve_for_role CC.

        Args:
            role: Agent role (ba, product_owner, architect, dev, qa)
            override_policy: Optional dict to override {mode, top_k, context_only}

        Returns:
            Resolved policy dict with mode, top_k, context_only
        """
        # Get role policy with fallback
        policy = self.ROLE_POLICIES.get(role, {
            "mode": "mix",
            "top_k": 30,
            "context_only": True,
        })

        # Allow runtime overrides (e.g., for testing)
        if override_policy:
            policy = {**policy, **override_policy}

        return policy

    async def retrieve_for_role(
        self,
        role: str,
        query: str,
        override_policy: Optional[dict] = None,
    ) -> str:
        """
        Retrieve context appropriate for the agent's role.
        Includes timing instrumentation for performance profiling.

        Uses role-specific policy unless overridden.
        Policy resolution delegated to _resolve_policy helper.

        Args:
            role: Agent role (ba, product_owner, architect, dev, qa)
            query: Query string
            override_policy: Optional dict to override {mode, top_k, context_only}

        Returns:
            Context string formatted for the agent
        """
        retrieval_start = time.perf_counter()

        # Resolve policy via extracted helper
        policy = self._resolve_policy(role, override_policy)

        logger.info(
            f"[{role.upper()}] Retrieving context with mode={policy['mode']}, "
            f"top_k={policy['top_k']}"
        )

        try:
            engine_start = time.perf_counter()
            if policy.get("context_only"):
                # Return raw context for agent's own prompt construction
                # Pass top_k from policy to engine for role-based retrieval
                result = await self.engine.get_context_only(
                    question=query,
                    mode=policy["mode"],
                    top_k=policy["top_k"],
                )
            else:
                # Return LLM-generated response
                # Pass top_k from policy to engine for role-based retrieval
                result = await self.engine.query(
                    question=query,
                    mode=policy["mode"],
                    top_k=policy["top_k"],
                )
            engine_time = time.perf_counter() - engine_start

            total_time = time.perf_counter() - retrieval_start

            # Log retrieval success with metrics
            result_preview = result[:100] + "..." if len(result) > 100 else result
            logger.info(
                f"[{role.upper()}] Retrieval complete: "
                f"total_time={total_time:.3f}s engine_time={engine_time:.3f}s "
                f"result_size={len(result)} chars context_only={policy.get('context_only', False)}"
            )
            logger.debug(f"✓ Retrieved {len(result)} chars: {result_preview}")

            return result

        except Exception as e:
            total_time = time.perf_counter() - retrieval_start
            logger.error(f"✗ Retrieval failed for {role} after {total_time:.3f}s: {e}")
            raise

    async def batch_retrieve(
        self,
        role: str,
        queries: list,
        parallel: bool = True,
    ) -> list:
        """
        Retrieve context for multiple queries (for roles processing multiple stories).

        Args:
            role: Agent role
            queries: List of query strings
            parallel: If True, retrieve in parallel; else sequential

        Returns:
            List of context strings
        """
        if parallel:
            import asyncio

            tasks = [
                self.retrieve_for_role(role, query)
                for query in queries
            ]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for query in queries:
                result = await self.retrieve_for_role(role, query)
                results.append(result)
            return results

    def get_policy_info(self, role: str) -> dict:
        """
        Get policy info for a role (useful for debugging/logging).

        Args:
            role: Agent role

        Returns:
            Policy dict with description
        """
        policy = self.ROLE_POLICIES.get(role, {})
        return {
            "role": role,
            "mode": policy.get("mode", "unknown"),
            "top_k": policy.get("top_k", "unknown"),
            "context_only": policy.get("context_only", "unknown"),
            "description": policy.get("description", ""),
        }

    @staticmethod
    def explain_modes() -> dict:
        """
        Explain LightRAG retrieval modes.

        Returns:
            Dict explaining each mode
        """
        return {
            "naive": "Vector similarity only (like ChromaDB). Fast but misses relationships.",
            "local": "Entities + immediate neighbors in graph. Good for code-specific context.",
            "global": "Community summaries from KG. Good for high-level architecture.",
            "hybrid": "Combines local entities/relationships with global community context. Recommended for architects.",
            "mix": "graph traversal + vector similarity combined. Balanced approach.",
        }
