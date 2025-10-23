from __future__ import annotations

from typing import Callable, Dict

from . import vertex_cli as _vertex_cli

try:
    from . import vertex_sdk as _vertex_sdk  # type: ignore
except Exception:  # pragma: no cover - sdk optional
    _vertex_sdk = None  # type: ignore

ProviderFn = Callable[..., str]

PROVIDER_REGISTRY: Dict[str, ProviderFn] = {
    "vertex_cli": _vertex_cli.chat,
}

if _vertex_sdk is not None:
    PROVIDER_REGISTRY["vertex_sdk"] = _vertex_sdk.chat  # type: ignore[attr-defined]
