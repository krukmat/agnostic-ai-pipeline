#!/usr/bin/env python3
"""CLI utility to optimize DSPy programs (BA / QA / PO) using MIPROv2."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import dspy
import typer

from dspy_baseline.optimizers import optimize_program

app = typer.Typer(help="Optimize DSPy programs with dspy.MIPROv2.")


def _examples_from_jsonl(path: Path, role: str) -> List[dspy.Example]:
    """Load JSONL records and wrap them as dspy.Example objects."""
    examples: List[dspy.Example] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        row: Dict[str, Any] = json.loads(raw_line)

        if role == "ba" and "requirements" in row:
            payload = {"concept": row["concept"], **row["requirements"]}
            example = dspy.Example(**payload).with_inputs("concept")
        elif role == "qa":
            example = dspy.Example(**row).with_inputs(
                "story_title", "story_description", "acceptance_criteria"
            )
        elif role == "product_owner":
            input_block = row.get("input", row)
            output_block = row.get("output", {})
            payload = {
                "concept": input_block.get("concept", ""),
                "requirements_yaml": input_block.get("requirements_yaml", ""),
                "existing_vision": input_block.get("existing_vision", ""),
                "product_vision": output_block.get("product_vision", ""),
                "product_owner_review": output_block.get("product_owner_review", ""),
            }
            example = dspy.Example(**payload).with_inputs(
                "concept", "requirements_yaml", "existing_vision"
            )
        else:
            example = dspy.Example(**row)
        examples.append(example)
    return examples


def _load_metric(metric_path: str) -> Callable[[Any, Any], float]:
    if ":" not in metric_path:
        raise typer.BadParameter(
            "Metric must be in the form 'module.submodule:function'"
        )
    module_name, func_name = metric_path.split(":", 1)
    module = importlib.import_module(module_name)
    metric = getattr(module, func_name, None)
    if metric is None:
        raise typer.BadParameter(
            f"Metric function '{func_name}' not found in {module_name}"
        )
    return metric


def _load_program(role: str) -> Any:
    if role == "ba":
        from dspy_baseline.modules.ba_requirements import BARequirementsModule

        return BARequirementsModule()
    if role == "qa":
        from dspy_baseline.modules.qa_testcases import QA_PROGRAM

        return QA_PROGRAM
    if role == "product_owner":
        from dspy_baseline.modules.product_owner import ProductOwnerModule

        return ProductOwnerModule()
    raise typer.BadParameter(
        f"Unsupported role '{role}'. Expected 'ba', 'qa' or 'product_owner'."
    )


def _extract_program_components(compiled_program: Any, role: str) -> Dict[str, Any]:
    """Extract serializable components from an optimized DSPy program.

    This extracts:
    - Signature instructions (optimized by MIPROv2)
    - Demos/examples (few-shot learning)
    - Other metadata

    Returns a JSON-serializable dictionary.
    """
    components: Dict[str, Any] = {
        "role": role,
        "type": type(compiled_program).__name__,
        "modules": {},
    }

    # Extract components from each predictive module
    for attr_name in dir(compiled_program):
        attr = getattr(compiled_program, attr_name, None)
        if attr is None:
            continue

        # Check if this is a dspy.Predict or similar module
        if hasattr(attr, "signature") and hasattr(attr, "demos"):
            module_data: Dict[str, Any] = {
                "type": type(attr).__name__,
            }

            # Extract signature information
            sig = attr.signature
            if hasattr(sig, "instructions"):
                module_data["instructions"] = sig.instructions
            if hasattr(sig, "fields"):
                # Extract field names and descriptions
                fields_data = {}
                for field_name, field_info in sig.fields.items():
                    fields_data[field_name] = {
                        "type": "input" if field_info.json_schema_extra.get("__dspy_field_type") == "input" else "output",
                        "desc": field_info.json_schema_extra.get("desc", ""),
                    }
                module_data["fields"] = fields_data

            # Extract demos (few-shot examples)
            if attr.demos:
                demos_data = []
                for demo in attr.demos:
                    demo_dict = {}
                    if hasattr(demo, "inputs"):
                        demo_dict["inputs"] = demo.inputs()
                    if hasattr(demo, "outputs"):
                        demo_dict["outputs"] = demo.outputs()
                    elif hasattr(demo, "_store"):
                        # Fallback: extract from internal store
                        demo_dict = {k: v for k, v in demo._store.items()}
                    demos_data.append(demo_dict)
                module_data["demos"] = demos_data

            components["modules"][attr_name] = module_data

    return components


def _default_metric(example: dspy.Example, prediction: Any, trace=None) -> float:
    """Fallback metric when none is provided (returns constant score)."""
    return 1.0


def _configure_lm(
    provider: str,
    model: str,
    *,
    vertex_project: Optional[str] = None,
    vertex_location: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
) -> dspy.LM:
    provider = provider.lower()
    if provider in {"vertex", "vertex_ai"}:
        project_id = vertex_project or os.environ.get(
            "GCP_PROJECT", "agnostic-pipeline-476015"
        )
        location = vertex_location or os.environ.get("VERTEX_LOCATION", "us-central1")
        return dspy.LM(f"vertex_ai/{model}", project=project_id, location=location)
    if provider == "ollama":
        base_url = (
            ollama_base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or "http://localhost:11434"
        )
        return dspy.LM(f"ollama/{model}", base_url=base_url)
    if provider == "openai":
        return dspy.LM(f"openai/{model}")
    if provider == "claude_cli":
        return dspy.LM(f"anthropic/{model}")
    raise typer.BadParameter(f"Unsupported provider '{provider}'.")


@app.command()
def main(
    role: str = typer.Option(
        ...,
        "--role",
        "-r",
        help="Program to optimize: 'ba' or 'qa'.",
    ),
    trainset_path: Path = typer.Option(
        ...,
        "--trainset",
        "-t",
        exists=True,
        readable=True,
        help="Path to JSONL trainset.",
    ),
    metric_path: Optional[str] = typer.Option(
        None,
        "--metric",
        "-m",
        help="Metric callable path 'module:function'. Optional.",
    ),
    valset_path: Optional[Path] = typer.Option(
        None,
        "--valset",
        help="Optional JSONL validation set for early stopping.",
    ),
    stop_metric_path: Optional[str] = typer.Option(
        None,
        "--stop-metric",
        help="Optional stop metric 'module:function' evaluated on the valset.",
    ),
    output_dir: Path = typer.Option(
        Path("artifacts/dspy/optimizer"),
        "--output",
        "-o",
        help="Directory where compiled program and metadata will be stored.",
    ),
    num_candidates: int = typer.Option(8, help="Number of candidates per iteration."),
    num_trials: int = typer.Option(8, help="Number of optimization trials."),
    max_bootstrapped_demos: int = typer.Option(8, help="Maximum bootstrapped demonstrations."),
    seed: int = typer.Option(0, help="Random seed for optimizer."),
    provider: str = typer.Option(
        "vertex_ai", help="LLM provider (vertex_ai, ollama, openai, claude_cli)."
    ),
    model: str = typer.Option(
        "gemini-2.5-flash", help="Model name for the selected provider."
    ),
    vertex_project: Optional[str] = typer.Option(
        None, help="Vertex AI project ID (if provider=vertex_ai)."
    ),
    vertex_location: Optional[str] = typer.Option(
        None, help="Vertex AI location (if provider=vertex_ai)."
    ),
    ollama_base_url: Optional[str] = typer.Option(
        None, help="Optional Ollama base URL (default http://localhost:11434)."
    ),
) -> None:
    """Compile the selected DSPy program using the provided trainset."""
    train_examples = _examples_from_jsonl(trainset_path, role=role)
    val_examples: Optional[List[dspy.Example]] = (
        _examples_from_jsonl(valset_path, role=role) if valset_path else None
    )

    metric = _load_metric(metric_path) if metric_path else _default_metric
    stop_metric = _load_metric(stop_metric_path) if stop_metric_path else None
    program = _load_program(role)

    lm = _configure_lm(
        provider,
        model,
        vertex_project=vertex_project,
        vertex_location=vertex_location,
        ollama_base_url=ollama_base_url,
    )
    dspy.configure(lm=lm)

    compiled = optimize_program(
        program=program,
        trainset=train_examples,
        metric=metric,
        num_candidates=num_candidates,
        num_trials=num_trials,
        max_bootstrapped_demos=max_bootstrapped_demos,
        seed=seed,
        valset=val_examples,
        stop_metric=stop_metric,
    )

    role_dir = output_dir / role
    role_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "role": role,
        "trainset": str(trainset_path),
        "valset": str(valset_path) if valset_path else None,
        "num_candidates": num_candidates,
        "num_trials": num_trials,
        "max_bootstrapped_demos": max_bootstrapped_demos,
        "seed": seed,
        "metric": metric_path or "default_constant_metric",
        "stop_metric": stop_metric_path or None,
        "trainset_size": len(train_examples),
        "valset_size": len(val_examples) if val_examples else 0,
        "provider": provider,
        "model": model,
    }
    metadata_path = role_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Try multiple serialization strategies
    program_path = role_dir / "program.pkl"
    success = False

    # Strategy 1: Try dill (standard pickle alternative)
    try:
        import dill
        with open(program_path, "wb") as f:
            dill.dump(compiled, f)
        typer.echo(f"✅ Optimized program saved to {program_path}")
        success = True
    except Exception as e:
        typer.echo(f"⚠️  dill serialization failed: {e}")

    # Strategy 2: Extract and save components manually (fallback)
    if not success:
        try:
            typer.echo("🔄 Attempting manual component extraction...")
            components = _extract_program_components(compiled, role)
            components_path = role_dir / "program_components.json"
            with open(components_path, "w", encoding="utf-8") as f:
                json.dump(components, f, indent=2, ensure_ascii=False)
            typer.echo(f"✅ Program components saved to {components_path}")
            typer.echo("💡 Use load_program_from_components() to reconstruct the program")
            success = True
        except Exception as e2:
            typer.echo(f"⚠️  Component extraction also failed: {e2}")

    if not success:
        typer.echo("❌ Could not serialize program with any method")
        typer.echo("💡 Program is still available in memory and was optimized successfully")

    typer.echo(f"📄 Metadata written to {metadata_path}")


if __name__ == "__main__":
    app()
