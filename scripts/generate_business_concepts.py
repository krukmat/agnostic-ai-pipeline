#!/usr/bin/env python3
"""Generate synthetic business concepts without LLM dependency."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List

import typer

DOMAINS = {
    "fintech": [
        "loan orchestration platform",
        "micro-investment marketplace",
        "risk scoring cockpit",
        "treasury automation suite"
    ],
    "healthcare": [
        "telemedicine triage portal",
        "patient adherence app",
        "lab automation dashboard",
        "digital therapeutics companion"
    ],
    "ecommerce": [
        "smart catalog engine",
        "last-mile fulfillment cloud",
        "returns optimization hub",
        "cross-border marketplace"
    ],
    "education": [
        "adaptive tutoring studio",
        "credential verification network",
        "learning analytics board",
        "campus operations cockpit"
    ],
    "logistics": [
        "fleet telemetry grid",
        "warehouse robotics console",
        "port operations planner",
        "cold-chain monitoring fabric"
    ],
    "hr": [
        "hybrid workforce planner",
        "skills graph navigator",
        "talent onboarding console",
        "compliance audit helper"
    ],
    "marketing": [
        "brand sentiment radar",
        "multi-channel journey builder",
        "growth experiment lab",
        "sponsorship intelligence platform"
    ],
}

REGIONS = ["LATAM", "EU", "APAC", "US", "Global"]
AUDIENCES = ["startups", "enterprises", "SMB", "public sector", "non-profits"]
TIERS = ["simple", "medium", "enterprise"]


def _sample_concept(domain: str, idx: int) -> str:
    base = random.choice(DOMAINS[domain])
    region = random.choice(REGIONS)
    audience = random.choice(AUDIENCES)
    tier = random.choice(TIERS)
    return (
        f"{base.title()} for {audience} teams in {region}, targeting {tier} operations "
        f"with emphasis on automation and insights."
    )


app = typer.Typer()

@app.command()
def main(
    output: Path = typer.Option(Path("artifacts/fase8/business_concepts.jsonl"), "--output"),
    count: int = typer.Option(200, help="Number of concepts to generate."),
    seed: int = typer.Option(42, help="Random seed for reproducibility."),
):
    random.seed(int(seed))
    output.parent.mkdir(parents=True, exist_ok=True)

    domains: List[str] = list(DOMAINS.keys())
    concepts = []
    while len(concepts) < count:
        domain = domains[len(concepts) % len(domains)]
        concept = {
            "id": f"BCON-{len(concepts)+1:04d}",
            "domain": domain,
            "concept": _sample_concept(domain, len(concepts)),
        }
        concepts.append(concept)

    with output.open("w", encoding="utf-8") as fh:
        for row in concepts:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    typer.echo(f"Generated {len(concepts)} concepts -> {output}")


if __name__ == "__main__":
    app()
