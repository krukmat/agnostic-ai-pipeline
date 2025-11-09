#!/usr/bin/env python3
"""Audit BA dataset for quality issues before fine-tuning.

Checks:
1. ID format (FR01 vs FR001)
2. YAML validity
3. Minimum requirements count
4. Field completeness
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import typer
import yaml

app = typer.Typer(help="Audit BA dataset for format issues")


def audit_example(example: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """Audit a single example and return issues found."""
    issues = {
        "example_id": example.get("concept_id", f"UNKNOWN-{idx}"),
        "index": idx,
        "id_format_issues": [],
        "yaml_validation_errors": [],
        "min_requirements_violations": [],
        "field_completeness_issues": [],
    }

    # Check field completeness
    requirements = example.get("requirements", {})
    required_fields = ["title", "description", "functional_requirements",
                      "non_functional_requirements", "constraints"]

    for field in required_fields:
        if field not in requirements:
            issues["field_completeness_issues"].append(f"Missing field: {field}")

    # Check each requirement category
    for category in ["functional_requirements", "non_functional_requirements", "constraints"]:
        if category not in requirements:
            continue

        items = requirements[category]

        # Check if it's a list (JSON format)
        if isinstance(items, list):
            # ID format check (should be XXX001, not XXX01)
            prefix_map = {
                "functional_requirements": "FR",
                "non_functional_requirements": "NFR",
                "constraints": "C"
            }
            prefix = prefix_map[category]

            for item in items:
                if isinstance(item, dict) and "id" in item:
                    item_id = item["id"]
                    # Check if ID matches XXX01 pattern (incorrect)
                    if re.match(rf"{prefix}\d{{2}}$", item_id):
                        issues["id_format_issues"].append(
                            f"{category}: {item_id} should be {prefix}0{item_id[len(prefix):]}"
                        )
                    # Check if ID matches XXX001 pattern (correct)
                    elif not re.match(rf"{prefix}\d{{3}}$", item_id):
                        issues["id_format_issues"].append(
                            f"{category}: {item_id} has invalid format (expected {prefix}###)"
                        )

            # Minimum count check
            if len(items) < 2:
                issues["min_requirements_violations"].append(
                    f"{category}: only {len(items)} items (minimum 2 required)"
                )

        # Check if it's a string (YAML format) - validate YAML
        elif isinstance(items, str):
            try:
                parsed = yaml.safe_load(items)
                if not isinstance(parsed, list):
                    issues["yaml_validation_errors"].append(
                        f"{category}: YAML does not parse to a list"
                    )
                elif len(parsed) < 2:
                    issues["min_requirements_violations"].append(
                        f"{category}: only {len(parsed)} items (minimum 2 required)"
                    )
                else:
                    # Check ID format in YAML
                    prefix_map = {
                        "functional_requirements": "FR",
                        "non_functional_requirements": "NFR",
                        "constraints": "C"
                    }
                    prefix = prefix_map[category]

                    for item in parsed:
                        if isinstance(item, dict) and "id" in item:
                            item_id = item["id"]
                            if re.match(rf"{prefix}\d{{2}}$", item_id):
                                issues["id_format_issues"].append(
                                    f"{category}: {item_id} should be {prefix}0{item_id[len(prefix):]}"
                                )
            except yaml.YAMLError as e:
                issues["yaml_validation_errors"].append(
                    f"{category}: YAML parsing error - {str(e)}"
                )

    return issues


@app.command()
def main(
    dataset: Path = typer.Option(
        ...,
        "--dataset",
        "-d",
        help="Path to JSONL dataset file",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(
        Path("artifacts/fase8/dataset_audit_report.json"),
        "--output",
        "-o",
        help="Path to output JSON report",
    ),
) -> None:
    """Audit BA dataset and generate quality report."""
    typer.echo(f"🔍 Auditing dataset: {dataset}")

    # Load dataset
    examples: List[Dict[str, Any]] = []
    for line in dataset.read_text(encoding="utf-8").splitlines():
        if line.strip():
            examples.append(json.loads(line))

    typer.echo(f"📊 Loaded {len(examples)} examples")

    # Audit each example
    all_issues: List[Dict[str, Any]] = []
    stats = {
        "total_examples": len(examples),
        "id_format_issues_count": 0,
        "yaml_validation_errors_count": 0,
        "min_requirements_violations_count": 0,
        "field_completeness_issues_count": 0,
        "valid_examples_count": 0,
        "examples_with_issues": [],
    }

    for idx, example in enumerate(examples):
        issues = audit_example(example, idx)

        has_issues = any([
            issues["id_format_issues"],
            issues["yaml_validation_errors"],
            issues["min_requirements_violations"],
            issues["field_completeness_issues"],
        ])

        if has_issues:
            all_issues.append(issues)
            stats["id_format_issues_count"] += len(issues["id_format_issues"])
            stats["yaml_validation_errors_count"] += len(issues["yaml_validation_errors"])
            stats["min_requirements_violations_count"] += len(issues["min_requirements_violations"])
            stats["field_completeness_issues_count"] += len(issues["field_completeness_issues"])
            stats["examples_with_issues"].append(issues["example_id"])
        else:
            stats["valid_examples_count"] += 1

    # Generate report
    report = {
        "dataset": str(dataset),
        "timestamp": "2025-11-09",
        "summary": stats,
        "issues_by_example": all_issues,
    }

    # Write report
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    typer.echo(f"\n✅ Audit complete!")
    typer.echo(f"📄 Report saved to: {output}")
    typer.echo(f"\n📊 Summary:")
    typer.echo(f"  Total examples: {stats['total_examples']}")
    typer.echo(f"  Valid examples: {stats['valid_examples_count']}")
    typer.echo(f"  Examples with issues: {len(all_issues)}")
    typer.echo(f"\n⚠️  Issue Breakdown:")
    typer.echo(f"  ID format issues: {stats['id_format_issues_count']}")
    typer.echo(f"  YAML validation errors: {stats['yaml_validation_errors_count']}")
    typer.echo(f"  Min requirements violations: {stats['min_requirements_violations_count']}")
    typer.echo(f"  Field completeness issues: {stats['field_completeness_issues_count']}")


if __name__ == "__main__":
    app()
