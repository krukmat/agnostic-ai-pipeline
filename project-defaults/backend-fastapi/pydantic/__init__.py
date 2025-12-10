# Minimal Pydantic-style BaseModel stub for offline execution.

from __future__ import annotations
from dataclasses import dataclass, field, fields, make_dataclass
from typing import Any, Dict


class BaseModel:
    def __init__(self, **data: Any):
        for key, value in data.items():
            setattr(self, key, value)

    def dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dict__}

    def model_dump(self) -> Dict[str, Any]:
        return self.dict()

    def __repr__(self) -> str:
        args = ", ".join(f"{k}={v!r}" for k, v in self.dict().items())
        return f"{self.__class__.__name__}({args})"
