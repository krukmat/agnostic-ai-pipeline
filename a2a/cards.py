"""Agent Card factories and handlers for each pipeline role."""
from __future__ import annotations

import asyncio
from typing import Dict, Tuple

from scripts.run_architect import run_architect_job
from scripts.run_ba import generate_requirements
from scripts.run_dev import implement_story
from scripts.run_product_owner import evaluate_alignment
from scripts.run_qa import run_quality_checks

from .client import A2AClient

from .server import AgentCard, AgentSkill, JsonCallable


def _stub_not_implemented(skill_id: str) -> JsonCallable:
    def _handler(payload: Dict[str, str]):
        return {
            "status": "not_implemented",
            "skill": skill_id,
            "payload": payload,
        }

    return _handler


def business_analyst_card() -> Tuple[AgentCard, Dict[str, JsonCallable]]:
    skill = AgentSkill(
        id="extract_requirements",
        name="Extract Requirements",
        description="Derives structured requirements from a concept description.",
        input_modes=["text/plain", "application/json"],
        output_modes=["application/json"],
    )

    def handler(payload: Dict[str, str]):
        concept = payload.get("concept")
        if not concept:
            return {"status": "error", "detail": "'concept' is required"}
        result = asyncio.run(generate_requirements(concept))
        return {"status": "ok", **result}

    card = AgentCard(
        name="Business Analyst Agent",
        description="Transforms concepts into structured requirements for the pipeline.",
        url="http://localhost:8001/",
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["application/json"],
        capabilities={"streaming": False},
        skills=[skill],
    )
    return card, {skill.id: handler}


def product_owner_card() -> Tuple[AgentCard, Dict[str, JsonCallable]]:
    skill = AgentSkill(
        id="evaluate_alignment",
        name="Evaluate Alignment",
        description="Assesses requirements against the product vision.",
        input_modes=["application/json"],
        output_modes=["application/json"],
    )

    def handler(payload: Dict[str, str]):
        result = evaluate_alignment()
        return {"status": "ok", **result}

    card = AgentCard(
        name="Product Owner Agent",
        description="Maintains product vision and validates requirement alignment.",
        url="http://localhost:8002/",
        version="0.1.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities={"streaming": False},
        skills=[skill],
    )
    return card, {skill.id: handler}


def architect_card() -> Tuple[AgentCard, Dict[str, JsonCallable]]:
    skill = AgentSkill(
        id="generate_plan",
        name="Generate Plan",
        description="Produces PRD, architecture, and backlog artifacts.",
        input_modes=["application/json"],
        output_modes=["application/json"],
    )

    def handler(payload: Dict[str, str]):
        result = asyncio.run(
            run_architect_job(
                concept=payload.get("concept"),
                architect_mode=payload.get("mode", "normal"),
                story_id=payload.get("story_id", ""),
                detail_level=payload.get("detail_level", "medium"),
                iteration_count=int(payload.get("iteration_count", 1)),
                force_tier=payload.get("force_tier"),
            )
        )
        return {"status": "ok", **result}

    card = AgentCard(
        name="Architect Agent",
        description="Generates technical plans and story backlogs from requirements.",
        url="http://localhost:8003/",
        version="0.1.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities={"streaming": False},
        skills=[skill],
    )
    return card, {skill.id: handler}


def developer_card() -> Tuple[AgentCard, Dict[str, JsonCallable]]:
    skill = AgentSkill(
        id="implement_story",
        name="Implement Story",
        description="Generates code and tests for an assigned story.",
        input_modes=["application/json"],
        output_modes=["application/json"],
    )

    def handler(payload: Dict[str, str]):
        result = asyncio.run(
            implement_story(
                story_id=payload.get("story_id"),
                retries=int(payload.get("retries", 3)),
            )
        )
        return {"status": "ok", **result}

    card = AgentCard(
        name="Developer Agent",
        description="Implements backlog stories by generating code and tests.",
        url="http://localhost:8004/",
        version="0.1.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities={"streaming": False},
        skills=[skill],
    )
    return card, {skill.id: handler}


def qa_card() -> Tuple[AgentCard, Dict[str, JsonCallable]]:
    skill = AgentSkill(
        id="run_quality_checks",
        name="Run Quality Checks",
        description="Executes test suites and reports findings.",
        input_modes=["application/json"],
        output_modes=["application/json"],
    )

    def handler(payload: Dict[str, str]):
        allow_flag = payload.get("allow_no_tests")
        if allow_flag is None:
            allow_no_tests = True
        else:
            allow_no_tests = str(allow_flag).lower() not in {"0", "false"}
        result = run_quality_checks(
            allow_no_tests=allow_no_tests,
            story=payload.get("story_id", ""),
        )
        return {"status": result.get("status", "unknown"), **result}

    card = AgentCard(
        name="QA Agent",
        description="Validates implementation quality via automated checks.",
        url="http://localhost:8005/",
        version="0.1.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities={"streaming": False},
        skills=[skill],
    )
    return card, {skill.id: handler}


def orchestrator_card() -> Tuple[AgentCard, Dict[str, JsonCallable]]:
    skill = AgentSkill(
        id="execute_pipeline",
        name="Execute Pipeline",
        description="Coordinates the end-to-end release process.",
        input_modes=["application/json"],
        output_modes=["application/json"],
    )

    def handler(payload: Dict[str, str]):
        concept = payload.get("concept")
        client = A2AClient()
        results = {}
        if concept:
            results["business_analyst"] = client.send_task(
                "business_analyst",
                "extract_requirements",
                {"concept": concept},
            )
        else:
            results["business_analyst"] = {"status": "skipped", "detail": "concept not provided"}

        results["product_owner"] = client.send_task("product_owner", "evaluate_alignment", {})
        arch_payload = {"concept": concept} if concept else {}
        results["architect"] = client.send_task("architect", "generate_plan", arch_payload)

        return {"status": "ok", "results": results}

    card = AgentCard(
        name="Orchestrator Agent",
        description="Delegates tasks to specialised agents to deliver releases.",
        url="http://localhost:8010/",
        version="0.1.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities={"streaming": False},
        skills=[skill],
    )
    return card, {skill.id: handler}


ROLE_CARD_FACTORY = {
    "business_analyst": business_analyst_card,
    "product_owner": product_owner_card,
    "architect": architect_card,
    "developer": developer_card,
    "qa": qa_card,
    "orchestrator": orchestrator_card,
}
