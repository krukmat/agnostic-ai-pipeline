"""Base synthetic pipeline for Phase 2A (local/dev-first)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from training.checkpoint import load_checkpoint, save_checkpoint
from training.llm_mock import MockLLM
from training.steps.cot_generator import ChainOfThoughtGenerator
from training.steps.format_validator import FormatValidatorStep
from training.steps.quality_filter import QualityFilterStep

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


class BaseSyntheticPipeline:
    """Shared local pipeline implementation for all roles."""

    DEFAULT_SEEDS: List[Dict[str, str]] = [
        {"instruction": "Analiza el requerimiento", "input": "Contexto base", "role": "generic"}
    ]

    def __init__(self, role: str, mode: str = "local", config: Dict[str, Any] | None = None):
        self.role = role
        self.mode = mode
        self.config = config or self._load_default_config()

        self.output_dir = Path(self.config.get("output_dir", "training/datasets")) / role
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = Path("artifacts/training/checkpoints") / f"{role}.json"

        self.llm = self._init_llm(mode)
        threshold = self._quality_threshold_for_role(role)
        self.cot = ChainOfThoughtGenerator()
        self.quality = QualityFilterStep(role=role, min_score=threshold)
        self.format_validator = FormatValidatorStep(role=role)

    def _init_llm(self, mode: str):
        if mode == "gpu":
            # In Phase 2A we keep local-first behavior; fallback to mock if GPU stack not present.
            try:  # pragma: no cover
                import vllm  # noqa: F401
            except Exception:
                return MockLLM(model_name="mock-gpu-fallback")
        return MockLLM(model_name="mock-local")

    def _load_default_config(self) -> Dict[str, Any]:
        path = Path("training/configs/base.yaml")
        if path.exists() and yaml is not None:
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {"output_dir": "training/datasets", "quality_thresholds": {self.role: 0.85}}

    def _quality_threshold_for_role(self, role: str) -> float:
        thresholds = self.config.get("quality_thresholds", {})
        try:
            return float(thresholds.get(role, 0.85))
        except Exception:
            return 0.85

    def _load_seeds(self, num_samples: int) -> List[Dict[str, str]]:
        seeds = self.DEFAULT_SEEDS or []
        if not seeds:
            return []
        out: List[Dict[str, str]] = []
        i = 0
        while len(out) < num_samples:
            item = dict(seeds[i % len(seeds)])
            item["role"] = self.role
            out.append(item)
            i += 1
        return out

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generate_batch(self, batch: List[Dict[str, str]], batch_id: int) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for seed in batch:
            generated = self.llm.generate(seed["instruction"], seed.get("input", ""), self.role)
            parsed = self.cot.format_output(
                f"Reasoning: {generated.get('reasoning', '')}\nAnswer: {generated.get('output', '')}"
            )
            rows.append(
                {
                    "instruction": seed["instruction"],
                    "input": seed.get("input", ""),
                    "output": parsed["output"],
                    "reasoning": parsed["reasoning"],
                    "role": self.role,
                    "metadata": {
                        "timestamp": self._now_iso(),
                        "trace_id": str(uuid.uuid4()),
                        "batch_id": batch_id,
                        "mode": self.mode,
                    },
                    "mode": self.mode,
                }
            )
        return rows

    def _save_batch(self, rows: List[Dict[str, Any]]) -> Path:
        out_file = self.output_dir / "results_latest.jsonl"
        with out_file.open("a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return out_file

    def _load_checkpoint(self) -> Dict[str, Any]:
        return load_checkpoint(self.checkpoint_file, self.role)

    def _save_checkpoint(self, data: Dict[str, Any]) -> None:
        save_checkpoint(self.checkpoint_file, data)

    def run(
        self,
        num_samples: int,
        batch_size: int,
        dry_run: bool = False,
        resume: bool = False,
    ) -> Dict[str, Any]:
        checkpoint = self._load_checkpoint()
        seeds = self._load_seeds(num_samples)
        start = int(checkpoint.get("generated", 0)) if resume else 0

        if dry_run:
            return {
                "total_seeds": len(seeds),
                "generated": 0,
                "filtered_out": 0,
                "data": [],
                "stats": {"mode": self.mode, "dry_run": True},
            }

        generated_rows: List[Dict[str, Any]] = []
        for batch_id, idx in enumerate(range(start, len(seeds), batch_size), start=checkpoint.get("last_batch_id", 0)):
            batch = seeds[idx : idx + batch_size]
            rows = self._generate_batch(batch, batch_id=batch_id)
            rows = self.quality.process(rows)
            rows = [r for r in rows if r.get("passed", False)]
            rows = self.format_validator.process(rows)
            rows = [r for r in rows if r.get("format_valid", False)]

            self._save_batch(rows)
            generated_rows.extend(rows)

            checkpoint["generated"] = int(checkpoint.get("generated", 0)) + len(rows)
            checkpoint["failed"] = int(checkpoint.get("failed", 0)) + (len(batch) - len(rows))
            checkpoint["filtered"] = int(checkpoint.get("filtered", 0)) + max(0, len(batch) - len(rows))
            checkpoint["last_batch_id"] = batch_id
            self._save_checkpoint(checkpoint)

        return {
            "total_seeds": len(seeds),
            "generated": len(generated_rows),
            "filtered_out": max(0, len(seeds) - len(generated_rows)),
            "data": generated_rows,
            "stats": {
                "mode": self.mode,
                "quality": self.quality.get_stats(),
                "format": self.format_validator.get_stats(),
            },
        }
