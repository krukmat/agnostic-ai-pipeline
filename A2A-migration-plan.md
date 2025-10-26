# A2A Migration Plan

This document captures the implementation blueprint for adopting the Agent-to-Agent (A2A) protocol across the **agnostic-ai-pipeline**, translating the “Resumen del Protocolo A2A (Agent-to-Agent)” guidance into actionable tasks.

---

## Branch Strategy

- Create a dedicated integration branch before starting any work:

- `git checkout -b feature/a2a-migration`

- All A2A-related changes should land on this branch and be merged to `main` only after the full plan is delivered and validated.

---

## Objectives and Scope

- Expose each pipeline role (BA, PO, Architect, Dev, QA, Orchestrator) as an A2A agent.
- Ensure standardised discovery, auth, and JSON-RPC task exchange.
- Preserve current behaviour while enabling multi-agent extensibility.

---

## Assumptions

- Python 3.10+ with local network connectivity.
- Ability to install the A2A SDK (or equivalent) when network access permits.
- Existing role scripts stay as business logic; A2A wraps them.

---

## High-Level Milestones

1. Foundations (SDK, utilities, configuration).
2. Role agents (Agent Cards, endpoints).
3. Orchestration flow (client and task lifecycle).
4. Resilience & security.
5. Documentation & verification.

---

## Detailed Task Breakdown

### Milestone 1 – Foundations
1. Catalogue roles and I/O contracts.
2. Create `a2a/` for shared utilities.
3. Add A2A SDK to `requirements.txt` (when network allows) and refresh the venv.
4. Add `config/a2a_agents.yaml` with per-role endpoint, auth, capabilities, skills.
5. Extend the config loader to provide typed access.
6. Define an A2A error taxonomy matching JSON-RPC codes.

### Milestone 2 – Role Agents
7. For each role:
   - Wrap logic in skill handlers.
   - Declare `AgentSkill` metadata.
   - Instantiate an `AgentCard` (identity, endpoint, capabilities, auth).
   - Serve `.well-known/agent-card.json` via FastAPI/Starlette.
8. Build `a2a/server.py` to register cards/skills, expose JSON-RPC (`message/send`, task state) and optional SSE.
9. Add CLI launchers `scripts/run_<role>_a2a.py`.
10. Standardise artifact serialization (documents, code, tests).

### Milestone 3 – Orchestration Flow
11. Implement `a2a/orchestrator_client.py` to:
    - Discover Agent Cards.
    - Validate skills and cache capabilities.
    - Provide helpers (`send_task(agent, skill, payload)`) issuing JSON-RPC with trace IDs.
12. Refactor the orchestrator to delegate all stage work via the client.
13. Track task lifecycle transitions using agent-supplied IDs.
14. Support streaming responses (when available) and convert to artifacts.
15. Add fallback behaviour for unreachable agents or missing skills.

### Milestone 4 – Resilience & Security
16. Add exponential backoff retries for transient HTTP errors.
17. Record per-task audit logs (agent, payload size, duration, outcome).
18. Scaffold authentication (static bearer tokens, document OAuth/mTLS extensions).
19. Expose health-check endpoints for each agent.

### Milestone 5 – Documentation & Verification
20. Update README with:
    - A2A architecture diagram.
    - Agent startup instructions (`make run-*-agent`).
    - JSON-RPC payload examples per skill.
21. Publish sample Agent Card JSON files for reference/testing.
22. Add smoke tests verifying card retrieval, round-trip success, and error handling.
23. Document operational checklist (startup order, environment variables, port matrix).
24. Outline regression coverage for legacy pathways.
25. Capture roadmap notes (dynamic discovery, third-party agents, advanced security).

---

## Deliverables

- New configuration files and the `a2a/` module.
- A2A-compliant agent servers per role.
- Orchestrator client + updated pipeline flow.
- Documentation (architecture, operations, API usage).
- Interoperability test scripts.

---

## Open Questions

1. Preferred ASGI framework/deployment model.
2. Production authentication requirements.
3. Priority of artifact streaming vs phased rollout.
4. SLA and retry expectations for inter-agent calls.

---

## Next Actions

1. Checkout `feature/a2a-migration`.
2. Stub the `a2a/` package and config loader updates.
3. Implement agents incrementally (start with BA).
4. Validate the A2A orchestration path end-to-end.
5. Harmonise per-role CLIs so that batch and A2A-serve modes are exposed from the same script (replace ad-hoc `run_*_agent.py` wrappers).

---

## Suggested Next Iteration (Priority Order)

1. **Resilience & Monitoring**
   - Add retry/backoff and structured logging in `A2AClient`.
   - Expose `/metrics` or integrate logging for FastAPI apps (Dev/QA particularly).
2. **QA Agent Refinement**
   - Enriquecer el resultado del skill `run_quality_checks` (lista de fallas, rutas afectadas, recomendación).
   - Mapear exit codes a estados comprensibles para el orquestador.
3. **Orchestrator Enhancement**
   - Encadenar Developer y QA dentro del skill `execute_pipeline`, manejando bloqueos o reintentos.
   - Propagar contextos (story ID, retries) y consolidar resultados por etapa.
4. **Security Posture**
   - Definir esquema de autenticación (`authentication.mode` ≠ none) y aplicarlo en server/client.
   - Documentar variables de entorno o tokens requeridos.
5. **Testing & Docs**
   - Crear smoke tests para `run_<role>.py run` y `serve` (uso de `httpx`/`pytest`).
   - Actualizar README con ejemplos de JSON-RPC reales y flujo de orquestador completo.

This plan ensures the pipeline evolves into a modular, interoperable, and standards-based multi-agent system aligned with the A2A specification.
