# PDD Next Level — Real-LLM Proof, Judge Loop, Internal Service, Methodology Breadth

**Plan:** `plans/2026-07-05-pdd-next-level-plan.md`
**Status:** PHASE-02 IMPLEMENTATION IN PROGRESS
**Last commit:** 2517a3b — PHASE-01 WIP: Anthropic provider, cost ceiling, CLI wiring

## Locked decisions (Grill Me defaults)

- Q-001: VM0051 (rice), AMS-II.G (cookstoves), VM0044 latest (biochar)
- Q-002: Seraphin externally blocked; name a Vietnam rice substitute by week 6
- Q-003: Tinh uses own install via one-command setup script
- Q-004: Public registry first, check Drive for curated sets
- Q-005: Cheap judge tier for iteration, frontier tier for sign-off runs only

## Phase progress

- [x] PHASE-01 infrastructure: Anthropic provider, CLI wiring, cost ceiling, tests
- [ ] PHASE-01 real runs: OpenAI + Anthropic Inegol drafts and provider scorecard — **BLOCKED on API keys**
- [ ] PHASE-02: Judge, redraft loop, tiered export gate, expert sign-off
  - [ ] TASK-02-01: `rules/verra/judge_rubric.yaml`
  - [ ] TASK-02-02: Tests for `review/judge.py`
  - [ ] TASK-02-03: Implement `src/pdd_agent/review/judge.py`
  - [ ] TASK-02-04: Redraft loop in `agent/section_orchestrator.py`
  - [ ] TASK-02-05: Tiered export gate in `export/docx_export.py`
  - [ ] TASK-02-06: CLI `judge` subcommand + `--judge/--no-judge` in `draft`
  - [ ] TASK-02-07: Run targeted test suite and report
- [ ] PHASE-03: FastAPI service + section-review UI + Tinh onboarding
- [ ] PHASE-04: Rice / biochar / cookstove corpora, rules, calc engines
- [ ] PHASE-05: Greenfield proof (Seraphin or substitute) + convergence closure

## PHASE-02 tasks (this session)

- [ ] TASK-02-01: Create `rules/verra/judge_rubric.yaml` with VVB desk-review rubric
- [ ] TASK-02-02: Write `tests/test_judge.py` (rubric loading, deterministic scoring, categories)
- [ ] TASK-02-03: Implement `src/pdd_agent/review/judge.py` (`JudgeResult`, `LLMJudge`, provider registry interface)
- [ ] TASK-02-04: Add `max_redraft_attempts` + auto-redraft loop to `SectionOrchestrator.draft_section`; add `redraft_section()`
- [ ] TASK-02-05: Implement `check_export_gate()` and `ExportGateResult` in `export/docx_export.py`; wire `--force` in CLI export
- [ ] TASK-02-06: Add `pdd-agent judge` CLI subcommand and `--judge/--no-judge` flag on `draft`
- [ ] TASK-02-07: Write `tests/test_export_gate.py` and update `tests/test_section_orchestrator.py`
- [ ] TASK-02-08: Run `pytest tests/test_judge.py tests/test_export_gate.py tests/test_section_orchestrator.py -v`
- [ ] TASK-02-09: Run `pytest -m "not corpus" -q` and report result

## Constraints

- Use only `demo` or `noop` provider in implementation and tests.
- Do NOT require OpenAI/Anthropic API keys.
- Follow existing code style (structlog, Pydantic, dataclasses).
- Minimal changes to existing behavior; default judge is OFF in `draft`.

## Blocker

No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` available in the environment. Real-LLM draft runs and the provider scorecard cannot proceed without them. PHASE-02 machinery uses `demo`/`noop` providers only.
