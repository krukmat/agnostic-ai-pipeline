from __future__ import annotations

from .base_pipeline import BaseSyntheticPipeline


class ArchitectPipeline(BaseSyntheticPipeline):
    DEFAULT_SEEDS = [
        {
            "instruction": "Como Architect, diseña una arquitectura con trade-offs y ADR breve",
            "input": "Sistema multi-tenant para facturación electrónica",
            "role": "architect",
        }
    ]
