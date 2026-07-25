# Final Report: Calc Spine, Cost Truth, and Preamble Normalization

**Date:** 2026-07-25
**Plan:** `plans/2026-07-25-calc-spine-and-cost-truth-plan.md`
**Phases implemented:** PHASE-01 through PHASE-05

## Summary

Connected the repo's four quantification engines (ACM0022, VM0051, VM0044, AMS-II.G) to the drafting pipeline they had never been wired into, fixed the `claude-code` provider's token and cost accounting (was under-counting by ~25x and reporting $0.00), added assistant-preamble stripping for all four real providers, and brought documentation back in line with reality.

## Changes by phase

### PHASE-01: Truthful Token and Cost Accounting
- `src/pdd_agent/llm/budget.py`: Added `cache_creation_tokens` and `cache_read_tokens` to `CallRecord`; `total_tokens` now includes cache tokens; `record()` accepts `cost_usd` for authoritative cost; `summary()` includes `total_cache_tokens`
- `src/pdd_agent/llm/claude_code_provider.py`: Parses `cache_creation_input_tokens`, `cache_read_input_tokens`, and `total_cost_usd` from CLI JSON output; passes all five values to budget
- `configs/model_pricing.yaml`: Updated comment to state cost comes from CLI's `total_cost_usd`

### PHASE-02: Assistant-Preamble Normalization
- `src/pdd_agent/llm/output_normalize.py` (new): `strip_assistant_preamble()` with horizontal-rule, leading-lines, and trailing-form stripping
- Wired into all four real providers: `claude_code_provider.py`, `openai_provider.py`, `anthropic_provider.py`, `ollama_provider.py`

### PHASE-03: Family-Agnostic Calc Dispatch
- `src/pdd_agent/calc/dispatch.py` (new): `CalcComponent`, `PddCalcResult`, `compute_for()`, `build_engine_inputs()` — maps ProjectInput to engine for all four methodology families
- `src/pdd_agent/agent/section_orchestrator.py`: Three-branch `_format_calc_injection` dispatch (PddCalcResult non-ACM0022 → `to_prompt_block()`; ACM0022 → existing WTE format verbatim)
- `src/pdd_agent/review/consistency.py`: Guarded ACM0022-specific baseline decomposition check with `hasattr`

### PHASE-04: Wire Calc Into Entry Points + `pdd-agent calc`
- Calc computed and passed to orchestrator in `cli.py:_run_draft`, `provider_scorecard.py:_run_one_provider`, `service/main.py:_execute_run` (gated on provider ≠ demo/noop)
- `run_review` passes `calc_result` to `check_quantitative_consistency`
- New `pdd-agent calc` subcommand with `--input` and `--output` flags
- Dead `_PROJECT_ALIASES` dict removed from `cli.py`

### PHASE-05: Documentation Truth-Sync and Hygiene
- `README.md`: Test count updated (752), Ollama description corrected, Known Gaps fixed, `pdd-agent calc` row added to CLI table
- `CLAUDE.md`: Plan pointer updated to current plan
- `activeContext.md`: Full rewrite for current state
- Leaked test artifact `data/index/__nonexistent_test.fts.db` deleted

## Test results
- **752 passed**, 7 deselected (up from 735 — 17 new tests added)
- New test files: `tests/test_output_normalize.py` (9 tests), `tests/test_calc_dispatch.py` (8 tests)
- `ruff check .`: All checks passed
- `ruff format --check .`: 136 files already formatted

## Operational phases deferred
- PHASE-06 (build production index + run real-model proof): Requires real `claude` CLI usage at ~$6/project
- Plan 2026-07-23 PHASE-03 (run first real-model proof): Same dependency
- Plan 2026-07-23 PHASE-04 (capture Verra registry API): Requires browser devtools inspection
