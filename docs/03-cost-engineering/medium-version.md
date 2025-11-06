# How I Cut AI Costs by 89% Using Smart Routing and Local Models

**The real cost breakdown from 47 iterations: where money goes, where it doesn't, and how to avoid the expensive traps most teams fall into.**

*Part 3 of 7 • [← Part 2: Multi-Role Pipeline](link-to-part-2) • [Part 1: The Vision](link-to-part-1)*

---

## The Problem: AI Costs Are Unpredictable

Here's what happened during our first sprint using only GPT-4:

**Day 1:** "This is amazing! We built three features!"
**Day 3:** "Wait, why is the bill at $180?"
**Day 7:** "We need to stop. We've burned through the monthly budget."

Sound familiar?

The problem isn't that GPT-4 is expensive. It's that most teams use expensive models for *everything*—including tasks that don't need them.

Imagine paying for AWS Lambda pricing on a static HTML page. That's what using GPT-4 for requirements drafts feels like.

---

## The Insight: Not All Tasks Need GPT-4

Let me show you what two weeks of actual usage looks like.

**The Real Numbers (14 Days, 47 Iterations):**
- **Total cost:** $47.30
- **Total iterations:** 47 features built end-to-end
- **Average cost per feature:** $1.01

**Cost breakdown by role:**
- BA + PO (Ollama local): **$0.00** (100% of work done locally)
- Architect (Gemini 2.5-pro): **$8.20** (17% of total cost)
- Developer (GPT-4/Codex/Ollama mix): **$32.50** (69% of total cost)
- QA (Claude 3.5 + Qwen): **$6.60** (14% of total cost)

**If I had used GPT-4 for everything:** ~$380

**Savings:** 87.5%

Here's the thing: quality didn't drop. QA validates everything. Tests still pass. Code still works. We just stopped burning money on drafts.

---

## Where Teams Waste Money (The Four Traps)

### Trap 1: Using GPT-4 for Brainstorming

Most teams do this:

```bash
# Every BA call hits GPT-4 at $15/1M tokens
make ba CONCEPT="Todo app"  # Cost: $2.50
make ba CONCEPT="Blog with markdown"  # Cost: $2.30
make ba CONCEPT="User auth system"  # Cost: $1.80
```

**Total for 3 drafts:** $6.60

Here's what we do instead:

```yaml
# config.yaml
roles:
  ba:
    provider: ollama        # Run locally
    model: granite4         # Free, fast enough for drafts
```

```bash
make ba CONCEPT="Todo app"  # Cost: $0
make ba CONCEPT="Blog with markdown"  # Cost: $0
make ba CONCEPT="User auth system"  # Cost: $0
```

**Total:** $0

The BA output goes to the PO anyway, which validates and refines it. You don't need GPT-4 quality for a first draft.

---

### Trap 2: No Fallback to Cheaper Models

This is what killed us in Week 1:

```
[Dev] GPT-4 timeout (attempt 1/3)
[Dev] GPT-4 timeout (attempt 2/3)
[Dev] GPT-4 timeout (attempt 3/3)
[Dev] Story failed. Manual retry required.
```

We paid for three failed attempts and got nothing.

Here's what happens now:

```
[Dev] GPT-4 timeout (attempt 1/3)
[Dev] Analyzing failure... API timeout detected
[Dev] Suggesting fallback: codex_cli (backup model)
[Dev] codex_cli timeout (attempt 2/3)
[Dev] Suggesting fallback: ollama/qwen2.5-coder (local)
[Dev] ollama success (attempt 3/3)
[Dev] Story S4 complete. Cost: $0 (local fallback)
```

We paid for one failed GPT-4 call (~$0.50), then got results for free using a local model.

**Savings per failure:** ~$4–5 (would've been three GPT-4 retries)

**Fallbacks triggered in 14 days:** 8

**Total savings from fallback:** ~$32–40

---

### Trap 3: Not Tracking Costs Per Iteration

Most teams don't know where their money goes until the bill arrives.

We capture costs in real-time:

```json
// artifacts/iterations/login-feature-20251102/summary.json
{
  "iteration_name": "login-feature-20251102",
  "total_cost": 6.85,
  "total_duration": 143,
  "stories_completed": 4,
  "breakdown": {
    "ba": { "cost": 0, "model": "ollama/granite4", "duration": 3 },
    "po": { "cost": 0, "model": "ollama/granite4", "duration": 4 },
    "architect": { "cost": 0.18, "model": "gemini-2.5-pro", "duration": 12 },
    "dev": {
      "S1": { "cost": 4.20, "model": "gpt-4-turbo", "attempts": 1 },
      "S2": { "cost": 0.80, "model": "codex_cli", "attempts": 2 },
      "S3": { "cost": 0, "model": "ollama/qwen2.5-coder", "attempts": 3 },
      "S4": { "cost": 0.32, "model": "ollama/qwen2.5-coder", "attempts": 1 }
    },
    "qa": { "cost": 1.35, "model": "claude-3-5-sonnet-latest", "duration": 18 }
  }
}
```

We know:
- Exact cost per story
- Which model was used (and why)
- How many retry attempts
- Duration per role

You can set budget alerts, analyze trends, and optimize hot paths.

---

### Trap 4: Retrying Infinitely Without Budget Control

Some teams configure retry logic like this:

```yaml
pipeline:
  max_recovery_attempts: 10  # Retry up to 10 times
  allow_cost_increase: true  # Allow more expensive fallbacks
```

Here's what happens:

```
[Dev] GPT-4 fails → Retry 1 ($5)
[Dev] GPT-4 fails → Retry 2 ($5)
[Dev] GPT-4 fails → Retry 3 ($5)
[Dev] GPT-4 fails → Retry 4 ($5)
[Dev] GPT-4 fails → Retry 5 ($5)
...
```

**Total wasted:** $50+ on retries before giving up.

Our config:

```yaml
pipeline:
  max_recovery_attempts: 2      # Fail fast after 2 attempts
  allow_cost_increase: false    # Block expensive fallbacks
  prefer_local: true            # Try local models first
```

If GPT-4 fails twice, we fall back to Ollama (free). We don't burn money retrying the same expensive model.

---

## The Cost Tier Strategy

We use three tiers:

### Free Tier (Ollama - Local Models)

**Use for:** Drafts, brainstorming, iterations, fallback
**Models:** granite4, qwen2.5-coder, mistral, llama3.3
**Cost:** $0
**Latency:** 1-3 seconds per call

**Roles:**
- BA: 100% local (all drafts)
- PO: 100% local (all validation)
- Dev: ~40% local (fallback after cloud failures)
- QA: ~30% local (fallback + non-critical checks)

**Setup:**
```bash
# Install Ollama
brew install ollama  # macOS
# or: curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull granite4
ollama pull qwen2.5-coder:32b

# Configure role
make set-role role=ba provider=ollama model="granite4"
```

**When it works well:**
- Requirements generation (BA)
- Product validation (PO)
- Simple CRUD endpoints (Dev fallback)
- Test validation (QA fallback)

**When it struggles:**
- Complex state management
- Security-critical code
- Edge case reasoning
- Structured output consistency

---

### Medium Tier (Gemini - $0.30/1M tokens)

**Use for:** Planning, architecture, story generation
**Model:** Gemini 2.5-pro
**Cost:** ~$0.20 per feature
**Latency:** 2-5 seconds per call

**Roles:**
- Architect: 100% Gemini (best price/quality for planning)

**Setup:**
```bash
# Authenticate with Google Cloud
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com

# Configure role
make set-role role=architect provider=vertex_sdk model="gemini-2.5-pro"
```

**Why Gemini for Architect:**
- Cheap enough for planning work
- Good at structured output (YAML, JSON)
- Fast response times
- 1M token context window (handles large requirements)

**Cost comparison for 47 iterations:**
- Gemini: $8.20
- GPT-4: Would've been ~$35
- Claude: Would've been ~$28

Savings: ~$20-27

---

### High Tier (GPT-4, Claude - $15-60/1M tokens)

**Use for:** Critical code generation, final QA validation
**Models:** GPT-4-turbo ($15/1M), Claude 3.5 Sonnet ($15/1M)
**Cost:** $4-6 per story
**Latency:** 3-8 seconds per call

**Roles:**
- Dev: Primary model for production code
- QA: Final validation before approval

**Setup:**
```bash
# GPT-4 via Codex CLI
export OPENAI_API_KEY="sk-..."
make set-role role=dev provider=codex_cli model="gpt-4-turbo"

# Claude via CLI
claude login
make set-role role=qa provider=claude_cli model="claude-3-5-sonnet-latest"
```

**Why pay premium:**
- Code quality matters (it's going to production)
- Edge case handling is better
- Structured output is more reliable
- Security best practices are better

**Cost comparison for 47 iterations:**
- Dev (GPT-4 primary + fallbacks): $32.50
- QA (Claude primary + fallbacks): $6.60
- If 100% GPT-4 with no fallbacks: Would've been ~$85

Savings: ~$46

---

## When to Use Local vs Cloud

Here's my decision tree:

```
Is it a draft or first iteration?
├─ Yes → Use local (Ollama)
└─ No → Continue

Is it user-facing production code?
├─ Yes → Use cloud (GPT-4, Claude)
└─ No → Continue

Is it planning/architecture (no code)?
├─ Yes → Use medium tier (Gemini)
└─ No → Continue

Did cloud model fail?
├─ Yes → Fallback to local (Ollama)
└─ No → Use cloud
```

**Examples:**

| Task | Model Choice | Reason |
|------|-------------|---------|
| Generate requirements.yaml | Ollama (local) | Draft, will be validated |
| Generate user stories | Gemini (cloud) | Planning, cheap enough |
| Implement /login endpoint | GPT-4 (cloud) | Production code, critical |
| Validate tests | Claude (cloud) | Quality gate, important |
| Fallback after GPT-4 timeout | Ollama (local) | Free retry, acceptable quality |
| Second requirements draft | Ollama (local) | Still a draft |

---

## Budget Control Configuration

Here's how we enforce cost limits:

```yaml
# config.yaml
pipeline:
  # Retry settings
  max_recovery_attempts: 2          # Stop after 2 fallbacks
  prefer_local: true                # Try local models first
  allow_cost_increase: false        # Block expensive fallbacks

  # Budget alerts (optional)
  cost_alert_threshold: 50.0        # Alert if monthly cost > $50
  cost_hard_limit: 100.0            # Stop pipeline if > $100

# Per-role cost tier
roles:
  ba:
    provider: ollama
    max_cost_per_call: 0            # Must be free

  architect:
    provider: vertex_sdk
    max_cost_per_call: 0.50         # Cap at $0.50/call

  dev:
    provider: codex_cli
    max_cost_per_call: 5.0          # Cap at $5/story
    backup_models:
      - provider: ollama
        model: qwen2.5-coder:32b    # Free fallback

  qa:
    provider: claude_cli
    max_cost_per_call: 2.0          # Cap at $2/validation
    backup_models:
      - provider: ollama
        model: qwen2.5-coder:32b    # Free fallback
```

If a role exceeds its budget, the pipeline fails fast and logs the reason:

```
[Dev] Story S3 cost estimate: $6.20
[Dev] Exceeds max_cost_per_call: $5.0
[Dev] Status: blocked_cost_budget
[Dev] Suggestion: Use cheaper model or increase budget
```

---

## The Model Recommendation System (RoRF)

Here's where it gets interesting.

**Problem:** Even within a role, not all tasks need the same model.

Example:
- Story S1: Simple CRUD endpoint → Ollama is fine
- Story S2: OAuth2 implementation → Needs GPT-4

Manually choosing models per story is tedious. So we built a router.

---

### What Is RoRF?

**RoRF = Routing or Ranking Framework**

It's a prompt classifier that analyzes task complexity and routes to the appropriate model:

- **Weak model** (cheap, fast): Ollama, Mistral
- **Strong model** (expensive, powerful): GPT-4, Claude

**Activation:**
```bash
export MODEL_RECO_ENABLED=1
make iteration CONCEPT="User authentication with OAuth2"
```

---

### How It Works

**Step 1: Prompt Analysis**

Before calling the Dev role, the system analyzes the story:

```python
# src/recommend/classifier.py
def classify_prompt_complexity(story: dict) -> str:
    """
    Returns: 'simple', 'medium', 'complex'
    """
    indicators = {
        'simple': ['CRUD', 'basic', 'simple', 'list', 'view'],
        'medium': ['validation', 'business logic', 'workflow'],
        'complex': ['OAuth', 'security', 'distributed', 'real-time']
    }

    description = story['description'].lower()

    if any(kw in description for kw in indicators['complex']):
        return 'complex'
    elif any(kw in description for kw in indicators['medium']):
        return 'medium'
    else:
        return 'simple'
```

**Step 2: Model Routing**

Based on complexity:

```yaml
# config/model_recommender.yaml
routing_rules:
  simple:
    model: ollama/qwen2.5-coder:32b
    max_cost: 0
    expected_quality: 0.75

  medium:
    model: vertex_sdk/gemini-2.5-pro
    max_cost: 0.50
    expected_quality: 0.85

  complex:
    model: codex_cli/gpt-4-turbo
    max_cost: 5.0
    expected_quality: 0.95
```

**Step 3: Execution**

```
[Dev] Story S1: "Create POST /api/users endpoint"
[Dev] Complexity: simple
[Dev] Recommended model: ollama/qwen2.5-coder:32b
[Dev] Cost estimate: $0
[Dev] Executing with Ollama...
[Dev] Success. Actual cost: $0

[Dev] Story S2: "Implement OAuth2 authentication with Google"
[Dev] Complexity: complex
[Dev] Recommended model: codex_cli/gpt-4-turbo
[Dev] Cost estimate: $5.20
[Dev] Executing with GPT-4...
[Dev] Success. Actual cost: $5.18
```

---

### Real Results with RoRF

**14-day test with RoRF enabled:**

| Complexity | Stories | Model Used | Avg Cost | Total Cost |
|-----------|---------|-----------|----------|-----------|
| Simple | 28 | Ollama | $0 | $0 |
| Medium | 12 | Gemini | $0.35 | $4.20 |
| Complex | 7 | GPT-4 | $4.80 | $33.60 |
| **Total** | **47** | **Mixed** | **$0.81** | **$37.80** |

**Without RoRF (all GPT-4):** $225

**Savings:** 83%

---

### How to Train/Tune the Router

The classifier uses simple keyword matching by default. You can improve it:

**Option 1: Add more keywords**

```yaml
# config/model_recommender.yaml
complexity_indicators:
  simple:
    - CRUD
    - basic
    - simple
    - list
    - view
    - display
  medium:
    - validation
    - business logic
    - workflow
    - calculations
    - reports
  complex:
    - OAuth
    - security
    - distributed
    - real-time
    - payment
    - encryption
```

**Option 2: Use embeddings (advanced)**

```python
# src/recommend/embedding_classifier.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def classify_with_embeddings(story: dict) -> str:
    embedding = model.encode(story['description'])

    # Compare to reference embeddings of known simple/medium/complex stories
    similarity_simple = cosine_similarity(embedding, ref_embeddings['simple'])
    similarity_complex = cosine_similarity(embedding, ref_embeddings['complex'])

    if similarity_complex > 0.8:
        return 'complex'
    elif similarity_simple > 0.8:
        return 'simple'
    else:
        return 'medium'
```

**Option 3: Fine-tune with feedback**

Track which stories succeeded/failed with which models, then adjust thresholds:

```python
# After each iteration
if story.status == 'done':
    feedback_log.append({
        'story': story.id,
        'complexity': story.classified_complexity,
        'model_used': story.model_used,
        'success': True,
        'cost': story.cost
    })

# Periodically retrain
retrain_classifier(feedback_log)
```

---

## ROI Breakdown: Why This Matters

Let's compare three approaches over **100 features**:

### Approach 1: All GPT-4 (No Optimization)

```
BA: 100 calls × $2.50 = $250
Architect: 100 calls × $3.00 = $300
Dev: 100 stories × $5.00 = $500
QA: 100 calls × $1.50 = $150

Total: $1,200
```

### Approach 2: Hybrid (Static Assignment)

```
BA (Ollama): 100 calls × $0 = $0
Architect (Gemini): 100 calls × $0.20 = $20
Dev (GPT-4): 100 stories × $5.00 = $500
QA (Claude): 100 calls × $1.50 = $150

Total: $670
Savings: 44%
```

### Approach 3: Hybrid + RoRF (Smart Routing)

```
BA (Ollama): 100 calls × $0 = $0
Architect (Gemini): 100 calls × $0.20 = $20
Dev (Mixed):
  - 60 simple (Ollama): $0
  - 25 medium (Gemini): $0.35 × 25 = $8.75
  - 15 complex (GPT-4): $5.00 × 15 = $75
QA (Mixed):
  - 70 simple (Ollama): $0
  - 30 critical (Claude): $1.50 × 30 = $45

Total: $148.75
Savings: 87.6%
```

**Monthly cost for a team building 100 features/month:**
- All GPT-4: $1,200/month
- Hybrid static: $670/month (saves $530)
- Hybrid + RoRF: $148.75/month (saves $1,051)

---

## What Could Go Wrong

Let's be honest about the tradeoffs:

**1. Local models are less consistent**

Ollama will occasionally hallucinate or generate malformed JSON. That's why we:
- Use local only for drafts (BA, PO)
- Have QA validate everything
- Fall back to cloud for critical steps

**2. RoRF can misclassify**

Sometimes a "simple" story is actually complex. When that happens:
- QA rejects it
- Architect refines it
- Next attempt uses a stronger model

Cost of misclassification: ~$0 (local attempt) + ~$5 (GPT-4 retry) = $5
Cost without RoRF: $5 every time

Still a win.

**3. Cost tracking isn't perfect**

We track API costs, but not:
- Local compute costs (electricity, hardware)
- Developer time configuring models
- Time spent debugging failures

For local Ollama on a laptop: ~$0.05/hour electricity
For cloud GPT-4: $5/feature

Local still wins.

---

## Try It Yourself

**Step 1: Set up cost tiers**

```bash
# Free tier (BA, PO)
make set-role role=ba provider=ollama model="granite4"
make set-role role=po provider=ollama model="granite4"

# Medium tier (Architect)
make set-role role=architect provider=vertex_sdk model="gemini-2.5-pro"

# High tier (Dev, QA)
make set-role role=dev provider=codex_cli model="gpt-4-turbo"
make set-role role=qa provider=claude_cli model="claude-3-5-sonnet-latest"
```

**Step 2: Enable RoRF (optional)**

```bash
export MODEL_RECO_ENABLED=1
```

**Step 3: Run an iteration**

```bash
make iteration CONCEPT="Todo app with user authentication"
```

**Step 4: Check costs**

```bash
cat artifacts/iterations/*/summary.json | jq '.total_cost'
```

You'll see:
- BA cost: $0
- PO cost: $0
- Architect cost: ~$0.20
- Dev cost: Mixed (some $0, some $5)
- QA cost: Mixed (some $0, some $1.50)

Total: Way less than all-GPT-4.

---

## What's Next

In **Part 4**, we'll dive into the fallback system: what happens when Gemini fails, how it scores backup models, and how to configure recovery strategies.

In **Part 5**, I'll show you how to run each role as an independent service (A2A mode) so different teams can own different parts of the pipeline.

---

**Part 3 of 7:** Cost Engineering + Model Recommendation
[← Part 2: Multi-Role Pipeline](link-to-part-2) | [Part 1: The Vision](link-to-part-1) | Part 4: Fallback System (coming soon)

Repository: https://github.com/krukmat/agnostic-ai-pipeline
Try it: `git clone https://github.com/krukmat/agnostic-ai-pipeline.git`

*Questions? Benchmarks? Cost data to share? Open an issue or start a discussion. Let's figure out the optimal cost strategy together.*
