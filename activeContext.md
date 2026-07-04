# PDD Next Level — Internal Service, Section-Review UI, Tinh Onboarding

**Plan:** `plans/2026-07-05-pdd-next-level-plan.md`
**Status:** PHASE-05 CONVERGENCE DOC COMPLETE — awaiting API keys + greenfield prospect
**Last commit:** b3b0f06 — PHASE-05 convergence doc and activeContext closure

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
- [x] PHASE-04: Rice / biochar / cookstove corpora, rules, calc engines (implementation complete; real registry corpus deferred)
- [x] PHASE-05: Convergence documentation and status hygiene (Seraphin blocked; Vietnam rice substitute documented in `docs/2026-07-05-convergence.md`)

## Constraints

- Use only `demo` or `noop` provider in implementation and tests.
- Do NOT require OpenAI/Anthropic API keys.
- Minimal server-rendered Jinja2 UI; no build pipeline.
- Follow existing code style (structlog, Pydantic, dataclasses).

## Blockers

1. No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` available in the environment. Real-LLM draft runs and the provider scorecard cannot proceed without them. Service uses `demo`/`noop` providers only.
2. Seraphin greenfield data is externally blocked; the substitute Vietnam rice prospect is documented but not yet run.
3. Real registered-PDD corpus ingestion (`ingest/registry_download.py`) is a stub; golden tests use synthetic values.

## Test results

- `pytest tests/test_service.py -v`: **12 passed**
- `pytest -m "not corpus" -q`: **534 passed, 7 deselected**

## Changed files

- `pyproject.toml` — added `service` optional dependency group (FastAPI, Uvicorn, Jinja2)
- `src/pdd_agent/llm/anthropic_provider.py` — new Anthropic provider
- `src/pdd_agent/llm/budget.py` — per-run cost ceiling
- `src/pdd_agent/review/judge.py` — new LLM-judge module
- `rules/verra/judge_rubric.yaml` — judge rubric config
- `src/pdd_agent/agent/section_orchestrator.py` — redraft loop and judge integration
- `src/pdd_agent/export/docx_export.py` — tiered export gate
- `src/pdd_agent/cli.py` — `judge` subcommand + provider env wiring
- `src/pdd_agent/service/main.py` — new FastAPI app, route handlers, background execution, persistence redirection
- `src/pdd_agent/service/__init__.py` — package marker
- `src/pdd_agent/service/templates/*.html` — Jinja2 UI templates
- `src/pdd_agent/service/static/style.css` — minimal service styles
- `scripts/setup_service.py` — one-command service setup script
- `src/pdd_agent/service/README.md` — service usage docs
- `src/pdd_agent/calc/methodology.py` — pluggable methodology interface
- `src/pdd_agent/calc/cookstove_amsiig.py`, `rice_vm0051.py`, `biochar_vm0044.py` — new calc engines
- `rules/verra/cookstove_amsiig_rules.yaml`, `rice_vm0051_rules.yaml`, `biochar_vm0044_rules.yaml` — per-family rules
- `tests/test_judge.py`, `tests/test_export_gate.py`, `tests/test_service.py`, `tests/test_cookstove_amsiig.py`, `tests/test_rice_vm0051.py`, `tests/test_biochar_vm0044.py` — new/updated tests
- `docs/2026-07-05-convergence.md` — PHASE-05 convergence closure doc
- `activeContext.md` — status updated

## Review / results

PHASE-01 through PHASE-04 implementation is complete in code and tests; PHASE-05 is closed out with documentation because the greenfield data is externally blocked.

- **PHASE-01:** Anthropic provider mirrors OpenAI provider structure; per-run cost ceiling enforces `PDD_MAX_COST_USD`. Real-LLM runs are blocked on API keys.
- **PHASE-02:** Judge rubric, deterministic demo judge, capped redraft loop, and tiered export gate are wired into the orchestrator and exporter.
- **PHASE-03:** FastAPI service with server-rendered section review and DOCX export runs locally; key integration hurdles were persistence-path redirection, SQLite retrieval thread-safety (corpus retrieval disabled in service), `/:path` section-key routing, and state-machine self-transitions.
- **PHASE-04:** Pluggable methodology interface added; ACM0022 remains green; AMS-II.G, VM0051, and VM0044 calc engines + rules + golden tests added.
- **PHASE-05:** Convergence doc written with Seraphin blocked and Vietnam rice prospect named as substitute; `compare_codex_vs_pipeline.py` not run for lack of a shared project.

The service can be started with:

```bash
python scripts/setup_service.py
pdd-agent-service
```

or, for development:

```bash
uv run --extra service python -m uvicorn pdd_agent.service.main:app --reload
```
