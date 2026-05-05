---
title: "Corpus-Driven PDD Generation to Reduce Synthetic Gibberish"
date: "2026-05-05"
status: "draft"
request: "use existing pdd docs as input for a new word doc to reduce the % of gibberish given that wte projects both old and new will have similar writing in certain section, evoke plan skill for multiphase then git commit push"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-22_wte-pdd-ingestion.md"
  - "plans/2026-05-01-soc-son-client-demo-output-plan.md"
---

# Plan: Corpus-Driven PDD Generation to Reduce Synthetic Gibberish

## Objective
Replace the current high-synthetic DemoProvider output with corpus-driven section drafting that reuses and adapts real paragraph text from the 13 existing VCS waste-to-energy PDDs. The goal is to reduce the synthetic/gibberish percentage from ~90-100% to under 30% by treating the corpus as a source of reusable prose, not just structural examples.

## Context Snapshot
- **Current state:** The latest demo DOCX (`reports/demo-packages/soc-son-like-waste-to-power-demonstration-project/run-20260504104319-5e2a70/`) is 100% synthetic — every section body is produced by `DemoProvider._demo_section_text()`, which emits deterministic hardcoded prose. The BM25 retrieval system (`src/pdd_agent/retrieval/`) indexes 13 real VCS PDDs but only injects up to 3 snippets as "structural guides" into prompts. The corpus text itself never flows into the final document.
- **Desired state:** A new `CorpusProvider` or section assembler retrieves full paragraphs from the most relevant corpus document(s) for each section, substitutes project-specific facts (names, locations, capacities, numbers), and emits adapted real text. The result reads like a real PDD draft because it is built from real PDD prose, not synthetic templates.
- **Key repo surfaces:** `src/pdd_agent/llm/provider.py`, `src/pdd_agent/agent/section_orchestrator.py`, `src/pdd_agent/retrieval/search.py`, `src/pdd_agent/retrieval/index.py`, `data/corpus/normalized/`, `schemas/pdd_section_schema.yaml`, `prompts/section_draft.md`, `export/docx_export.py`, `scripts/run_demo.py`.
- **Out of scope:** Wiring a commercial LLM API for free-form generation; removing the synthetic/demo disclosure from the cover page; turning the output into an audit-ready final filing; expanding the corpus beyond the current 13 WTE PDDs.

## Research Inputs
- `research/2026-04-22_wte-pdd-ingestion.md` — Confirms the 13 VCS PDDs are structurally parseable and methodology-bucketed. BM25 retrieval is already operational. The risk is not ingestion but evidence integrity; corpus-driven drafting preserves traceability by construction.
- `plans/2026-05-01-soc-son-client-demo-output-plan.md` — The Phase 03-04 demo path produced readable synthetic prose but explicitly avoided real corpus reuse. This plan extends that work by replacing the DemoProvider with a corpus-driven provider, keeping the same export and disclosure contract.

## Assumptions and Constraints
- **ASM-001:** WTE PDDs share enough common prose (methodology applicability, baseline scenario descriptions, monitoring plan structures) that paragraph-level reuse across projects is feasible without free-form generation.
- **ASM-002:** The normalized corpus JSONs (`data/corpus/normalized/*.norm.json`) contain sufficient paragraph-level text to support direct reuse for at least the BOILERPLATE, NARRATIVE, and METHODOLOGY_DEPENDENT content classes.
- **ASM-003:** Project-specific facts (name, location, capacity, emission numbers) can be substituted into corpus text via deterministic string replacement or lightweight templating without requiring an LLM.
- **CON-001:** The corpus does not contain prose for every possible new project configuration; some sections will still require synthetic fill when corpus coverage is sparse.
- **CON-002:** The output must remain explicitly labeled as a synthetic demo/adaptation because facts have been substituted into text originally written for other projects.
- **DEC-001:** The corpus-driven path should build on the existing `demo` artifact contract (`reports/demo-packages/`) rather than the review-gated workflow.
- **DEC-002:** BM25 retrieval should remain the primary matching mechanism; embeddings or vector search are out of scope for this iteration.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Analyze corpus coverage per section and identify reusable vs sparse sections | None | Corpus coverage map, section-level reuse feasibility report |
| PHASE-02 | Build paragraph-level retrieval and a CorpusProvider that adapts real text with fact substitution | PHASE-01 | CorpusProvider, fact-substitution engine, prompt update |
| PHASE-03 | Integrate CorpusProvider into the demo workflow, export pipeline, and CLI | PHASE-02 | Updated run_demo.py, CLI flag, demo-package generation |
| PHASE-04 | Verify gibberish reduction end-to-end and measure synthetic-vs-corpus word ratios | PHASE-03 | Fresh demo DOCX, coverage metrics, passing tests |
| PHASE-05 | Harden edge cases (sparse sections, multi-document blending, fallback to DemoProvider) | PHASE-04 | Fallback rules, blended-section strategy, updated docs |

## Detailed Phases

### PHASE-01 - Corpus Coverage And Reuse Feasibility Mapping
**Goal**
Determine which sections have rich, reusable paragraph text across the 13 corpus PDDs and which sections are too sparse or project-specific to support corpus-driven drafting.

**Tasks**
- [ ] TASK-01-01: Write a corpus coverage analyzer script that, for each canonical section/sub-section in `schemas/pdd_section_schema.yaml`, counts how many corpus documents have non-trivial text (>200 chars) for that exact section.
- [ ] TASK-01-02: For each section, compute average word count and character count across corpus hits, flagging sections with <2 documents or <100 chars average as "sparse."
- [ ] TASK-01-03: Manually sample 2-3 high-coverage sections and 2-3 low-coverage sections to confirm the analyzer's output matches human judgment of reuse quality.
- [ ] TASK-01-04: Produce a machine-readable coverage map JSON (`data/corpus/section_coverage_map.json`) that the orchestrator can consult at runtime to decide whether to use corpus-driven drafting or fallback to DemoProvider for a given section.
- [ ] TASK-01-05: Update the plan's risk register if any critical section (e.g. 3.5 Additionality, 4.1 Baseline Emissions) is flagged as sparse.

**Files / Surfaces**
- `data/corpus/normalized/*.norm.json` — Source text for analysis.
- `schemas/pdd_section_schema.yaml` — Canonical section list to iterate.
- `src/pdd_agent/retrieval/search.py` — Existing query interface; may need a bulk-extraction helper.
- `src/pdd_agent/ingest/normalize.py` — Understand how text blocks map to headings/sections.
- `data/corpus/section_coverage_map.json` — New runtime artifact.

**Dependencies**
- None

**Exit Criteria**
- [ ] Coverage map exists and accurately reflects which sections have enough real text to support corpus-driven drafting.
- [ ] Sparse sections are explicitly identified so PHASE-02 can build fallback logic.
- [ ] A human spot-check confirms the analyzer's judgments.

**Phase Risks**
- **RISK-01-01:** The normalized JSONs may not preserve paragraph boundaries well enough for clean extraction; mitigate by inspecting raw normalized output before automating.
- **RISK-01-02:** Section heading drift across corpus documents may cause under-counting; mitigate by using the existing heading-drift map in the schema and fuzzy heading matching.

### PHASE-02 - CorpusProvider And Fact Substitution Engine
**Goal**
Build a provider that returns adapted real corpus text instead of synthetic prose, using deterministic fact substitution to make the text project-specific.

**Tasks**
- [ ] TASK-02-01: Add a failing test that proves the current DemoProvider is 100% synthetic and that a future CorpusProvider must emit text containing a corpus citation.
- [ ] TASK-02-02: Implement `CorpusProvider` in `src/pdd_agent/llm/provider.py` (or a new `corpus_provider.py`) that:
  a. Accepts the same `draft_section` interface as `BaseProvider`.
  b. Uses `get_examples_for_section(section_id, sub_section_id, k=3)` to retrieve the top corpus matches.
  c. Selects the longest/highest-quality corpus text block as the primary source.
  d. Returns the full text (not a 1000-char snippet) with provenance markers.
- [ ] TASK-02-03: Build a lightweight fact-substitution engine (`src/pdd_agent/drafting/fact_substitution.py`) that takes corpus text + `ProjectInput` + assumption register and replaces:
  - Old project name → new project name
  - Old city/country → new city/country
  - Old capacity → new capacity (when numerically close or explicitly marked)
  - Old methodology IDs → new methodology IDs
  - Old proponent name → new proponent name
  - Old dates → new dates
  The engine must label any substitution it makes with `[ADAPTED FROM CORPUS: ...]` so the provenance chain is intact.
- [ ] TASK-02-04: Add a `content_class`-aware routing rule:
  - BOILERPLATE and NARRATIVE → prefer corpus text with substitution.
  - METHODOLOGY_DEPENDENT and QUANTITATIVE → prefer corpus text if methodology IDs match; otherwise fallback to DemoProvider + strong synthetic label.
  - FACTUAL → skip corpus; use ProjectInput directly.
- [ ] TASK-02-05: Update `SectionOrchestrator._build_prompt()` so that when the provider is `corpus`, the prompt instructs the provider to perform substitution rather than generation. (The prompt change may be minimal if the substitution engine is provider-internal.)
- [ ] TASK-02-06: Ensure the coverage map from PHASE-01 is consulted at runtime; if a section is marked sparse, `CorpusProvider` automatically falls back to `DemoProvider` for that section.

**Files / Surfaces**
- `src/pdd_agent/llm/provider.py` — New `CorpusProvider` registration.
- `src/pdd_agent/drafting/fact_substitution.py` — New substitution engine.
- `src/pdd_agent/agent/section_orchestrator.py` — Provider-aware routing and prompt adjustments.
- `src/pdd_agent/retrieval/search.py` — May need a full-text retrieval method that returns complete paragraph blocks rather than highlighted snippets.
- `data/corpus/section_coverage_map.json` — Runtime input for fallback decisions.

**Dependencies**
- PHASE-01 coverage map.

**Exit Criteria**
- [ ] `CorpusProvider` exists, is registered, and passes unit tests for known sections.
- [ ] Fact substitution engine correctly replaces project names, locations, and capacities in sample corpus paragraphs.
- [ ] Sparse sections automatically fallback to DemoProvider without crashing.
- [ ] Every adapted paragraph carries a corpus provenance marker.

**Phase Risks**
- **RISK-02-01:** Blind string substitution may corrupt numbers or methodology references; mitigate by requiring explicit substitution rules and rejecting ambiguous matches.
- **RISK-02-02:** Corpus text may contain site-specific evidence (e.g. "the EIA was approved by the Hanoi DEP in 2023") that cannot be safely substituted; mitigate by flagging sentences with regulatory or date references for human review rather than blind adaptation.

### PHASE-03 - Integration Into Demo Workflow And Export
**Goal**
Wire the CorpusProvider into the demo generation pipeline so operators can produce a reduced-gibberish DOCX with one command.

**Tasks**
- [ ] TASK-03-01: Add `--provider corpus` CLI argument to `scripts/run_demo.py` and `src/pdd_agent/cli.py`.
- [ ] TASK-03-02: Update `run_demo_benchmark()` or the equivalent demo runner to instantiate `CorpusProvider` when requested, load the coverage map, and run the full orchestrator.
- [ ] TASK-03-03: Ensure the DOCX export (`export/docx_export.py`) renders corpus-adapted text correctly, including the `[ADAPTED FROM CORPUS: ...]` provenance footers.
- [ ] TASK-03-04: Add a "corpus coverage summary" to the demo package: a short table showing, per section, whether the text was corpus-driven or synthetic-fallback, plus the source document name.
- [ ] TASK-03-05: Run a full demo workflow with `--provider corpus` and publish the output to `reports/demo-packages/<project-slug>/run-<timestamp>-<hash>/` plus `latest.docx`.

**Files / Surfaces**
- `scripts/run_demo.py` — CLI and runner updates.
- `src/pdd_agent/cli.py` — Argument parsing.
- `src/pdd_agent/phase05/benchmark.py` — Demo runner integration.
- `src/pdd_agent/export/docx_export.py` — Render adapted text and coverage summary.
- `src/pdd_agent/export/review_package.py` — Package assembly.

**Dependencies**
- PHASE-02 CorpusProvider and substitution engine.

**Exit Criteria**
- [ ] `python scripts/run_demo.py --provider corpus` completes end to end and publishes a DOCX.
- [ ] The published DOCX contains real adapted corpus text in high-coverage sections.
- [ ] Sparse sections still contain readable synthetic fallback text.
- [ ] The coverage summary table is visible in the DOCX appendix.

**Phase Risks**
- **RISK-03-01:** If the export pipeline expects Markdown and the corpus text contains raw formatting, rendering may break; mitigate by normalizing corpus text to plain Markdown during substitution.
- **RISK-03-02:** The coverage summary may expose internal document names the operator does not want shared; mitigate by using document slugs, not full filenames, and keeping the summary in an appendix rather than the cover.

### PHASE-04 - End-to-End Verification And Gibberish Measurement
**Goal**
Prove the new pipeline reduces synthetic content and measure exactly how much.

**Tasks**
- [ ] TASK-04-01: Build a `gibberish_scorer.py` script that analyzes a DraftRun or DOCX and classifies each paragraph as:
  - `corpus_adapted` — contains `[ADAPTED FROM CORPUS` or `[CORPUS:` marker
  - `synthetic` — contains `[SYNTHETIC` or `demo_curated` or was produced by DemoProvider
  - `placeholder` — contains `[PLACEHOLDER`
  The scorer outputs word counts and percentages per category.
- [ ] TASK-04-02: Run the scorer against:
  a. The old DemoProvider output (baseline: ~100% synthetic).
  b. The new CorpusProvider output (target: <30% synthetic).
- [ ] TASK-04-03: Add automated tests (`tests/test_corpus_provider.py`, `tests/test_fact_substitution.py`) covering substitution accuracy, fallback behavior, and provenance marker presence.
- [ ] TASK-04-04: Manually inspect the generated DOCX: open it, read Sections 1.1, 3.4, 4.1, and 5.2, and confirm they read like real PDD prose rather than synthetic templates.
- [ ] TASK-04-05: Update `reports/demo-scorecard.md` or create `reports/corpus-driven-scorecard.md` with the before/after metrics.

**Files / Surfaces**
- `scripts/gibberish_scorer.py` — New measurement tool.
- `tests/test_corpus_provider.py` — Provider unit tests.
- `tests/test_fact_substitution.py` — Substitution engine unit tests.
- `reports/demo-scorecard.md` — Updated with corpus-driven metrics.

**Dependencies**
- PHASE-03 integrated pipeline.

**Exit Criteria**
- [ ] Automated tests pass for CorpusProvider, substitution, and fallback behavior.
- [ ] Gibberish scorer shows synthetic content below 30% of total words in the new output.
- [ ] Manual inspection confirms at least 3 high-coverage sections read as adapted real prose.
- [ ] A scorecard document captures the before/after comparison.

**Phase Risks**
- **RISK-04-01:** The 30% synthetic target may be unreachable if too many sections are sparse; mitigate by defining an explicit acceptance band (e.g. 30-50%) and documenting which sections must improve in a future corpus expansion.
- **RISK-04-02:** Word-count-based scoring may misclassify short synthetic headers or captions; mitigate by scoring only paragraph bodies, not metadata tables or captions.

### PHASE-05 - Edge Cases, Fallbacks, And Documentation Hardening
**Goal**
Make the corpus-driven path production-stable by handling multi-document blending, ambiguous substitutions, and clear operator documentation.

**Tasks**
- [ ] TASK-05-01: Implement multi-document blending for sections where 2-3 corpus documents each have partial coverage: concatenate the best paragraphs from each with clear provenance transitions.
- [ ] TASK-05-02: Add a "substitution ambiguity" review flag: if the fact-substitution engine encounters a value it cannot safely replace (e.g. an embedded regulatory reference), it emits a `[REVIEW: substitution ambiguity]` marker instead of guessing.
- [ ] TASK-05-03: Harden the fallback logic so that a missing coverage map, a failed retrieval query, or an empty corpus result always degrades gracefully to DemoProvider with a logged warning.
- [ ] TASK-05-04: Update `README.md` with a new section explaining the corpus-driven demo path, how to run it, and how to interpret the coverage summary.
- [ ] TASK-05-05: Update `AGENTS.md` or `docs/` with the fact-substitution rules so future agents know which fields are safe to substitute and which require review flags.

**Files / Surfaces**
- `src/pdd_agent/drafting/fact_substitution.py` — Ambiguity detection and multi-source blending.
- `src/pdd_agent/llm/provider.py` — Fallback hardening.
- `README.md` — Operator documentation.
- `docs/` or `AGENTS.md` — Agent-facing substitution rules.

**Dependencies**
- PHASE-04 verification and metrics.

**Exit Criteria**
- [ ] The corpus-driven pipeline never crashes due to missing data or failed retrieval; it always falls back safely.
- [ ] Ambiguous substitutions are flagged for review rather than silently corrupted.
- [ ] Documentation allows a new engineer to run `--provider corpus` without reading the source code.

**Phase Risks**
- **RISK-05-01:** Multi-document blending may produce disjointed prose; mitigate by requiring paragraph-level transitions and only blending when the content class is BOILERPLATE or NARRATIVE.
- **RISK-05-02:** Over-hardening may mask real data-quality issues; mitigate by logging every fallback and ambiguity flag so they remain auditable.

## Verification Strategy
- **TEST-001:** `tests/test_corpus_provider.py` — assert that CorpusProvider returns text containing `[CORPUS:` or `[ADAPTED FROM CORPUS:` for high-coverage sections and falls back to synthetic for sparse sections.
- **TEST-002:** `tests/test_fact_substitution.py` — assert that project name, location, capacity, and methodology IDs are substituted correctly; assert that ambiguous regulatory references trigger review flags.
- **TEST-003:** `scripts/gibberish_scorer.py` — run against both old and new demo artifacts and emit a JSON report with word counts per category.
- **MANUAL-001:** Run `python scripts/run_demo.py --provider corpus`, open the DOCX, and read Sections 1.1, 3.4, 4.1, 5.2. Confirm they contain real PDD prose adapted to the Soc Son-like project.
- **MANUAL-002:** Inspect the coverage summary appendix and confirm it accurately lists which sections were corpus-driven vs synthetic.
- **OBS-001:** Log `provider=corpus`, `corpus_coverage_pct`, `substitution_count`, `ambiguity_flag_count`, and `fallback_count` for every run.

## Risks and Alternatives
- **RISK-001:** Corpus text may be too project-specific to adapt cleanly; mitigate by starting with BOILERPLATE and NARRATIVE sections, which are the most generic.
- **RISK-002:** Operators may expect the new output to be audit-ready because it reads like a real PDD; mitigate by keeping the cover-page synthetic disclosure and adding an explicit "adapted from corpus" statement in the appendix.
- **ALT-001:** Use a local LLM (Ollama) to paraphrase corpus text instead of deterministic substitution; not chosen because the Ollama provider is currently a stub and paraphrasing would lose explicit provenance traceability.
- **ALT-002:** Build vector embeddings for semantic paragraph retrieval; not chosen because BM25 already works, the corpus is small (13 docs), and embeddings add complexity without clear gain for exact section matching.
- **ALT-003:** Manually curate a "best of" paragraph library from the corpus; not chosen because it is labor-intensive and the existing normalized JSONs already contain the paragraphs.

## Grill Me
1. **Q-001:** Should the corpus-driven provider replace DemoProvider entirely, or should both remain available side by side?
   - **Recommended default:** Both remain available side by side (`--provider demo` vs `--provider corpus`).
   - **Why this matters:** It determines whether the old synthetic path is deprecated or preserved as a fallback. Preserving it is safer for comparison and debugging.
   - **If answered differently:** Replacing DemoProvider simplifies the codebase but removes the ability to quickly generate a deterministic baseline for comparison.

2. **Q-002:** For fact substitution, should the system use deterministic regex replacement, or should it call an LLM to rewrite corpus paragraphs with new facts?
   - **Recommended default:** Deterministic regex replacement for this iteration.
   - **Why this matters:** LLM rewriting is more fluent but loses explicit provenance and introduces hallucination risk. Deterministic substitution is traceable and testable.
   - **If answered differently:** Using an LLM would require wiring a real provider, adding cost/latency, and building a hallucination-detection layer.

3. **Q-003:** If a corpus paragraph contains a site-specific regulatory reference that cannot be safely substituted (e.g. "approved by the Turkish Ministry in 2019"), should the system drop that sentence, flag it, or leave it as-is?
   - **Recommended default:** Flag it with `[REVIEW: substitution ambiguity]` and keep the sentence so a human can decide.
   - **Why this matters:** Dropping sentences may remove important context; leaving them unchanged introduces factual errors about the wrong jurisdiction.
   - **If answered differently:** Dropping would produce cleaner but potentially incomplete text; leaving as-is would reduce the perceived gibberish percentage but at the cost of factual accuracy.

4. **Q-004:** What is the acceptable synthetic percentage if the 30% target is not reachable after the first implementation pass?
   - **Recommended default:** Accept 30-50% as a Phase 04 pass, with a concrete Phase 05 plan to drive it lower.
   - **Why this matters:** It sets the stop-loss for the first implementation cycle and prevents infinite refinement.
   - **If answered differently:** A stricter target (<20%) may require corpus expansion or LLM rewriting, pushing scope beyond this plan.

## Suggested Next Step
Run PHASE-01 to produce the section coverage map. Once the map identifies which sections are rich in reusable text, proceed to PHASE-02 to build the CorpusProvider and substitution engine.