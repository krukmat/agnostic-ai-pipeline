SHELL := /bin/bash
.DEFAULT_GOAL := help

PY    := PYTHONPATH=. ./.venv/bin/python -u

help:
	@echo "Targets:"
	@echo "  setup        -> venv + deps base"
	@echo "  ba           -> Business Analyst (DSPy, genera planning/requirements.yaml)"
	@echo "  po           -> Product Owner (valida visión vs requirements)"
	@echo "  plan         -> Arquitecto + normaliza historias"
	@echo "  dev          -> Developer (toma siguiente 'todo')"
	@echo "  qa           -> QA textual (+tests si QA_RUN_TESTS=1)"
	@echo "  agentic-iteration -> Iteración agentic (LLM orquestador) con CONCEPT"
	@echo "  fix-stories  -> Normaliza planning/stories.yaml"
	@echo "  show-config  -> Muestra config.yaml"
	@echo "  set-role     -> role=<ba|architect|dev|qa> provider=<ollama|openai> model=..."
	@echo "  set-quality  -> profile=<low|normal|high> [role=...]"
	@echo "  clean        -> Limpia artifacts/ y reestablece planning/ + project/ (usa CLEAN_FLUSH=0 para conservarlos)"
	@echo "  warmup       -> Inicia los servicios A2A remotos necesarios"
	@echo "  spike        -> (deprecated) BA→PO→Architect→Dev sin QA; usar agentic-iteration"

spike:
	@echo "==> Spike deprecated. Use 'make agentic-iteration CONCEPT=\"...\" MAX_STEPS=2 MAX_ACTIONS=2' en su lugar."
	@exit 1

setup:
	python3 -m venv .venv || true
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -r requirements.txt
	./.venv/bin/pip install pyyaml httpx openai >/dev/null

ba:
	@if [ -z "$$CONCEPT" ]; then echo 'Set CONCEPT="..."'; exit 1; fi
	@echo "==> Ejecutando BA (configurable DSPy/legacy)"
	CONCEPT="$$CONCEPT" $(PY) scripts/run_ba.py
	@echo "==> planning/requirements.yaml actualizado (DSPy)"

.PHONY: dspy-ba
dspy-ba:
	@if [ -z "$$CONCEPT" ]; then echo 'Set CONCEPT="..."'; exit 1; fi
	@echo "Running DSPy BA module..."
	$(PY) dspy_baseline/scripts/run_ba.py --concept "$$CONCEPT" --verbose


po:
	CONCEPT="$$CONCEPT" USE_DSPY_PO="$${USE_DSPY_PO:-}" $(PY) scripts/run_product_owner.py
	@echo "==> planning/product_owner_review.yaml"
	@sed -n '1,40p' planning/product_owner_review.yaml 2>/dev/null || true

plan:
	@if [ -z "$$CONCEPT" ]; then \
		$(PY) -c 'import sys,yaml,pathlib; from scripts.utils.yaml_sanitizer import sanitize_requirements_yaml; path=pathlib.Path("planning/requirements.yaml"); raw=path.read_text(encoding="utf-8") if path.exists() else ""; clean=sanitize_requirements_yaml(raw) if raw else ""; data=yaml.safe_load(clean) if clean else None; meta=data.get("meta") if isinstance(data, dict) else {}; concept=meta.get("original_request") if isinstance(meta, dict) else ""; sys.exit(0 if isinstance(concept,str) and concept.strip() else 1)' || { echo 'Set CONCEPT="..." or ensure planning/requirements.yaml contains meta.original_request'; exit 1; }; \
	fi
	CHECK_ARCHITECTURE=0 ALLOW_EMPTY_STORIES=1 $(PY) scripts/checks/pipeline_guard.py
	CONCEPT="$$CONCEPT" \
	FORCE_ARCHITECT_TIER="$${FORCE_ARCHITECT_TIER:-}" \
	$(PY) scripts/run_architect.py
	$(PY) scripts/fix_stories.py
	@echo "==> planning/stories.yaml (primeras 60 líneas)"
	@sed -n '1,60p' planning/stories.yaml || true

dev:
	STORY="$$STORY" DEV_RETRIES="$${DEV_RETRIES:-3}" $(PY) scripts/run_dev.py

qa:
	DSPY_QA_SKIP_IF_MISSING="$${DSPY_QA_SKIP_IF_MISSING:-0}" $(PY) scripts/generate_dspy_testcases.py
	DSPY_QA_SKIP_IF_MISSING="$${DSPY_QA_SKIP_IF_MISSING:-0}" $(PY) scripts/lint_dspy_testcases.py
	QA_RUN_TESTS="$${QA_RUN_TESTS:-0}" $(PY) scripts/run_qa.py

clean:
	CLEAN_FLUSH="$${CLEAN_FLUSH:-$${FLUSH:-1}}" $(PY) scripts/run_cleanup.py

loop:
	@echo "==> Target loop deprecated. Use agentic-iteration."
	@exit 1

loop-dev:
	@echo "==> Target loop-dev deprecated. Use agentic-iteration."
	@exit 1

fix-stories:
	$(PY) scripts/fix_stories.py

agentic-iteration:
	@if [ -z "$$CONCEPT" ]; then echo 'Set CONCEPT="..."'; exit 1; fi
	@echo "==> Ejecutando iteración agentic con concepto: $${CONCEPT}"
	$(PY) scripts/run_orchestrator_agent.py --concept "$${CONCEPT}" $${MAX_STEPS:+--max-steps $${MAX_STEPS}} $${MAX_ACTIONS:+--max-actions-per-step $${MAX_ACTIONS}}

agentic-iteration-v2:
	@if [ -z "$$CONCEPT" ]; then echo 'Set CONCEPT="..."'; exit 1; fi
	@echo "==> Ejecutando iteración agentic V2 con concepto: $${CONCEPT}"
	$(PY) scripts/run_orchestrator_agent.py --concept "$${CONCEPT}" --use-v2 $${MAX_STEPS:+--max-steps $${MAX_STEPS}}

# Database observability targets (Fase 5)
db-stats:
	@echo "==> Database Statistics"
	PYTHONPATH=. $(PY) scripts/db_stats.py

db-models:
	@echo "==> Model Statistics"
	PYTHONPATH=. $(PY) scripts/db_stats.py --models

db-costs:
	@echo "==> Cost Summary"
	PYTHONPATH=. $(PY) scripts/db_stats.py --costs

db-verify:
	@echo "==> Verifying DB vs YAML consistency"
	PYTHONPATH=. $(PY) scripts/db_verify.py -v

db-migrate:
	@echo "==> Running database migration"
	PYTHONPATH=. $(PY) scripts/db_migrate.py

drivers-validate:
	@echo "==> Validating driver definitions"
	PYTHONPATH=. $(PY) -m drivers.registry validate --all

drivers-show:
	@echo "==> Resolving drivers from config.yaml (behind feature flag)"
	PYTHONPATH=. $(PY) scripts/drivers_show.py

drivers-list:
	@echo "==> Listing available drivers"
	PYTHONPATH=. $(PY) -m drivers.registry list

drivers-plan:
	@echo "==> Planning driver execution from config.yaml"
	PYTHONPATH=. $(PY) -m drivers.registry plan

drivers-scaffold:
	@echo "==> Scaffolding driver templates (when missing)"
	PYTHONPATH=. $(PY) scripts/drivers_scaffold.py

drivers-test:
	@echo "==> Running driver layer tests (pytest)"
	PYTHONPATH=. $(PY) -m pytest -q tests/driver_layer

qa-smoke:
	@echo "==> QA Smoke: backend-fastapi"
	@if [ -f project/backend-fastapi/tests/test_smoke.py ]; then \
		.venv/bin/pytest -q project/backend-fastapi/tests/test_smoke.py || true; \
	else \
		echo "(skip) backend smoke not present"; \
	fi
	@echo "==> QA Smoke: web-express"
	@if [ -f project/web-express/package.json ]; then \
		if [ -x project/web-express/node_modules/.bin/jest ]; then \
			cd project/web-express && npm test -- --passWithNoTests || true; \
		else \
			echo "(skip) Jest not installed in web-express"; \
		fi; \
	else \
		echo "(skip) web package.json not found"; \
	fi

dev-smoke:
	@echo "==> Dev Smoke: backend-fastapi"
	@if [ -f project/backend-fastapi/tests/test_smoke.py ]; then \
		.venv/bin/pytest -q project/backend-fastapi/tests/test_smoke.py || true; \
	else \
		echo "(skip) backend smoke not present"; \
	fi
	@echo "==> Dev Smoke: web-express"
	@if [ -f project/web-express/package.json ]; then \
		if [ -x project/web-express/node_modules/.bin/jest ]; then \
			cd project/web-express && npm test -- --passWithNoTests || true; \
		else \
			echo "(skip) Jest not installed in web-express"; \
		fi; \
	else \
		echo "(skip) web package.json not found"; \
	fi

qa-summary:
	@echo "==> QA Summary"
	@STORY_FILE=""; \
	if [ -n "$$STORY" ] && [ -f artifacts/qa/"$$STORY"/qa_summary.json ]; then \
		STORY_FILE=artifacts/qa/"$$STORY"/qa_summary.json; \
	else \
		STORY_FILE=$$(ls -t artifacts/qa/*/qa_summary.json 2>/dev/null | head -n1); \
	fi; \
	if [ -z "$$STORY_FILE" ]; then \
		echo "(no qa_summary.json found)"; \
		exit 0; \
	fi; \
	if command -v jq >/dev/null 2>&1; then \
		jq . "$$STORY_FILE"; \
	else \
		$(PY) -m json.tool "$$STORY_FILE"; \
	fi

# 7.6 — Lint/Typing (new modules)
lint-new:
	@echo "==> Lint (ruff) for new modules (drivers/*, scripts/utils)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check drivers scripts/utils; \
	else \
		echo "(skip) ruff not installed"; \
	fi

typecheck-new:
	@echo "==> Type check (mypy) for new modules"
	@if command -v mypy >/dev/null 2>&1; then \
		mypy --ignore-missing-imports drivers scripts/utils; \
	else \
		echo "(skip) mypy not installed"; \
	fi

show-config:
	$(PY) -c "import yaml,sys;print(yaml.safe_load(open('config.yaml').read()))"

set-role:
	$(PY) scripts/set_role.py --role $(role) --provider $(provider) --model $(model)

set-quality:
	$(PY) scripts/set_quality.py --profile $(profile) $(if $(role),--role $(role),)

iteration:
	@ITERATION_NAME=$${ITERATION_NAME:-iteration-$$(date +%Y%m%d-%H%M%S)}; \
	echo "==> Running iteration $$ITERATION_NAME"; \
	ITERATION_NAME="$$ITERATION_NAME" \
	CONCEPT="$$CONCEPT" \
	LOOPS="$${LOOPS:-1}" \
	ALLOW_NO_TESTS="$${ALLOW_NO_TESTS:-0}" \
	SKIP_BA="$${SKIP_BA:-0}" \
	SKIP_PLAN="$${SKIP_PLAN:-0}" \
	$(PY) scripts/run_iteration.py

warmup:
	@echo "--- Warming up remote services ---"
	@$(PY) -c "from a2a.runtime import warmup; warmup()"

.PHONY: dspy-qa
dspy-qa:
	@$(PY) scripts/generate_dspy_testcases.py

.PHONY: dspy-qa-lint
dspy-qa-lint:
	@$(PY) scripts/lint_dspy_testcases.py

.PHONY: reco-demo reco-on reco-off gcloud-init gcloud-auth-adc gcloud-enable-apis vertex-ping provider-vertex-cli

reco-demo:
	$(PY) scripts/reco_demo.py

reco-on:
	export MODEL_RECO_ENABLED=true

reco-off:
	export MODEL_RECO_ENABLED=false

gcloud-init:
	@gcloud init

gcloud-auth-adc:
	@gcloud auth application-default login

gcloud-enable-apis:
	@gcloud services enable aiplatform.googleapis.com

vertex-ping:
	@PROJECT_ID=$${PROJECT_ID:-$${GCP_PROJECT}} LOCATION=$${LOCATION:-$${VERTEX_LOCATION:-us-central1}} MODEL=$${MODEL:-$${VERTEX_MODEL:-gemini-2.5-flash}} \
	bash scripts/vertex_chat.sh "ping"

provider-vertex-cli:
	@python3 scripts/providers/vertex_cli.py < prompts/vertex_payload.json

# Phase 1: Graph RAG with LightRAG (F1-T6: Makefile targets)
.PHONY: rag-index rag-status rag-query rag-visualize

rag-index:
	@echo "==> Building/updating Knowledge Graph from pipeline artifacts"
	$(PY) -c "import asyncio; from graph_rag.ingestion import ingest_pipeline_artifacts; from graph_rag.engine import GraphRAGEngine; from scripts.llm import load_config; cfg = load_config(); engine = GraphRAGEngine(cfg.get('graph_rag', {})); asyncio.run(engine.initialize()); asyncio.run(ingest_pipeline_artifacts(engine)); asyncio.run(engine.finalize())"
	@echo "✓ Graph RAG Knowledge Graph indexed"

rag-status:
	@echo "==> Graph RAG Status"
	@ls -lah artifacts/graph_rag/ 2>/dev/null || echo "  (KG not yet created - run 'make rag-index' first)"

rag-query:
	@if [ -z "$$QUERY" ]; then echo "Usage: make rag-query QUERY=\"your question\" [MODE=mix|hybrid|local|global|naive] [ROLE=architect]"; exit 1; fi
	@MODE=$${MODE:-mix} ROLE=$${ROLE:-architect} $(PY) scripts/rag_query_cli.py --query "$$QUERY" --mode "$$MODE" --role "$$ROLE"

rag-visualize:
	@echo "==> Starting LightRAG WebUI at http://localhost:9621"
	@echo "    (Ctrl+C to stop)"
	@lightrag-server --working-dir ./artifacts/graph_rag --port 9621

.PHONY: test-fast test-rag-real test-no-integration test-integration test-integration-real test-with-integration test-all

test-fast:
	@echo "==> Running fast tests (excluding integration_real)"
	PYTHONPATH=. $(PY) -m pytest -m "not integration_real" -q

test-no-integration:
	@echo "==> Running unit-only profile (no integration)"
	PYTHONPATH=. $(PY) -m pytest -m "unit and not integration and not integration_real" -q

test-integration:
	@echo "==> Running integration profile (integration marker)"
	PYTHONPATH=. $(PY) -m pytest -m "integration and not integration_real" -q

test-integration-real:
	@echo "==> Running integration_real profile"
	PYTHONPATH=. $(PY) -m pytest -m integration_real -q

test-with-integration:
	@echo "==> Running unit + integration + integration_real profile"
	PYTHONPATH=. $(PY) -m pytest -m "unit or integration or integration_real" -q

test-all:
	@echo "==> Running full test suite (optional deps may be skipped)"
	PYTHONPATH=. $(PY) -m pytest -q

test-rag-real:
	@echo "==> Running real Graph RAG integration tests"
	PYTHONPATH=. $(PY) -m pytest -m integration_real -q

# ═════════════════════════════════════════════════════════════════
# SYNTHETIC DATA GENERATION (Distilabel Phase 2A)
# ═════════════════════════════════════════════════════════════════

.PHONY: synthetic-data synthetic-validate synthetic-stats synthetic-stats-all synthetic-all-local synthetic-all-gpu synthetic-clean test-distilabel-local test-distilabel-gpu test-distilabel-all

DRY_RUN_FLAG := $(if $(DRY_RUN),--dry-run,)

synthetic-data:
	@echo "==> Generating synthetic data for role: $(ROLE)"
	PYTHONPATH=. ./.venv/bin/python -m training.scripts.run_synthetic_pipeline \
		--role $(ROLE) \
		--mode $(or $(MODE),local) \
		--num-samples $(or $(NUM_SAMPLES),10) \
		--batch-size $(or $(BATCH_SIZE),5) \
		$(DRY_RUN_FLAG)

synthetic-validate:
	@echo "==> Validating synthetic dataset for role: $(ROLE)"
	PYTHONPATH=. ./.venv/bin/python -m training.scripts.validate_datasets \
		--role $(ROLE) \
		--output-dir $(or $(OUTPUT_DIR),training/datasets)

synthetic-stats:
	@echo "==> Stats for role: $(ROLE)"
	PYTHONPATH=. ./.venv/bin/python -c "from pathlib import Path; role='$(ROLE)'; p=Path('training/datasets')/role; files=list(p.glob('*.jsonl')); total=sum(sum(1 for _ in f.open('r', encoding='utf-8')) for f in files); print({'role': role, 'files': len(files), 'rows': total})"

synthetic-stats-all:
	@for role in ba product_owner architect dev qa; do \
		$(MAKE) --no-print-directory synthetic-stats ROLE=$$role; \
	done

synthetic-all-local:
	@for role in ba product_owner architect dev qa; do \
		$(MAKE) --no-print-directory synthetic-data ROLE=$$role MODE=local; \
	done

synthetic-all-gpu:
	@for role in ba product_owner architect dev qa; do \
		$(MAKE) --no-print-directory synthetic-data ROLE=$$role MODE=gpu; \
	done

synthetic-clean:
	@rm -rf training/datasets/* artifacts/training/checkpoints/*
	@echo "==> Synthetic artifacts cleaned"

test-distilabel-local:
	PYTHONPATH=. ./.venv/bin/pytest tests/test_distilabel*.py -m "not integration_gpu" -q

test-distilabel-gpu:
	PYTHONPATH=. ./.venv/bin/pytest tests/test_distilabel*.py -m "integration_gpu" -q

test-distilabel-all:
	PYTHONPATH=. ./.venv/bin/pytest tests/test_distilabel*.py -q

# Post-training targets
include post_training/Makefile.posttrain.mk
