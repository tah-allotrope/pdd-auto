---
title: "PDD-Auto Next Level: Prove the LLM Path, Then Go Broad"
date: "2026-07-05"
type: "brainstorm"
depth: "standard"
source_request: "Take the pdd-auto project to another level entirely"
slug: "pdd-next-level"
---

# Brainstorm: PDD-Auto Next Level — Prove the LLM Path, Then Go Broad

## Problem & Why Now
<!-- seeds /plan ## Objective -->
The pipeline skeleton is unusually mature — deterministic ACM0022 calc engine (validated against Inegol), corpus RAG (SQLite FTS5/BM25), 5-state review workflow, VCS v4.4 DOCX rendering, provenance discipline — but **the intelligence layer is still simulated**. Every impressive demo result ("36 sections, 0 review flags") comes from the deterministic `noop`/`demo`/`corpus` providers. The OpenAI gpt-4o provider is implemented but has never been run end-to-end; Phase 2 and Phase 3 of the upgrade plan have all task boxes checked but **zero acceptance criteria verified**. Meanwhile the market brief (`research/2026-06-22_carbon-pdd-barriers-automation.md`) documents $100K–400K per PDD, 6–36 month timelines, and zero open-source competitors — a window that won't stay open. The move to "another level" is: make the real-LLM drafting path produce a VVB-desk-review-grade PDD, wrap it in a shared internal service, and simultaneously expand from one methodology to four families.

## Current vs Desired State
<!-- seeds /plan ## Context Snapshot -->
- **Current state:** CLI-only pipeline (`src/pdd_agent/cli.py`, 17 subcommands). Real calc engine for ACM0022 only (`calc/acm0022.py` + CDM tools 03/04/05/06/07/12/14). LLM providers: OpenAI (implemented, unproven), Ollama (local), no Anthropic. Review checks validate structure/numbers/placeholders but not prose faithfulness. Two intake paths (spreadsheet via `phase06/spreadsheet_mapper.py`, document via `ingest/extract.py`). One validated project (Inegol, calc only). External deps: `gws` CLI for Drive, LibreOffice for PDF. ~313 tests. `activeContext.md` contradicts the plan on Phase-3 status.
- **Desired state:** (1) A real-LLM (OpenAI + Anthropic, benchmarked head-to-head) PDD for Inegol that a domain expert judges submittable to a VVB with minor edits, with an LLM-judge quality gate and capped auto-redraft loop; (2) a local FastAPI service + web UI exposing intake upload, run status, section-by-section review (surfacing the existing 5-state machine), and gated DOCX export — shared with Tinh as the converged single track; (3) three new methodology families — **rice cultivation, biochar, cookstoves** — each with corpus, screening rules, and calc engine, built in full-parallel tracks; (4) Seraphin as the greenfield confirmation when its data arrives.
- **Key repo surfaces:** `src/pdd_agent/llm/provider.py` + `openai_provider.py` (add `anthropic_provider.py`), `agent/section_orchestrator.py` (judge + redraft loop), `review/` (new LLM-judge module, tiered export gate), `export/docx_export.py` (gate enforcement), `calc/` (three new engines + shared methodology interface), `rules/verra/` (new family rules), `ingest/` + `retrieval/` (new-family corpora), new `service/` (FastAPI) + web UI, `phase05/benchmark.py` (provider comparison scorecard), `plans/2026-06-22-pdd-pipeline-upgrade-plan.md` (Phase 2–3 acceptance criteria to check off).

## Resolved Decisions
<!-- the grilled Q&A; each one keeps /plan's Grill Me empty -->
- **DEC-001:** Direction is **prove-it-real, then productize** — verify the real LLM drafting path before any product bet; the current demos prove nothing about LLM output.
- **DEC-002:** Success bar = **VVB-desk-review-grade PDD**: a complete real-LLM PDD for a real project that a domain expert (user/Tinh) judges submittable with only minor edits. Checking off Phase 2–3 acceptance criteria happens as a by-product, not as the goal.
- **DEC-003:** **Two-stage validation: Inegol first, then Seraphin.** Inegol proves fidelity fast (data + registered reference PDD + validated calc already in repo); Seraphin proves greenfield capability when its data arrives.
- **DEC-004:** **Add an AnthropicProvider and run both providers head-to-head** on the Inegol draft; the benchmark scorecard (`phase05/benchmark.py`) picks the default. Gives empirical model choice + vendor redundancy.
- **DEC-005:** Quality judged by **LLM-judge rubric + human expert sign-off**: automated per-section scoring against a VVB desk-review rubric (completeness, evidence citation, methodology conformance, no fabricated facts; registered Inegol PDD as reference), then human final pass on the full document.
- **DEC-006:** Judge failures trigger **auto-redraft with capped retries (2–3 per section)**, feeding judge findings back into the section prompt; persistent failures park in the existing `needs-domain-review` state.
- **DEC-007:** **Tiered export gate**: hard-block export only for calc-contradicting numbers, fabricated evidence citations, or unresolved `[MISSING]` in Sections 3–4; everything else exports as a labeled DRAFT with markers in the reviewer appendix.
- **DEC-008:** Product shape = **internal FastAPI service + web preview UI** (intake upload, run status, section review, DOCX download) for the team's own consulting delivery; defer multi-tenant SaaS.
- **DEC-009:** The web UI does **first-class section review**: each section shows state, judge findings, citations, provenance; reviewer approves, edits inline, or sends back for redraft — making the 5-state machine a tracked, sellable audit trail.
- **DEC-010:** Breadth targets are **rice cultivation, biochar, and cookstoves** (user's explicit pick) alongside existing WTE/ACM0022.
- **DEC-011:** **Full parallel tracks**: corpus, screening rules, AND calc engines for all three new families are built simultaneously with the WTE proof (user chose this over staggering; accepted risk: drafting-layer rework churns four tracks).
- **DEC-012:** Timeline **~8 weeks total, modest LLM spend** (low hundreds of $/month; ~$5–20 per full draft+judge+redraft cycle) — WTE/Inegol proof targeted in the first 2–3 weeks.
- **DEC-013:** **Converge with Tinh's track**: the pipeline/service becomes the shared tool; Tinh's curation judgment becomes the expert-sign-off role; `scripts/compare_codex_vs_pipeline.py` serves as the convergence test.
- **DEC-014:** *(implied by DEC-011)* The calc layer gets a **pluggable methodology interface** as part of building three engines in parallel — designing it against four concrete engines at once.
- **DEC-015:** Deployment is **local-only for now**: FastAPI service runs on the user's machines, outputs shared via Drive as today. No VM/container infra this push. (Tension with DEC-013 noted: Tinh needs his own local setup or remote access to the user's instance — see Q-003.)

## Assumptions & Constraints
<!-- seeds /plan ## Assumptions and Constraints -->
- **ASM-001:** OpenAI and Anthropic API keys are (or can be made) available for the drafting runs.
- **ASM-002:** Enough registered Verra PDDs exist publicly for rice, biochar, and cookstove corpora (Verra registry documents are public; ingestion path may need a registry scraper alongside the existing Drive path).
- **ASM-003:** The Inegol registered PDD is a legitimate quality reference for the LLM-judge rubric (fidelity proof, not greenfield proof — that's Seraphin's job).
- **ASM-004:** Tinh is willing to adopt the converged tool and act as expert reviewer.
- **CON-001:** Modest LLM budget — low hundreds of $/month; per-section redraft cap (DEC-006) and token budgets enforce it.
- **CON-002:** Regulation keeps some steps human: third-party validation, stakeholder consultation/FPIC, legal ownership (carried over from the upgrade plan).
- **CON-003:** Local-only deployment (DEC-015) — no cloud infra, auth, or tenancy work this push.
- **CON-004:** ~8-week window; full-parallel breadth (DEC-011) means the plan must define four tracks that don't serialize on one person's attention — heavy subagent/parallel-session use expected.
- **CON-005:** Fragile deps remain (`gws` CLI, LibreOffice, python-docx); the service must degrade gracefully as the CLI already does.

## Approaches Considered
<!-- seeds /plan ## Risks and Alternatives -->
- **Chosen:** Prove the real-LLM path on Inegol with a judge+redraft loop and tiered export gate, wrap in a local internal service with first-class section review, and build rice/biochar/cookstove corpora+rules+calc engines in full parallel — converging both team tracks on one tool within ~8 weeks.
- **ALT-001:** Productize now (SaaS/API first) — rejected: nothing LLM-drafted is proven; product on synthetic output is a credibility trap.
- **ALT-002:** Depth-only (audit quality, stay CLI) — rejected: leaves the market window and team convergence unaddressed.
- **ALT-003:** Stagger new families after the WTE proof (the recommended-but-declined sequencing) — user chose full parallel for speed to coverage; risk of drafting-layer rework churning all tracks is accepted.
- **ALT-004:** Single provider (OpenAI only) — rejected in favor of dual-provider benchmarking for empirical model choice.
- **ALT-005:** Cloud VM deployment — declined for now; local-only keeps infra cost/risk at zero at the price of harder sharing with Tinh.

## Out of Scope
- Multi-tenant SaaS, billing, external users.
- Verra registry API integration (Phase-04 of the upgrade plan stays deferred).
- ARR/VM0047 and landfill-gas ACM0001 families (considered, not picked).
- Cloud/container deployment (revisit after this push).
- Automating regulation-mandated human steps (validation, FPIC, legal ownership).

## Open Questions
<!-- the few that survived; seed /plan ## Grill Me -->
1. **Q-001:** Which exact methodology/version per new family — e.g. rice: VM0051 vs CDM AMS-III.AU; cookstoves: AMS-II.G vs Gold Standard metered; biochar: VM0044 version?
   - **Recommended default:** VM0051 (rice), AMS-II.G (cookstoves), VM0044 (biochar) — the mainstream Verra/CDM picks with the most public PDDs.
   - **Why this matters:** Determines each calc engine's spec, required CDM tools, and which registered PDDs to ingest.
2. **Q-002:** When is Seraphin data expected, and who chases it?
   - **Recommended default:** Treat as externally-blocked; run the greenfield confirmation whenever it lands, without gating the 8-week plan on it.
   - **Why this matters:** It's the only true greenfield proof; if it never arrives, a substitute greenfield project is needed before broad claims.
3. **Q-003:** How does Tinh access the local-only service (DEC-015 vs convergence DEC-013) — his own local install, or remote access (e.g. tunnel) to yours?
   - **Recommended default:** Ship a one-command local setup (scripted install incl. deps) so Tinh runs his own instance; revisit hosting if that proves painful.
   - **Why this matters:** Convergence fails in practice if the shared tool is hard for the second user to reach.
4. **Q-004:** Are rice/biochar/cookstove corpus documents already collected anywhere (e.g. Tinh's Drive), or does ingestion start from the public Verra registry?
   - **Recommended default:** Assume public-registry sourcing; add a small registry-download step to the ingest path.
   - **Why this matters:** Sets whether the corpus track is a day of downloads or a week of scraper work.

## Suggested Next Step
Run `/plan pdd-next-level` to turn this into a multi-phase implementation plan.
