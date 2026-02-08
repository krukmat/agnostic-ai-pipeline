from __future__ import annotations

from .base_pipeline import BaseSyntheticPipeline


class QAPipeline(BaseSyntheticPipeline):
    DEFAULT_SEEDS = [
        {
            "instruction": "Como QA, define casos de prueba funcionales y edge-cases",
            "input": "Flujo de pago con tarjeta y validación 3DS",
            "role": "qa",
        }
    ]
