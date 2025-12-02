Exception Swallowing Audit
==========================

Scope: all `except Exception: pass` occurrences in the repository (code and docs), excluding third-party packages under `.venv/`.

Code locations
--------------
- scripts/architect/complexity_classifier.py:96 — classifier load fallback
- scripts/dspy_lm_helper.py:97 — apply `max_tokens` attribute on LM
- scripts/dspy_lm_helper.py:159 — parse `DSPY_MIPRO_MAX_TOKENS`
- scripts/run_architect.py:132 — prompt load/config handling
- scripts/run_architect.py:592 — architect execution branch
- scripts/run_architect.py:602 — architect execution branch
- scripts/run_architect.py:616 — architect execution branch
- scripts/run_qa.py:431 — QA DB log_event best-effort
- scripts/tune_dspy.py:185 — DSPy program traversal
- scripts/tune_dspy.py:190 — DSPy program traversal
- scripts/tune_dspy.py:226 — DSPy program traversal
- scripts/tune_dspy.py:242 — DSPy program traversal
- scripts/utils/db_context.py:43 — DB context fallback

Documentation references
------------------------
- docs/DRIVER_LAYER_EXEC_PLAN.md:236, 240 — BUG-007 describing hidden errors due to `except Exception: pass` blocks.

Notes
-----
- None of the above are third-party; all are in-repo and previously silenced errors. They have been updated to emit warnings and fall back explicitly (Dec 02, 2025).
