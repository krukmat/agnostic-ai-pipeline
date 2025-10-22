"""Runtime helpers for launching A2A agents."""
from __future__ import annotations

from typing import Mapping, Callable, Any
from urllib.parse import urlparse

import uvicorn

from .config import A2AConfig
from .server import AgentCard, JsonCallable, create_agent_app


def run_agent(role: str, card: AgentCard, handlers: Mapping[str, JsonCallable], *, reload: bool = False) -> None:
    agent_def = A2AConfig().agent(role)
    parsed = urlparse(agent_def.url)
    host = parsed.hostname or "0.0.0.0"
    port = parsed.port or 0
    if not port:
        raise ValueError(f"Agent URL must include an explicit port (role={role}, url={agent_def.url})")

    app = create_agent_app(card, handlers)
    uvicorn.run(app, host=host, port=port, reload=reload)
