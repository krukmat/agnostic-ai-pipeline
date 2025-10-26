from __future__ import annotations

import httpx
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

from logger import logger


class A2AClient:
    """HTTP client helpers for interacting with A2A agents."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def is_healthy(self) -> bool:
        """Check whether the remote agent reports a healthy status."""
        if not self.base_url:
            return False
        url = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return isinstance(data, dict) and data.get("status") == "ok"
        except httpx.RequestError as exc:
            logger.warning(f"[A2AClient] Health check request error for {url}: {exc}")
            return False
        except httpx.HTTPStatusError as exc:
            logger.warning(
                f"[A2AClient] Health check HTTP error for {url}: {exc.response.status_code}"
            )
            return False

    async def send_task(
        self,
        skill_id: str,
        payload: Mapping[str, Any],
        *,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a JSON-RPC message to the remote agent."""
        if not self.base_url:
            raise RuntimeError("Remote agent URL is not configured.")

        endpoint = f"{self.base_url}/jsonrpc"
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=json_payload)
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as exc:
            raise RuntimeError(f"Request error contacting agent at {endpoint}: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Agent at {endpoint} returned HTTP {exc.response.status_code}"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(f"Agent response malformed (expected object): {data!r}")

        if "error" in data:
            raise RuntimeError(f"Agent returned error: {data['error']}")

        result = data.get("result", {})
        if not isinstance(result, dict):
            raise RuntimeError(f"Agent result malformed (expected object): {result!r}")
        return result
