"""
Action Executor for orchestration.

Dispatches actions to role handlers and collects results.
Handles concurrent execution and error handling.
"""

import asyncio
import time
from typing import List, Dict, Callable
from logger import logger


class ActionExecutor:
    """Dispatches actions to role handlers."""

    def __init__(self, role_handlers: Dict[str, Callable]):
        """
        Initialize executor with role handlers.

        Args:
            role_handlers: Dict mapping tool names to async handler functions
                          e.g., {"RUN_BA": execute_ba_handler, ...}
        """
        self.role_handlers = role_handlers
        logger.info(f"[executor] Initialized with {len(role_handlers)} role handlers")

    async def execute_actions(self, actions: List[Dict]) -> List[Dict]:
        """
        Execute actions concurrently where possible.

        Args:
            actions: List of action dicts with 'tool', 'arguments', 'reason'

        Returns:
            List of result dicts with 'tool', 'status', 'elapsed', optional 'error'
        """
        if not actions:
            logger.debug("[executor] No actions to execute")
            return []

        logger.info(f"[executor] Executing {len(actions)} actions")

        # For now, execute sequentially to avoid conflicts
        # In production, could parallelize independent actions
        results = []
        for action in actions:
            result = await self._execute_single_action(action)
            results.append(result)

        return results

    async def _execute_single_action(self, action: Dict) -> Dict:
        """Execute a single action and return result."""
        tool = action.get("tool", "UNKNOWN")
        arguments = action.get("arguments", {})
        reason = action.get("reason", "")

        logger.info(f"[executor] Executing: {tool} ({reason})")

        handler = self.role_handlers.get(tool)
        if not handler:
            logger.error(f"[executor] No handler for tool: {tool}")
            return {
                "tool": tool,
                "status": "error",
                "error": f"No handler for {tool}",
                "elapsed": 0,
            }

        start = time.time()
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            elapsed = time.time() - start
            logger.info(f"[executor] {tool} completed: status={result.get('status')}, elapsed={elapsed:.1f}s")

            return {
                "tool": tool,
                "status": result.get("status", "ok"),
                "elapsed": elapsed,
                **({"story_id": result.get("story_id")} if "story_id" in result else {}),
                **({"error": result.get("error")} if "error" in result else {}),
            }

        except Exception as exc:
            elapsed = time.time() - start
            logger.error(f"[executor] {tool} failed: {exc}")
            return {
                "tool": tool,
                "status": "exception",
                "error": str(exc),
                "elapsed": elapsed,
            }
