from __future__ import annotations

from .base_pipeline import BaseSyntheticPipeline


class BAPipeline(BaseSyntheticPipeline):
    DEFAULT_SEEDS = [
        {
            "instruction": "Como BA, redacta requerimientos funcionales y no funcionales",
            "input": "Aplicación de gestión de turnos médicos",
            "role": "ba",
        }
    ]
