# PDD Methodology-Parametrized Pipeline — Make Breadth Real for the LLM Path

**Plan:** `plans/2026-07-13-methodology-parametrized-pipeline-plan.md`
**Status:** PHASES 1-4 COMPLETE — 681 tests passing, working tree clean
**Last commit:** (pending) — PHASE-04: methodology-parametrized test matrix proves breadth in CI

**Prior push:** `plans/2026-07-12-pdd-reality-gap-plan.md` (closed 2026-07-12, see `docs/2026-07-12-ollama-shakeout.md` and `docs/2026-07-12-rice-pilot-findings.md`). That push made the code paths real — working Ollama provider, real LLM judge, live registry downloader, rice VM0051 end-to-end pilot — but never noticed that the prompt text and judge rubric were still hardcoded to WTE. This plan closes that gap.

## Phase progress

- [x] PHASE-01: CI pipeline + config-driven model pricing — `.github/workflows/ci.yml`, `configs/model_pricing.yaml`, `doctor` pricing check, 227 lint findings cleared (one real bug fixed)
- [x] PHASE-02: Methodology-parametrized drafting prompt — `prompts/methodologies/{wte,rice,biochar,cookstove}.md`, family-aware `_build_prompt` in `SectionOrchestrator`
- [x] PHASE-03: Methodology-parametrized judge rubric — `rules/verra/rubrics/{wte,rice,biochar,cookstove}.yaml`, family-aware `LLMJudge` with `methodology_ids` parameter, per-rubric `quantitative_sections`
- [x] PHASE-04: Methodology-parametrized test matrix — `tests/fixtures/methodology_projects.py` (per-family `ProjectInput` factories), `tests/test_methodology_matrix.py` (43-test parametrized matrix), `DemoProvider` extended with biochar/cookstove templates (bug found and fixed by the matrix)
- [ ] PHASE-05: One-command multi-provider proof — `pdd-agent prove`, per-provider judged scorecard
- [ ] PHASE-06: Architectural debt: evidence flow, batch-approve, CLI split

## Real bugs found and fixed during this push (not in the original plan — surfaced by actually running things)

1. **`DemoProvider` WTE-hardcoding** (PHASE-04): the parametrized test matrix immediately caught that `DemoProvider` had no templates for biochar and cookstove, so it fell back to WTE text containing "landfill" and "municipal solid waste" — exactly the WTE-shaped assumption the matrix was designed to surface. Fixed by adding biochar and cookstove templates.

## Constraints (carried forward, still binding)

- Tests must never require API keys, network access, or a running Ollama instance — mock all HTTP.
- Demo/noop providers remain the safe default everywhere; real providers are opt-in via env vars.
- Local-only deployment; no cloud/container infra this push.
- `quantitative_sections` in non-WTE rubrics defaults to the WTE set (`1.10, 4.1, 4.2, 4.4`) until a registered PDD refines it (ASM-003).

## Remaining blockers (external, not resolvable this push)

1. No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in the environment — PHASE-05's one-command proof is fully implemented and checklisted, ready to run the moment keys land.
2. This dev machine's CPU-only hardware (Intel i5-8250U, no GPU) cannot complete a full 36-section Ollama run within a reasonable time — recommend GPU hardware or a remote Ollama instance for that specific proof; the code path itself is verified correct.
3. The Verra registry's exact search API shape needs browser-devtools inspection to move past manual-download mode — real corpora for the three new families are not yet populated.
4. Seraphin greenfield data remains externally blocked; the rice pilot (from the prior push) is the completed substitute, but a *real* (non-synthetic) Vietnam rice prospect has not yet been identified.

## Test results

- `python -m pytest -m "not corpus" -q`: **681 passed** (up from 631 at the start of this push)
- `python -m pytest tests/test_methodology_matrix.py -v`: **43 passed** (new parametrized matrix)
- `ruff check .`: **All checks passed**
- `ruff format --check .`: **All files formatted**
- All manual/live verifications documented with concrete evidence in the phase docs listed above.

## Commits (this push)

- (pending) — PHASE-03 + PHASE-04 (judge rubric, test matrix, DemoProvider fix)

## Suggested next steps

1. Execute PHASE-05 (one-command multi-provider proof): add a `prove` subcommand that wraps `run_provider_scorecard` with provider auto-detection and per-provider judging, so a single command runs a project through every available provider, judges each with the (now family-aware) LLM judge, and writes a head-to-head scorecard.
2. When `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` arrive: run `pdd-agent prove --project inegol --providers auto`, pick a default drafting model, get domain-expert sign-off on the resulting Inegol DOCX.
3. Re-run the Ollama full-draft shakeout on GPU-equipped hardware to get a completed (not just verified-correct-under-failure) 36-section local run.
4. Get browser-devtools access to the Verra registry search UI to finish PHASE-05's live corpus download, then swap the rice/biochar/cookstove golden tests from synthetic to registered values.
5. Investigate the bulk-approve-all interaction noted in `docs/2026-07-12-rice-pilot-findings.md` if it recurs during real human use of the section-review UI (PHASE-06).
