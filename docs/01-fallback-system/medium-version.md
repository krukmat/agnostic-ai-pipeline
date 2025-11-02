# How My AI Pipeline Automatically Recovered from 8 Model Failures

*Inside the scoring, budgeting, and metadata that keep the factory running when models misbehave.*

Day 4 of the two-week experiment the Vertex AI endpoint started spitting 502s right in the middle of `make loop`. Instead of paging me, the pipeline calmly wrote a note in the story metadata, scored a backup, and relaunched the developer role with Codex. Codex timed out. The system tried again, this time with a local Qwen 32B model, and the story shipped. That was the moment I stopped worrying about vendor roulette.

Across 47 iterations the pipeline hit eight real failures—timeouts, malformed JSON, rate limits. Every one of them recovered automatically because the orchestrator keeps a diary of what went wrong, understands which models are good at which tasks, and never exceeds the recovery budget.

**Fast recap**

- Each failure appends a `model_history` entry, a human-readable reason, and a timestamp directly onto the story.
- Backup models earn points for matching the failure type, staying under budget, and running locally when possible.
- The developer agent can swap providers without hand-editing configs because `model_override` carries the full provider hint into `run_dev.py`.

---

## When the Primary Model Stumbles

The recovery routine kicks in the moment `execute_role("developer")` returns anything other than `ok`. First the orchestrator logs the miss inside the story itself—`recovery_attempts`, `last_failure_reason`, and a fresh record in `metadata.model_history`. Only then does it decide whether to try again.

![Flowchart showing how the orchestrator records the failure, updates model history, decides if fallback is allowed, and writes model_override](https://raw.githubusercontent.com/krukmat/agnostic-ai-pipeline/main/docs/01-fallback-system/diagram1-fallback-signals.png)

Here is the heart of `scripts/orchestrate.py` (`_process_story`), slightly trimmed for readability:

```python
story["metadata"]["recovery_attempts"] = story["metadata"].get("recovery_attempts", 0) + 1
story["metadata"]["last_failure_reason"] = "blocked_dev"
story["metadata"]["last_dev_error"] = error_details
story["metadata"]["model_history"].append({
    "provider": model_info.get("provider"),
    "model": model_info.get("model"),
    "timestamp": model_info.get("timestamp"),
    "attempt": len(story["metadata"]["model_history"]) + 1,
    "status": dev_status,
})
```

> **Safety brake:** before scoring backups the orchestrator checks `max_recovery_attempts`. If we already spent our two tries, the story flips to `blocked_recovery_budget` and the loop stops. No infinite retries, no surprise bills.

---

## Scoring Specialists Instead of Blind Retries

Favorites are declared in `config.yaml`. Each backup model lists a `reason`, a `cost_tier`, and one or more `specialties` (for example `structured_output`, `code_generation`, `local_execution`). When a failure arrives, the orchestrator compares the error to those specialties and builds a score. The highest score wins the next attempt.

```python
for backup in backup_models:
    score = 0
    specialties = backup.get("specialties", [])
    if requires_structure and "structured_output" in specialties:
        score += 10
    if not allow_cost_increase:
        score += {"free": 5, "medium": 3}.get(cost_tier, 0)
    if prefer_local and cost_tier == "free":
        score += 3
```

![Diagram illustrating the scoring flow for fallback models](https://raw.githubusercontent.com/krukmat/agnostic-ai-pipeline/main/docs/01-fallback-system/diagram2-scoring-matrix.png)

I deliberately keep the scoring simple. Structured-output specialists get the nod when the developer agent fails to emit a FILES block. Local Qwen models receive a gentle bias so the system prefers free retries over expensive cloud calls. And if no untried candidate survives the filters, `model_override` is cleared and the next loop sticks with the primary configuration.

---

## Guardrails for Token Spend

The fallback engine only works if it respects the budget. Three settings keep it honest:

1. `allow_cost_increase: false` refuses to jump from Gemini straight to a pricier model during recovery.
2. `prefer_local: true` nudges the score toward free Ollama models when quality allows.
3. `max_recovery_attempts: 2` caps the loop so QA can step in before costs or latency spiral.

Those knobs meant the eight fallbacks that happened last month added **$0** to the bill. When Codex hesitated, the system immediately pivoted to a local Qwen run without touching the cloud wallet.

---

## Case File: Story S6 (PATCH /api/tasks)

Story S6 is my favorite failure report. Gemini 2.5-pro never produced a valid FILES block. Codex timed out. Qwen delivered the patch. The orchestrator left a breadcrumb trail the whole way.

![Timeline showing three attempts: Gemini fails, Codex fails, Ollama succeeds while metadata grows](https://raw.githubusercontent.com/krukmat/agnostic-ai-pipeline/main/docs/01-fallback-system/diagram3-model-history-timeline.png)

The story metadata after that run (trimmed for clarity):

```yaml
- id: S6
  description: "Create PATCH /api/tasks/{id} endpoint"
  status: in_review
  metadata:
    recovery_attempts: 2
    model_history:
      - provider: vertex_sdk
        model: gemini-2.5-pro
        attempt: 1
        status: error
        timestamp: 2025-11-02T09:40:07Z
        error: "No valid FILES JSON block"
      - provider: codex_cli
        model: default
        attempt: 2
        status: error
        timestamp: 2025-11-02T09:41:15Z
        error: "API timeout"
      - provider: ollama
        model: qwen2.5-coder:32b
        attempt: 3
        status: ok
        timestamp: 2025-11-02T09:43:11Z
    model_override:
      provider: ollama
      model: qwen2.5-coder:32b
      reason: "Code specialist, runs locally"
      cost_tier: free
      specialties: [code_generation, local_execution]
```

Because the winning model writes itself back into `model_override`, the next `make loop` run will start with Qwen immediately. No guesswork, no manual edits.

---

## Config Quick Reference

Everything lives in `config.yaml`. The developer section currently looks like this:

```yaml
roles:
  dev:
    provider: vertex_sdk
    model: gemini-2.5-pro
    backup_models:
      - provider: codex_cli
        model: default
        reason: "Codex CLI for structured output fallback"
        cost_tier: high
        specialties: [structured_output, code_generation]
      - provider: ollama
        model: qwen2.5-coder:32b
        reason: "Code specialist, runs locally"
        cost_tier: free
        specialties: [code_generation, local_execution]
      - provider: vertex_cli
        model: gemini-2.5-pro
        reason: "Alternative Gemini access method"
        cost_tier: medium
        specialties: [general_purpose]

pipeline:
  max_recovery_attempts: 2
  model_fallback:
    enabled: true
    auto_suggest: true
    allow_cost_increase: false
    prefer_local: true
```

Tailor the specialties to the failures you see most often—strict JSON, long-context reasoning, high read/write traffic. The orchestrator will do the rest.

---

## How I Keep Myself Honest

- `planning/stories.yaml` is the source of truth. If a story is stuck, I inspect `metadata.model_history` before rerunning anything.
- `artifacts/iterations/*/summary.json` tells me how many recoveries triggered in a loop and which model saved the day.
- `artifacts/auto-dev` stores the raw responses from every failed attempt, which makes it easy to compare prompts.
- `logs/orchestrate.log` (when enabled) records the full scoring breakdown including candidates that were skipped.

---

**Next in the series (Part 3):** we zoom out to the full multi-role factory—BA, PO, Architect, Developer, QA—and how artifacts move between them.

Missed Part 1? [Read the vision here.](https://iotforce.medium.com/why-an-agentic-model-agnostic-pipeline-beats-a-pile-of-scripts-b57661276505)
