# I Spent $347 Testing AI Models in Two Weeks. Here's What I Built Instead.

**The AI landscape of 2025 is chaos. Here's how I stopped playing vendor roulette and built a software factory that works with any model.**

---

## The Problem (and it's getting worse)

Last month, I burned through $347 testing whether GPT-4 could generate our backend code. It worked beautifully—until OpenAI changed their API three days later and our prompts started returning garbage. We scrambled to Claude. Then Gemini. Then back to GPT-4 with new prompts.

You know where this goes.

Here's the uncomfortable truth about building with AI in 2025: **the "perfect model" doesn't exist, and even if it did, it'll be different next week.**

**The 2025 AI Landscape:**
- 120+ available LLM models
- ~15 new models per month
- $0–$60 cost per 1M tokens range

The AI model landscape is fragmented, volatile, and expensive. Every team faces the same brutal cycle:

1. Pick a model based on benchmarks and hype
2. Write prompts that work with that specific model
3. Ship to production
4. Model changes, pricing shifts, or API goes down
5. Scramble to rewrite everything for the next model
6. Repeat weekly

Meanwhile, costs are unpredictable, prompts live in someone's Notion doc, outputs aren't reproducible, and every model change feels like a complete rewrite. We're stuck in vendor roulette while trying to ship actual features.

---

## The Insight: Stop Betting on One Model

> **What if we stopped trying to find the ONE perfect model?**
>
> What if we treated AI models like we treat servers—with routing, fallbacks, cost tiers, and observability?

Think about how we handle infrastructure:

- We don't use AWS for everything just because it's popular
- We route cheap requests to cheap servers, critical ones to premium
- When a service fails, we have automatic failover
- We track costs per service, set budgets, and get alerts

Why don't we do this with AI models?

---

## The Concept: AI Software Factory Pipeline

I built a proof-of-concept that treats AI code generation like a **software factory**. Instead of one model doing everything, we have specialized roles—just like a real development team:

**[IMAGE 1: Pipeline Flow Diagram]**
*Business Analyst → Product Owner → Architect → Developer → QA → Artifacts*

Each role can use a **different model**. More importantly, each role can automatically fall back to alternative models when the primary one fails.

### How It Actually Works

Let's say you want to build a login feature. You run one command:

```bash
make iteration CONCEPT="User login with email and password"
```

The pipeline then:

**[IMAGE 2: Sequence Diagram with Costs]**
*Shows the flow from User → BA (Ollama - Free) → PO (Ollama - Free) → Architect (Gemini - $0.20) → Developer (GPT-4 - $5.00) → QA (Claude - $1.50)*

1. **Business Analyst** (local Ollama model, free) → generates `requirements.yaml`
2. **Product Owner** (local Ollama, free) → validates requirements
3. **Architect** (Gemini, $0.20) → creates user stories and architecture
4. **Developer** (GPT-4, ~$5) → writes the actual code and tests
5. **QA** (Claude, $1.50) → validates everything, runs tests, writes report

Total cost for a complete feature: **~$7**. Compare that to running everything through GPT-4: **~$25**.

**The key insight:** Use cheap local models for drafts and ideation. Use expensive cloud models only for the critical review and code generation steps.

---

## The 2025 Challenge: Too Many Models, Not Enough Certainty

Here's what the AI landscape looks like right now:

- **OpenAI**: GPT-4 is powerful but expensive ($15/1M tokens). o1 is smarter but costs $60/1M.
- **Anthropic**: Claude 3.5 Sonnet is brilliant at following instructions but has rate limits.
- **Google**: Gemini 2.5 is cheap ($0.30/1M) and fast, but inconsistent with structured output.
- **Open Source**: Qwen 2.5, DeepSeek, Llama 3.3—free and local, but each has quirks.

Every model has different:
- Pricing structures (per token, per request, per month)
- Context window limits (8k to 1M tokens)
- Strengths (coding vs writing vs reasoning)
- API reliability (99.9% uptime vs "it works on my laptop")
- Data privacy rules (cloud vs on-premise only)

Teams waste weeks doing trial-and-error:

> "We tested GPT-4 for a week. Great results but too expensive. Switched to Gemini, saved money but quality dropped. Tried Claude, hit rate limits. Went back to GPT-4. Now we're testing Llama 3.3 locally but prompts need rewriting..."

Sound familiar? This is the problem my pipeline solves.

---

## Automatic Fallback: When Models Fail

Here's where it gets interesting. In my testing, models fail about **12-18% of the time**:

- API timeouts or rate limits
- Malformed JSON output (especially with structured generation)
- Context window exceeded
- Random hallucinations that break downstream tasks

Most teams handle this manually: check logs, retry with different prompt, maybe switch models, waste 2 hours debugging.

The pipeline handles it automatically:

**[IMAGE 3: Fallback Flow Diagram]**
*Shows Story S6 failing with Gemini → Analyzing failure → Scoring backup models → Trying Codex CLI → Fallback to Ollama*

Here's the actual metadata after Story S6 failed with Gemini and retried with Codex:

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

    model_override:
      provider: ollama
      model: qwen2.5-coder:32b
      reason: "Code specialist, runs locally"
      cost_tier: free
      specialties: [code_generation, local_execution]
```

Everything is tracked: which models tried, when they failed, why they failed, what to try next. No manual intervention needed.

---

## Real Numbers from Two Weeks of Testing

I ran this pipeline for 14 days straight, building various features. Here's what happened:

**The Stats:**
- **47** total iterations run
- **$47.30** total cost (all models)
- **8** automatic fallbacks triggered

**Cost breakdown by role:**
- BA + PO (Ollama local): $0.00
- Architect (Gemini): $8.20
- Developer (mix of GPT-4, Codex, Ollama): $32.50
- QA (Claude + local): $6.60

**If I had used only GPT-4 for everything:** ~$380

The fallback system saved my ass twice:
- Day 4: Vertex AI went down for 3 hours. Pipeline switched to Ollama, kept working.
- Day 9: Hit Claude rate limit during QA. Fell back to local Qwen model, finished the job.

---

## How to Try It (5 Minutes)

The whole thing is open source. You can run it locally right now:

```bash
# Clone and setup
git clone https://github.com/krukmat/agnostic-ai-pipeline.git
cd agnostic-ai-pipeline
make setup

# Run a full iteration (strict TDD mode)
make iteration CONCEPT="Todo app with user auth"

# Check the generated artifacts
tree artifacts/iterations/todo-app-iteration/
cat planning/stories.yaml
cat artifacts/iterations/todo-app-iteration/summary.json
```

You'll get:
- `requirements.yaml` - What the BA understood
- `stories.yaml` - User stories with acceptance criteria
- `project/` - Actual generated code
- `artifacts/qa/` - QA test results and coverage report

---

## What This Means for Teams

This isn't a replacement for human developers. It's infrastructure for AI-assisted development that doesn't lock you into one vendor.

What changes:

- **Experimentation is cheap again.** Swap models per role, see what works, measure costs.
- **API outages don't stop you.** Automatic fallback to backup models.
- **Costs are predictable.** Set budgets per role, fail fast if exceeded.
- **Everything is auditable.** Full model_history, diffs, rollbacks.
- **No vendor lock-in.** Switch from OpenAI to Anthropic to local models with a config change.

---

## This Is Part 1 of a Series

This article covers the vision and the problem. Over the next few weeks, I'll document the entire system in detail—how it works, why certain decisions were made, and what I learned building it.

### The Full Series:

**Part 1: The Vision (You Are Here)**
Why vendor lock-in is killing AI projects, and how a software factory approach solves it.

**Part 2: Inside the Fallback System**
How automatic model fallback actually works: failure analysis, specialty scoring, cost optimization, and the `model_history` that tracks everything.

**Part 3: The Multi-Role Pipeline Deep-Dive**
Business Analyst → Architect → Developer → QA. How each role works, what prompts they use, and how they hand off artifacts to each other.

**Part 4: Cost Engineering at Scale**
Real numbers from running 200+ iterations. When to use local vs cloud, how to set budgets per role, and where most teams overspend.

**Part 5: Agent-to-Agent (A2A) Mode**
Running each role as an independent HTTP service. Distributed teams, remote execution, and why this matters for real companies.

**Part 6: Building Your Own Adapters**
How to add new model providers, write validators, hook into CI/CD, and extend the pipeline for your stack.

**Part 7: Lessons from Production**
What broke, what surprised me, and what I'd do differently. The uncomfortable truths about AI-generated code in 2025.

---

Each article will include working code examples, actual cost breakdowns, and things that failed. This isn't vendor documentation—it's a build log.

**Follow along:** Star the repo to get notified when new articles drop, or check the [Discussions](https://github.com/krukmat/agnostic-ai-pipeline/discussions) for early drafts and questions.

⭐ **View on GitHub:** https://github.com/krukmat/agnostic-ai-pipeline

---

## Join the Build

If you've felt this pain, I want to hear from you:

- Fork it. Break it. Tell me what breaks.
- Share your model combinations and cost data.
- PRs welcome: validators, adapters, cost hooks, better docs.
- Benchmarks are gold—especially if you're comparing multiple models.

The goal isn't to build the perfect AI pipeline. It's to build **infrastructure that survives while the AI landscape keeps changing**.

Because the only certainty in 2025? Next week there'll be three new models, two API changes, and another round of "which model should we use?" debates.

Let's build something that doesn't care.

---

*This is an open PoC. All code is available under MIT license.*
*Repository: https://github.com/krukmat/agnostic-ai-pipeline*
*Documentation: https://krukmat.github.io/agnostic-ai-pipeline/*

*Questions? Feedback? Found a bug? Open an issue or reach out. This works best as a community effort.*
