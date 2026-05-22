---
title: "Demo Corpus Bundle & Test Cleanup"
date: "2026-05-22"
status: "draft"
request: "Sprint 3 implementation for colleague-testable demo: bundle small demo corpus subset for provenance, add degraded-mode warnings, clean up stale test skip guards (GAP-02, GAP-07)"
plan_type: "multi-phase"
research_inputs:
  - "reports/2026-05-22-colleague-demo-gap-analysis.md"
---

# Plan: Demo Corpus Bundle & Test Cleanup

## Objective
Bundle a small demo corpus subset so colleagues see realistic corpus-backed provenance in demo output instead of empty citations, and clean up stale test skip guards so the test suite is self-explanatory on fresh clones. This sprint adds the most depth to the demo experience and polishes the developer onboarding.

## Context Snapshot
- **Current state:** The normalized corpus (18 JSON files) and FTS5 index are gitignored. When demos run without the index, the retrieval layer silently returns empty results (`search.py:112`, `search.py:150`, `search.py:183`). The `DemoProvider` generates deterministic text regardless of retrieval, so demo output is unaffected functionally — but provenance citations in the DOCX are empty. The test suite has 7 skipped tests: 6 in `test_section_parser.py` (corpus-dependent) and 1 in `test_docx_export.py` (python-docx import check). The python-docx skip guard is stale since python-docx is now a core dependency in `pyproject.toml`.
- **Desired state:** A `demo/corpus/` directory contains 2-3 normalized JSON docs (publicly available Verra project descriptions relevant to Soc Son and Inegol). Demo scripts build a temporary FTS5 index from this subset automatically, so provenance citations appear in output. The test suite has clear `@pytest.mark.corpus` markers for corpus-dependent tests, and the stale python-docx skip guard is removed.
- **Key repo surfaces:** `data/corpus/normalized/*.norm.json`, `src/pdd_agent/retrieval/index.py`, `src/pdd_agent/retrieval/search.py`, `src/pdd_agent/agent/section_orchestrator.py`, `tests/test_section_parser.py`, `tests/test_docx_export.py`, `pyproject.toml`
- **Out of scope:** Bundling the full 18-doc corpus (only 2-3 demo-relevant docs). Wiring real LLM providers. Changing the retrieval algorithm.

## Research Inputs
- `reports/2026-05-22-colleague-demo-gap-analysis.md` — Defines GAP-02 (silent degradation without index) and GAP-07 (stale test skips). Notes the retrieval layer's graceful degradation pattern. Identifies IP risk for corpus bundling and recommends only publicly available Verra registry docs.

## Assumptions and Constraints
- **ASM-001:** The Verra VCS project descriptions in the corpus are publicly available on the Verra registry and can be redistributed in normalized (extracted text) form.
- **ASM-002:** 2-3 docs are sufficient for meaningful provenance: one Soc Son-related, one Inegol-related, and optionally one methodology reference.
- **ASM-003:** The demo FTS5 index can be built on-the-fly during demo runs (sub-second for 2-3 docs) rather than pre-built and committed.
- **CON-001:** The bundled corpus must not include any proprietary or client-specific data — only public Verra registry content.
- **CON-002:** Existing corpus-dependent tests in `test_section_parser.py` expect 13 documents; these should continue to skip on fresh clones but pass when the full corpus is available.
- **DEC-001:** Use a `demo/corpus/` directory separate from `data/corpus/normalized/` so the gitignore for the full corpus is undisturbed.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Select and bundle demo corpus subset | None | `demo/corpus/` directory with 2-3 `.norm.json` files |
| PHASE-02 | Add demo index builder and degraded-mode logging | PHASE-01 | Updated `src/pdd_agent/retrieval/index.py`, new `src/pdd_agent/demo_setup.py` |
| PHASE-03 | Wire demo scripts to use demo corpus index | PHASE-02 | Updated `scripts/run_demo.py`, `scripts/run_inegol_demo.py` |
| PHASE-04 | Test cleanup: remove stale skips, add corpus markers | None | Updated `tests/test_section_parser.py`, `tests/test_docx_export.py`, `pyproject.toml` |
| PHASE-05 | Verification and documentation | PHASE-01-04 | Updated `QUICKSTART.md`, `activeContext.md` |

## Detailed Phases

### PHASE-01 — Select and Bundle Demo Corpus Subset
**Goal**
Choose 2-3 normalized corpus documents that provide meaningful retrieval context for both the Soc Son and Inegol demo cases, and commit them under `demo/corpus/`.

**Tasks**
- [ ] TASK-01-01: Review the 18 normalized docs in `data/corpus/normalized/` and select:
  - `VCS_Soc_Son_Project-Description.norm.json` — direct reference for Soc Son demo
  - `VCS_Inegol_Project-Description.norm.json` — direct reference for Inegol demo
  - `VCS_Bergama_Project-Description.norm.json` — Turkish WTE project, provides comparative context for both cases
- [ ] TASK-01-02: Create `demo/corpus/` directory at repo root.
- [ ] TASK-01-03: Copy the 3 selected `.norm.json` files into `demo/corpus/`.
- [ ] TASK-01-04: Verify the files don't contain sensitive information beyond what's publicly available on the Verra registry (project names, locations, methodology parameters, quantification approaches).
- [ ] TASK-01-05: Create `demo/corpus/README.md` explaining: what these files are, where they came from (Verra VCS public registry), why only 3 are included (demo subset), and how to build the full corpus (`pdd-agent ingest`).
- [ ] TASK-01-06: Verify total size of the 3 files is reasonable (each is ~50-200 KB of JSON text).

**Files / Surfaces**
- `demo/corpus/VCS_Soc_Son_Project-Description.norm.json` — New tracked file
- `demo/corpus/VCS_Inegol_Project-Description.norm.json` — New tracked file
- `demo/corpus/VCS_Bergama_Project-Description.norm.json` — New tracked file
- `demo/corpus/README.md` — New file explaining the subset

**Dependencies**
- None

**Exit Criteria**
- [ ] 3 `.norm.json` files exist in `demo/corpus/`
- [ ] Each file is valid JSON with `headings` and `text_blocks` keys
- [ ] Total size is under 1 MB
- [ ] `demo/corpus/README.md` explains provenance and purpose

**Phase Risks**
- **RISK-01-01:** Corpus files may contain extracted text from copyrighted PDFs. Mitigation: Verra VCS project descriptions are public registry documents intended for stakeholder review; normalized text extraction for indexing is transformative use. Add provenance notes in README.

### PHASE-02 — Demo Index Builder and Degraded-Mode Logging
**Goal**
Add the ability to build a temporary FTS5 index from the demo corpus, and add warning logs when the retrieval layer operates without any index.

**Tasks**
- [ ] TASK-02-01: Add a `build_demo_index()` function in a new `src/pdd_agent/demo_setup.py` module that:
  - Locates `demo/corpus/` relative to repo root
  - Creates a temporary FTS5 index at `data/index/demo.fts.db` using `RetrievalIndex.build(normalized_dir=demo_corpus_dir)`
  - Returns the `RetrievalIndex` instance
  - Logs a clear message: "Built demo index from {n} documents in demo/corpus/"
- [ ] TASK-02-02: Add a `pdd-agent demo-setup` CLI command in `src/pdd_agent/cli.py` that calls `build_demo_index()` and prints success.
- [ ] TASK-02-03: Add a warning log in `src/pdd_agent/retrieval/search.py` at each graceful-degradation point (`search()`, `get_examples_for_section()`, `get_section_heading_examples()`) that fires once per session: "Retrieval index not available — demo running without corpus-backed provenance. Run 'pdd-agent demo-setup' to build a demo index."
- [ ] TASK-02-04: Use a module-level flag (`_INDEX_WARNING_SHOWN = False`) to ensure the warning only fires once, not per-section.
- [ ] TASK-02-05: Write a unit test verifying `build_demo_index()` creates a valid FTS5 index from `demo/corpus/` files and that `is_built()` returns True afterward.

**Files / Surfaces**
- `src/pdd_agent/demo_setup.py` — New module with `build_demo_index()`
- `src/pdd_agent/cli.py` — Add `demo-setup` subcommand
- `src/pdd_agent/retrieval/search.py` — Add once-per-session warning at degradation points
- `tests/test_demo_setup.py` — New test file

**Dependencies**
- PHASE-01 (needs `demo/corpus/` files to exist)

**Exit Criteria**
- [ ] `pdd-agent demo-setup` creates `data/index/demo.fts.db` and prints success
- [ ] Running a demo without the index prints a single warning (not per-section)
- [ ] Unit test for `build_demo_index()` passes

**Phase Risks**
- **RISK-02-01:** The demo index path (`demo.fts.db`) may conflict with the production index path (`corpus.fts.db`). Mitigation: use a separate filename; the `RetrievalIndex` constructor accepts a `db_path` parameter.
- **RISK-02-02:** The `get_retrieval_index()` singleton may not pick up the demo index if the production index path doesn't exist. Mitigation: have `build_demo_index()` also set the module-level `_index` singleton, or have demo scripts pass the demo index explicitly.

### PHASE-03 — Wire Demo Scripts to Use Demo Corpus Index
**Goal**
Make both demo scripts automatically use the demo index if available, so provenance citations appear in output without manual setup.

**Tasks**
- [ ] TASK-03-01: In `scripts/run_demo.py`, before calling `run_demo_benchmark()`, check if `data/index/demo.fts.db` exists. If not, and if `demo/corpus/` exists, call `build_demo_index()` automatically. Log: "Auto-building demo index for corpus provenance..."
- [ ] TASK-03-02: In `scripts/run_inegol_demo.py`, add the same auto-build logic before the orchestrator run.
- [ ] TASK-03-03: Ensure the auto-built demo index is used by the `SectionOrchestrator` during the run. This may require updating `get_retrieval_index()` in `src/pdd_agent/retrieval/index.py` to check for `demo.fts.db` as a fallback when `corpus.fts.db` doesn't exist.
- [ ] TASK-03-04: Verify that demo DOCX output now includes non-empty provenance citations when the demo index is available.
- [ ] TASK-03-05: Run both demo scripts and confirm the output DOCX has corpus-backed provenance in at least some sections.

**Files / Surfaces**
- `scripts/run_demo.py` — Add auto-build demo index logic
- `scripts/run_inegol_demo.py` — Add auto-build demo index logic
- `src/pdd_agent/retrieval/index.py` — Add demo index fallback in `get_retrieval_index()`

**Dependencies**
- PHASE-02 (needs `build_demo_index()` to exist)

**Exit Criteria**
- [ ] Running `python scripts/run_demo.py` on a fresh clone with `demo/corpus/` auto-builds the index and produces provenance
- [ ] Running `python scripts/run_inegol_demo.py` also auto-builds and produces provenance
- [ ] When neither index exists and `demo/corpus/` is absent, scripts still work (graceful degradation)

**Phase Risks**
- **RISK-03-01:** Auto-building the index adds ~0.5-1s to demo startup. Mitigation: acceptable for a demo; the index is cached after first build.
- **RISK-03-02:** The `DemoProvider` may not use retrieval results even when available (it generates deterministic text). Mitigation: provenance is still populated in the `DraftSection` metadata even if the text itself is deterministic. The DOCX export uses provenance from section metadata.

### PHASE-04 — Test Cleanup
**Goal**
Remove stale test skip guards and add explicit corpus markers so the test suite is self-explanatory on fresh clones.

**Tasks**
- [ ] TASK-04-01: In `tests/test_docx_export.py`, remove the `python-docx` import skip guards at lines ~140 and ~159. Since `python-docx>=1.1.0` is a core dependency in `pyproject.toml`, these guards are stale.
- [ ] TASK-04-02: In `tests/test_section_parser.py`, add `@pytest.mark.corpus` decorator to all tests in `TestParseCorpus` and `TestCorpusSectionIndex` classes that check for `corpus_dir.exists()`.
- [ ] TASK-04-03: Register the `corpus` marker in `pyproject.toml` under `[tool.pytest.ini_options]`:
  ```toml
  markers = [
      "corpus: tests that require the normalized corpus in data/corpus/normalized/",
  ]
  ```
- [ ] TASK-04-04: Update the skip logic in corpus-dependent tests to use the marker + runtime check pattern:
  ```python
  @pytest.mark.corpus
  def test_parses_all_documents(self, corpus_dir):
      if not corpus_dir.exists():
          pytest.skip("Normalized corpus not available")
  ```
- [ ] TASK-04-05: Add a note in `QUICKSTART.md` (or update the existing one from Sprint 1): "Run `pytest -m 'not corpus'` to skip corpus-dependent tests on a fresh clone."
- [ ] TASK-04-06: Run `pytest` and verify: (a) corpus-dependent tests skip with clear messages, (b) python-docx tests no longer skip, (c) no regressions.

**Files / Surfaces**
- `tests/test_docx_export.py` — Remove stale skip guards
- `tests/test_section_parser.py` — Add `@pytest.mark.corpus` decorators
- `pyproject.toml` — Register `corpus` marker
- `QUICKSTART.md` — Add `pytest -m 'not corpus'` tip

**Dependencies**
- None (independent of PHASE-01 through PHASE-03)

**Exit Criteria**
- [ ] `pytest -m 'not corpus'` runs all non-corpus tests with 0 skipped
- [ ] `pytest` on a fresh clone shows corpus tests as skipped with "Normalized corpus not available" reason
- [ ] `pytest` on a full environment runs all tests including corpus-dependent ones
- [ ] No python-docx skip guards remain in the codebase

**Phase Risks**
- **RISK-04-01:** Removing python-docx skip guards may reveal hidden test failures if python-docx behavior changed. Mitigation: unlikely since the rest of the test suite already exercises python-docx extensively (DOCX export tests pass with 204+ tests).

### PHASE-05 — Verification and Documentation
**Goal**
End-to-end verification of the full demo experience with corpus provenance, and update documentation.

**Tasks**
- [ ] TASK-05-01: On a clean environment (no full corpus), run `python scripts/run_demo.py` and verify: (a) demo index auto-builds, (b) DOCX has provenance citations, (c) output banner shows the DOCX path.
- [ ] TASK-05-02: On a clean environment, run `python scripts/run_inegol_demo.py` and verify the same.
- [ ] TASK-05-03: Run `pytest` and verify test count matches expectations (skipped corpus tests, no python-docx skips).
- [ ] TASK-05-04: Run `pytest -m 'not corpus'` and verify 0 skipped.
- [ ] TASK-05-05: Update `QUICKSTART.md` to add an optional "Enhanced Demo" section: "For richer output with corpus-backed provenance, run `pdd-agent demo-setup` before the demo scripts."
- [ ] TASK-05-06: Update `activeContext.md` with Sprint 3 completion status.

**Files / Surfaces**
- `QUICKSTART.md` — Add enhanced demo section
- `activeContext.md` — Update

**Dependencies**
- PHASE-01 through PHASE-04

**Exit Criteria**
- [ ] Full demo experience works on clean environment with auto-built index
- [ ] Test suite is self-explanatory (clear skip reasons, no stale guards)
- [ ] Documentation updated
- [ ] `activeContext.md` updated

**Phase Risks**
- **RISK-05-01:** None significant — this is verification and documentation.

## Verification Strategy
- **TEST-001:** Run `pytest tests/test_demo_setup.py` to verify demo index builder works.
- **TEST-002:** Run `pytest -m 'not corpus'` to verify non-corpus tests all pass without skips.
- **TEST-003:** Run `pytest` on a full environment (with corpus) to verify all 211+ tests pass.
- **MANUAL-001:** On a clean clone with `demo/corpus/`, run both demo scripts and open the DOCX files. Verify provenance citations appear in at least 5 sections.
- **MANUAL-002:** On a clean clone without `demo/corpus/`, run demo scripts and verify they still work with empty provenance and a single warning log.

## Risks and Alternatives
- **RISK-001:** Committing normalized corpus text may raise IP concerns if the PDFs are not truly public. Mitigation: verify each document is available on the public Verra registry before bundling. Add provenance notes.
- **RISK-002:** Demo index fallback logic may interfere with production index behavior. Mitigation: use separate filenames (`demo.fts.db` vs `corpus.fts.db`) and clear precedence rules.
- **ALT-001:** Instead of bundling real corpus docs, could generate synthetic corpus docs. Not chosen because real corpus data provides authentic provenance and the documents are publicly available.
- **ALT-002:** Instead of auto-building the index in demo scripts, could require a manual `pdd-agent demo-setup` step. Not chosen because it adds friction; auto-build is sub-second and invisible.

## Grill Me
1. **Q-001:** Are the Verra VCS project descriptions (Soc Son, Inegol, Bergama) publicly downloadable from the Verra registry, and is it acceptable to commit their normalized text to this repo?
   - **Recommended default:** Yes — Verra VCS project descriptions are public registry documents. Commit the normalized text (not the original PDFs) with provenance notes.
   - **Why this matters:** If the documents are not public or redistribution is restricted, the bundled corpus approach is blocked and we fall back to the warning-only approach.
   - **If answered differently:** Remove PHASE-01 and PHASE-03. Keep only PHASE-02 (degraded-mode warnings) and PHASE-04 (test cleanup).

## Suggested Next Step
Answer Q-001 about corpus IP, then begin PHASE-01 and PHASE-04 in parallel (they are independent). PHASE-02 and PHASE-03 follow sequentially.

## Target Timeline
- **2026-05-27:** PHASE-01 + PHASE-04 (parallel)
- **2026-05-28:** PHASE-02 + PHASE-03 + PHASE-05 (sequential)
