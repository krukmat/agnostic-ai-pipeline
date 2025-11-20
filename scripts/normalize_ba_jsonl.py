"""Normalize BA JSONL to a consistent schema for downstream tools.

Reads a JSONL where each line may be either:
- Top-level: {"concept": str, "requirements": dict or str, ...}
- Wrapped:   {"input": {"concept": str, "requirements_yaml": str, ...}, ...}

Writes JSONL with unified shape:
  {"input": {"concept": <str>, "requirements_yaml": <YAML str>}}

Optional: preserves fields under "meta" if present in the original requirements dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import typer
import yaml

app = typer.Typer(help="Normalize BA JSONL into {input: {concept, requirements_yaml}} lines.")


def _to_yaml_str(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    try:
        return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=False)
    except Exception:
        return str(obj)


def _extract(line: Dict[str, Any]) -> Dict[str, Any]:
    # Support both shapes
    if "input" in line and isinstance(line["input"], dict):
        concept = (line["input"].get("concept") or "").strip()
        req_yaml = line["input"].get("requirements_yaml") or line["input"].get("requirements")
        req_yaml = _to_yaml_str(req_yaml) if req_yaml is not None else ""
        return {"input": {"concept": concept, "requirements_yaml": req_yaml}}

    concept = (line.get("concept") or "").strip()
    if "requirements_yaml" in line:
        req_yaml = _to_yaml_str(line["requirements_yaml"])
    else:
        req_yaml = _to_yaml_str(line.get("requirements", ""))
    return {"input": {"concept": concept, "requirements_yaml": req_yaml}}


@app.command()
def normalize(
    src: Path = typer.Argument(..., help="Input BA JSONL path"),
    dst: Path = typer.Argument(..., help="Output normalized JSONL path"),
) -> None:
    if not src.exists():
        typer.echo(f"[normalize] missing input: {src}")
        raise typer.Exit(code=1)
    dst.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with src.open("r", encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for raw in fin:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
                out = _extract(obj)
                # minimal sanity check
                inp = out.get("input", {})
                if not inp.get("concept") or not inp.get("requirements_yaml"):
                    continue
                fout.write(json.dumps(out, ensure_ascii=False) + "\n")
                written += 1
            except Exception:
                continue
    typer.echo(f"[normalize] wrote {written} records to {dst}")


if __name__ == "__main__":
    app()

