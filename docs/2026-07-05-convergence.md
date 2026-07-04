# PDD Next Level — Convergence Closure

date: 2026-07-05
status: draft

## Summary

This document closes the **PDD Next Level** push (`plans/2026-07-05-pdd-next-level-plan.md`). It records what was built in PHASES 01–04, why PHASE-05's original Seraphin target is blocked, what substitute greenfield project takes its place, and what remains before the service can be handed to Tinh.

## What was built

| Phase | Deliverable | Status |
|---|---|---|
| PHASE-01 | Anthropic provider, cost ceiling, CLI wiring, tests | ✅ Complete (real runs blocked) |
| PHASE-02 | LLM-judge rubric, redraft loop, tiered export gate, CLI `judge` | ✅ Complete |
| PHASE-03 | Local FastAPI service + section-review UI + setup script | ✅ Complete |
| PHASE-04 | Pluggable methodology interface, AMS-II.G / VM0051 / VM0044 calc engines + rules + golden tests | ✅ Complete |

Key capabilities now in `main`:

- `src/pdd_agent/llm/anthropic_provider.py` — mirrors `openai_provider.py`; uses lazy import so tests pass without `anthropic` installed.
- `src/pdd_agent/llm/budget.py` — per-run token/cost budget with hard stop via `PDD_MAX_COST_USD`.
- `src/pdd_agent/review/judge.py` + `rules/verra/judge_rubric.yaml` — deterministic demo scoring; ready to swap in a real LLM-judge model.
- `src/pdd_agent/agent/section_orchestrator.py` — capped auto-redraft loop (max 3), `needs-domain-review` parking.
- `src/pdd_agent/export/docx_export.py` — hard-block on calc contradiction / invalid `[E###]` / unresolved `[MISSING]` in Sections 3–4; watermarked DRAFT otherwise; `--force` override.
- `src/pdd_agent/service/main.py` + templates + `scripts/setup_service.py` — one-command local service for Tinh.
- `src/pdd_agent/calc/methodology.py` interface + `calc/cookstove_amsiig.py`, `calc/rice_vm0051.py`, `calc/biochar_vm0044.py` — new methodology families with golden tests.

## Blockers

1. **Real LLM runs (PHASE-01):** `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are not in the environment or `.env`. All PHASE-01 implementation is done, but the Inegol draft runs and provider scorecard cannot execute.
2. **Seraphin greenfield data (PHASE-05):** externally blocked. Per Grill Me Q-002 fallback, a **Vietnam rice prospect** is the substitute greenfield project.
3. **Registry corpus ingestion (PHASE-04):** `ingest/registry_download.py` is a stub. Real registered-PDD golden numbers are deferred; current golden tests use synthetic-but-documented methodology values.

## Substitute greenfield project: Vietnam rice prospect

Because Seraphin data is not available and the pipeline now has a VM0051 rice calc engine, the greenfield proof will target a **Vietnam rice AWD / dry-seeding project**. This exercises:

- The new **VM0051** track.
- The `ProjectInput` schema extensions for rice hydrology/cultivation.
- The section-review UI on a non-WTE project.
- The FastAPI service intake path with a non-Inegol shape.

Until a concrete prospect is identified, the substitute is documented only; no run artifacts exist.

## Convergence with Tinh

- The service (`scripts/setup_service.py`) is the single shared surface for both tracks.
- The comparison doc `docs/2026-06-15-tinh-track-vs-repo-comparison.md` remains the baseline; this doc supersedes its PHASE-05 status.
- `scripts/compare_codex_vs_pipeline.py` (TASK-05-02) has **not** been run because the Codex-track artifacts were not refreshed in this push and no shared project data is available.
- Tinh onboarding step: run `python scripts/setup_service.py` then `pdd-agent-service`; execute one full review cycle on a demo Inegol run; capture friction in a new issue.

## Test status

```bash
pytest -m "not corpus" -q
# 531 passed, 7 deselected
```

## Remaining work before handoff

1. Provide API keys and re-run PHASE-01 real-LLM Inegol drafts + provider scorecard.
2. Identify a concrete Vietnam rice prospect and run it end-to-end through the service.
3. Build/execute `scripts/compare_codex_vs_pipeline.py` once a shared project exists.
4. Implement `ingest/registry_download.py` to replace synthetic golden-test numbers with registered-PDD values.
5. Update README to remove the "second project" caveat and document the service quickstart.

## Decisions

- Demo/noop providers remain the default everywhere; real-provider gates are opt-in via env vars.
- The 8-week timeline is preserved; this closure snapshot represents the end of the autonomous implementation sprint, not the end of the plan.
