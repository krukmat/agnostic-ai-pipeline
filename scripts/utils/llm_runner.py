from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from logger import logger


class LLMRunner:
    """Lightweight strategy to run one or more LLM clients with fallback."""

    def __init__(self, clients: List):
        self.clients = clients or []

    @classmethod
    def from_client(cls, primary, backups: Optional[List[Callable[[], object]]] = None) -> "LLMRunner":
        clients = []
        if primary:
            clients.append(primary)
        for factory in backups or []:
            try:
                client = factory()
                if client:
                    clients.append(client)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"[LLMRunner] Skipping backup factory: {exc}")
        return cls(clients)

    async def chat(self, system: str, user: str, retries: int = 1) -> Tuple[str, dict]:
        last_err: Exception | None = None
        for client in self.clients:
            for attempt in range(1, max(1, retries) + 1):
                try:
                    text = await client.chat(system=system, user=user)
                    info = {
                        "provider": getattr(client, "provider_type", "unknown"),
                        "model": getattr(client, "model", "unknown"),
                    }
                    return text, info
                except Exception as exc:
                    last_err = exc
                    logger.debug(f"[LLMRunner] Attempt {attempt} failed for {getattr(client,'provider_type','?')}: {exc}")
                    if attempt < retries:
                        continue
                    break
        if last_err:
            raise last_err
        raise RuntimeError("[LLMRunner] No clients configured")
