"""
Generate Product Owner payloads (concept + requirements) for DSPy datasets.

Two sources are supported:
1. Existing BA synthetic datasets (JSONL) – reused and normalized.
2. Synthesized concepts produced via templated combinatorics (deterministic, seedable).

The output format is a JSONL file stored under artifacts/synthetic/product_owner/.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import typer
import yaml

from scripts.common import ART, ensure_dirs

app = typer.Typer(help="Generate Product Owner concept payloads for DSPy datasets.")

PO_DIR = ART / "synthetic" / "product_owner"


# ----------------------------- Helpers ------------------------------------- #

def _ensure_meta(requirements: Dict[str, Any], concept: str) -> Dict[str, Any]:
    meta = requirements.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    if not meta.get("original_request"):
        meta["original_request"] = concept
    normalized = dict(requirements)
    normalized["meta"] = meta
    return normalized


def _yaml_dump(data: Dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()


def _infer_tier(score: Optional[float]) -> str:
    if score is None:
        return "medium"
    if score >= 0.8:
        return "corporate"
    if score >= 0.65:
        return "medium"
    return "simple"


def _load_existing_examples(
    path: Path, limit: int, rng: random.Random
) -> List[Dict[str, Any]]:
    if not path.exists():
        typer.echo(f"[warn] Existing dataset not found: {path}")
        return []

    lines: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            requirements = data.get("requirements")
            if not isinstance(requirements, dict):
                continue
            concept = data.get("concept") or requirements.get("description")
            if not concept:
                continue
            normalized = _ensure_meta(requirements, concept)
            payload = {
                "concept": concept,
                "requirements_yaml": _yaml_dump(normalized),
                "tier": _infer_tier(data.get("score")),
                "metadata": {
                    "origin": "existing",
                    "source_file": str(path),
                    "source_concept_id": data.get("concept_id"),
                    "score": data.get("score"),
                },
            }
            lines.append(payload)

    if not lines:
        return []

    rng.shuffle(lines)
    return lines[:limit] if limit > 0 else lines


# ----------------------- Synthetic Generation ------------------------------ #

PLATFORM_TYPES = [
    "Operations Control Tower",
    "Customer Signals Hub",
    "Inventory Command API",
    "Incident Automation Studio",
    "Payments Compliance Portal",
    "Partner Enablement Workspace",
    "Sustainability Analytics Platform",
    "Clinical Intake Dashboard",
]

DOMAINS = [
    "e-commerce marketplaces",
    "logistics providers",
    "healthcare clinics",
    "clean-energy cooperatives",
    "fintech lenders",
    "university extension programs",
    "municipal smart-city teams",
    "manufacturing supply chains",
]

FOCUS_AREAS = [
    "predictive insights",
    "process automation",
    "risk observability",
    "personalized engagement",
    "compliance tracking",
    "inventory resilience",
    "financial reconciliation",
]

REGIONS = [
    "North America",
    "LATAM",
    "EMEA",
    "APAC",
    "India",
]

FUNCTIONAL_FEATURES = [
    "Allow operators to configure {focus} workflows per business unit.",
    "Provide guided playbooks for {focus} with contextual checklists.",
    "Offer role-based dashboards that highlight anomalies in {focus}.",
    "Expose REST/GraphQL APIs so partners submit updates programmatically.",
    "Trigger notifications in Slack/Teams when KPIs deviate from targets.",
    "Support sandbox environments to simulate {focus} scenarios before go-live.",
    "Generate audit-ready activity logs for every workflow transition.",
]  # at least 6 options

NFR_OPTIONS = [
    "99.9% uptime with multi-region failover.",
    "Average API response time under 300ms at P95.",
    "WCAG 2.1 AA accessibility compliance across dashboards.",
    "SOC 2 Type II controls with quarterly penetration testing.",
    "Data encrypted in transit (TLS 1.3) and at rest (AES-256).",
    "Configurable retention policies to meet GDPR and HIPAA.",
]

CONSTRAINT_OPTIONS = [
    "Must deploy on existing Kubernetes clusters and PostgreSQL.",
    "Budget capped at $500k for the first 12-month release.",
    "All customer data must remain within regional data centers.",
    "Integrations limited to OAuth2 providers already audited by security.",
    "Solution must expose OpenAPI 3.1 compliant documentation.",
]


def _generate_concept(seed_idx: int, rng: random.Random) -> Dict[str, Any]:
    tier_choice = rng.choices(
        population=["simple", "medium", "corporate"],
        weights=[0.3, 0.5, 0.2],
        k=1,
    )[0]
    platform = rng.choice(PLATFORM_TYPES)
    domain = rng.choice(DOMAINS)
    focus = rng.choice(FOCUS_AREAS)
    region = rng.choice(REGIONS)

    concept = (
        f"{platform} for {domain} in {region}, targeting {tier_choice} operations "
        f"with emphasis on {focus}."
    )

    description = (
        f"Deliver a {platform.lower()} that helps {domain} tackle {focus} by combining "
        f"workflow automation, shared dashboards, and open APIs."
    )

    def build_functionals() -> List[Dict[str, str]]:
        selected = rng.sample(FUNCTIONAL_FEATURES, k=4)
        fr_list = []
        for idx, template in enumerate(selected, start=1):
            fr_list.append(
                {
                    "id": f"FR{idx:03d}",
                    "description": template.format(focus=focus),
                    "priority": rng.choice(["High", "Medium"]),
                }
            )
        return fr_list

    def build_nfrs() -> List[Dict[str, str]]:
        selected = rng.sample(NFR_OPTIONS, k=3)
        return [
            {
                "id": f"NFR{idx:03d}",
                "description": text,
                "priority": rng.choice(["High", "Medium"]),
            }
            for idx, text in enumerate(selected, start=1)
        ]

    def build_constraints() -> List[Dict[str, str]]:
        selected = rng.sample(CONSTRAINT_OPTIONS, k=2)
        return [
            {"id": f"C{idx:03d}", "description": text, "priority": rng.choice(["High", "Medium"])}
            for idx, text in enumerate(selected, start=1)
        ]

    requirements = {
        "title": f"{platform} - {focus.title()}",
        "description": description,
        "functional_requirements": build_functionals(),
        "non_functional_requirements": build_nfrs(),
        "constraints": build_constraints(),
        "meta": {"original_request": concept},
    }

    payload = {
        "concept": concept,
        "requirements_yaml": _yaml_dump(requirements),
        "tier": tier_choice,
        "metadata": {
            "origin": "synthetic",
            "region": region,
            "focus": focus,
            "platform": platform,
            "seed_index": seed_idx,
        },
    }
    return payload


def _generate_synthetic_examples(count: int, rng: random.Random) -> List[Dict[str, Any]]:
    return [_generate_concept(idx, rng) for idx in range(count)]


# ----------------------- Main CLI Command ---------------------------------- #


@app.command()
def generate(
    existing_path: Path = typer.Option(
        Path("artifacts/synthetic/ba_train_v2_fixed.jsonl"),
        help="Path to BA synthetic dataset for reuse.",
    ),
    existing_limit: int = typer.Option(
        120,
        help="Maximum number of existing BA examples to include (0 = all).",
    ),
    synthetic_count: int = typer.Option(
        130,
        help="Number of templated synthetic examples to generate.",
    ),
    output: Path = typer.Option(
        PO_DIR / "concepts.jsonl",
        help="Destination JSONL file for Product Owner payloads.",
    ),
    seed: int = typer.Option(42, help="Random seed for deterministic generation."),
) -> None:
    """Entry point: combines existing BA outputs with synthetic concepts."""

    ensure_dirs()
    rng = random.Random(seed)

    existing = _load_existing_examples(existing_path, existing_limit, rng)
    synthetic = _generate_synthetic_examples(max(synthetic_count, 0), rng)

    combined = existing + synthetic
    if not combined:
        typer.echo("[error] No payloads generated. Check inputs.")
        raise typer.Exit(code=1)

    output.parent.mkdir(parents=True, exist_ok=True)

    for idx, entry in enumerate(combined, start=1):
        entry["concept_id"] = f"POCON-{idx:04d}"

    with output.open("w", encoding="utf-8") as fh:
        for entry in combined:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    tier_counts: Dict[str, int] = {}
    for entry in combined:
        tier = entry.get("tier", "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    typer.echo(
        f"[ok] Generated {len(combined)} payloads "
        f"({len(existing)} existing, {len(synthetic)} synthetic) → {output}"
    )
    typer.echo(f"Tier distribution: {tier_counts}")


if __name__ == "__main__":
    app()
