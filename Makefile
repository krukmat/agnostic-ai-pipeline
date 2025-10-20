SHELL := /bin/bash
.DEFAULT_GOAL := help

PY    := ./.venv/bin/python

help:
	@echo "Targets:"
	@echo "  setup        -> venv + deps base"
	@echo "  ba           -> Business Analyst (genera requirements.yaml)"
	@echo "  plan         -> Arquitecto + normaliza historias"
	@echo "  dev          -> Developer (toma siguiente 'todo')"
	@echo "  qa           -> QA textual (+tests si QA_RUN_TESTS=1)"
	@echo "  loop         -> Orquestador Dev→QA (auto-promueve, LOOP_MODE=dev_only para solo Dev)"
	@echo "  loop-dev     -> Development loop (solo dev, no QA)"
	@echo "  iteration    -> BA→Architect→Dev→QA en cadena + snapshot bajo artifacts/iterations/"
	@echo "  fix-stories  -> Normaliza planning/stories.yaml"
	@echo "  show-config  -> Muestra config.yaml"
	@echo "  set-role     -> role=<ba|architect|dev|qa> provider=<ollama|openai> model=..."
	@echo "  set-quality  -> profile=<low|normal|high> [role=...]"
	@echo "  clean        -> Limpia artifacts/ (FLUSH=1 también borra planning/ y project/)"

setup:
	python3 -m venv .venv || true
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -r requirements.txt
	./.venv/bin/pip install pyyaml httpx openai >/dev/null

ba:
	@if [ -z "$$CONCEPT" ]; then echo 'Set CONCEPT="..."'; exit 1; fi
	CONCEPT="$$CONCEPT" $(PY) scripts/run_ba.py
	@echo "==> planning/requirements.yaml generado"

plan:
	@if [ -z "$$CONCEPT" ]; then \
		$(PY) -c 'import sys,yaml,pathlib; path=pathlib.Path("planning/requirements.yaml"); data=yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None; meta=data.get("meta") if isinstance(data, dict) else {}; concept=meta.get("original_request") if isinstance(meta, dict) else ""; sys.exit(0 if isinstance(concept,str) and concept.strip() else 1)' || { echo 'Set CONCEPT="..." or ensure planning/requirements.yaml contains meta.original_request'; exit 1; }; \
	fi
	CONCEPT="$$CONCEPT" \
	FORCE_ARCHITECT_TIER="$${FORCE_ARCHITECT_TIER:-}" \
	$(PY) scripts/run_architect.py
	$(PY) scripts/fix_stories.py
	@echo "==> planning/stories.yaml (primeras 60 líneas)"
	@sed -n '1,60p' planning/stories.yaml || true

dev:
	STORY="$$STORY" DEV_RETRIES="$${DEV_RETRIES:-3}" $(PY) scripts/run_dev.py

qa:
	QA_RUN_TESTS="$${QA_RUN_TESTS:-0}" $(PY) scripts/run_qa.py

clean:
	CLEAN_FLUSH="$${CLEAN_FLUSH:-$${FLUSH:-0}}" $(PY) scripts/run_cleanup.py

loop:
	LOOP_MODE="$${LOOP_MODE:-full}" MAX_LOOPS="$${MAX_LOOPS:-1}" ALLOW_NO_TESTS="$${ALLOW_NO_TESTS:-0}" ARCHITECT_INTERVENTION="$${ARCHITECT_INTERVENTION:-1}" $(PY) scripts/orchestrate.py

loop-dev:
	@echo "==> Ejecutando development loop (solo dev, no QA)..."
	@while $(PY) -c "import yaml,sys; stories=yaml.safe_load(open('planning/stories.yaml')); [sys.exit(1) for s in stories if isinstance(s,dict) and s.get('status')=='todo']" 2>/dev/null; do \
		echo "==> Ejecutando siguiente historia 'todo'..."; \
		$(MAKE) dev DEV_RETRIES=$${DEV_RETRIES:-4} || { echo "==> Dev falló, reintentando..."; sleep 2; }; \
		sleep 1; \
	done || echo "==> Todas las historias procesadas o archivo vacío"
	@echo "==> Development loop completado"

fix-stories:
	$(PY) scripts/fix_stories.py

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
