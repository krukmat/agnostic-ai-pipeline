# agnostic-ai-pipeline · Vertex AI (Gemini) provider via **gcloud**

**Branch:** `codex-cli-provider`  
**Goal:** Add a drop‑in provider so the pipeline can call **Google Vertex AI (Gemini)** using **gcloud** credentials. Support two paths:

1) **REST via gcloud token** (no new SDK dependencies).  
2) **Google GenAI SDK** (ADC‑based) as an optional alternative.

This document is written for an autonomous coding agent (Codex) to implement end‑to‑end.

---

## TL;DR (Deliverables)

- New provider(s):
  - `scripts/providers/vertex_cli.py` (primary; REST via `gcloud auth print-access-token`).
  - `scripts/providers/vertex_sdk.py` (optional; GenAI SDK via ADC).
- New CLI helper (optional): `scripts/vertex_chat.sh` for quick smoke tests.
- Config additions: new `providers.vertex_cli` and `providers.vertex_sdk` blocks in `config.yaml`.
- Makefile targets: `gcloud-init`, `gcloud-auth-adc`, `gcloud-enable-apis`, `vertex-ping`, `provider-vertex-cli`.
- Provider registry wiring so `--provider vertex_cli` / `--provider vertex_sdk` works anywhere the pipeline picks a model.
- Minimal tests: a smoke test and a dry‑run.

---

## Repository paths to touch

```
.
├─ scripts/
│  ├─ providers/
│  │  ├─ __init__.py            # (edit) register new providers
│  │  ├─ vertex_cli.py          # (new) REST provider using gcloud token
│  │  └─ vertex_sdk.py          # (new, optional) SDK provider using ADC
│  ├─ vertex_chat.sh            # (new, optional) curl-based smoke test
│  └─ set_role.py               # (edit if needed) ensure it passes provider/model
├─ Makefile                     # (edit) add gcloud/vertex helpers
├─ config.yaml                  # (edit) add provider configs
├─ tests/
│  └─ smoke/test_vertex_provider.py   # (new) smoke tests
└─ README.md (or docs/)         # (edit) usage notes
```

> If filenames differ in this branch, adapt paths but keep the same responsibilities.

---

## Prerequisites

Local (developer machine):

```bash
# Install & initialize gcloud (per OS). Then:
gcloud init
# Choose or set the project
gcloud config set project <PROJECT_ID>
# Pick a region for Vertex AI (e.g., us-central1 or europe-west1)
gcloud config set ai/location <LOCATION>

# Optional: Application Default Credentials (for SDK path)
gcloud auth application-default login

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com
```

CI (GitHub Actions):
- Use `google-github-actions/setup-gcloud@v2`.
- Authenticate a Service Account (SA) via key or Workload Identity Federation.
- Minimum roles for SA: `roles/aiplatform.user`. Add storage roles if you later read/write GCS.

Environment variables supported by the provider(s):

- `GCP_PROJECT` *(required unless passed via config)*
- `VERTEX_LOCATION` (default: `us-central1`)
- `VERTEX_MODEL` (default: `gemini-2.5-flash`)
- `VERTEX_TEMPERATURE` (default: `0.2`)
- `VERTEX_MAX_OUTPUT_TOKENS` (default: `2048`)
- `USE_OPENAI_COMPAT` (`0|1`) — if `1`, try OpenAI‑compatible endpoint; else use standard `generateContent`.

---

## config.yaml additions

Append (do **not** remove existing providers):

```yaml
providers:
  vertex_cli:
    kind: "chat"
    project_id: "${GCP_PROJECT}"
    location: "${VERTEX_LOCATION:-us-central1}"
    model: "${VERTEX_MODEL:-gemini-2.5-flash}"
    temperature: ${VERTEX_TEMPERATURE:-0.2}
    max_output_tokens: ${VERTEX_MAX_OUTPUT_TOKENS:-2048}

  vertex_sdk:
    kind: "chat"
    project_id: "${GCP_PROJECT}"
    location: "${VERTEX_LOCATION:-us-central1}"
    model: "${VERTEX_MODEL:-gemini-2.5-flash}"
    temperature: ${VERTEX_TEMPERATURE:-0.2}
    max_output_tokens: ${VERTEX_MAX_OUTPUT_TOKENS:-2048}
```

> If your config loader doesn’t support env interpolation, hardcode values and rely on env only as fallback inside provider code.

---

## Provider interface (contract)

**Input** (what the pipeline currently sends to providers; adapt if different):

```json
{
  "messages": [
    {"role":"system","content":[{"type":"text","text":"You are ..."}]},
    {"role":"user","content":[{"type":"text","text":"<prompt>"}]}
  ],
  "model": "<model-id>",
  "project_id": "<gcp-project>",
  "location": "<vertex-region>",
  "temperature": 0.2,
  "max_output_tokens": 2048
}
```

**Output** (normalize to the pipeline’s expected plain string):

```text
<assistant_text_response>
```

> If your runner expects a JSON envelope, keep `{ "text": "..." }`. The code below returns a string by default; adapt as needed.

---

## `scripts/providers/vertex_cli.py` (new)

A lightweight shim that:
- gets a bearer via `gcloud auth print-access-token`,
- calls **Vertex AI** using either:
  - **Standard Vertex generateContent** endpoint, or
  - **OpenAI‑compatible** endpoint when `USE_OPENAI_COMPAT=1`.
- maps your pipeline’s `messages` → proper Vertex payload, returns plain text.

```python
# scripts/providers/vertex_cli.py
import json, os, subprocess, sys
from typing import List, Dict

import httpx

# ------------------ utils ------------------

def _env(name: str, default: str = None):
    v = os.environ.get(name, default)
    if v is None:
        raise RuntimeError(f"Missing required env: {name}")
    return v


def _gcloud_token() -> str:
    out = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    if not out:
        raise RuntimeError("Empty access token from gcloud")
    return out


# Convert OpenAI-style messages -> Vertex contents
# Input messages example: [{role: 'user'|'system'|'assistant', content: [{type:'text', text:'...'}]}]

def _to_vertex_contents(messages: List[Dict]):
    contents = []
    for m in messages:
        role = m.get("role", "user")
        parts = m.get("content", [])
        # Vertex expects {role: 'user'|'model', parts:[{text:...}]}
        vrole = "user" if role in ("user", "system") else "model"
        vparts = []
        for p in parts:
            if p.get("type") == "text":
                vparts.append({"text": p.get("text", "")})
        if vparts:
            contents.append({"role": vrole, "parts": vparts})
    return contents


def _call_generate_content(project_id: str, location: str, model: str, contents: List[Dict], temperature: float, max_tokens: int, timeout: float = 120.0) -> str:
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/"
        f"locations/{location}/publishers/google/models/{model}:generateContent"
    )
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    headers = {
        "Authorization": f"Bearer {_gcloud_token()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        # Response shape: {candidates:[{content:{parts:[{text: ...}]}}]}
        cands = data.get("candidates", [])
        if not cands:
            return ""
        parts = cands[0].get("content", {}).get("parts", [])
        for p in parts:
            if "text" in p:
                return p["text"]
        return ""


def _call_openai_compat(project_id: str, location: str, model: str, messages: List[Dict], temperature: float, max_tokens: int, timeout: float = 120.0) -> str:
    # OpenAI-compatible chat completions endpoint (if available in your region/account)
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1beta/projects/{project_id}/"
        f"locations/{location}/endpoints/openapi/chat/completions"
    )
    # Convert our internal structure directly; many setups accept the same message shape.
    payload = {
        "model": f"google/{model}" if not model.startswith("google/") else model,
        "messages": messages,
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {_gcloud_token()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        # Response shape: {choices:[{message:{content:[{type:'text', text:'...'}]}}]}
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {})
        content = message.get("content") or []
        # Concatenate text parts if present
        out = []
        for p in content:
            if p.get("type") == "text" and p.get("text"):
                out.append(p["text"])
        return "\n".join(out).strip()


def chat(messages: List[Dict], model: str = None, project_id: str = None, location: str = None, temperature: float = 0.2, max_output_tokens: int = 2048, **_):
    project_id = project_id or os.environ.get("GCP_PROJECT") or _env("GCP_PROJECT")
    location = location or os.environ.get("VERTEX_LOCATION", "us-central1")
    model = model or os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")

    use_openai = os.environ.get("USE_OPENAI_COMPAT", "0") == "1"

    if use_openai:
        return _call_openai_compat(project_id, location, model, messages, float(temperature), int(max_output_tokens))

    contents = _to_vertex_contents(messages)
    return _call_generate_content(project_id, location, model, contents, float(temperature), int(max_output_tokens))


if __name__ == "__main__":
    req = json.load(sys.stdin)
    text = chat(**req)
    # Print plain text so the pipeline can capture it easily
    sys.stdout.write(text)
```

---

## `scripts/vertex_chat.sh` (optional, new)

```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${PROJECT_ID:-${GCP_PROJECT:?set GCP_PROJECT or PROJECT_ID}}"
LOCATION="${LOCATION:-${VERTEX_LOCATION:-us-central1}}"
MODEL="${MODEL:-${VERTEX_MODEL:-gemini-2.5-flash}}"
PROMPT="${1:-Hello from CLI}"

# Standard Vertex generateContent
read -r -d '' BODY <<JSON || true
{
  "contents": [{"role":"user","parts":[{"text":"$PROMPT"}]}],
  "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256}
}
JSON

curl -sS -X POST \
 -H "Authorization: Bearer $(gcloud auth print-access-token)" \
 -H "Content-Type: application/json" \
 "https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL}:generateContent" \
 -d "$BODY"
```

Make executable: `chmod +x scripts/vertex_chat.sh`.

---

## `scripts/providers/vertex_sdk.py` (optional, new)

```python
# scripts/providers/vertex_sdk.py
import os, json, sys
from google import genai
from google.genai.types import HttpOptions


def chat(messages, model=None, project_id=None, location=None, temperature=0.2, max_output_tokens=2048, **_):
    client = genai.Client(
        http_options=HttpOptions(api_version="v1"),
        vertexai=True,
        project=project_id or os.environ.get("GCP_PROJECT"),
        location=location or os.environ.get("VERTEX_LOCATION", "us-central1"),
    )
    # Reuse the messages structure directly; SDK accepts both strings and parts
    resp = client.models.generate_content(
        model=model or os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
        contents=messages,
        config={
            "temperature": float(temperature),
            "max_output_tokens": int(max_output_tokens),
        },
    )
    # Normalize
    sys.stdout.write(resp.text or "")


if __name__ == "__main__":
    req = json.load(sys.stdin)
    chat(**req)
```

> Requires `pip install google-genai httpx` (httpx only if you keep CLI path too). For ultra‑lean installs, you can make SDK optional behind an extras flag.

---

## Provider registry wiring

Wherever providers are mapped (example shown — adjust to your project):

```python
# scripts/providers/__init__.py (example)
from . import vertex_cli as _vertex_cli
try:
    from . import vertex_sdk as _vertex_sdk
except Exception:
    _vertex_sdk = None

PROVIDER_REGISTRY = {
    # existing providers ...
    "vertex_cli": _vertex_cli.chat,
}
if _vertex_sdk is not None:
    PROVIDER_REGISTRY["vertex_sdk"] = _vertex_sdk.chat
```

If your pipeline uses a factory function, append the same mapping there.

---

## Makefile changes

Append:

```make
# ---- gcloud / vertex helpers ----
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
	@python3 scripts/providers/vertex_cli.py < prompts/payload.json
```

> If `prompts/payload.json` doesn’t exist, create a minimal one aligned to your provider contract.

---

## GitHub Actions (CI) sketch

```yaml
# .github/workflows/vertex-smoke.yml
name: vertex-smoke
on: [workflow_dispatch]

jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install httpx google-genai

      - uses: google-github-actions/setup-gcloud@v2
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}

      - name: Auth SA
        run: |
          echo '${{ secrets.GCP_SA_KEY_JSON }}' > /tmp/key.json
          gcloud auth activate-service-account --key-file=/tmp/key.json
          gcloud config set project ${{ secrets.GCP_PROJECT_ID }}

      - name: Enable APIs (idempotent)
        run: gcloud services enable aiplatform.googleapis.com

      - name: Smoke test (REST)
        env:
          GCP_PROJECT: ${{ secrets.GCP_PROJECT_ID }}
          VERTEX_LOCATION: us-central1
          VERTEX_MODEL: gemini-2.5-flash
        run: |
          bash scripts/vertex_chat.sh "CI hello"
```

---

## Minimal tests

`tests/smoke/test_vertex_provider.py`

```python
import json, os, subprocess, sys

def test_vertex_cli_smoke():
    if not os.environ.get("GCP_PROJECT"):
        return  # skip if env not set
    payload = {
        "messages": [
            {"role":"user","content":[{"type":"text","text":"Say OK"}]}
        ]
    }
    p = subprocess.run(
        [sys.executable, "scripts/providers/vertex_cli.py"],
        input=json.dumps(payload), text=True, capture_output=True, check=True
    )
    assert isinstance(p.stdout, str)
    assert p.stdout.strip() != ""
```

> Mark as smoke; don’t assert exact wording.

---

## Usage examples

Local (REST via CLI):

```bash
export GCP_PROJECT=<PROJECT_ID>
export VERTEX_LOCATION=us-central1
export VERTEX_MODEL=gemini-2.5-flash

# One-shot prompt
bash scripts/vertex_chat.sh "Summarize this pipeline in one sentence."

# Through the pipeline’s provider call
python3 scripts/providers/vertex_cli.py <<'JSON'
{"messages":[{"role":"user","content":[{"type":"text","text":"Hello!"}]}]}
JSON
```

Pipeline role selection (example):

```bash
make set-role role=ba provider=vertex_cli model="gemini-2.5-flash"
make plan
```

---

## Troubleshooting

- **401 / unauthenticated**: ensure `gcloud auth print-access-token` returns a token and your account/SA has `roles/aiplatform.user`. Check project/region.
- **404 on OpenAI‑compat endpoint**: set `USE_OPENAI_COMPAT=0` (default) and use the standard `generateContent` endpoint.
- **Quota errors**: verify Vertex AI quota in the selected region; switch to `*-flash` models for cheaper/faster tests.
- **Empty output**: log the raw JSON to inspect `candidates[0].content.parts[].text`.

---

## Security notes

- Prefer **Workload Identity** in CI over raw keys.
- Do not commit SA keys. Use GitHub Secrets.
- Keep project/region consistent to avoid data residency surprises.

---

## Definition of Done (DoD)

- [ ] `vertex_cli.py` and (optional) `vertex_sdk.py` created and pass `ruff/flake8` (if linting present).
- [ ] `config.yaml` includes `vertex_cli`/`vertex_sdk` entries.
- [ ] Provider registry maps `vertex_cli` (and `vertex_sdk` if present).
- [ ] `scripts/vertex_chat.sh` works locally and in CI.
- [ ] `make vertex-ping` returns a non‑empty response.
- [ ] Smoke test passes when `GCP_PROJECT` is set with valid auth.
- [ ] README/docs updated with setup instructions.

---

## Work plan for Codex (step‑by‑step)

1. Create `scripts/providers/vertex_cli.py` with the exact implementation above.
2. (Optional) Create `scripts/providers/vertex_sdk.py` with the exact implementation above.
3. Add `scripts/vertex_chat.sh` and `chmod +x`.
4. Update `scripts/providers/__init__.py` to register `vertex_cli` and conditionally `vertex_sdk`.
5. Append Makefile targets provided above.
6. Update `config.yaml` with the two provider blocks.
7. Add `tests/smoke/test_vertex_provider.py` and wire into the existing test runner (pytest or equivalent).
8. Add `.github/workflows/vertex-smoke.yml` workflow. Store `GCP_PROJECT_ID` and `GCP_SA_KEY_JSON` in repo secrets.
9. Run `make vertex-ping` locally and ensure a non‑empty response.
10. Open a PR titled: **feat(provider): Vertex AI (Gemini) via gcloud token (+ optional SDK)** with a summary of changes and instructions to enable on environments.

---

## Streamlined Execution Plan

1. **Bootstrap once**
   - Confirm `gcloud` is authenticated for the target project (`gcloud config list`); run `gcloud services enable aiplatform.googleapis.com` only if it is not already enabled.
   - Optional SDK path: execute `gcloud auth application-default login` only when `vertex_sdk.py` will be exercised.

2. **Implement core provider path**
   - Add `scripts/providers/vertex_cli.py` (REST via `gcloud auth print-access-token`) and register it in `scripts/providers/__init__.py`.
   - Extend `config.yaml` with the `vertex_cli` block and ensure the existing client can resolve it (no additional Make targets required at this stage).

3. **Add minimal tooling**
   - Create `scripts/vertex_chat.sh` for manual smoke tests (chmod +x).
   - Introduce `tests/smoke/test_vertex_provider.py` that shells out to `vertex_cli.py`; skip when `GCP_PROJECT` is unset.

4. **Optional enhancements (only if required)**
   - Implement `scripts/providers/vertex_sdk.py` and conditionally register `vertex_sdk`.
   - Add Make targets (`vertex-ping`, `gcloud-auth-adc`, etc.) and the CI workflow when automated validation is desired.

5. **Validate & document**
   - Run the smoke script (`bash scripts/vertex_chat.sh "hello"`) and the pytest smoke test with authenticated gcloud.
   - Update README/docs with a brief setup snippet and usage example.
   - Commit on `codex-cli-provider` and prepare the PR **feat(provider): Vertex AI (Gemini) via gcloud token (+ optional SDK)** summarizing both core and optional pieces.

---

## Post-Implementation Checklist

1. Authenticate locally with `gcloud init` (and `gcloud auth application-default login` if the SDK provider will be used).
2. Export `GCP_PROJECT` plus any overrides (`VERTEX_LOCATION`, `VERTEX_MODEL`, `VERTEX_TEMPERATURE`, etc.).
3. Run `make vertex-ping` or `bash scripts/vertex_chat.sh "Hello"` to confirm the REST provider.
4. Execute `./.venv/bin/pytest -q tests/smoke/test_vertex_provider.py` with the environment configured to validate the smoke test.
5. Populate CI secrets (`GCP_PROJECT_ID`, `GCP_SA_KEY_JSON`) and trigger the `vertex-smoke` workflow to confirm remote execution.

---

## Single prompt for Codex (copy‑paste)

```
You are an autonomous senior engineer working on the repository `agnostic-ai-pipeline` (branch `codex-cli-provider`). Implement a new provider for Google Vertex AI (Gemini) using gcloud credentials and deliver an optional SDK-based variant.

SCOPE OF WORK
1) Create files and edits exactly as specified in the document “Vertex AI (Gemini) provider via gcloud — Implementation Guide for Codex”. If a path is missing, adapt to current repo structure but keep the same responsibilities.
2) Primary path: REST provider using `gcloud auth print-access-token` and the standard Vertex `generateContent` endpoint. Secondary path: optional SDK provider using `google-genai` (ADC). Both must normalize output to a plain text string.
3) Update the provider registry so the pipeline can be invoked with `--provider vertex_cli` or `--provider vertex_sdk`.
4) Add Makefile targets, config.yaml provider blocks, a curl smoke script, a pytest smoke test, and a simple GitHub Actions workflow.
5) Ensure local and CI smoke tests pass when given correct secrets.

ACCEPTANCE CRITERIA
- `scripts/providers/vertex_cli.py` returns a non-empty text response for a simple user prompt when `GCP_PROJECT` and gcloud auth are configured.
- `make vertex-ping` prints a JSON response containing generated text.
- `tests/smoke/test_vertex_provider.py` passes locally (when env is set) and is skipped when env not set.
- Registry mapping allows pipeline calls with `provider=vertex_cli`/`vertex_sdk`.
- No breaking changes to existing providers.

EXECUTION NOTES
- Keep code minimal; handle only text prompts.
- If OpenAI-compatible endpoint is not available, default to the standard `generateContent` path.
- Avoid committing secrets; use env variables and GitHub Secrets as indicated.
```
