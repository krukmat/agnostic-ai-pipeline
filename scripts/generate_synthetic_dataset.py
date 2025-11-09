#!/usr/bin/env python3
"""Generate synthetic requirements dataset from concept list."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List

import typer

app = typer.Typer()

FUNCTIONAL_TEMPLATES = [
    "Allow users to {action} with contextual guidance",
    "Provide analytics on {entity} including trends and anomalies",
    "Integrate with {integration} to synchronize data",
    "Offer role-based workspaces for {audience}"
]

NON_FUNCTIONAL = [
    "99.9% uptime during business hours",
    "Response time <500ms for key APIs",
    "WCAG AA accessibility compliance",
    "Data encrypted at rest (AES-256) and in transit (TLS1.2)",
]

CONSTRAINTS = [
    "Must deploy on existing Kubernetes clusters",
    "Budget capped at $500k for first release",
    "Follow regional data residency requirements",
    "Integrate with corporate SSO (SAML/OIDC)",
]

INTEGRATIONS = ["Salesforce", "Slack", "SAP", "Outlook", "Workday", "Stripe"]
ACTIONS = ["submit requests", "monitor KPIs", "plan capacity", "launch campaigns", "manage inventory", "track compliance"]
ENTITIES = ["tasks", "assets", "orders", "shipments", "appointments", "campaigns"]
AUDIENCES = ["analysts", "operators", "executives", "agents", "field teams"]


def _generate_requirements(idx: int, concept: str) -> Dict[str, object]:
    random.seed(idx * 17)
    fr_list = []
    for i, template in enumerate(FUNCTIONAL_TEMPLATES, start=1):
        text = template.format(
            action=random.choice(ACTIONS),
            entity=random.choice(ENTITIES),
            integration=random.choice(INTEGRATIONS),
            audience=random.choice(AUDIENCES),
        )
        fr_list.append({
            "id": f"FR{i:02d}",
            "description": text,
            "priority": random.choice(["High", "Medium"]),
        })

    nfr_list = [
        {"id": f"NFR{i:02d}", "description": desc, "priority": random.choice(["High", "Medium"])}
        for i, desc in enumerate(random.sample(NON_FUNCTIONAL, k=3), start=1)
    ]

    constraint_list = [
        {"id": f"C{i:02d}", "description": desc, "priority": random.choice(["High", "Medium"])}
        for i, desc in enumerate(random.sample(CONSTRAINTS, k=2), start=1)
    ]

    return {
        "title": concept.split(" ")[0] + " Platform",
        "description": concept,
        "functional_requirements": fr_list,
        "non_functional_requirements": nfr_list,
        "constraints": constraint_list,
    }


@app.command()
def main(
    concepts_path: Path = typer.Option(..., "--concepts", exists=True, help="Concepts JSONL"),
    output_path: Path = typer.Option(Path("artifacts/synthetic/ba_synthetic_raw.jsonl"), "--output"),
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, line in enumerate(concepts_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        req = _generate_requirements(idx, item["concept"])
        rows.append({
            "concept_id": item["id"],
            "concept": item["concept"],
            "requirements": req,
            "score": round(random.uniform(0.55, 0.95), 3),
        })

    with output_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    typer.echo(f"Generated synthetic dataset ({len(rows)} entries) -> {output_path}")


if __name__ == "__main__":
    app()
