"""A2A error taxonomy utilities.

Provides thin wrappers around JSON-RPC error codes so that agents and
clients can report failures in a consistent way.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class A2AErrorCode(Enum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    UPSTREAM_FAILURE = -32000
    TIMEOUT = -32001
    UNAVAILABLE = -32002


@dataclass(frozen=True)
class A2AError(Exception):
    code: A2AErrorCode
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_jsonrpc(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.data is not None:
            payload["data"] = self.data
        return payload


def error_response(code: A2AErrorCode, message: str, *, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a JSON-RPC error envelope."""
    return A2AError(code=code, message=message, data=data).to_jsonrpc()


class A2AStatusError(A2AError):
    """An A2AError that includes an HTTP status code."""
    def __init__(self, message: str, *, status_code: int, data: Optional[Dict[str, Any]] = None):
        super().__init__(code=A2AErrorCode.UPSTREAM_FAILURE, message=message, data=data)
        self.status_code = status_code
