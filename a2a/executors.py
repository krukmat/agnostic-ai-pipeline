from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

from .client import A2AClient
from .config import load_a2a_config
from logger import logger


class RoleExecutor(ABC):
    """Abstract base class for executing a role's logic."""

    @abstractmethod
    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the role's logic with the given payload."""
        raise NotImplementedError


class LocalExecutor(RoleExecutor):
    """Executes a role's logic locally by importing and calling its function."""

    def __init__(self, role: str, handler: Callable[..., Any]):
        self.role = role
        self.handler = handler

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[Executor] Executing role '{self.role}' locally.")
        result = self.handler(**payload)
        if inspect.isawaitable(result):
            return await result
        return result


class RemoteExecutor(RoleExecutor):
    """Executes a role's logic remotely by calling its A2A service."""

    def __init__(
        self,
        role: str,
        skill_id: str,
        agent_config: Dict[str, Any],
        fallback_executor: RoleExecutor,
    ):
        self.role = role
        self.skill_id = skill_id
        self.fallback_executor = fallback_executor
        self.agent_url = str((agent_config or {}).get("url", "")).rstrip("/")
        self.client = A2AClient(self.agent_url) if self.agent_url else None

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[Executor] Executing role '{self.role}' remotely.")

        if not self.client:
            logger.warning(
                f"[Executor] Remote agent URL missing for role '{self.role}'. "
                "Falling back to local execution."
            )
            return await self.fallback_executor.execute(payload)

        try:
            if not await self.client.is_healthy():
                logger.warning(
                    f"[Executor] Remote agent for role '{self.role}' is not healthy. "
                    "Falling back to local execution."
                )
                return await self.fallback_executor.execute(payload)

            return await self.client.send_task(self.skill_id, payload)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                f"[Executor] Remote execution for role '{self.role}' failed: {exc}. "
                "Falling back to local execution."
            )
            return await self.fallback_executor.execute(payload)


def get_executor(role: str, handler: Callable[..., Any], *, skill_id: str) -> RoleExecutor:
    """
    Factory function to create the appropriate executor based on the configuration.
    """
    a2a_config = load_a2a_config()
    global_mode = str(a2a_config.get("execution_mode", "auto")).lower()

    agents_cfg = a2a_config.get("agents", {}) if isinstance(a2a_config, dict) else {}
    role_config = agents_cfg.get(role, {}) if isinstance(agents_cfg, dict) else {}

    # Support legacy configs under a2a.roles[role].strategy
    legacy_roles = a2a_config.get("roles", {}) if isinstance(a2a_config, dict) else {}
    legacy_strategy = (
        legacy_roles.get(role, {}).get("strategy") if isinstance(legacy_roles, dict) else None
    )

    role_strategy = str(role_config.get("strategy", legacy_strategy or "auto")).lower()
    execution_strategy = role_strategy if role_strategy != "auto" else global_mode

    local_executor = LocalExecutor(role, handler)

    if execution_strategy == "local":
        return local_executor

    if not role_config.get("url"):
        if execution_strategy == "remote":
            logger.warning(
                f"[Executor] Remote strategy requested for role '{role}' but no URL configured. "
                "Defaulting to local execution."
            )
        return local_executor

    return RemoteExecutor(
        role=role,
        skill_id=skill_id,
        agent_config=role_config,
        fallback_executor=local_executor,
    )
