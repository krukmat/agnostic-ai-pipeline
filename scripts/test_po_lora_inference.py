"""
Test inference for trained Product Owner LoRA model.

This script loads the base Qwen2.5-7B-Instruct model and the trained LoRA adapter,
then runs inference tests with Product Owner prompts to validate the fine-tuning results.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import typer
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)
from peft import PeftModel

app = typer.Typer(help="Test Product Owner LoRA model inference.")


# Test cases with realistic Product Owner validation prompts
TEST_CASES = [
    {
        "name": "basic_blog_validation",
        "prompt": """[INSTRUCTIONS]
You are a Product Owner reviewing requirements from a Business Analyst.
Validate the requirements, identify missing details, and provide feedback.

[REQUIREMENTS]
Title: Simple Blog Platform
Description: Users should be able to create and view blog posts.

Features:
- Users can create blog posts
- Posts have title and content
- Users can view all published posts

[YOUR RESPONSE]""",
    },
    {
        "name": "ecommerce_requirements",
        "prompt": """[INSTRUCTIONS]
You are a Product Owner reviewing requirements from a Business Analyst.
Validate the requirements, identify missing details, and provide feedback.

[REQUIREMENTS]
Title: E-commerce Product Catalog
Description: Build a product catalog for an online store.

Features:
- Display list of products with images
- Show product details (name, price, description)
- Search products by name
- Filter by category

[YOUR RESPONSE]""",
    },
    {
        "name": "authentication_system",
        "prompt": """[INSTRUCTIONS]
You are a Product Owner reviewing requirements from a Business Analyst.
Validate the requirements, identify missing details, and provide feedback.

[REQUIREMENTS]
Title: User Authentication System
Description: Implement user login and registration.

Features:
- User registration with email and password
- User login with credentials
- Password reset functionality
- Session management

[YOUR RESPONSE]""",
    },
    {
        "name": "task_management",
        "prompt": """[INSTRUCTIONS]
You are a Product Owner reviewing requirements from a Business Analyst.
Validate the requirements, identify missing details, and provide feedback.

[REQUIREMENTS]
Title: Task Management Dashboard
Description: Users need to track their tasks and projects.

Features:
- Create tasks with title, description, due date
- Mark tasks as complete
- Organize tasks into projects
- View task list with filters

[YOUR RESPONSE]""",
    },
    {
        "name": "incomplete_requirements",
        "prompt": """[INSTRUCTIONS]
You are a Product Owner reviewing requirements from a Business Analyst.
Validate the requirements, identify missing details, and provide feedback.

[REQUIREMENTS]
Title: Social Media Integration
Description: Add social media features.

Features:
- Share posts
- Like content

[YOUR RESPONSE]""",
    },
]


def load_model(
    base_model: str,
    adapter_path: Optional[Path],
    load_4bit: bool = True,
    device: str = "auto",
) -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    """
    Load model (base or base + LoRA adapter).

    Args:
        base_model: HuggingFace model name
        adapter_path: Path to LoRA adapter (None for baseline)
        load_4bit: Use 4-bit quantization
        device: Device map

    Returns:
        Tuple of (tokenizer, model)
    """
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: Dict[str, Any] = {"device_map": device}

    if load_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        model_kwargs.update(
            quantization_config=quant_config,
            torch_dtype=torch.float16,
        )
    else:
        model_kwargs["torch_dtype"] = torch.float16

    typer.echo(f"[load_model] Loading base model: {base_model}...")
    model = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)

    if adapter_path:
        typer.echo(f"[load_model] Loading LoRA adapter from: {adapter_path}...")
        model = PeftModel.from_pretrained(model, str(adapter_path))
        typer.echo("[load_model] LoRA adapter loaded successfully")
    else:
        typer.echo("[load_model] Running in baseline mode (no adapter)")

    return tokenizer, model


def generate_response(
    tokenizer: AutoTokenizer,
    model: AutoModelForCausalLM,
    prompt: str,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> str:
    """
    Generate response for a given prompt.

    Args:
        tokenizer: Tokenizer instance
        model: Model instance
        prompt: Input prompt
        max_new_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter

    Returns:
        Generated text
    """
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

    # Move inputs to same device as model
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode and extract only the generated part (skip input prompt)
    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Try to extract only the response part after the prompt
    if "[YOUR RESPONSE]" in full_text:
        response = full_text.split("[YOUR RESPONSE]", 1)[1].strip()
    else:
        # Fallback: remove the original prompt length
        response = full_text[len(prompt):].strip()

    return response


@app.command()
def test(
    base_model: str = typer.Option(
        "Qwen/Qwen2.5-7B-Instruct", help="Base model name."
    ),
    adapter_path: Optional[Path] = typer.Option(
        None, help="Path to LoRA adapter (None for baseline test)."
    ),
    output_dir: Path = typer.Option(
        Path("artifacts/inference_tests"), help="Directory to save results."
    ),
    load_4bit: bool = typer.Option(
        True, help="Use 4-bit quantization."
    ),
    max_new_tokens: int = typer.Option(
        512, help="Maximum tokens to generate."
    ),
    temperature: float = typer.Option(
        0.7, help="Sampling temperature."
    ),
    top_p: float = typer.Option(
        0.9, help="Nucleus sampling parameter."
    ),
    test_cases: Optional[List[int]] = typer.Option(
        None, help="Test case indices to run (e.g., --test-cases 0 --test-cases 1)."
    ),
) -> None:
    """
    Run inference tests on Product Owner LoRA model.
    """
    # Load model
    tokenizer, model = load_model(
        base_model=base_model,
        adapter_path=adapter_path,
        load_4bit=load_4bit,
    )

    # Determine which test cases to run
    if test_cases:
        selected_cases = [TEST_CASES[i] for i in test_cases if i < len(TEST_CASES)]
    else:
        selected_cases = TEST_CASES

    typer.echo(f"\n[test] Running {len(selected_cases)} test cases...")

    results = []
    for idx, test_case in enumerate(selected_cases):
        typer.echo(f"\n{'='*80}")
        typer.echo(f"Test Case {idx + 1}/{len(selected_cases)}: {test_case['name']}")
        typer.echo(f"{'='*80}\n")

        prompt = test_case["prompt"]

        typer.echo("[Prompt]")
        typer.echo(prompt[:200] + "..." if len(prompt) > 200 else prompt)
        typer.echo("\n[Generating response...]")

        response = generate_response(
            tokenizer=tokenizer,
            model=model,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        typer.echo("\n[Response]")
        typer.echo(response)
        typer.echo(f"\n{'='*80}\n")

        results.append({
            "test_case": test_case["name"],
            "prompt": prompt,
            "response": response,
            "response_length": len(response),
        })

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)

    model_type = "finetuned" if adapter_path else "baseline"
    output_file = output_dir / f"inference_results_{model_type}.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "model": base_model,
                "adapter_path": str(adapter_path) if adapter_path else None,
                "config": {
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "load_4bit": load_4bit,
                },
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    typer.echo(f"\n[test] Results saved to: {output_file}")
    typer.echo(f"[test] Total test cases: {len(results)}")
    typer.echo(f"[test] Average response length: {sum(r['response_length'] for r in results) / len(results):.0f} chars")


@app.command()
def compare(
    baseline_results: Path = typer.Option(
        Path("artifacts/inference_tests/inference_results_baseline.json"),
        help="Baseline inference results.",
    ),
    finetuned_results: Path = typer.Option(
        Path("artifacts/inference_tests/inference_results_finetuned.json"),
        help="Fine-tuned model inference results.",
    ),
    output_file: Path = typer.Option(
        Path("artifacts/inference_tests/comparison_report.md"),
        help="Comparison report output file.",
    ),
) -> None:
    """
    Compare baseline vs fine-tuned model results.
    """
    if not baseline_results.exists():
        typer.echo(f"[compare] ERROR: Baseline results not found: {baseline_results}")
        raise typer.Exit(code=1)

    if not finetuned_results.exists():
        typer.echo(f"[compare] ERROR: Fine-tuned results not found: {finetuned_results}")
        raise typer.Exit(code=1)

    with baseline_results.open("r") as f:
        baseline = json.load(f)

    with finetuned_results.open("r") as f:
        finetuned = json.load(f)

    # Generate comparison report
    report_lines = [
        "# Product Owner LoRA Model - Inference Comparison",
        "",
        f"**Date**: {os.popen('date').read().strip()}",
        "",
        "## Configuration",
        "",
        f"- **Base Model**: {baseline['model']}",
        f"- **LoRA Adapter**: {finetuned['adapter_path']}",
        f"- **Max New Tokens**: {baseline['config']['max_new_tokens']}",
        f"- **Temperature**: {baseline['config']['temperature']}",
        f"- **Top P**: {baseline['config']['top_p']}",
        "",
        "---",
        "",
        "## Results Comparison",
        "",
    ]

    for i, (base_result, ft_result) in enumerate(zip(baseline["results"], finetuned["results"])):
        test_name = base_result["test_case"]

        report_lines.extend([
            f"### Test Case {i + 1}: {test_name}",
            "",
            "#### Baseline Model Response",
            "```",
            base_result["response"],
            "```",
            "",
            "#### Fine-tuned Model Response",
            "```",
            ft_result["response"],
            "```",
            "",
            "#### Metrics",
            f"- Baseline length: {base_result['response_length']} chars",
            f"- Fine-tuned length: {ft_result['response_length']} chars",
            "",
            "---",
            "",
        ])

    report_lines.extend([
        "## Summary Statistics",
        "",
        f"- **Total test cases**: {len(baseline['results'])}",
        f"- **Average baseline length**: {sum(r['response_length'] for r in baseline['results']) / len(baseline['results']):.0f} chars",
        f"- **Average fine-tuned length**: {sum(r['response_length'] for r in finetuned['results']) / len(finetuned['results']):.0f} chars",
        "",
    ])

    # Write report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    typer.echo(f"[compare] Comparison report saved to: {output_file}")


if __name__ == "__main__":
    app()
