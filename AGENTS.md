# Repository Guidelines

## Project Structure & Module Organization
The pipeline lives in `scripts/` (orchestrators, role runners, QA tools) and persists generated assets in `artifacts/` and `planning/`. Delivery code sits under `project/`: `backend-fastapi/` (FastAPI services in `app/` and pytest suites in `tests/`) and `web-express/` (Express handlers in `src/` and Jest specs in `tests/`). Keep new modules grouped by feature, mirroring the existing filenames (`feature_catalog.py`, `feature_catalog.js`) so backend and web features stay aligned.

## Build, Test, and Development Commands
Use `make setup` once to create `.venv` and install requirements. `make ba`, `make plan`, `make dev STORY=S#`, and `make qa QA_RUN_TESTS=1` drive the BA→Architect→Dev→QA loop; `make loop` automates the sequence with optional overrides (`MAX_LOOPS`, `ALLOW_NO_TESTS`). Run backend tests directly with `./.venv/bin/pytest -q project/backend-fastapi` and web tests with `npm test -- --passWithNoTests` inside `project/web-express` when a `package.json` is present.
When you need a full product pass from concept to QA in una sola orden, use `make iteration CONCEPT="..." LOOPS=2`; it snapshots deliverables under `artifacts/iterations/`.

## Coding Style & Naming Conventions
Python follows 4-space indentation, snake_case modules, and short, purposeful docstrings; keep FastAPI routers in lowercase files that match route purpose. JavaScript uses ES modules with camelCase functions inside snake_case filenames. Prefer pure functions per feature and mirror API signatures between tiers. Update stubs instead of inlining logic inside routers; add targeted comments only where flow is non-obvious.

## Testing Guidelines
Back-end tests live in `project/backend-fastapi/tests` and default to `pytest`, but you may use `unittest` style classes as seen in `test_story_S*.py`. Name new files `test_<feature>.py`. Front-end specs reside in `project/web-express/tests`; name them `<feature>.test.js` so Jest picks them up. Aim for scenario-level assertions that match the authored story and keep coverage over critical flows (auth, catalog, cart, checkout). When adding tests, run `make qa QA_RUN_TESTS=1` to capture artifacts in `artifacts/qa/`.

## Commit & Pull Request Guidelines
Commits follow Conventional Commit prefixes (`feat:`, `fix:`, `config:`) per existing history; keep the subject under 72 characters and include scope when updating a single area (e.g., `feat(web): add catalog sorting`). Each PR should summarize the story addressed, list affected directories, attach QA output (pytest/Jest logs or `artifacts/qa/last_report.json`), and link the tracked story. Screenshots or terminal snippets are encouraged for UI or CLI-visible changes.

## Agent Workflow Tips
Before running role-specific scripts, ensure `config.yaml` reflects the desired providers via `make set-role` and quality profile via `make set-quality`. Store intermediate plans in `planning/` and never delete generated artifacts; instead, roll forward with additional stories or patches.
