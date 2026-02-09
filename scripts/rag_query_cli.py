"""
CLI helper for 'make rag-query' - executes Graph RAG query with MODE override.

R1-T2: Implements proper MODE parameter handling for Graph RAG queries.

Usage (from Makefile):
    python scripts/rag_query_cli.py --query "..." [--mode hybrid|local|global|naive|mix]
"""

import asyncio
import argparse
import logging
import sys

logger = logging.getLogger(__name__)


async def main():
    """Execute Graph RAG query with optional mode override."""
    parser = argparse.ArgumentParser(description="Query Graph RAG with optional mode override")
    parser.add_argument("--query", required=True, help="Query string")
    parser.add_argument("--mode", default="mix", help="Retrieval mode (naive|local|global|hybrid|mix)")
    parser.add_argument("--role", default="architect", help="Agent role for context retrieval")
    args = parser.parse_args()

    try:
        from graph_rag.engine import GraphRAGEngine
        from graph_rag.retrieval import AgentRetriever
        from scripts.llm import load_config

        # Load configuration
        config = load_config()
        graph_rag_config = config.get("graph_rag", {})

        # Initialize engine
        engine = GraphRAGEngine(graph_rag_config)
        await engine.initialize()

        # Create retriever and query with MODE override
        retriever = AgentRetriever(engine)

        # R1-T2: Pass mode as override_policy to apply CLI argument
        override_policy = {"mode": args.mode}
        result = await retriever.retrieve_for_role(
            args.role,
            args.query,
            override_policy=override_policy,
        )

        # Print result
        print(result)

        # Cleanup
        await engine.finalize()

    except Exception as e:
        logger.error(f"✗ Query failed: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
