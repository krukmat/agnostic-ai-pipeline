from __future__ import annotations

import json
import sys
from typing import Optional

import typer

from a2a.client import A2AClient

app = typer.Typer(help="Orchestrator agent CLI")


@app.command()
def execute(concept: Optional[str] = typer.Option(None, help="Concept to pass to orchestrator")) -> None:
    client = A2AClient()
    payload = {"concept": concept} if concept else {}
    result = client.send_task("orchestrator", "execute_pipeline", payload)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(reload: bool = typer.Option(False, help="Auto-reload server on code changes")) -> None:
    from a2a.cards import orchestrator_card
    from a2a.runtime import run_agent

    card, handlers = orchestrator_card()
    run_agent("orchestrator", card, handlers, reload=reload)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        typer.echo("Supply a subcommand (execute/serve). See --help for details.")
    app()
