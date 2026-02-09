#!/usr/bin/env python3
"""CLI para ejecutar pipelines sintéticos de Phase 2A."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from training.pipelines.architect_pipeline import ArchitectPipeline
from training.pipelines.ba_pipeline import BAPipeline
from training.pipelines.dev_pipeline import DevPipeline
from training.pipelines.po_pipeline import POPipeline
from training.pipelines.qa_pipeline import QAPipeline


PIPELINE_MAP = {
    "ba": BAPipeline,
    "product_owner": POPipeline,
    "architect": ArchitectPipeline,
    "dev": DevPipeline,
    "qa": QAPipeline,
}


def load_config(path: Path) -> dict:
    if path.exists() and yaml is not None:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run synthetic pipeline")
    p.add_argument("--role", required=True, choices=list(PIPELINE_MAP.keys()))
    p.add_argument("--mode", default="local", choices=["local", "gpu"])
    p.add_argument("--num-samples", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=5)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--resume-from-checkpoint", action="store_true")
    p.add_argument("--config", type=Path, default=Path("training/configs/base.yaml"))
    p.add_argument("--output-dir", type=Path, default=Path("training/datasets"))
    return p


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    config["output_dir"] = str(args.output_dir)

    pipeline_cls = PIPELINE_MAP[args.role]
    pipeline = pipeline_cls(role=args.role, mode=args.mode, config=config)

    result = pipeline.run(
        num_samples=args.num_samples,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        resume=args.resume_from_checkpoint,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
