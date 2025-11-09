#!/usr/bin/env python3
"""Fix BA dataset format issues before fine-tuning.

Corrections:
1. ID format: FR01 → FR001, NFR01 → NFR001, C01 → C001
2. YAML string conversion (if needed)
3. Validation of corrections
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import typer
import yaml

app = typer.Typer(help="Fix BA dataset format issues")


def fix_id_format(item_id: str) -> str:
    """Fix ID format from XXX01 to XXX001."""
    # Match FR01, NFR01, C01 patterns and fix to FR001, NFR001, C001
    match = re.match(r"(FR|NFR|C)(\d{2})$", item_id)
    if match:
        prefix, number = match.groups()
        return f"{prefix}0{number}"
    return item_id


def fix_example(example: Dict[str, Any], convert_to_yaml: bool = False) -> Dict[str, Any]:
    """Fix a single example's format issues."""
    fixed = example.copy()

    if "requirements" not in fixed:
        return fixed

    requirements = fixed["requirements"]

    # Fix each requirements category
    for category in ["functional_requirements", "non_functional_requirements", "constraints"]:
        if category not in requirements:
            continue

        items = requirements[category]

        # Handle list format (JSON)
        if isinstance(items, list):
            fixed_items = []
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    fixed_item = item.copy()
                    fixed_item["id"] = fix_id_format(item["id"])
                    fixed_items.append(fixed_item)
                else:
                    fixed_items.append(item)

            # If convert_to_yaml flag is set, convert to YAML string
            if convert_to_yaml:
                yaml_str = yaml.safe_dump(fixed_items, allow_unicode=True, default_flow_style=False)
                requirements[category] = yaml_str.strip()
            else:
                requirements[category] = fixed_items

        # Handle string format (YAML)
        elif isinstance(items, str):
            try:
                parsed = yaml.safe_load(items)
                if isinstance(parsed, list):
                    fixed_items = []
                    for item in parsed:
                        if isinstance(item, dict) and "id" in item:
                            fixed_item = item.copy()
                            fixed_item["id"] = fix_id_format(item["id"])
                            fixed_items.append(fixed_item)
                        else:
                            fixed_items.append(item)

                    # Re-serialize to YAML string
                    yaml_str = yaml.safe_dump(fixed_items, allow_unicode=True, default_flow_style=False)
                    requirements[category] = yaml_str.strip()
            except yaml.YAMLError:
                # If parsing fails, leave as-is
                pass

    return fixed


@app.command()
def main(
    input_file: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Input JSONL dataset file",
        exists=True,
        readable=True,
    ),
    output_file: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output JSONL dataset file (corrected)",
    ),
    convert_to_yaml: bool = typer.Option(
        False,
        "--convert-to-yaml",
        help="Convert JSON lists to YAML strings",
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Validate corrections after processing",
    ),
) -> None:
    """Fix BA dataset format issues."""
    typer.echo(f"🔧 Fixing dataset: {input_file}")
    typer.echo(f"📝 Output: {output_file}")
    if convert_to_yaml:
        typer.echo("✨ Converting JSON lists to YAML strings")

    # Load dataset
    examples: List[Dict[str, Any]] = []
    for line in input_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            examples.append(json.loads(line))

    typer.echo(f"📊 Loaded {len(examples)} examples")

    # Fix each example
    fixed_examples: List[Dict[str, Any]] = []
    corrections_count = 0

    for example in examples:
        fixed = fix_example(example, convert_to_yaml=convert_to_yaml)
        fixed_examples.append(fixed)

        # Count corrections (approximate)
        if "requirements" in example:
            for category in ["functional_requirements", "non_functional_requirements", "constraints"]:
                if category in example["requirements"]:
                    items = example["requirements"][category]
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "id" in item:
                                if re.match(r"(FR|NFR|C)\d{2}$", item["id"]):
                                    corrections_count += 1

    # Write fixed dataset
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        for example in fixed_examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")

    typer.echo(f"\n✅ Fixed {len(fixed_examples)} examples")
    typer.echo(f"🔧 Applied ~{corrections_count} ID corrections")
    typer.echo(f"📄 Saved to: {output_file}")

    # Validation
    if validate:
        typer.echo("\n🔍 Validating corrections...")

        errors = 0
        for idx, example in enumerate(fixed_examples):
            if "requirements" not in example:
                continue

            requirements = example["requirements"]

            for category in ["functional_requirements", "non_functional_requirements", "constraints"]:
                if category not in requirements:
                    continue

                items = requirements[category]

                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "id" in item:
                            item_id = item["id"]
                            # Check if still has incorrect format
                            if re.match(r"(FR|NFR|C)\d{2}$", item_id):
                                typer.echo(f"  ⚠️  Example {idx}: {category} still has incorrect ID: {item_id}")
                                errors += 1

                elif isinstance(items, str):
                    try:
                        parsed = yaml.safe_load(items)
                        if isinstance(parsed, list):
                            for item in parsed:
                                if isinstance(item, dict) and "id" in item:
                                    item_id = item["id"]
                                    if re.match(r"(FR|NFR|C)\d{2}$", item_id):
                                        typer.echo(f"  ⚠️  Example {idx}: {category} still has incorrect ID: {item_id}")
                                        errors += 1
                    except yaml.YAMLError as e:
                        typer.echo(f"  ⚠️  Example {idx}: {category} has YAML error: {e}")
                        errors += 1

        if errors == 0:
            typer.echo("✅ Validation passed! No format errors detected.")
        else:
            typer.echo(f"⚠️  Validation found {errors} remaining issues.")


if __name__ == "__main__":
    app()
