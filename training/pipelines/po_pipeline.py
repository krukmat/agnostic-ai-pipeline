from __future__ import annotations

from .base_pipeline import BaseSyntheticPipeline


class POPipeline(BaseSyntheticPipeline):
    DEFAULT_SEEDS = [
        {
            "instruction": "Como Product Owner, prioriza backlog y define criterios de aceptación",
            "input": "MVP de e-commerce para productos digitales",
            "role": "product_owner",
        }
    ]
