# How My AI Pipeline Automatically Recovered from 8 Model Failures

**What happens when Gemini times out, GPT-4 hits rate limits, or Claude returns garbage? Here's how automatic fallback works—and why it saved my pipeline.**

*Part 4 of 7 • [← Part 3: Cost Engineering](link-to-part-3) • [Part 2: Multi-Role Pipeline](link-to-part-2) • [Part 1: The Vision](link-to-part-1)*

---

## The Reality: Models Fail. A Lot.

Here's what happened on Day 4 of testing:

```
[Dev] Story S6: Implementing OAuth2 flow
[Dev] Using primary model: vertex_sdk/gemini-2.5-pro
[Dev] Request failed: 503 Service Unavailable
[Dev] Duration: 45 seconds
[Dev] Cost: $0 (no response)
```

Vertex AI was down. Our primary model couldn't respond.

In a typical setup, this is where you stop, file a ticket, wait for Google to fix it, and lose half a day.

But here's what actually happened:

```
[Dev] Primary model failed: vertex_sdk/gemini-2.5-pro
[Dev] Analyzing failure... API unavailable (503)
[Dev] Scoring backup models by specialty...
[Dev] Backup candidate: codex_cli/gpt-4-turbo (score: 85, cost: $5)
[Dev] Backup candidate: ollama/qwen2.5-coder (score: 78, cost: $0)
[Dev] Selected: codex_cli/gpt-4-turbo (cost acceptable, high score)
[Dev] Retry attempt 2/3 with gpt-4-turbo...
[Dev] Success. Duration: 8 seconds. Cost: $4.80
[Dev] Story S6 complete.
```

The pipeline automatically:
1. Detected the failure type (API unavailable)
2. Scored backup models by specialty and cost
3. Fell back to GPT-4
4. Completed the story successfully

Total delay: **53 seconds** (45s waiting for Gemini + 8s GPT-4 success)

Without fallback: **Hours** (waiting for Vertex AI to come back online)

---

## Why Models Fail (And It's Not Just Downtime)

Over 14 days and 47 iterations, I tracked every failure. Here's what I learned:

**Total LLM calls:** 312
**Failures:** 42 (13.5%)
**Automatic recoveries:** 34 (81% recovery rate)
**Manual intervention:** 8 (19% couldn't auto-recover)

### The Five Failure Types

**1. API Timeouts (32% of failures)**
```
Error: Request timeout after 120 seconds
Provider: vertex_sdk, openai, claude_cli
```
The model takes too long to respond. Sometimes it's network, sometimes the request is too complex.

**2. Rate Limits (28% of failures)**
```
Error: 429 Too Many Requests
Retry-After: 60 seconds
Provider: claude_cli, openai
```
You hit the provider's rate limit. Common with Claude and OpenAI during peak hours.

**3. Malformed Output (24% of failures)**
```
Error: JSON parsing failed
Expected: { "code": "...", "tests": "..." }
Received: "Sure! Here's the code:\n```python\n..."
```
The model returns valid text but doesn't follow the structured output format you specified.

**4. Context Window Exceeded (10% of failures)**
```
Error: Input tokens (145,328) exceed max context (128,000)
Provider: vertex_sdk/gemini-2.5-pro
```
Your prompt + context is too big for the model's context window.

**5. API Unavailable (6% of failures)**
```
Error: 503 Service Unavailable
Provider: vertex_sdk, claude_cli
```
The entire service is down. Rare but it happens.

---

## The Fallback Architecture

Here's how it works end-to-end:

![Fallback Flow Diagram](diagram1-fallback-flow.png)
*Complete fallback flow: from primary failure to automatic recovery*

### Step 1: Primary Model Attempt

```python
# scripts/run_dev.py
async def implement_story(story: dict, config: dict):
    primary_model = config['roles']['dev']

    try:
        response = await llm_client.chat(
            system=prompts['developer'],
            user=story['description'],
            model=primary_model['model'],
            provider=primary_model['provider']
        )
        return response, {"status": "success", "model": primary_model['model']}

    except Exception as e:
        # Failure detected, enter fallback mode
        return None, {"status": "failed", "error": str(e), "model": primary_model['model']}
```

### Step 2: Failure Analysis

When a failure happens, the orchestrator analyzes it:

```python
# scripts/orchestrate.py
def analyze_failure_and_suggest_model(error_msg: str, story: dict, config: dict):
    """
    Analyzes failure and suggests best backup model.

    Returns: (suggested_model, reason, specialties)
    """
    failure_type = detect_failure_type(error_msg)

    if failure_type == "timeout":
        # Prefer faster models
        specialties = ["fast_inference", "code_generation"]
    elif failure_type == "rate_limit":
        # Prefer different provider
        specialties = ["different_provider", "code_generation"]
    elif failure_type == "malformed_output":
        # Prefer models good at structured output
        specialties = ["structured_output", "code_generation"]
    elif failure_type == "context_exceeded":
        # Prefer models with larger context
        specialties = ["large_context", "code_generation"]
    elif failure_type == "api_unavailable":
        # Prefer different provider
        specialties = ["different_provider", "code_generation"]

    # Score and rank backup models
    scored_backups = score_backup_models(
        backup_models=config['roles']['dev']['backup_models'],
        specialties=specialties,
        max_cost=config['pipeline']['max_recovery_cost']
    )

    return scored_backups[0]  # Return highest-scoring model
```

### Step 3: Specialty Scoring

Each model has specialties defined in config:

```yaml
# config.yaml
providers:
  codex_cli:
    specialties:
      code_generation: 10        # Best at code
      structured_output: 8       # Good at JSON
      fast_inference: 6
    cost_tier: high

  ollama:
    specialties:
      code_generation: 7
      fast_inference: 10         # Fastest (local)
      different_provider: 10     # Always available
      structured_output: 5
    cost_tier: free

  vertex_sdk:
    specialties:
      code_generation: 9
      large_context: 10          # 1M tokens
      structured_output: 7
      fast_inference: 8
    cost_tier: medium
```

**Scoring algorithm:**

```python
def score_backup_models(backup_models, specialties, max_cost):
    scored = []

    for model in backup_models:
        score = 0

        # Add points for matching specialties
        for specialty in specialties:
            if specialty in model['specialties']:
                score += model['specialties'][specialty]

        # Penalty for exceeding cost
        if model['cost_tier'] == 'free':
            score += 5  # Bonus for free
        elif model['cost_tier'] == 'high' and max_cost < 5.0:
            score -= 10  # Penalty if budget is tight

        scored.append({
            'model': model,
            'score': score
        })

    # Sort by score descending
    return sorted(scored, key=lambda x: x['score'], reverse=True)
```

### Step 4: Retry with Backup Model

```python
# Back in run_dev.py
if response is None:
    # Get suggested backup model from orchestrator
    backup = orchestrator.analyze_failure_and_suggest_model(
        error_msg=model_info['error'],
        story=story,
        config=config
    )

    # Retry with backup model
    try:
        response = await llm_client.chat(
            system=prompts['developer'],
            user=story['description'],
            model=backup['model'],
            provider=backup['provider']
        )

        # Success! Update model_history
        story['model_history'].append({
            'attempt': 2,
            'model': backup['model'],
            'provider': backup['provider'],
            'status': 'success',
            'reason': backup['reason']
        })

    except Exception as e:
        # Second failure, try next backup...
        pass
```

---

## Real Examples from Production

Let me show you three actual failures and how they recovered.

### Example 1: Vertex AI Downtime (Day 4)

**Story S6:** Implement OAuth2 authentication

**Primary attempt:**
```
[Dev] Model: vertex_sdk/gemini-2.5-pro
[Dev] Error: 503 Service Unavailable
[Dev] Duration: 45 seconds
[Dev] Cost: $0
```

**Failure analysis:**
```python
failure_type = "api_unavailable"
specialties = ["different_provider", "code_generation"]
```

**Backup scoring:**
```
codex_cli/gpt-4-turbo: score=85 (different_provider:10, code_generation:10)
ollama/qwen2.5-coder: score=78 (different_provider:10, code_generation:7)
```

**Backup attempt:**
```
[Dev] Model: codex_cli/gpt-4-turbo
[Dev] Status: Success
[Dev] Duration: 8 seconds
[Dev] Cost: $4.80
```

**Total cost:** $4.80 (vs. $0 if we waited for Vertex to recover, but hours lost)

---

### Example 2: Claude Rate Limit (Day 9)

**Story S12:** Generate comprehensive QA test suite

**Primary attempt:**
```
[QA] Model: claude_cli/claude-3-5-sonnet-latest
[QA] Error: 429 Too Many Requests, Retry-After: 60
[QA] Duration: 2 seconds
[QA] Cost: $0
```

**Failure analysis:**
```python
failure_type = "rate_limit"
specialties = ["different_provider", "code_generation"]
```

**Backup scoring:**
```
ollama/qwen2.5-coder: score=88 (different_provider:10, fast_inference:10, cost:free)
vertex_sdk/gemini-2.5-pro: score=82 (different_provider:10, code_generation:9)
```

**Backup attempt:**
```
[QA] Model: ollama/qwen2.5-coder:32b
[QA] Status: Success
[QA] Duration: 4 seconds
[QA] Cost: $0
```

**Total cost:** $0 (local fallback saved the day)

---

### Example 3: Malformed JSON Output (Day 11)

**Story S18:** Create REST API endpoints with validation

**Primary attempt:**
```
[Dev] Model: ollama/mistral:7b-instruct
[Dev] Error: JSON parsing failed
[Dev] Response: "Sure! Here's the implementation:\n\n```python\ndef create..."
[Dev] Duration: 3 seconds
[Dev] Cost: $0
```

**Failure analysis:**
```python
failure_type = "malformed_output"
specialties = ["structured_output", "code_generation"]
```

**Backup scoring:**
```
codex_cli/gpt-4-turbo: score=90 (structured_output:8, code_generation:10)
vertex_sdk/gemini-2.5-pro: score=85 (structured_output:7, code_generation:9)
```

**Backup attempt:**
```
[Dev] Model: codex_cli/gpt-4-turbo
[Dev] Status: Success
[Dev] Duration: 6 seconds
[Dev] Cost: $4.20
```

**Total cost:** $4.20 (paid for quality when free model failed)

---

## The model_history Metadata

Every story tracks its complete model history:

```yaml
# planning/stories.yaml
- id: S6
  description: "Implement OAuth2 authentication"
  status: done
  model_history:
    - attempt: 1
      model: gemini-2.5-pro
      provider: vertex_sdk
      timestamp: "2025-11-06T14:32:10Z"
      status: failed
      error: "503 Service Unavailable"
      duration: 45
      cost: 0

    - attempt: 2
      model: gpt-4-turbo
      provider: codex_cli
      timestamp: "2025-11-06T14:32:55Z"
      status: success
      duration: 8
      cost: 4.80
      reason: "Fallback due to API unavailable"
      specialties_used: ["different_provider", "code_generation"]
```

This gives you:
- **Complete audit trail** - Which models were tried, in what order
- **Cost tracking** - How much each attempt cost
- **Performance metrics** - Duration per attempt
- **Failure reasons** - Why each attempt failed
- **Recovery strategy** - Which specialties were prioritized

---

## Recovery Budget: Preventing Cost Explosions

Here's a dangerous config:

```yaml
# ❌ DON'T DO THIS
pipeline:
  max_recovery_attempts: 10      # Too many retries
  allow_cost_increase: true      # No cost limit
  prefer_local: false            # Prefer cloud even for retries
```

This can spiral:

```
[Dev] Attempt 1: GPT-4 ($5) - Failed
[Dev] Attempt 2: GPT-4 ($5) - Failed
[Dev] Attempt 3: Claude ($6) - Failed
[Dev] Attempt 4: GPT-4 ($5) - Failed
[Dev] Attempt 5: Claude ($6) - Failed
...
Total wasted: $27+ with no success
```

**Our config prevents this:**

```yaml
# ✅ SAFE CONFIG
pipeline:
  max_recovery_attempts: 2       # Fail fast after 2 fallbacks
  allow_cost_increase: false     # Block expensive fallbacks
  prefer_local: true             # Try free models first
  max_recovery_cost: 5.0         # Cap at $5 per recovery
```

**Result:**

```
[Dev] Attempt 1: Gemini ($0.30) - Failed
[Dev] Attempt 2: Ollama ($0) - Failed
[Dev] Max recovery attempts reached (2/2)
[Dev] Status: blocked_recovery_budget
[Dev] Suggestion: Review story complexity or increase budget
```

Story gets blocked, you get notified, costs stay under control.

---

## Cost Optimization in Fallback

**Strategy 1: Prefer Local First**

```yaml
roles:
  dev:
    provider: codex_cli
    model: gpt-4-turbo
    backup_models:
      - provider: ollama
        model: qwen2.5-coder:32b     # Try free first
      - provider: vertex_sdk
        model: gemini-2.5-pro        # Then cheap cloud
      - provider: codex_cli
        model: gpt-4-turbo           # Last resort: expensive
```

If primary fails, try free → cheap → expensive.

**Strategy 2: Block Cost Increase**

```yaml
pipeline:
  allow_cost_increase: false
```

If primary costs $0.30 (Gemini), fallback can't use $5 model (GPT-4).

**Strategy 3: Different Provider Only**

```yaml
pipeline:
  fallback_strategy: different_provider_only
```

If Vertex AI fails, only try OpenAI, Anthropic, or Ollama. Don't retry Vertex.

---

## How to Configure Your Fallback Strategy

### For Maximum Reliability (Cost Secondary)

```yaml
# config.yaml
roles:
  dev:
    provider: codex_cli
    model: gpt-4-turbo
    backup_models:
      - provider: claude_cli
        model: claude-3-5-sonnet-latest
      - provider: vertex_sdk
        model: gemini-2.5-pro
      - provider: ollama
        model: qwen2.5-coder:32b

pipeline:
  max_recovery_attempts: 3
  allow_cost_increase: true        # Pay more if needed
  prefer_local: false              # Prefer cloud quality
```

Use when: Production deployments, critical features.

---

### For Maximum Cost Savings (Reliability Secondary)

```yaml
# config.yaml
roles:
  dev:
    provider: ollama
    model: qwen2.5-coder:32b
    backup_models:
      - provider: vertex_sdk
        model: gemini-2.5-pro
      - provider: codex_cli
        model: gpt-4-turbo

pipeline:
  max_recovery_attempts: 2
  allow_cost_increase: false       # Stay within budget
  prefer_local: true               # Prefer free models
  max_recovery_cost: 1.0           # Cap at $1
```

Use when: Experimentation, prototyping, development.

---

### Balanced (Recommended)

```yaml
# config.yaml
roles:
  dev:
    provider: vertex_sdk
    model: gemini-2.5-pro
    backup_models:
      - provider: ollama
        model: qwen2.5-coder:32b
      - provider: codex_cli
        model: gpt-4-turbo

pipeline:
  max_recovery_attempts: 2
  allow_cost_increase: true        # Allow one expensive retry
  prefer_local: true               # Try free first
  max_recovery_cost: 5.0           # Cap at $5
```

Use when: Most scenarios. Good balance of cost and reliability.

---

## Deep Dive: Client Rehydration

When orchestrator calls Developer role with a backup model, it needs to reconstruct the full LLM client config. This is non-trivial because CLI providers have 18+ properties.

```python
# scripts/run_dev.py (lines 262-330)
async def implement_story_with_override(story: dict, model_override: dict):
    """
    Rehydrate LLM client with full provider config.
    """
    # Load original config
    original_config = load_config('config.yaml')

    # Get provider definition
    provider_def = original_config['providers'][model_override['provider']]

    # Build full client config with all 18 CLI properties
    client_config = {
        'provider': model_override['provider'],
        'model': model_override['model'],

        # CLI-specific (if provider type == 'cli')
        'command': provider_def.get('command'),
        'cwd': provider_def.get('cwd'),
        'timeout': provider_def.get('timeout', 300),
        'input_format': provider_def.get('input_format', 'stdin_text'),
        'output_clean': provider_def.get('output_clean', True),
        'parse_json': provider_def.get('parse_json', True),
        'append_system_prompt': provider_def.get('append_system_prompt', False),
        'extra_args': provider_def.get('extra_args', []),
        'debug': provider_def.get('debug', False),
        'debug_args': provider_def.get('debug_args', False),
        'log_stderr': provider_def.get('log_stderr', True),
        # ... (18 total properties)

        # HTTP-specific (if provider type == 'http')
        'base_url': provider_def.get('base_url'),
        'api_key': provider_def.get('api_key'),
        'headers': provider_def.get('headers', {}),
        # ...
    }

    # Create rehydrated client
    client = Client(config=client_config)

    # Execute with backup model
    response = await client.chat(
        system=prompts['developer'],
        user=story['description']
    )

    return response
```

Why this matters:
- CLI providers like `codex_cli`, `claude_cli`, `vertex_cli` need full subprocess config
- HTTP providers like `ollama`, `openai` need base_url, API keys, headers
- Can't just pass model name—need entire provider definition
- Orchestrator doesn't know provider internals, so Developer role owns rehydration

---

## Metadata Persistence and Ownership

**Who owns what:**

| Metadata Field | Owner | Updated By | Persisted In |
|---------------|-------|-----------|-------------|
| `model_history` | Orchestrator | Developer role | `stories.yaml` |
| `recovery_attempts` | Orchestrator | Orchestrator | `stories.yaml` |
| `last_failure_reason` | Orchestrator | Developer role | `stories.yaml` |
| `model_override` | Orchestrator | Orchestrator | `stories.yaml` |
| `cost` | Developer role | Developer role | `summary.json` |
| `duration` | Developer role | Developer role | `summary.json` |

**Why Orchestrator owns model_history:**
- Orchestrator sees the full fallback chain
- Developer role only sees its own attempt
- Orchestrator decides which backup to try next
- Orchestrator persists to YAML after each attempt

**Pattern:**

```python
# Orchestrator (scripts/orchestrate.py)
for attempt in range(1, max_attempts + 1):
    # Call Developer role
    response, model_info = await run_dev(story, model_override)

    # Orchestrator captures metadata
    story['model_history'].append({
        'attempt': attempt,
        'model': model_info['model'],
        'provider': model_info['provider'],
        'status': model_info['status'],
        'error': model_info.get('error'),
        'cost': model_info.get('cost', 0),
        'duration': model_info.get('duration', 0),
        'timestamp': datetime.utcnow().isoformat()
    })

    # Persist after each attempt
    save_yaml('planning/stories.yaml', stories)

    if model_info['status'] == 'success':
        break
    else:
        # Analyze failure, suggest backup
        model_override = analyze_failure_and_suggest_model(...)
```

This ensures **crash safety**: If the pipeline crashes mid-retry, you don't lose metadata.

---

## What Could Go Wrong

Let's be honest about the limitations:

### 1. All Backups Fail

**Scenario:** Primary + 2 backups all timeout.

```
[Dev] Attempt 1: Gemini - timeout
[Dev] Attempt 2: GPT-4 - timeout
[Dev] Attempt 3: Ollama - timeout
[Dev] Status: blocked_recovery_budget
```

**Solution:**
- Increase timeout in config
- Simplify the story (it's too complex)
- Manual intervention required

**Frequency:** ~3% of stories (8 out of 312 calls)

---

### 2. Backup Model Produces Lower Quality

**Scenario:** Primary (GPT-4) fails, falls back to Ollama, produces buggy code.

```
[Dev] Attempt 1: GPT-4 - failed
[Dev] Attempt 2: Ollama - success (but tests fail)
[QA] Tests failed: 4/10 passing
[QA] Status: rejected
```

**Solution:**
- QA catches it and rejects
- Architect refines story
- Next attempt uses stronger model

**Frequency:** ~12% of local fallbacks

---

### 3. Cost Overruns Despite Budget

**Scenario:** You set `max_recovery_cost: 5.0` but primary costs $0.30, backup costs $4.80, next backup costs $5.00.

Total: $10.10 (exceeds budget)

**Solution:**
- `allow_cost_increase: false` blocks the third attempt
- Story gets blocked with clear reason
- You review and decide manually

---

## Try It Yourself

**Step 1: Configure fallback chain**

```bash
# Edit config.yaml
roles:
  dev:
    provider: vertex_sdk
    model: gemini-2.5-pro
    backup_models:
      - provider: ollama
        model: qwen2.5-coder:32b
      - provider: codex_cli
        model: gpt-4-turbo

pipeline:
  max_recovery_attempts: 2
  prefer_local: true
  max_recovery_cost: 5.0
```

**Step 2: Run iteration and simulate failure**

```bash
# Simulate Vertex AI down by setting invalid credentials
export VERTEX_UNAVAILABLE=1

make iteration CONCEPT="User authentication system"
```

**Step 3: Check model_history**

```bash
cat planning/stories.yaml | grep -A 20 "model_history"
```

You'll see:
- Attempt 1: Gemini (failed)
- Attempt 2: Ollama (success)
- Reason: "Fallback due to API unavailable"

---

## Real Stats from 14 Days

**Summary:**

| Metric | Value |
|--------|-------|
| Total LLM calls | 312 |
| Primary failures | 42 (13.5%) |
| Successful fallbacks | 34 (81% recovery) |
| Failed after all retries | 8 (19% manual intervention) |
| Cost saved via local fallback | $38-45 |
| Time saved vs manual retry | ~4-6 hours |

**Most common fallback path:**
```
Gemini (fail) → Ollama (success): 18 times
GPT-4 (fail) → Ollama (success): 9 times
Claude (rate limit) → Ollama (success): 7 times
```

**Local Ollama saved my ass 34 times in 14 days.**

---

## What's Next

In **Part 5**, we'll explore A2A (Agent-to-Agent) mode: running each role as an independent HTTP service. Imagine BA running on one server, Dev on another, QA on a third—all talking to each other via REST APIs.

In **Part 6**, I'll show you how to build your own custom providers and validators, hook into CI/CD, and extend the pipeline for your specific stack.

---

**Part 4 of 7:** Inside the Fallback System
[← Part 3: Cost Engineering](link-to-part-3) | [Part 2: Multi-Role Pipeline](link-to-part-2) | [Part 1: The Vision](link-to-part-1) | Part 5: A2A Mode (coming soon)

Repository: https://github.com/krukmat/agnostic-ai-pipeline
Try it: `git clone https://github.com/krukmat/agnostic-ai-pipeline.git`

*Questions? Hit a weird failure mode? Open an issue. Let's make this fallback system bulletproof together.*
