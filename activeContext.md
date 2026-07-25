# PDD Pipeline — Calc Spine, Cost Truth, and Preamble Normalization

**Plan:** `plans/2026-07-25-calc-spine-and-cost-truth-plan.md`
**Status:** PHASE-01 through PHASE-05 COMPLETE — 752 tests passing, working tree clean
**Prior plan:** `plans/2026-07-23-run-real-model-proof-plan.md` (PHASE-01/02 complete: shared judge selection + in-loop redraft fix)

## Phase progress (2026-07-25 plan)

- [x] PHASE-01: Truthful token/cost accounting — `CallRecord` extended with `cache_creation_tokens`/`cache_read_tokens`, `TokenBudget.record()` accepts `cost_usd`, `ClaudeCodeProvider` parses all four token classes + `total_cost_usd`
- [x] PHASE-02: Assistant-preamble normalization — `src/pdd_agent/llm/output_normalize.py`, wired into all four real providers (claude-code, openai, anthropic, ollama)
- [x] PHASE-03: Family-agnostic calc dispatch — `src/pdd_agent/calc/dispatch.py` with `compute_for()`, `PddCalcResult`, `PddCalcResult.to_prompt_block()`, three-branch `_format_calc_injection` in orchestrator, guarded ACM0022-specific consistency check
- [x] PHASE-04: Calc wired into three drafting entry points (`cli.py:_run_draft`, `provider_scorecard.py:_run_one_provider`, `service/main.py:_execute_run`), `pdd-agent calc` subcommand added, `run_review` passes `calc_result` to consistency check
- [x] PHASE-05: Documentation truth-sync — dead `_PROJECT_ALIASES` removed, leaked test artifact deleted, CLAUDE.md plan pointer updated

## Phase progress (2026-07-23 plan)

- [x] PHASE-01: Extract shared judge-selection logic — `src/pdd_agent/llm/judge_selection.py`
- [x] PHASE-02: Fix in-loop redraft judge — `SectionOrchestrator` uses `resolve_judge_provider()`, cached per instance
- [ ] PHASE-03: Run first real-model proof (operational — requires `claude` CLI + real cost)
- [ ] PHASE-04: Capture live Verra registry search API (operational — requires browser devtools)

## Test results

- `python -m pytest -m "not corpus" -q`: **752 passed**, 7 deselected
- `ruff check .`: **All checks passed**
- `ruff format --check .`: **All files formatted**

## Remaining blockers (external, not resolvable this push)

1. No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in the environment — real-provider proof runs require the `claude` CLI (present on reference machine) or API keys.
2. Verra registry's exact search API shape needs browser-devtools inspection to move past manual-download mode.
3. PHASE-06 (real-model proof) and PHASE-04 of the 07-23 plan (registry capture) are operational phases requiring real CLI usage and interactive browser capture respectively.

## Suggested next steps

1. Run `pdd-agent prove --project rice --providers claude-code` with `PDD_MAX_COST_USD=15` to produce the first real-model proof with calc spine active.
2. Capture the Verra registry search API shape via browser devtools.
3. Build the production retrieval index: `pdd-agent build-index --corpus-dir data/corpus/normalized --index-db data/index/corpus.fts.db`.
