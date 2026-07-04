---
title: "PDD Next Level: Real-LLM Proof, Judge Loop, Internal Service, Methodology Breadth"
date: "2026-07-05"
status: "draft"
request: "pdd-next-level (from research/2026-07-05_pdd-next-level-brainstorm.md)"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-05_pdd-next-level-brainstorm.md"
  - "research/2026-06-22_carbon-pdd-barriers-automation.md"
  - "research/2026-06-22_pdd-pipeline-upgrade-brainstorm.md"
---

# Plan: PDD Next Level — Real-LLM Proof, Judge Loop, Internal Service, Methodology Breadth

## Objective
Produce a VVB-desk-review-grade PDD for Inegol using real LLM drafting (OpenAI gpt-4o and a new Anthropic provider, benchmarked head-to-head), gated by an LLM-judge + capped auto-redraft loop and a tiered export gate; wrap the pipeline in a local FastAPI service with first-class section review shared with Tinh; and in parallel build corpus, screening rules, and calc engines for three new methodology families (rice, biochar, cookstoves). Target: ~8 weeks, modest LLM spend, WTE proof in the first 2–3 weeks.

## Context Snapshot
- **Current state:** Mature CLI pipeline (`src/pdd_agent/cli.py`, 17 subcommands) with a validated ACM0022 calc engine (`calc/acm0022.py` + CDM tools 03/04/05/06/07/12/14), SQLite FTS5/BM25 corpus RAG (`retrieval/`), 5-state per-section review workflow (`review/states.py`), structural review checks (`review/checks.py`, `consistency.py`, `tbd_tracker.py`), and VCS v4.4 DOCX export (`export/docx_export.py`). **All demo output to date is synthetic** — the registry (`llm/provider.py:get_provider_registry`) auto-registers only `noop`/`demo`/`corpus`; `OpenAIProvider` is implemented but never run end-to-end; no Anthropic provider exists. Upgrade-plan Phases 2–3 have tasks checked but zero acceptance criteria verified.
- **Desired state:** (1) Real-LLM Inegol PDD judged submittable by expert sign-off, with Phase 2–3 acceptance criteria checked off as a by-product; (2) LLM-judge rubric + auto-redraft (2–3 retries cap) + tiered export gate wired into the orchestrator; (3) local FastAPI service + web UI (intake upload, run status, section review/approve/redraft, gated DOCX download) used by both team tracks; (4) rice/biochar/cookstove corpora, screening rules, and calc engines behind a pluggable methodology interface; (5) Seraphin greenfield run when data arrives.
- **Key repo surfaces:** `src/pdd_agent/llm/provider.py` (registry, `BaseProvider`, `ModelConfig`, `configure_provider`), `llm/openai_provider.py` (template for the Anthropic provider), `llm/budget.py`, `agent/section_orchestrator.py` (`draft_section`, `run`, `run_review` — insertion point for judge/redraft), `review/` (new `judge.py`, gate logic), `export/docx_export.py` (gate enforcement), `calc/` (new engines + interface), `domain/methodology_screen.py` + `rules/verra/wte_methodology_rules.yaml` (new family rules), `ingest/` + `retrieval/index.py` (new corpora), `phase05/benchmark.py` (provider comparison), `prompts/section_draft_v2.md` (judge feedback injection), `plans/2026-06-22-pdd-pipeline-upgrade-plan.md` (acceptance criteria), `activeContext.md` (status hygiene).
- **Out of scope:** Multi-tenant SaaS, billing, external users; Verra registry API (stays deferred); ARR/landfill-gas families; cloud/container deployment; automating regulation-mandated human steps (validation, FPIC, legal ownership).

## Research Inputs
- `research/2026-07-05_pdd-next-level-brainstorm.md` — Source of all 15 DEC-* decisions; fixes direction (prove-then-productize), success bar (VVB-desk-review-grade), providers (dual, benchmarked), judge/redraft/gate design, product shape (local service + section-review UI), breadth targets (rice/biochar/cookstoves, full parallel), timeline (~8 weeks), and convergence with Tinh's track.
- `research/2026-06-22_carbon-pdd-barriers-automation.md` — Market urgency ($100K–400K per PDD, zero open-source competitors) justifies the aggressive parallel breadth; also names cookstoves/rice as high-volume segments, supporting corpus availability assumptions.
- `research/2026-06-22_pdd-pipeline-upgrade-brainstorm.md` — Prior DEC-004 (OpenAI first), DEC-007 (top-k corpus injection), DEC-011 (web preview aspiration) carried forward; this plan supersedes its sequencing.

## Assumptions and Constraints
- **ASM-001:** OpenAI and Anthropic API keys are available (or obtainable within days) for drafting runs.
- **ASM-002:** Public Verra registry provides enough registered PDDs for rice/biochar/cookstove corpora; ingestion may need a registry-download step alongside the existing `gws` Drive path.
- **ASM-003:** The registered Inegol PDD (in `ref/` and corpus) is a valid quality reference for the judge rubric; greenfield capability is proven later on Seraphin.
- **ASM-004:** Tinh adopts the converged tool and serves as expert reviewer (sign-off role).
- **CON-001:** Modest LLM budget (low hundreds $/month); ~$5–20 per full draft+judge+redraft cycle; enforced via `llm/budget.py` token budgets and the redraft cap.
- **CON-002:** Regulation keeps validation, stakeholder consultation/FPIC, and legal ownership human.
- **CON-003:** Local-only deployment — no cloud infra, auth hardening, or tenancy work.
- **CON-004:** ~8-week window with full-parallel breadth; the four workstreams must not serialize on one person — breadth tracks are structured for parallel agent execution.
- **CON-005:** Fragile deps (`gws` CLI, LibreOffice, python-docx) remain; service must degrade gracefully like the CLI does.
- **DEC-001..015:** All fifteen decisions in the brainstorm are fixed inputs to this plan (dual providers, judge+capped redraft, tiered gate, section-review UI, rice/biochar/cookstoves in full parallel, local-only, converge with Tinh).

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Real-LLM drafting proven: Anthropic provider + dual-provider Inegol runs + benchmark | None | `llm/anthropic_provider.py`, two full Inegol draft runs, provider scorecard, default model chosen |
| PHASE-02 | Quality machinery: LLM-judge, capped auto-redraft, tiered export gate; expert sign-off on Inegol | PHASE-01 | `review/judge.py`, orchestrator redraft loop, gated export, signed-off Inegol PDD, Phase 2–3 acceptance checked |
| PHASE-03 | Local FastAPI service + web UI with first-class section review | PHASE-02 (judge states) | `service/` app, section-review UI, one-command setup for Tinh |
| PHASE-04 | Methodology breadth: rice/biochar/cookstove corpora, rules, calc engines behind a pluggable interface | None (parallel with 01–03; judge integration needs PHASE-02) | 3 corpora + screening rules + calc engines, `calc/methodology.py` interface |
| PHASE-05 | Greenfield confirmation (Seraphin) + convergence closure | PHASE-02; external data | Seraphin PDD run, convergence test vs Codex track, status hygiene |

## Detailed Phases

### PHASE-01 - Prove the Real-LLM Drafting Path
**Goal**
Run the full Inegol PDD draft through real LLMs — the existing OpenAI provider and a new Anthropic provider — and pick the default model from an empirical head-to-head scorecard.

**Tasks**
- [ ] TASK-01-01: Write failing tests for `AnthropicProvider` (mirror `tests/` coverage of `openai_provider.py`: client init, retry/backoff, token/cost tracking, `DraftSection` contract with provenance markers preserved).
- [ ] TASK-01-02: Implement `src/pdd_agent/llm/anthropic_provider.py` subclassing `BaseProvider` (model default `claude-sonnet-5`, configurable to `claude-opus-4-8`), mirroring `openai_provider.py` structure; register in `configure_provider()` in `llm/provider.py`.
- [ ] TASK-01-03: Add `anthropic` provider choice to CLI `draft` / `run-vietnam-pdd` arguments in `src/pdd_agent/cli.py`; wire API keys via env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) into `ModelConfig`.
- [ ] TASK-01-04: Verify token-budget enforcement (`llm/budget.py`) applies to both providers; add per-run cost ceiling with hard stop and clear log line.
- [ ] TASK-01-05: Run the full Inegol draft (all sections) with `--provider openai` and `--provider anthropic`; persist both runs under `data/runs/` with cost/token telemetry.
- [ ] TASK-01-06: Extend `phase05/benchmark.py` to compare two draft runs against the registered Inegol reference (coverage, grounding/citation density, review-flag burden, cost, latency); emit `reports/provider-scorecard.md`.
- [ ] TASK-01-07: Pick the default drafting model from the scorecard; record decision + rationale in the plan file and `configs/`.

**Files / Surfaces**
- `src/pdd_agent/llm/anthropic_provider.py` - new provider (greenfield).
- `src/pdd_agent/llm/provider.py` - register `anthropic` in `configure_provider()`.
- `src/pdd_agent/llm/openai_provider.py` - template; verify it actually runs (first real execution).
- `src/pdd_agent/llm/budget.py` - cost ceiling.
- `src/pdd_agent/cli.py` - provider flag plumbing.
- `src/pdd_agent/phase05/benchmark.py` - two-run comparison mode.
- `tests/` - new provider tests (TDD: red before implementation).

**Dependencies**
- OpenAI + Anthropic API keys (ASM-001).

**Exit Criteria**
- [ ] Two complete real-LLM Inegol draft runs exist in `data/runs/` with all sections drafted as real prose (no `[PLACEHOLDER]`), evidence citations present, and Section 4 values matching `calc/acm0022.py` output.
- [ ] `reports/provider-scorecard.md` exists and names a default model with rationale.
- [ ] Total spend for the phase ≤ $50 in API costs.
- [ ] All new and existing tests pass (`pytest`).

**Phase Risks**
- **RISK-01-01:** The never-run OpenAI provider fails on first real execution (auth, response parsing, prompt-length). Mitigation: smoke-test on one section before full runs; fix before scaling.
- **RISK-01-02:** Real LLM output ignores the anti-hallucination markers / evidence-ID discipline in `prompts/section_draft_v2.md`. Mitigation: treat as prompt iteration inside this phase; the judge (PHASE-02) is the systematic backstop.

### PHASE-02 - Judge, Redraft Loop, Tiered Gate, Expert Sign-off
**Goal**
Turn structural QA into prose-faithfulness QA: an LLM-judge scores each section against a VVB desk-review rubric, failures auto-redraft (capped), export is tiered-gated, and a human expert signs off the Inegol PDD — the VVB-desk-review-grade proof (DEC-002).

**Tasks**
- [ ] TASK-02-01: Define the judge rubric as config (`rules/verra/judge_rubric.yaml`): completeness vs section schema, evidence-citation validity (cited `[E###]` IDs must exist in the evidence registry), methodology conformance, no fabricated facts (spot-check against `ProjectInput` + calc results), marker hygiene.
- [ ] TASK-02-02: Write failing tests for `review/judge.py` (rubric loading, per-section scoring output shape, deterministic failure categories: `critical` vs `advisory`).
- [ ] TASK-02-03: Implement `src/pdd_agent/review/judge.py`: LLM-judge callable via the provider registry (judge model configurable, default = cheaper tier, e.g. `gpt-4o-mini`/`claude-haiku-4-5-20251001`), scoring each `DraftSection` against the rubric with the registered Inegol PDD as reference when available.
- [ ] TASK-02-04: Add the redraft loop to `agent/section_orchestrator.py:draft_section`: on judge failure, re-prompt with judge findings appended, max 2–3 attempts (configurable), then transition the section to `needs-domain-review` in `review/states.py`. Record attempts + costs on the `DraftRun`.
- [ ] TASK-02-05: Implement the tiered export gate in `export/docx_export.py` (or a pre-export check in `review/`): hard-block on (a) numbers contradicting `calc` results per `review/consistency.py`, (b) citations to nonexistent evidence IDs, (c) unresolved `[MISSING]` in Sections 3–4; everything else exports as watermarked DRAFT with markers in the reviewer appendix. Add `--force` escape hatch that logs an override.
- [ ] TASK-02-06: Add CLI `judge` subcommand (run judge standalone on an existing run) and integrate judge into the `draft` flow behind `--judge/--no-judge`.
- [ ] TASK-02-07: Run the full loop on Inegol with the default model from PHASE-01; iterate prompts/rubric until the judge pass-rate stabilizes.
- [ ] TASK-02-08: Expert review: deliver the gated DOCX to the user + Tinh via the existing `export/review_package.py`; collect sign-off or itemized defects; iterate once if needed.
- [ ] TASK-02-09: Check off the Phase-2/3 acceptance criteria in `plans/2026-06-22-pdd-pipeline-upgrade-plan.md` that this proof satisfies; reconcile `activeContext.md` status.

**Files / Surfaces**
- `src/pdd_agent/review/judge.py` - new LLM-judge module.
- `rules/verra/judge_rubric.yaml` - new rubric config.
- `src/pdd_agent/agent/section_orchestrator.py` - redraft loop in `draft_section`; attempt/cost accounting on `DraftRun`.
- `src/pdd_agent/review/states.py` - park judge-failed sections in `needs-domain-review`.
- `src/pdd_agent/export/docx_export.py`, `review/consistency.py` - tiered gate enforcement.
- `src/pdd_agent/cli.py` - `judge` subcommand + `--judge` flag.
- `prompts/` - new `judge_section.md`, redraft-feedback prompt fragment.
- `plans/2026-06-22-pdd-pipeline-upgrade-plan.md`, `activeContext.md` - acceptance/status hygiene.

**Dependencies**
- PHASE-01 (default model chosen; real drafting works).

**Exit Criteria**
- [ ] Judge scores every section of an Inegol run; redraft loop demonstrably fixes at least one flagged section automatically; persistent failures land in `needs-domain-review`.
- [ ] Export hard-blocks a run seeded with a calc-contradicting number and a fabricated citation (test fixture), and exports a DRAFT with advisory markers otherwise.
- [ ] **Expert sign-off recorded: Inegol PDD judged submittable to a VVB with only minor edits** (DEC-002 — the plan's headline exit).
- [ ] Phase-2/3 acceptance boxes in the upgrade plan updated to reflect verified reality.

**Phase Risks**
- **RISK-02-01:** Judge gaming — redrafts optimize for the rubric, not quality. Mitigation: judge model ≠ drafting model; expert sign-off is the final bar; rubric spot-checks facts against `ProjectInput`/calc, not style.
- **RISK-02-02:** Cost blowout from judge+redraft multiplication. Mitigation: cheap judge tier, retry cap, per-run cost ceiling from TASK-01-04.
- **RISK-02-03:** Expert finds systemic prose failures (not per-section). Mitigation: capture as rubric additions; one bounded iteration loop, then re-scope rather than churn.

### PHASE-03 - Local Service + Section-Review Web UI
**Goal**
Wrap the pipeline in a local FastAPI service with a web UI that makes the 5-state review machine first-class: upload intake, watch runs, review/approve/edit/redraft sections, download gated DOCX. One-command setup so Tinh can run his own instance (DEC-013/015).

**Tasks**
- [ ] TASK-03-01: Scaffold `src/pdd_agent/service/` FastAPI app: routes for intake upload (spreadsheet/document → existing `phase06/spreadsheet_mapper.py` / `ingest/extract.py`), run creation/status (wrapping `SectionOrchestrator.run`), section listing with state/judge findings/provenance, and gated DOCX download.
- [ ] TASK-03-02: Run execution in a background worker (FastAPI `BackgroundTasks` or a simple thread + run-state polling from `data/runs/`); no external queue.
- [ ] TASK-03-03: Section review endpoints: approve, inline edit (persisted as human-edit provenance on the section), send-back-for-redraft (re-invokes the PHASE-02 loop for that section); all transitions through `review/states.py`.
- [ ] TASK-03-04: Minimal web UI (server-rendered templates or a small static SPA — keep self-contained, no build pipeline if avoidable): run dashboard, per-section review screen showing state badge, judge findings, evidence citations, provenance, and text diff after edits.
- [ ] TASK-03-05: One-command setup script (`scripts/setup_service.py` or `make serve`): venv, deps, optional-dep checks (LibreOffice, `gws`), env-key validation, launch on localhost. Document in `README`.
- [ ] TASK-03-06: Tests: API contract tests with the `demo` provider (no API cost); state-transition tests through the endpoints.
- [ ] TASK-03-07: Onboard Tinh: he runs the setup on his machine, executes one full Inegol review cycle through the UI; capture friction as issues.

**Files / Surfaces**
- `src/pdd_agent/service/` - new FastAPI app + templates/static.
- `src/pdd_agent/review/states.py` - reused as the API's state backbone (inspect for any needed transition additions, e.g. human-edit event).
- `src/pdd_agent/phase06/spreadsheet_mapper.py`, `ingest/extract.py` - intake reuse.
- `scripts/` - setup script.
- `pyproject.toml`/`requirements` - add `fastapi`, `uvicorn`.

**Dependencies**
- PHASE-02 (judge findings and gate states are what the UI surfaces). UI skeleton can start earlier against `demo`-provider runs.

**Exit Criteria**
- [ ] Full cycle through the UI on localhost: upload Inegol intake → run → review sections → approve/edit/redraft → download gated DOCX.
- [ ] Tinh completes one review cycle on his own instance (ASM-004); friction list captured.
- [ ] Service degrades gracefully with LibreOffice/`gws` absent (DOCX-only, no upload), matching CLI behavior.

**Phase Risks**
- **RISK-03-01:** UI scope creep. Mitigation: review screen is the only rich page; everything else is a list + buttons; defer polish until after PHASE-05.
- **RISK-03-02:** Local-only blocks Tinh (Windows/deps friction). Mitigation: setup script tested on a clean machine; fallback = screen-share review sessions on the user's instance; revisit hosting (Q-003) if friction persists.

### PHASE-04 - Methodology Breadth: Rice, Biochar, Cookstoves (Parallel Tracks)
**Goal**
Extend the pipeline from WTE-only to four families. Per DEC-011 this runs **in parallel** with PHASES 01–03 (corpus and rules work is independent; calc engines integrate with the judge machinery once PHASE-02 lands). Structured as three independent tracks sharing common groundwork, each executable by a separate agent/session.

**Tasks**
Common groundwork:
- [ ] TASK-04-01: Extract a pluggable methodology interface `src/pdd_agent/calc/methodology.py` (protocol: inputs schema fragment, `baseline/project/leakage/net` computation, per-parameter provenance, required-monitoring params) by refactoring `calc/acm0022.py` behind it without behavior change (existing 313 tests stay green).
- [ ] TASK-04-02: Add a public-registry corpus source: `ingest/registry_download.py` fetching registered PDD PDFs from the Verra registry for a given methodology, feeding the existing `normalize.py` → `bucket.py` → `retrieval/index.py` chain (per-family index or family-tagged corpus).
- [ ] TASK-04-03: Generalize `rules/verra/` layout to per-family rule files; extend `domain/methodology_screen.py` to load multiple families.
- [ ] TASK-04-04: Extend `schemas/project_input.py` with per-family input extensions (rice hydrology/cultivation params, biochar feedstock/pyrolysis params, cookstove fleet/fuel params) without breaking the WTE contract.

Per-family tracks (each: corpus → rules → calc engine → golden test):
- [ ] TASK-04-05: **Cookstoves** (default AMS-II.G, pending Q-001): ingest ≥8 registered PDDs; screening rules; calc engine (fuel savings × fNRB × EF) + tests validated against one registered PDD's published numbers.
- [ ] TASK-04-06: **Rice** (default VM0051, pending Q-001): ingest ≥8 registered PDDs; screening rules; calc engine (baseline CH4 from flooded rice, project AWD/dry-seeding reductions) + golden test vs a registered PDD.
- [ ] TASK-04-07: **Biochar** (default VM0044, pending Q-001): ingest ≥6 registered PDDs; screening rules; calc engine (feedstock → stable carbon, permanence factors) + golden test vs a registered PDD.
- [ ] TASK-04-08: For each family, run one end-to-end draft with the default model + judge (post-PHASE-02) on a synthetic-but-plausible `ProjectInput`; benchmark scorecard per family.

**Files / Surfaces**
- `src/pdd_agent/calc/methodology.py` - new interface; `calc/acm0022.py` refactored behind it.
- `src/pdd_agent/calc/{cookstove_amsiig,rice_vm0051,biochar_vm0044}.py` - new engines (names track Q-001).
- `src/pdd_agent/ingest/registry_download.py` - new corpus source.
- `rules/verra/` - per-family rules YAMLs; `domain/methodology_screen.py`, `domain/methodology_rules.py` - multi-family loading.
- `schemas/project_input.py`, `schemas/pdd_section_schema.yaml` - family extensions.
- `tests/` - interface regression + per-family golden tests.

**Dependencies**
- TASK-04-01..04 precede the per-family tracks; per-family tracks are mutually independent (parallel agents).
- TASK-04-08 needs PHASE-02 (judge) and PHASE-01 (default model).

**Exit Criteria**
- [ ] ACM0022 runs unchanged behind the new interface (all existing tests green).
- [ ] Each family: indexed corpus, screening rules resolving correctly, calc engine with a golden test matching a registered PDD's published emission numbers within tolerance.
- [ ] One judged end-to-end draft per family with a scorecard.

**Phase Risks**
- **RISK-04-01:** Full-parallel churn — drafting-layer changes from PHASE-02 ripple into three tracks (accepted in DEC-011/ALT-003). Mitigation: per-family tracks touch calc/rules/corpus only; drafting integration is confined to TASK-04-08 at the end.
- **RISK-04-02:** Calc engines are each a PHASE-1-sized effort; three in 8 weeks is the plan's biggest schedule risk. Mitigation: cookstoves first (simplest); golden-test scope limited to one reference project per family; cut biochar first if the window compresses.
- **RISK-04-03:** Registry sourcing harder than assumed (ASM-002/Q-004). Mitigation: manual download of the first N PDFs unblocks each track while the downloader is built.

### PHASE-05 - Greenfield Proof + Convergence Closure
**Goal**
Confirm greenfield capability on Seraphin when its data arrives, close the convergence with Tinh's track, and leave status/docs consistent.

**Tasks**
- [ ] TASK-05-01: When Seraphin data lands: intake via `ingest/extract.py` (document path) or spreadsheet mapper, full draft+judge+gate run, expert sign-off pass (same bar as Inegol).
- [ ] TASK-05-02: Run `scripts/compare_codex_vs_pipeline.py` on a shared project as the convergence test (DEC-013); record results in `docs/`.
- [ ] TASK-05-03: Retire or archive the parallel Codex-track artifacts in agreement with Tinh; update `docs/2026-06-15-tinh-track-vs-repo-comparison.md` with a convergence conclusion.
- [ ] TASK-05-04: Status hygiene: reconcile `activeContext.md`, README claims ("second project" caveat), remove stray `tmp_wte_model.xlsx`; final `/report`-style summary of the 8-week push.

**Files / Surfaces**
- `scripts/compare_codex_vs_pipeline.py` - convergence test.
- `docs/`, `activeContext.md`, `README` - closure documentation.

**Dependencies**
- PHASE-02 (machinery); Seraphin data (external — do not gate other phases on it; Q-002).

**Exit Criteria**
- [ ] Seraphin (or substitute greenfield project, per Q-002 fallback) PDD passes expert sign-off.
- [ ] Convergence test recorded; both users working through the shared service.
- [ ] No status contradictions between plan files, `activeContext.md`, and README.

**Phase Risks**
- **RISK-05-01:** Seraphin data never arrives. Mitigation: Q-002 fallback — pick a substitute greenfield project by week 6 so the greenfield claim doesn't slip indefinitely.

## Verification Strategy
- **TEST-001:** `pytest` green at every phase boundary; new modules follow red/green TDD (provider, judge, gate, methodology interface, per-family engines each get failing tests first).
- **TEST-002:** Golden tests: ACM0022 regression behind the new interface; one registered-PDD numeric golden test per new family (PHASE-04 exit).
- **TEST-003:** Gate fixture test: a seeded run with a calc-contradicting number and fabricated citation must hard-block export (TASK-02-05).
- **MANUAL-001:** Expert sign-off on the Inegol PDD (PHASE-02) and the greenfield PDD (PHASE-05) — the plan's two headline acceptance events.
- **MANUAL-002:** Tinh completes a full review cycle on his own service instance (PHASE-03 exit).
- **OBS-001:** Per-run cost/token telemetry on every real-LLM run (`DraftRun` + logs); monthly spend tracked against CON-001; redraft-attempt counts monitored for judge-loop pathology.
- **OBS-002:** `reports/provider-scorecard.md` and per-family scorecards from `phase05/benchmark.py` as the durable quality record.

## Risks and Alternatives
- **RISK-001:** The 8-week window with full-parallel breadth (DEC-011) is aggressive; the WTE proof is the critical path and must not be starved by breadth work. Mitigation: PHASES 01–02 get priority attention weeks 1–3; breadth tracks run as separate agent sessions; drop order if compressed: biochar → rice → (cookstoves last to cut).
- **RISK-002:** Real LLM quality may be materially below the corpus-provider illusion, requiring prompt/RAG rework that ripples everywhere. Mitigation: discovered in week 1 (PHASE-01) by design, before service and breadth investment locks in.
- **ALT-001:** Staggered breadth after the WTE proof (originally recommended) — declined by user in DEC-011 for speed to coverage; the accepted churn risk is contained via RISK-04-01 mitigation.
- **ALT-002:** Cloud VM deployment for shared access — declined (DEC-015); local-only with a setup script; revisit if Q-003 friction materializes.
- **ALT-003:** Single-provider (OpenAI-only) proof — declined (DEC-004); dual-provider benchmark is cheap (~1 provider class) and de-risks vendor choice for the product phase.

## Grill Me
1. **Q-001:** Exact methodology/version per family — rice: VM0051 vs CDM AMS-III.AU; cookstoves: AMS-II.G vs Gold Standard metered; biochar: VM0044 (which version)?
   - **Recommended default:** VM0051 (rice), AMS-II.G (cookstoves), VM0044 latest (biochar).
   - **Why this matters:** Fixes each calc engine's spec, required tools, and which registered PDDs to ingest (TASK-04-05..07).
   - **If answered differently:** Engine module names, rule files, and corpus queries change; effort roughly similar except GS-metered cookstoves, which adds a metering data model.
2. **Q-002:** Seraphin data — expected when, and who chases it? Acceptable substitute greenfield project if it slips past week 6?
   - **Recommended default:** Treat as externally blocked; name a substitute (e.g. a Vietnam rice prospect, which would also exercise the new rice track) by week 6.
   - **Why this matters:** PHASE-05's greenfield claim; without it the proof stays fidelity-only.
   - **If answered differently:** If data is imminent, PHASE-05 schedules normally; if never, the substitute becomes the acceptance project.
3. **Q-003:** How does Tinh access the local-only service — his own install (setup script) or remote access to your instance?
   - **Recommended default:** Own install via the one-command setup (TASK-03-05).
   - **Why this matters:** PHASE-03's convergence exit criterion depends on it.
   - **If answered differently:** Remote access adds a tunnel + basic auth task to PHASE-03 and relaxes the setup-script bar.
4. **Q-004:** Do rice/biochar/cookstove corpus documents already exist in Tinh's Drive folders, or does sourcing start from the public Verra registry?
   - **Recommended default:** Public registry (build TASK-04-02 downloader); check Drive first — if curated sets exist, the downloader shrinks to a nice-to-have.
   - **Why this matters:** Whether the corpus track is days or a week per family.
   - **If answered differently:** Drive-sourced corpora reuse the existing `gws` ingest path unchanged; TASK-04-02 drops.
5. **Q-005:** Judge model budget posture — is a cheaper judge tier (gpt-4o-mini / Haiku) acceptable, or should the judge run on the frontier tier for the two acceptance runs?
   - **Recommended default:** Cheap tier for iteration; frontier-tier judge for the two sign-off runs only.
   - **Why this matters:** Judge cost dominates the redraft loop at scale (CON-001).
   - **If answered differently:** Frontier-everywhere multiplies per-run cost ~3–5×; budget ceiling in TASK-01-04 must rise.

## Suggested Next Step
Answer the Grill Me questions (defaults are safe to proceed on), then begin PHASE-01 with TASK-01-01 (failing AnthropicProvider tests) — and in parallel, kick off PHASE-04 common groundwork (TASK-04-01 interface refactor + Q-004 corpus check) in separate sessions.
