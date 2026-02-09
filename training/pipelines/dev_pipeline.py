from __future__ import annotations

from .base_pipeline import BaseSyntheticPipeline


class DevPipeline(BaseSyntheticPipeline):
    DEFAULT_SEEDS = [
        {
            "instruction": "Como Developer, implementa endpoint CRUD y tests base",
            "input": "Entidad: Customer con alta/baja/modificación/listado",
            "role": "dev",
        }
    ]
