SHELL := /bin/bash
.DEFAULT_GOAL := help

PY    := ./.venv/bin/python

help:
	@echo "Targets:"
	@echo "  setup        -> venv + deps base"
	@echo "  plan         -> Arquitecto + normaliza historias"
	@echo "  dev          -> Developer (toma siguiente 'todo')"
	@echo "  qa           -> QA textual (+tests si QA_RUN_TESTS=1)"
	@echo "  loop         -> Orquestador Dev→QA (auto-promueve)"
	@echo "  fix-stories  -> Normaliza planning/stories.yaml"
	@echo "  show-config  -> Muestra config.yaml"
	@echo "  set-role     -> role=<architect|dev|qa> provider=<ollama|openai> model=..."
	@echo "  set-quality  -> profile=<low|normal|high> [role=...]"

setup:
	python3 -m venv .venv || true
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -r requirements.txt
	./.venv/bin/pip install pyyaml httpx openai >/dev/null

plan:
	@if [ -z "$$CONCEPT" ]; then echo 'Set CONCEPT="..."'; exit 1; fi
	CONCEPT="$$CONCEPT" $(PY) scripts/run_architect.py
	$(PY) scripts/fix_stories.py
	@echo "==> planning/stories.yaml (primeras 60 líneas)"
	@sed -n '1,60p' planning/stories.yaml || true

dev:
	STORY="$$STORY" DEV_RETRIES="$${DEV_RETRIES:-3}" $(PY) scripts/run_dev.py

qa:
	QA_RUN_TESTS="$${QA_RUN_TESTS:-0}" $(PY) scripts/run_qa.py

loop:
	MAX_LOOPS="$${MAX_LOOPS:-1}" ALLOW_NO_TESTS="$${ALLOW_NO_TESTS:-0}" $(PY) scripts/orchestrate.py

fix-stories:
	$(PY) scripts/fix_stories.py

show-config:
	$(PY) -c "import yaml,sys;print(yaml.safe_load(open('config.yaml').read()))"

set-role:
	$(PY) scripts/set_role.py --role $(role) --provider $(provider) --model $(model)

set-quality:
	$(PY) scripts/set_quality.py --profile $(profile) $(if $(role),--role $(role),)
