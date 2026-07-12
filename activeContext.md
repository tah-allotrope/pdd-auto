# PDD Reality Gap — Make the Existing Machine Real

**Plan:** `plans/2026-07-12-pdd-reality-gap-plan.md`
**Status:** ALL 6 PHASES COMPLETE — 606 tests passing, working tree clean
**Last commit:** 4ef66c0 — PHASE-06: rice VM0051 end-to-end pilot proves methodology breadth

**Prior push:** `plans/2026-07-05-pdd-next-level-plan.md` (closed 2026-07-05, see `docs/2026-07-05-convergence.md`). That push built the skeleton (Anthropic provider, judge/redraft loop, FastAPI service, calc breadth) but never proved any of it against a real LLM or exercised the service's real code paths. This plan closed that gap.

## Phase progress

- [x] PHASE-01: Repo hygiene and environment foundation — `.env`, `pdd-agent doctor`, docs refresh, two root-cause bugs fixed (packaging, test-isolation leak)
- [x] PHASE-02: Real `OllamaProvider` (was a stub) — live-verified against a real local Ollama instance; full 36-section run infeasible on this CPU-only dev machine (documented with evidence, not a code defect)
- [x] PHASE-03: Service reality fixes — thread-safe `RetrievalIndex`, provider opt-in with cost-ceiling gating, all import-time monkeypatching removed, durable run-status lifecycle
- [x] PHASE-04: Real LLM judge (structured JSON findings, model tiers) + `pdd-agent scorecard` — live-verified with the demo provider; key-gated live run checklisted for OpenAI/Anthropic
- [x] PHASE-05: Verra registry downloader + 3 new family bucket configs — live-verified against the real registry (best-effort real search, clean fallback to documented manual-download mode)
- [x] PHASE-06: Rice VM0051 end-to-end pilot — drafted/reviewed/exported through both CLI and a live service instance; proves methodology-breadth claim; found and fixed 2 real bugs no existing WTE-shaped test had ever caught

## Real bugs found and fixed during this push (not in the original plan — surfaced by actually running things)

1. **Packaging** (PHASE-01): `pdd-agent` console script never worked outside the repo root — `schemas/` wasn't declared in the hatchling wheel build target.
2. **Test-isolation leak** (PHASE-01): full test runs unconditionally dirtied tracked `reports/assumption-burden.md` via three unguarded write call sites.
3. **Latent `NameError`** (PHASE-02): `cli.py`'s provider-config function referenced names only imported in a different function's local scope — would have crashed the first real API key ever set.
4. **Budget mispricing** (PHASE-02): unknown local model names silently priced as GPT-4o instead of $0.
5. **`DemoProvider` methodology-blindness** (PHASE-06): hardcoded WTE-specific narrative text regardless of project methodology — 9/36 sections said "landfill" and "biogas" for a rice project.
6. **`export_run_to_docx()` runs_dir bug** (PHASE-06): ignored any redirected run-persistence directory, always reading the hardcoded default — the service's forced DOCX export 500'd on a real (non-default) round trip. Masked by an existing test that monkeypatched the exact module constant the bug lived in.
7. **`?force=1` gate bypass gap** (PHASE-06): the service's force query param never reached `export_run_to_docx()`'s own hard-block gate, only the separate review-state check.

Full details: `docs/2026-07-12-ollama-shakeout.md`, `docs/2026-07-12-rice-pilot-findings.md`.

## Constraints (carried forward, still binding)

- Tests must never require API keys, network access, or a running Ollama instance — mock all HTTP.
- Demo/noop providers remain the safe default everywhere; real providers are opt-in via env vars.
- Local-only deployment; no cloud/container infra this push.

## Remaining blockers (external, not resolvable this push)

1. No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in the environment — PHASE-04's key-gated live provider scorecard is fully implemented and checklisted (`docs/2026-07-12-provider-scorecard-checklist.md`), ready to run the moment keys land.
2. This dev machine's CPU-only hardware (Intel i5-8250U, no GPU) cannot complete a full 36-section Ollama run within a reasonable time — recommend GPU hardware or a remote Ollama instance for that specific proof; the code path itself is verified correct.
3. The Verra registry's exact search API shape needs browser-devtools inspection to move past manual-download mode — real corpora for the three new families are not yet populated.
4. Seraphin greenfield data remains externally blocked; the rice pilot (PHASE-06) is the completed substitute, but a *real* (non-synthetic) Vietnam rice prospect has not yet been identified.

## Test results

- `python -m pytest -m "not corpus" -q`: **606 passed, 7 deselected** (up from 534 at the start of this push)
- All manual/live verifications documented with concrete evidence in the phase docs listed above.

## Commits (this push)

- `40b308e`..`3fe256f` — PHASE-01 (repo hygiene, `.env`, doctor, docs, 2 bug fixes)
- `6397c7e` — PHASE-02 + PHASE-05 (Ollama provider, registry downloader)
- `a357630` — PHASE-03 + PHASE-04 (service reality, real judge, scorecard)
- `4ef66c0` — PHASE-06 (rice pilot, 2 more bug fixes)

## Suggested next steps

1. When `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` arrive: run the checklist in `docs/2026-07-12-provider-scorecard-checklist.md`, pick a default drafting model, get domain-expert sign-off on the resulting Inegol DOCX.
2. Re-run the Ollama full-draft shakeout on GPU-equipped hardware to get a completed (not just verified-correct-under-failure) 36-section local run.
3. Get browser-devtools access to the Verra registry search UI to finish PHASE-05's live corpus download, then swap the rice/biochar/cookstove golden tests from synthetic to registered values.
4. Investigate the bulk-approve-all interaction noted in `docs/2026-07-12-rice-pilot-findings.md` if it recurs during real human use of the section-review UI.
