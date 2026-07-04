# PDD Next Level — Internal Service, Section-Review UI, Tinh Onboarding

**Plan:** `plans/2026-07-05-pdd-next-level-plan.md`
**Status:** PHASE-03 IMPLEMENTATION COMPLETE
**Last commit:** current working tree

## Locked decisions (Grill Me defaults)

- Q-001: VM0051 (rice), AMS-II.G (cookstoves), VM0044 latest (biochar)
- Q-002: Seraphin externally blocked; name a Vietnam rice substitute by week 6
- Q-003: Tinh uses own install via one-command setup script
- Q-004: Public registry first, check Drive for curated sets
- Q-005: Cheap judge tier for iteration, frontier tier for sign-off runs only

## Phase progress

- [x] PHASE-01 infrastructure: Anthropic provider, CLI wiring, cost ceiling, tests
- [ ] PHASE-01 real runs: OpenAI + Anthropic Inegol drafts and provider scorecard — **BLOCKED on API keys**
- [x] PHASE-02: Judge, redraft loop, tiered export gate, expert sign-off
- [x] PHASE-03: FastAPI service + section-review UI + Tinh onboarding
  - [x] TASK-03-01: Update `pyproject.toml` with FastAPI / Uvicorn / Jinja2 service extras
  - [x] TASK-03-02: Scaffold `src/pdd_agent/service/main.py` with intake, run, section-review, and DOCX export endpoints
  - [x] TASK-03-03: Build server-rendered Jinja2 UI (`dashboard`, `run_detail`, `section_review`, `base`)
  - [x] TASK-03-04: Add service setup script (`scripts/setup_service.py`) and README
  - [x] TASK-03-05: Write `tests/test_service.py` API contract tests using demo provider
  - [x] TASK-03-06: Fix background-run persistence, section-key routing, and retrieval thread-safety issues
  - [x] TASK-03-07: Run `pytest tests/test_service.py -v`
  - [x] TASK-03-08: Run `pytest -m "not corpus" -q` and report result
- [ ] PHASE-04: Rice / biochar / cookstove corpora, rules, calc engines
- [ ] PHASE-05: Greenfield proof (Seraphin or substitute) + convergence closure

## Constraints

- Use only `demo` or `noop` provider in implementation and tests.
- Do NOT require OpenAI/Anthropic API keys.
- Minimal server-rendered Jinja2 UI; no build pipeline.
- Follow existing code style (structlog, Pydantic, dataclasses).

## Blocker

No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` available in the environment. Real-LLM draft runs and the provider scorecard cannot proceed without them. Service uses `demo`/`noop` providers only.

## Test results

- `pytest tests/test_service.py -v`: **12 passed**
- `pytest -m "not corpus" -q`: **531 passed, 7 deselected**

## Changed files

- `pyproject.toml` — added `service` optional dependency group (FastAPI, Uvicorn, Jinja2)
- `src/pdd_agent/service/main.py` — new FastAPI app, route handlers, background execution, persistence redirection
- `src/pdd_agent/service/__init__.py` — package marker
- `src/pdd_agent/service/templates/*.html` — Jinja2 UI templates
- `src/pdd_agent/service/static/style.css` — minimal service styles
- `scripts/setup_service.py` — one-command service setup script
- `src/pdd_agent/service/README.md` — service usage docs
- `tests/test_service.py` — new API contract tests
- `activeContext.md` — status updated

## Review / results

PHASE-03 delivers a runnable local FastAPI service with server-rendered section review and DOCX export, all exercised via `demo` provider tests. Key integration hurdles:

1. **Persistence paths:** `DraftRun.save` and `ReviewStateStore.save`/`load` hardcode paths relative to their own modules. The service monkeypatches them at import time to use the configurable `PDD_SERVICE_RUNS_DIR` directory (`data/runs` under repo root by default).
2. **Retrieval thread-safety:** The SQLite-backed retrieval index binds its connection to the creating thread. Because drafting runs in a FastAPI `BackgroundTask`, corpus retrieval is disabled in the service process by patching retrieval helpers to return empty lists and by setting `inject_corpus_retrieval=False`.
3. **Section-key routing:** Section keys like `1/1.1` contain `/`. FastAPI requires the `:path` converter to capture them correctly.
4. **State-machine self-transitions:** The section-edit endpoint targets `ready-for-human-edit` even when the section is already in that state. The service skips the transition when current and target states match, persisting the edited text and provenance note without error.

The service can be started with:

```bash
python scripts/setup_service.py
pdd-agent-service
```

or, for development:

```bash
uv run --extra service python -m uvicorn pdd_agent.service.main:app --reload
```
