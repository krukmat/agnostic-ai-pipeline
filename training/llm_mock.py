"""Mock LLM for local/dev synthetic generation."""

from __future__ import annotations

import hashlib


class MockLLM:
    """Deterministic mock LLM to support local testing without GPU."""

    def __init__(self, model_name: str = "mock-local"):
        self.model_name = model_name

    def generate(self, instruction: str, input_text: str, role: str) -> dict:
        seed = f"{role}|{instruction}|{input_text}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
        reasoning = f"Role={role}; análisis determinístico local; digest={digest}"
        output = (
            f"[{role}] Respuesta sintética para: {instruction[:80]} | "
            f"input={input_text[:80]} | id={digest}"
        )
        return {"output": output, "reasoning": reasoning}
