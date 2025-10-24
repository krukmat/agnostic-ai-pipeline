# Codex Task: Add a Local, Content-Based Model Recommender (Python, OSS) to `agnostic-ai-pipeline`

You are Codex. Implement a **local, open‑source, Python** model recommender that picks the best model **per prompt** before a generation call. Use **RoRF (Routing on Random Forests)** with a **pretrained Jina‑based router** so the entire pipeline can run **offline** (no external API keys required). Keep the current CLI (`make ba`, `make plan`, etc.) working exactly as is.

---

## Why RoRF?
- **Data‑driven recommendations** (not just rules): RoRF uses a learned classifier over prompt embeddings to decide between two configured models (e.g., **strong** vs **cheap**).
- **Local**: Use the **Jina embeddings** versions of RoRF’s pretrained routers to avoid external APIs.
- **Simple**: Provides a `Controller` with `.route(prompt)` returning the chosen model label; we map that string to the actual model ID(s) the pipeline uses (local Ollama or cloud).

> Alternatives considered (not selected for now): `semantic-router` (great but rule-based), `RouteLLM` (popular but default routers depend on OpenAI embeddings). This task focuses on *automatic* recommendation with minimal external dependencies.

---

## Deliverables (Definition of Done)
1. A **Python module** `src/recommend/model_recommender.py` exposing:
   - `recommend_model(prompt: str, role: str | None = None) -> str`
   - returns a **model identifier** string that the pipeline already accepts (e.g., an **Ollama** model name or your gateway alias).
2. A **YAML config** `config/model_recommender.yaml` that maps **roles** to a `(strong, weak)` pair and the **RoRF router id** to use.
3. Zero regression: existing commands (`make ba`, `make plan`, `make dev`, `make qa`) continue to work, now calling the recommender to select a model.
4. A **smoke script** `scripts/reco_demo.py` printing recommended models for example prompts across roles.
5. **Unit tests** `tests/test_model_recommender.py` that assert the function returns a valid model from the configured set.
6. **README block** in `README.md` explaining how to enable/disable the recommender and how to tune the `threshold` for cost/quality trade‑offs.

---

## Constraints & Non‑Goals
- **No breaking changes** to CLI UX.
- **Local‑first**: default configuration must work without any external API keys or internet.
- Do **not** refactor unrelated pipeline parts.
- Keep the recommender **optional** via an env flag (`MODEL_RECO_ENABLED=true|false`).

---

## Step‑By‑Step Tasks

### 1) Add dependency
Update `pyproject.toml` or `requirements.txt`:
```bash
pip install rorf pyyaml
```
If the project uses a lockfile, update it accordingly.

### 2) Create config `config/model_recommender.yaml`
Add a new file with this content (safe defaults; replace model ids to match your local setup):
```yaml
# RoRF-based per-prompt recommender
enabled: true
default_threshold: 0.30   # higher -> more traffic to "strong"
routes:
  # Each role can specify its own strong/weak pair and router id
  ba:
    router_id: notdiamond/rorf-jina-llama31405b-gpt4o       # any Jina-based pretrained router is fine
    strong: ollama/qwen2.5:32b-instruct                     # <-- replace with your local "strong" model id (or gateway alias)
    weak:   ollama/qwen2.5:7b-instruct                      # <-- replace with your local "cheap/fast" model id
    threshold: 0.25
  plan:
    router_id: notdiamond/rorf-jina-llama31405b-mistrallarge
    strong: ollama/llama3.1:70b-instruct
    weak:   ollama/llama3.1:8b-instruct
  dev:
    router_id: notdiamond/rorf-jina-llama31405b-llama3170b
    strong: ollama/qwen2.5-coder:32b
    weak:   ollama/qwen2.5-coder:7b
    threshold: 0.35
  qa:
    router_id: notdiamond/rorf-jina-gpt4o-gpt4omini
    strong: ollama/llama3.1:70b-instruct
    weak:   ollama/llama3.1:8b-instruct
```

### 3) Implement `src/recommend/model_recommender.py`
Create the module with:
```python
# src/recommend/model_recommender.py
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import yaml
from rorf.controller import Controller  # RoRF

CONFIG_PATH = os.getenv("MODEL_RECO_CONFIG", "config/model_recommender.yaml")
RECO_ENABLED = os.getenv("MODEL_RECO_ENABLED", "true").lower() == "true"


@dataclass(frozen=True)
class RoleRoute:
    router_id: str
    strong: str
    weak: str
    threshold: float


@lru_cache(maxsize=1)
def _load_cfg() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=16)
def _build_controller(router_id: str, strong: str, weak: str, threshold: float) -> Controller:
    # RoRF Controller decides between model_a (strong) and model_b (weak)
    return Controller(router=router_id, model_a=strong, model_b=weak, threshold=threshold)


def _role_route(role: Optional[str]) -> RoleRoute:
    cfg = _load_cfg()
    routes = cfg.get("routes", {})
    default_threshold = float(cfg.get("default_threshold", 0.30))

    role_cfg = routes.get((role or "default"))
    if not role_cfg:
        # Fallback: use the first route defined in config
        if not routes:
            raise RuntimeError("No routes configured in model_recommender.yaml")
        key, role_cfg = next(iter(routes.items()))

    router_id = role_cfg["router_id"]
    strong = role_cfg["strong"]
    weak = role_cfg["weak"]
    threshold = float(role_cfg.get("threshold", default_threshold))
    return RoleRoute(router_id, strong, weak, threshold)


def recommend_model(prompt: str, role: Optional[str] = None) -> str:
    """Return a model id for this prompt, optionally conditioned on role."""
    if not RECO_ENABLED:
        # If disabled, prefer configured "weak" (cheap) model to be safe.
        rr = _role_route(role)
        return rr.weak

    rr = _role_route(role)
    controller = _build_controller(rr.router_id, rr.strong, rr.weak, rr.threshold)
    # RoRF returns either rr.strong or rr.weak depending on learned decision
    return controller.route(prompt)
```

### 4) Wire into the pipeline
Locate the central LLM call path (e.g., `src/llm/client.py` or where messages are sent). Before you pass `model=...` to the client, call:
```python
from recommend.model_recommender import recommend_model

# given role and prompt (or constructed user content)
chosen = recommend_model(prompt_text, role=role_name)  # returns model string
# pass it through to your existing client:
client.chat.completions.create(model=chosen, messages=messages, **kwargs)
```

If the project currently derives `model` from config per role, preserve that as **fallback** when `MODEL_RECO_ENABLED=false`.

### 5) Add a smoke script `scripts/reco_demo.py`
```python
#!/usr/bin/env python3
import sys
from recommend.model_recommender import recommend_model

EXAMPLES = [
    ("ba",   "Summarize this long stakeholder requirement into 5 bullets."),
    ("plan", "Break down this epic into sprints and user stories."),
    ("dev",  "Write a Python function to parse a CSV of invoices and compute VAT."),
    ("qa",   "Generate 5 high-value test cases for edge cases on date parsing."),
]

for role, prompt in EXAMPLES:
    m = recommend_model(prompt, role=role)
    print(f"[{role}] -> {m}")
```

### 6) Add unit tests `tests/test_model_recommender.py`
```python
import os
from recommend.model_recommender import recommend_model, _load_cfg

def test_recommender_returns_configured_model_ids():
    cfg = _load_cfg()
    for role, route in cfg["routes"].items():
        strong = route["strong"]; weak = route["weak"]
        out = recommend_model("hello world", role)
        assert out in {strong, weak}, f"Unexpected model '{out}' for role={role}"

def test_disable_flag_uses_weak_model(monkeypatch):
    monkeypatch.setenv("MODEL_RECO_ENABLED", "false")
    cfg = _load_cfg()
    role, route = next(iter(cfg["routes"].items()))
    assert recommend_model("anything", role) == route["weak"]
```

### 7) README documentation
Append to `README.md`:
```md
## Model Recommender (Local, RoRF)
- Enable: `export MODEL_RECO_ENABLED=true`
- Config: `config/model_recommender.yaml`
- Tuning: increase `threshold` to route more traffic to **strong** models.
- Disable: `export MODEL_RECO_ENABLED=false` (falls back to per-role configured model).
```

### 8) Makefile helpers (optional)
Add targets:
```make
.PHONY: reco-demo reco-on reco-off
reco-demo:
	python scripts/reco_demo.py

reco-on:
	export MODEL_RECO_ENABLED=true

reco-off:
	export MODEL_RECO_ENABLED=false
```

---

## Notes & Tuning
- **Threshold**: Controls the fraction that goes to **strong**. Start at `0.30`, adjust per role after observing costs/quality.
- **Calibration (optional)**: RoRF exposes a CLI to calibrate the threshold with your evaluation set if you have one. Not required for initial rollout.
- **Model IDs**: The recommender returns **exact strings** the pipeline should pass to your LLM client. If you use a local gateway (e.g., LiteLLM) or Ollama directly, set those identifiers in the YAML.
- **Safety**: Keep `MODEL_RECO_ENABLED=false` as an emergency off switch if any regression appears.

---

## Acceptance Criteria (Automated + Manual)
- `pytest -q` green for the new tests.
- `python scripts/reco_demo.py` prints a valid model for each role without internet.
- `make ba/plan/dev/qa` use `recommend_model()` when enabled and behave identically when disabled.
- No extra network keys required for the default (Jina-based) routers.

---

## Implementation & Adaptation Plan

1. **Baseline analysis** – Inventory current role → model mappings in `config.yaml` and collect representative prompts from `artifacts/<role>/last_raw.txt` to calibrate the recommender against real traffic.
2. **Dependency provisioning** – Add `rorf` and `pyyaml` to `requirements.txt`, then rebuild `.venv` with `make setup` to ensure offline availability inside the pipeline runtime.
3. **Configuration scaffolding** – Create `config/model_recommender.yaml` with role-specific routes that mirror existing provider choices; use gateway aliases (`local-dev-code`, etc.) when the LiteLLM proxy is present, otherwise point directly to Ollama model ids.
4. **Environment toggles** – Define `MODEL_RECO_ENABLED` (default `true`) and optional `MODEL_RECO_CONFIG`; add a guard in the orchestrator startup scripts so rollback is a one-line env change.
5. **Controller module** – Implement `recommend/model_recommender.py` using RoRF controllers with LRU caches, mapping `role` to routes and falling back to weak models when disabled or misconfigured.
6. **Pipeline integration** – Update the shared LLM client (`scripts/llm.py` entry point) so each role call obtains the prompt text, invokes `recommend_model`, and only overrides the existing per-role model when the flag is enabled.
7. **Smoke tooling** – Add `scripts/reco_demo.py` plus an optional `make reco-demo` target to validate routing decisions manually across roles before running full iterations.
8. **Test coverage** – Introduce `tests/test_model_recommender.py` with fixtures that assert strong/weak outputs per role, disabled-mode behavior, and config override handling.
9. **Documentation updates** – Expand `README.md` with an opt-in guide covering enable/disable steps, threshold tuning, and how the recommender coexists with existing provider configurations.
10. **Rollout validation** – Execute `make iteration` with `MODEL_RECO_ENABLED=true`, inspect LiteLLM/RoRF logs for routing decisions, then rerun with the flag off to confirm backward compatibility; capture results in `artifacts/iterations/` for audit.

## Commit Plan
- Create feature branch `feature/model-recommender-rorf` from the latest mainline.
- PR 1: deps + config + module + tests + smoke script.
- PR 2: wire-in call sites (minimal diff; behind `MODEL_RECO_ENABLED`).
- PR 3 (optional): threshold calibration tooling & metrics logging.
