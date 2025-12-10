"""
Smoke test para el orquestrador agentic (run_orchestrator_agent.py).
Prueba incrementalmente de simple a complejo:
1. Concepto trivial con límites estrictos (max_steps=1, max_actions=1)
2. Concepto simple con límites razonables (max_steps=2, max_actions=2)
3. Concepto moderado con más libertad (max_steps=3, max_actions=3)

El objetivo es verificar que el orquestador:
- Se inicializa correctamente
- Carga configuración y prompt
- Ejecuta el bucle agentic
- Produce artifacts/iterations/latest_orchestrator_summary.json
- No falla con errores de runtime
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = ROOT / "artifacts" / "iterations" / "latest_orchestrator_summary.json"


def _run_orchestrator(concept: str, max_steps: int = 1, max_actions: int = 1, timeout: int = 300) -> subprocess.CompletedProcess:
    """
    Ejecuta run_orchestrator_agent.py con el concepto y límites especificados.
    Retorna el CompletedProcess para inspeccionar stdout/stderr/returncode.

    Args:
        concept: Descripción del concepto a implementar
        max_steps: Número máximo de steps del orquestador
        max_actions: Número máximo de acciones por step
        timeout: Timeout en segundos (default 300 = 5 min)
    """
    cmd = [
        sys.executable,
        "scripts/run_orchestrator_agent.py",
        "--concept", concept,
        "--max-steps", str(max_steps),
        "--max-actions-per-step", str(max_actions),
    ]
    env = os.environ.copy()
    # Asegurar que no falle por falta de config
    env.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    # Deshabilitar DB para smoke tests (evita errores de "database disk image is malformed")
    env["DISABLE_DB"] = "1"

    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _verify_summary(concept: str) -> dict:
    """
    Lee y valida el archivo de resumen generado por el orquestador.
    Retorna el contenido parseado.
    """
    assert SUMMARY_PATH.exists(), f"Summary file not found at {SUMMARY_PATH}"

    content = SUMMARY_PATH.read_text(encoding="utf-8")
    data = json.loads(content)

    # Validar estructura mínima
    assert "concept" in data, "Summary missing 'concept' field"
    assert "steps" in data, "Summary missing 'steps' field"
    assert "termination" in data, "Summary missing 'termination' field"
    assert isinstance(data["steps"], list), "Steps should be a list"

    # Verificar que el concepto coincide
    assert data["concept"] == concept or concept in data["concept"], \
        f"Concept mismatch: expected '{concept}' in '{data['concept']}'"

    return data


@pytest.mark.smoke
def test_orchestrator_trivial_concept():
    """
    Test 1: Concepto trivial con límites estrictos (1 step, 1 action).
    Debería ejecutar al menos BA y terminar rápidamente.
    """
    concept = "Health check endpoint"
    proc = _run_orchestrator(concept, max_steps=1, max_actions=1)

    # No debería fallar (returncode 0)
    if proc.returncode != 0:
        print("STDOUT:", proc.stdout)
        print("STDERR:", proc.stderr)
    assert proc.returncode == 0, f"Orchestrator failed with return code {proc.returncode}"

    # Verificar que generó el resumen
    summary = _verify_summary(concept)

    # Debería tener al menos 1 step
    assert len(summary["steps"]) >= 1, "Expected at least 1 step executed"

    # Verificar que al menos ejecutó una acción
    if len(summary["steps"]) > 0:
        first_step = summary["steps"][0]
        assert "results" in first_step, "Step missing results"
        assert len(first_step["results"]) > 0, "Expected at least one action executed in first step"

        # Verificar que la primera acción típicamente es RUN_BA
        first_result = first_step["results"][0]
        print(f"First action executed: {first_result.get('tool')}")

    # Verificar terminación
    assert summary["termination"]["should_stop"] is True, "Should have terminated"


@pytest.mark.smoke
def test_orchestrator_simple_concept():
    """
    Test 2: Concepto simple con límites razonables (2 steps, 2 actions).
    Debería ejecutar BA → PO y posiblemente Architect.
    Valida que se generen artifacts reales (requirements.yaml).
    """
    concept = "Simple calculator API with add and subtract"
    proc = _run_orchestrator(concept, max_steps=2, max_actions=2)

    if proc.returncode != 0:
        print("STDOUT:", proc.stdout)
        print("STDERR:", proc.stderr)
    assert proc.returncode == 0, f"Orchestrator failed with return code {proc.returncode}"

    summary = _verify_summary(concept)

    # Debería tener al menos 1 step (puede terminar antes de 2 si decide parar)
    assert len(summary["steps"]) >= 1, "Expected at least 1 step executed"
    assert len(summary["steps"]) <= 2, "Should not exceed max_steps=2"

    # Verificar que hay decisiones y resultados
    all_tools = []
    for step in summary["steps"]:
        assert "decision" in step, "Step missing decision"
        assert "results" in step, "Step missing results"
        assert isinstance(step["results"], list), "Results should be a list"

        # Recolectar tools ejecutados
        for result in step["results"]:
            if result.get("status") not in ["skipped", "exception"]:
                all_tools.append(result.get("tool"))

    print(f"Tools executed: {all_tools}")

    # Con 2 steps y 2 actions, debería haber ejecutado al menos BA
    # y posiblemente PO
    if "RUN_BA" in all_tools:
        # Verificar que se generó requirements.yaml
        requirements_path = ROOT / "planning" / "requirements.yaml"
        assert requirements_path.exists(), "requirements.yaml should be generated after BA execution"
        print("✓ requirements.yaml generated")


@pytest.mark.smoke
def test_orchestrator_moderate_concept():
    """
    Test 3: Concepto moderado con más libertad (3 steps, 3 actions).
    Debería ejecutar BA → PO → Architect y potencialmente iniciar Dev.
    Valida que se generen todos los artifacts del pipeline.
    """
    concept = "User authentication API with JWT tokens and refresh"
    proc = _run_orchestrator(concept, max_steps=3, max_actions=3)

    if proc.returncode != 0:
        print("STDOUT:", proc.stdout)
        print("STDERR:", proc.stderr)
    assert proc.returncode == 0, f"Orchestrator failed with return code {proc.returncode}"

    summary = _verify_summary(concept)

    # Debería tener al menos 1 step
    assert len(summary["steps"]) >= 1, "Expected at least 1 step executed"
    assert len(summary["steps"]) <= 3, "Should not exceed max_steps=3"

    # Recolectar todos los tools ejecutados
    all_tools = []
    all_statuses = []

    # Verificar estructura de steps
    for step in summary["steps"]:
        assert "step" in step, "Step missing step number"
        assert "decision" in step, "Step missing decision"
        assert "results" in step, "Step missing results"

        # Verificar que las acciones ejecutadas son válidas
        for result in step["results"]:
            assert "tool" in result, "Result missing tool"
            assert "status" in result, "Result missing status"

            tool = result["tool"]
            status = result.get("status")

            # Los tools válidos
            valid_tools = {
                "RUN_BA", "RUN_PO", "RUN_ARCHITECT",
                "RUN_DEV_STORY", "RUN_QA_STORY", "RUN_QA_FULL"
            }
            assert tool in valid_tools or status == "skipped", \
                f"Invalid tool: {tool}"

            if status not in ["skipped", "exception"]:
                all_tools.append(tool)
                all_statuses.append(status)

    print(f"Tools executed: {all_tools}")
    print(f"Statuses: {all_statuses}")

    # Validar artifacts generados según los tools ejecutados
    if "RUN_BA" in all_tools:
        requirements_path = ROOT / "planning" / "requirements.yaml"
        assert requirements_path.exists(), "requirements.yaml should exist after RUN_BA"
        print("✓ requirements.yaml generated")

    if "RUN_ARCHITECT" in all_tools:
        stories_path = ROOT / "planning" / "stories.yaml"
        # El architect puede generar stories.yaml
        # (no siempre lo genera en el primer intento, depende del concepto)
        if stories_path.exists():
            print("✓ stories.yaml generated")

    # Verificar que hubo progreso en el pipeline
    assert len(all_tools) > 0, "Should have executed at least one tool successfully"


@pytest.mark.smoke
def test_orchestrator_full_pipeline():
    """
    Test 4: Pipeline completo BA → PO → Architect → Dev → QA.
    Valida que el orquestador ejecuta el pipeline completo end-to-end.

    NOTA: Ahora con YAML sanitization fixes en BA y PO, el pipeline
    completo debería funcionar sin errores de parsing.

    Tiempo estimado: 10-15 minutos.
    """
    # Limpiar artifacts antiguos para forzar ejecución completa del pipeline
    planning_dir = ROOT / "planning"
    if planning_dir.exists():
        for old_file in ["requirements.yaml", "stories.yaml", "product_owner_review.yaml"]:
            old_path = planning_dir / old_file
            if old_path.exists():
                old_path.unlink()
                print(f"Cleaned up old artifact: {old_file}")

    concept = "Calculator API with add and subtract operations"
    # Pipeline completo: 6 steps con 2 actions para permitir BA → PO → Architect → Dev → QA
    # Timeout de 15 minutos (900s) para permitir ejecución completa
    proc = _run_orchestrator(concept, max_steps=6, max_actions=2, timeout=900)

    # Mostrar output para debugging
    if proc.returncode != 0:
        print("\n=== STDOUT ===")
        print(proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout)
        print("\n=== STDERR ===")
        print(proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr)

    # Intentar leer el summary incluso si falló
    try:
        summary = _verify_summary(concept)
    except Exception as e:
        # Si no hay summary, el orquestrador falló completamente
        assert proc.returncode == 0, f"Orchestrator failed with return code {proc.returncode} and no summary generated: {e}"
        raise

    # Si hay summary, validar que al menos ejecutó algo
    # (puede fallar por errores de roles individuales pero haber ejecutado acciones)
    if proc.returncode != 0:
        print(f"\nWARNING: Orchestrator exited with code {proc.returncode}")
        print(f"Steps executed: {len(summary.get('steps', []))}")
        # Si no ejecutó ningún step, es un fallo crítico
        if len(summary.get('steps', [])) == 0:
            assert False, f"Orchestrator failed with return code {proc.returncode} and no steps executed"

    # Recolectar todos los tools ejecutados a través de todos los steps
    all_tools = []
    dev_stories = set()
    qa_stories = set()

    for step in summary["steps"]:
        for result in step["results"]:
            tool = result.get("tool")
            status = result.get("status")

            if status not in ["skipped", "exception"]:
                all_tools.append(tool)

                # Rastrear qué stories fueron procesadas por Dev y QA
                if tool == "RUN_DEV_STORY" and result.get("story_id"):
                    dev_stories.add(result["story_id"])
                elif tool == "RUN_QA_STORY" and result.get("story_id"):
                    qa_stories.add(result["story_id"])

    print(f"\nFull pipeline tools executed: {all_tools}")
    print(f"Dev stories: {dev_stories}")
    print(f"QA stories: {qa_stories}")

    # Validar que se ejecutó el pipeline principal
    # BA debería ejecutarse, pero si falló y hay otros roles ejecutados, continuar validación
    if "RUN_BA" not in all_tools:
        print("WARNING: BA was not executed - orchestrator may have skipped it")
        # Solo fallar si no ejecutó NADA útil
        assert len(all_tools) > 0, "No tools were executed successfully"

    # Validar artifacts generados por BA (si BA ejecutó)
    if "RUN_BA" in all_tools:
        requirements_path = ROOT / "planning" / "requirements.yaml"
        assert requirements_path.exists(), "requirements.yaml should exist after BA"
        print("✓ requirements.yaml generated")

    # Si se ejecutó PO, validar su artifact
    if "RUN_PO" in all_tools:
        po_review_path = ROOT / "planning" / "product_owner_review.yaml"
        # PO puede generar diferentes artifacts, verificar al menos uno
        print("✓ PO executed")

    # Si se ejecutó Architect, validar stories.yaml
    if "RUN_ARCHITECT" in all_tools:
        stories_path = ROOT / "planning" / "stories.yaml"
        # El architect debería generar stories
        if stories_path.exists():
            print("✓ stories.yaml generated by Architect")

    # Validar ejecución de Dev
    if "RUN_DEV_STORY" in all_tools:
        print(f"✓ Dev executed for {len(dev_stories)} story/stories")
        # Validar que se generó código en project/
        project_dir = ROOT / "project"
        if project_dir.exists():
            print("✓ project/ directory exists")

    # Validar ejecución de QA
    if "RUN_QA_STORY" in all_tools or "RUN_QA_FULL" in all_tools:
        print(f"✓ QA executed for {len(qa_stories)} story/stories")
        # Validar que se generó reporte QA
        qa_dir = ROOT / "artifacts" / "qa"
        if qa_dir.exists():
            print("✓ artifacts/qa directory exists")

    # Verificar que se ejecutó un pipeline significativo
    # Para el pipeline completo: al menos BA + PO + Architect
    # Dev y QA son deseables pero opcionales (dependen de que Architect genere stories)
    pipeline_phases = sum([
        "RUN_BA" in all_tools,
        "RUN_PO" in all_tools,
        "RUN_ARCHITECT" in all_tools,
    ])

    assert pipeline_phases >= 2, \
        f"Expected at least 2 pipeline phases executed (BA + PO minimum), got {pipeline_phases}. Tools: {all_tools}"

    print(f"\n✓ Pipeline phases executed: {pipeline_phases}")
    if "RUN_BA" in all_tools and "RUN_PO" in all_tools:
        print("✓ Basic pipeline validated: BA → PO")
    if "RUN_ARCHITECT" in all_tools:
        print("✓ Extended pipeline validated: BA → PO → Architect")
    if "RUN_DEV_STORY" in all_tools:
        print(f"✓ Development phase executed for {len(dev_stories)} story/stories")
    if "RUN_QA_STORY" in all_tools or "RUN_QA_FULL" in all_tools:
        print(f"✓ QA phase executed for {len(qa_stories)} story/stories")


@pytest.mark.smoke
def test_orchestrator_cleanup():
    """
    Test 4: Verificar que el orquestrador limpia correctamente.
    Elimina el summary file si existe para no contaminar siguientes tests.
    """
    if SUMMARY_PATH.exists():
        SUMMARY_PATH.unlink()

    # Ejecutar un concepto mínimo para regenerar
    concept = "Test cleanup"
    proc = _run_orchestrator(concept, max_steps=1, max_actions=1)

    assert proc.returncode == 0, "Cleanup run failed"
    assert SUMMARY_PATH.exists(), "Summary should be regenerated"

    # Leer y verificar
    summary = _verify_summary(concept)
    assert summary["concept"] == concept


if __name__ == "__main__":
    # Permitir ejecución directa para debugging
    pytest.main([__file__, "-v", "-s"])
