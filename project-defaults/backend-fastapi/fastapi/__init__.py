# Minimal FastAPI stub for offline test environments.
#
# This module provides just enough structure to allow generated code and tests
# to import FastAPI primitives when the real dependency cannot be installed.
# Extend cautiously if new features are required.

from __future__ import annotations
from typing import Any, Callable, Dict, List, Tuple


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str = ""):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FastAPI:
    def __init__(self, *_, **__):
        self.routes: List[Tuple[str, str, Callable[..., Any]]] = []

    def _register(self, method: str, path: str, func: Callable[..., Any]) -> Callable[..., Any]:
        self.routes.append((method.upper(), path, func))
        return func

    def get(self, path: str, **_kwargs):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._register("GET", path, func)
        return decorator

    def post(self, path: str, **_kwargs):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._register("POST", path, func)
        return decorator

    def put(self, path: str, **_kwargs):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._register("PUT", path, func)
        return decorator

    def delete(self, path: str, **_kwargs):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._register("DELETE", path, func)
        return decorator


class APIRouter(FastAPI):
    pass


class Depends:
    def __init__(self, dependency: Callable[..., Any]):
        self.dependency = dependency

