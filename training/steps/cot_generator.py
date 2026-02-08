"""Chain-of-thought generator helper step."""

from __future__ import annotations

from typing import Dict


class ChainOfThoughtGenerator:
    """Generate/parse reasoning + answer structure for synthetic samples."""

    def __init__(self, cot_template: str | None = None):
        self.cot_template = cot_template or self._default_cot_template()

    def _default_cot_template(self) -> str:
        return (
            "Reasoning: analiza paso a paso la solicitud.\n"
            "Answer: responde de forma estructurada y accionable."
        )

    def format_output(self, generation: str) -> Dict[str, str]:
        output = generation
        reasoning = ""
        if "Reasoning:" in generation and "Answer:" in generation:
            parts = generation.split("Answer:", 1)
            reasoning = parts[0].replace("Reasoning:", "").strip()
            output = parts[1].strip()
        return {"output": output, "reasoning": reasoning}
