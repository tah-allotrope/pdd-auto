# PHASE-01 Report — Real-LLM Drafting Proof

**Date:** 2026-07-05
**Status:** INFRASTRUCTURE COMPLETE — BLOCKED ON API KEYS FOR REAL RUNS
**Commit:** 2517a3b
**Branch:** main

## What was delivered

- `src/pdd_agent/llm/anthropic_provider.py` — new `AnthropicProvider` subclassing `BaseProvider`:
  - Default model `claude-sonnet-5`, configurable to `claude-opus-4-8`
  - Retry/backoff for rate limits, timeouts, connection errors
  - Token/cost tracking via `TokenBudget.set_budget()`
  - Graceful degradation when `anthropic` package is not installed
  - Preserves `DraftSection` contract and provenance markers
- `tests/test_anthropic_provider.py` — 13 tests mirroring `test_openai_provider.py` coverage, all passing
- `src/pdd_agent/llm/provider.py` — `anthropic` registered in `configure_provider()`
- `src/pdd_agent/cli.py` — API provider env-var wiring and help-text updates:
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` auto-detected
  - Optional model/base_url/max_tokens/temperature via env vars
  - Provider choice `anthropic` surfaced in `draft`, `extract`, `screen`, `benchmark`, `run-vietnam-pdd`
- `src/pdd_agent/llm/budget.py` — per-run cost ceiling (`max_cost_usd`) with hard stop
  - Anthropic model pricing added to default pricing table
  - `summary()` reports `max_cost_usd` and `cost_ceiling_hit`
- `src/pdd_agent/agent/section_orchestrator.py` — reads `PDD_MAX_TOKENS` / `PDD_MAX_COST_USD` env vars, logs budget ceiling at run start and estimated cost at run end
- `pyproject.toml` — added `anthropic>=0.40.0` to `[project.optional-dependencies] llm`

## Test results

```
pytest -m "not corpus" -q
460 passed, 7 deselected
```

New `tests/test_anthropic_provider.py`: 13 passed.

## What is blocked

PHASE-01 exit criteria require **two complete real-LLM Inegol draft runs** (OpenAI + Anthropic), cost telemetry, and a provider scorecard. This requires:

- `OPENAI_API_KEY` — not present in environment or `.env` file
- `ANTHROPIC_API_KEY` — not present in environment or `.env` file
- Optional: `anthropic` package installed (declared in `pyproject.toml[llm]`)

Without API keys, the provider classes can be unit-tested with mocks, but no real API calls can be made and therefore no empirical provider scorecard can be produced.

## Next step to unblock

Provide `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` (e.g., via environment variables or a `.env` file), then re-run PHASE-01 to execute:

```bash
pdd-agent draft --input configs/demo/inegol_project_input.yaml --provider openai --run-id inegol-openai-001
pdd-agent draft --input configs/demo/inegol_project_input.yaml --provider anthropic --run-id inegol-anthropic-001
```

Optionally set spend guardrails:

```bash
export PDD_MAX_COST_USD=50.0
export PDD_MAX_TOKENS=500000
```

## Note on scope

This plan (`plans/2026-07-05-pdd-next-level-plan.md`) is sized for ~8 weeks with parallel tracks and external dependencies (Tinh onboarding, Seraphin data). Code infrastructure for the later phases can be implemented without keys, but the headline acceptance events (real-LLM runs, expert sign-off, Tinh review cycle, greenfield Seraphin proof) cannot be compressed into a single session.
