# PDD Next Level — Real-LLM Proof, Judge Loop, Internal Service, Methodology Breadth

**Plan:** `plans/2026-07-05-pdd-next-level-plan.md`
**Status:** PHASE-01 INFRASTRUCTURE COMPLETE — BLOCKED ON API KEYS FOR REAL LLM RUNS
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
- [ ] PHASE-03: FastAPI service + section-review UI + Tinh onboarding
- [ ] PHASE-04: Rice / biochar / cookstove corpora, rules, calc engines
- [ ] PHASE-05: Greenfield proof (Seraphin or substitute) + convergence closure

## Blocker

No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` available in the environment. Real-LLM draft runs and the provider scorecard cannot proceed without them.

## Recent report

- `reports/2026-07-05-phase-01-report.md`
