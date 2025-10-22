"""HTTP client helpers for interacting with A2A agents."""
from __future__ import annotations

import httpx
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

from .config import A2AConfig


class A2AClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self._config = A2AConfig()
        self._timeout = timeout

    def fetch_card(self, role: str) -> Dict[str, Any]:
        agent = self._config.agent(role)
        url = agent.url.rstrip("/") + "/.well-known/agent-card.json"
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def send_task(self, role: str, skill_id: str, payload: Mapping[str, Any], *, request_id: Optional[str] = None) -> Dict[str, Any]:
        agent = self._config.agent(role)
        endpoint = agent.url.rstrip("/") + "/jsonrpc"
        rpc_id = request_id or str(uuid4())
        json_payload = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "message/send",
            "params": {
                "skill_id": skill_id,
                "payload": dict(payload),
            },
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(endpoint, json=json_payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"Agent '{role}' returned error: {data['error']}")
            return data.get("result", {})
