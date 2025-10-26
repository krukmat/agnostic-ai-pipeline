"""Utility to expose pipeline roles as A2A-compatible HTTP services."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .errors import A2AErrorCode, error_response


@dataclass(frozen=True)
class AgentSkill:
    """Metadata describing a callable capability exposed by an agent."""

    id: str
    name: str
    description: str
    input_modes: List[str]
    output_modes: List[str]
    examples: List[str] | None = None

    def to_card_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_modes": self.input_modes,
            "output_modes": self.output_modes,
        }
        if self.examples:
            data["examples"] = self.examples
        return data


@dataclass(frozen=True)
class AgentCard:
    name: str
    description: str
    url: str
    version: str
    default_input_modes: List[str]
    default_output_modes: List[str]
    capabilities: Mapping[str, Any]
    skills: Iterable[AgentSkill]
    authentication: Optional[Mapping[str, Any]] = None

    def to_json(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "default_input_modes": self.default_input_modes,
            "default_output_modes": self.default_output_modes,
            "capabilities": dict(self.capabilities),
            "authentication": dict(self.authentication or {"mode": "none"}),
            "skills": [skill.to_card_dict() for skill in self.skills],
        }


JsonCallable = Callable[[Dict[str, Any]], Any]


def create_agent_app(card: AgentCard, handlers: Mapping[str, JsonCallable]) -> FastAPI:
    """Instantiate a FastAPI app that exposes the given card and skills.

    - `/.well-known/agent-card.json` returns the Agent Card for discovery.
    - `POST /jsonrpc` implements a minimal JSON-RPC 2.0 endpoint supporting
      the `message/send` method. Parameters must include a `skill_id` and
      a `payload` dictionary passed to the registered handler.
    - `/health` provides a simple readiness probe.
    """

    app = FastAPI(title=card.name, version=card.version)

    @app.get("/.well-known/agent-card.json")
    def read_agent_card() -> Dict[str, Any]:
        return card.to_json()

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/jsonrpc")
    def jsonrpc_endpoint(payload: Dict[str, Any]) -> JSONResponse:
        jsonrpc_version = payload.get("jsonrpc")
        method = payload.get("method")
        request_id = payload.get("id")
        params = payload.get("params", {})

        if jsonrpc_version != "2.0":
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": error_response(A2AErrorCode.INVALID_REQUEST, "JSON-RPC 2.0 required"),
                },
            )

        if method != "message/send":
            return JSONResponse(
                status_code=404,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": error_response(A2AErrorCode.METHOD_NOT_FOUND, "Unsupported method"),
                },
            )

        skill_id = params.get("skill_id")
        if not isinstance(skill_id, str):
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": error_response(A2AErrorCode.INVALID_PARAMS, "skill_id must be a string"),
                },
            )

        handler = handlers.get(skill_id)
        if handler is None:
            return JSONResponse(
                status_code=404,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": error_response(A2AErrorCode.METHOD_NOT_FOUND, f"Skill '{skill_id}' not found"),
                },
            )

        payload_data = params.get("payload")
        if not isinstance(payload_data, dict):
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": error_response(A2AErrorCode.INVALID_PARAMS, "payload must be an object"),
                },
            )

        try:
            result = handler(payload_data)
        except Exception as exc:  # pragma: no cover - defensive
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": error_response(
                        A2AErrorCode.INTERNAL_ERROR,
                        "Skill execution failed",
                        data={"detail": str(exc)},
                    ),
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            },
        )

    return app
