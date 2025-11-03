#!/usr/bin/env python3
"""
CLI script to run DSPy BA module.
Usage example: python dspy_baseline/scripts/run_ba.py --concept "Your business idea"
"""

from pathlib import Path
from typing import Optional
import os
import sys

ROOT = Path(__file__).parent.parent.parent
DEFAULT_CACHE_DIR = ROOT / "artifacts" / "dspy" / "cache"
DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHEDIR", str(DEFAULT_CACHE_DIR))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dspy
import typer
import yaml

from dspy_baseline.modules.ba_requirements import generate_requirements  # noqa: E402

app = typer.Typer()


def load_llm_config() -> dspy.LM:
    """Load LLM provider/model from config.yaml and return DSPy LM instance."""
    config_path = ROOT / "config.yaml"

    if not config_path.exists():
        typer.echo(
            f"Warning: {config_path} not found, using default LM openai/gpt-4",
            err=True,
        )
        return dspy.LM("openai/gpt-4")

    config = yaml.safe_load(config_path.read_text())
    ba_config = config.get("roles", {}).get("ba", {})

    provider = ba_config.get("provider", "openai")
    model = ba_config.get("model", "gpt-4")

    if provider == "openai":
        lm_name = f"openai/{model}"
    elif provider == "claude_cli":
        lm_name = f"anthropic/{model}"
    elif provider == "ollama":
        lm_name = f"ollama/{model}"
    else:
        typer.echo(
            f"Warning: Unknown provider '{provider}', falling back to openai/gpt-4",
            err=True,
        )
        lm_name = "openai/gpt-4"

    # TODO: Extend to map temperature and max_tokens once DSPy add-ons are aligned.
    return dspy.LM(lm_name)


@app.command()
def main(
    concept: str = typer.Option(..., help="Business concept description"),
    output: Path = typer.Option(
        ROOT / "artifacts" / "dspy" / "requirements_dspy.yaml",
        help="Output YAML file path",
    ),
    verbose: bool = typer.Option(False, help="Enable verbose logging"),
) -> None:
    """Generate BA requirements using DSPy and store them as YAML."""
    typer.echo("🤖 DSPy BA Generator")
    typer.echo(f"Concept: {concept[:80]}{'...' if len(concept) > 80 else ''}")

    if verbose:
        typer.echo("Loading LLM config...")
    lm = load_llm_config()

    if verbose:
        typer.echo("Generating requirements with DSPy...")
    try:
        requirements = generate_requirements(concept=concept, lm=lm)
    except Exception as exc:  # pragma: no cover - best effort logging
        typer.echo(f"Error generating requirements: {exc}", err=True)
        raise typer.Exit(1) from exc

    if verbose:
        typer.echo(f"Writing output to {output}...")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.dump(
            requirements,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    )

    typer.echo(f"✅ Requirements generated at {output}")

    if verbose:
        typer.echo("\nPreview:")
        typer.echo(
            yaml.dump(
                requirements,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        )


if __name__ == "__main__":
    app()
