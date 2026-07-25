# pdd-agent

Python 3.11+ pipeline that drafts Verra VCS Project Design Documents (WTE/ACM0022, plus VM0051/VM0044/AMS-II.G calc engines) via corpus RAG + rule-based review. See `README.md` for architecture and `activeContext.md` for current status.

## Setup
`pip install -e ".[dev,service,export,llm]"`

## Test
- Full suite: `python -m pytest -m "not corpus" -q`
- Single file: `python -m pytest tests/test_service.py -v`
- Diagnose environment: `pdd-agent doctor`

## Provider constraints
- Tests must never require API keys, network access, or a running Ollama instance — mock all HTTP.
- Demo/noop providers are always the safe default; real providers (`openai`, `anthropic`) are opt-in via `{PROVIDER}_API_KEY` env vars and require `PDD_MAX_COST_USD` to be set.
- `.env` in the invocation directory is loaded automatically (`python-dotenv`); never commit one.

## Artifact contracts
- `reports/review-packages/` — internal reviewer-facing area; placeholder bodies, review notes, assumption-gated content are expected (`noop` provider).
- `reports/demo-packages/` — client-demo area; readable synthetic sample, zero placeholders, strong synthetic disclosure (`demo` provider). Run folders here are committed to git.

## Conventions
- structlog event-style logging (`logger.warning("event_name", key=value)`), Pydantic v2 for `ProjectInput` (`schemas/project_input.py`, top-level package outside `src/`), dataclasses elsewhere. Ruff, line length 100.
- Optional external tools (`gws`, LibreOffice) must degrade gracefully — never a hard requirement.

## Where to look
- Active plan: newest file in `plans/`. Current push: `plans/2026-07-25-calc-spine-and-cost-truth-plan.md`.
- Strategy context: newest brief in `research/`.
