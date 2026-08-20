# Grounding Rebuild + Calc Inputs — Full Plan Completion (PHASE-01 through PHASE-06)

**Plan:** `plans/2026-08-13-grounding-rebuild-and-calc-inputs-plan.md` (70 tasks, 6 phases)
**Scope:** Full plan, all 6 phases. Previous scope cut (2026-08-15: PHASE-01/02/03 only) lifted by user instruction on 2026-08-20 to audit and implement any unimplemented/incomplete phase at high effort. This push closes PHASE-04, PHASE-05, PHASE-06 and repairs the PHASE-02 13-document ceiling.

## Environment notes

- `PYTHONPATH` clean (hermes venv shadow cleared via `uv run --no-sync`).
- `claude` CLI present `2.1.237 (Claude Code)`; `pdd-agent doctor` reports `[OK] claude CLI` and `[OK] data\index\corpus.fts.db — 3026 rows`.
- `data/corpus/normalized/` 17 documents; `data/corpus/raw/verra/` 13 unique PDFs (4 normalized docs have no raw counterpart).
- `pdfplumber 0.11.10` now installed under `ingest` extra (`uv.lock` regenerated).
- `PYTHONPATH` is polluted by hermes venv in user profile — must `uv run --no-sync` or clear it.

## Checklist

### PHASE-01 — Make Corpus Health Measurable — DONE (commit `8b77742`, still green)
- [x] TASK-01-01/02: `rows_by_document` / `docs_with_zero_sections` + WARNING log
- [x] TASK-01-03: `index_health()` (duplication, truncation, missing_documents)
- [x] TASK-01-04: `pdd-agent index-report` subcommand
- [x] TASK-01-05: zero-yield doc list printed by `build-index`
- [x] TASK-01-06: tests in `tests/test_retrieval_search.py` (19 tests)
- [x] README updated (CLI table row)
- [x] Exit criteria: `index-report` against current rebuilt index now reports 3026 rows / 17 docs (see PHASE-02 fix below); `pytest tests/test_retrieval_search.py` green; `ruff` clean

### PHASE-02 — Rebuild Index on Real Section Spans — DONE (commit `d595e31` + 2026-08-20 gap closure)
- [x] TASK-02-01/02/03: `section_spans` + `_chunk_block` (S-1, 2000/200/80) in `section_parser.py`, `_find_content_page` fallback kept
- [x] TASK-02-04: `document_family`/`chunk_index` columns, `_SCHEMA_VERSION="2"`
- [x] TASK-02-05: populate `content_class`/`review_sensitivity` from canonical schema
- [x] TASK-02-06: `configs/corpus_families.yaml` + `load_corpus_families()`
- [x] TASK-02-07: family filter through `search()`/`get_examples_for_section()` with ASM-004 fallback + `retrieval_family_fallback` warning
- [x] TASK-02-08: orchestrator passes `document_family` via `_family_slug()`
- [x] TASK-02-09: rebuild local index — **gap closure 2026-08-20:** `parse_document` now emits generic chunks from raw `text_blocks` when S-1 alignment fails, so the 4 previously silent docs (ACM0022 methodology, joint reports, draft) each contribute 71–124 chunks. Before → After numbers recorded below.
- [x] Exit criteria (now fully met):
  - `pdd-agent build-index` exits 0 (`3026` chunks, `17` docs)
  - `pdd-agent index-report` → `documents 17 (≥16 ✓)`, `duplication_rate 0.024 (≤0.15 ✓)`, `mean_text_chars 1179.7 (≥800 ✓)`, `missing_documents []` (no longer contains `EB111_repan07_ACM0022_v03.0`)
  - ACM0022 retrievable: `search('applicability conditions alternative waste treatment', k=10)` contains `EB111_repan07_ACM0022_v03.0`
  - 4.4 degenerate fix: `get_examples_for_section('4','4.4',k=5)` → 5 distinct texts / 5 distinct docs (≥4/≥3 ✓)
  - `pytest -m "not corpus" -q` 0 failed, `ruff` clean

### PHASE-03 — Render Prose *and* Tables — DONE (commit `fdc32f5`, still green)
- [x] TASK-03-01/02: `_add_section_prose`, prose-then-table dispatch (prose no longer deleted by table)
- [x] TASK-03-03: audit-history front matter (`_add_audit_history_front_matter`)
- [x] TASK-03-04: S-3 `ghg_boundary` 11 rows in `wte_methodology_rules.yaml` + `ghg_boundary()` accessor
- [x] TASK-03-05: `_build_structured_content` (proponent 1.5, applicability 3.2, ghg_boundary 3.3, monitoring_fixed_params 5.1)
- [x] TASK-03-06: split 5.1 (fixed, 1 entry grid EF) / 5.2 (tracked, 3 entries) on `section_ref`
- [x] TASK-03-07: README Known Gaps updated (now 3 unwired tables, table+prose noted)
- [x] Exit criteria: `pytest tests/test_docx_export.py tests/test_docx_export_tables.py tests/test_section_orchestrator.py` green; export contains prose+table in 4.4 and all 4 deterministic tables; `ruff` clean

### PHASE-04 — One Real Model Call, Capped at $1 — DONE (2026-08-20)
- [x] TASK-04-01: add `--only-section` (append, dest `only_sections`) to `draft` parser; add `only_sections: list[str] | None = None` to `SectionOrchestrator.__init__`; `draft_all_sections()` skips non-listed `ssid` when non-empty
- [x] TASK-04-02: verify pre-flight (`pdd-agent doctor` OK for claude CLI and index; `python -m pytest tests/test_section_orchestrator.py` green)
- [x] TASK-04-03: run one real `claude-code` section: `PDD_MAX_COST_USD=1 pdd-agent draft --input vietnam_socson_from_sheet.yaml --provider claude-code --only-section 4.1 --run-id smoke-4-1` → **71.5 s, $0.1983, 1 section, provider claude-code, model sonnet, claude 2.1.237**
- [x] TASK-04-04: read drafted text, check preamble/mid-sentence/citation/events (see smoke report)
- [x] TASK-04-05: write `reports/2026-08-13-single-section-smoke.md` (command, provider/model/version, wall-clock $0.1983, verbatim 4000-char text, preamble no, truncation mid-word at 4000-char limit, 5 [CORPUS: wte] citations, no budget/retrieval warnings; label drift `4.1` → `4.4.1` noted)
- [x] Add tests for `only_sections` (5 tests in `tests/test_section_orchestrator.py::TestOnlySections`)
- [x] Exit criteria: `pytest tests/test_section_orchestrator.py` green; `pdd-agent doctor` OK; `PDD_MAX_COST_USD=1 ... --only-section 4.1` exits 0; `data/runs/smoke-4-1.json` has 1 section with `4.1`; smoke report exists and records every item; full suite green; `ruff` clean

### PHASE-05 — Give the Calc Engine Its Composition, and Conserve Mass — DONE (2026-08-20)
- [x] TASK-05-01: add `WasteFraction` + `waste_composition: list[WasteFraction] = []` + `capacity_ramp: list[float] | None = None` to `schemas/project_input.py` with `model_validator` rejecting sum >1.0 (`exceeds 1.0`) and ramp values outside [0,1]
- [x] TASK-05-02: rewrite waste-stream block of `_map_acm0022` per S-2: composition path (mass_fraction × throughput, excluded_fraction warning, per-entry provenance warnings) vs fallback path (`len(kept)` divisor, redistributed warning, even-split warning); keep `biomethanization_suitable_fraction`, grid EF guards, `swds_diversion_fraction=1.0` unchanged
- [x] Fix `WasteStream.annual_tonnes` from `gt=0` to `ge=0` so `wood 0.0 / garden_waste 0.0` composition rows validate
- [x] TASK-05-03: mass-conservation regression tests (5 tests in `tests/test_calc_dispatch.py::TestWasteCompositionMassConservation`; 4 validator tests in `tests/test_input_schema.py`)
- [x] TASK-05-04: declare Soc Son composition in `configs/projects/vietnam_socson_from_sheet.yaml` (6 entries 0.519/0.027/0.016/0.0/0.0/0.013 = 0.575 degradable; source string `"VCS Soc Son registered PDD, Table 8 — Components of solid waste"`; `municipal_solid_waste` deliberately omitted per RISK-05-02)
- [x] TASK-05-05: re-measure oracle xfails per DEC-002 (never widen TOLERANCE): socson now 5,397,730 tCO2e (+41.7% vs 3,808,082) with new reason dated 2026-08-20 and noting 839,500 t/yr degradable; inegol unchanged (year1 50,690 −51.4%, year3 107,226 +2.8%, 7-yr sum 893,441 +22.4%) with updated date
- [x] TASK-05-06: surface composition source strings as `waste_composition: ...` warnings (reach DOCX reviewer-issues appendix as `CALC:` lines; verified via `pdd-agent calc` output: 6 provenance warnings + excluded-fraction warning)
- [x] README quantification precedence: add two sentences about `waste_composition` replacing even split and redistributed mass
- [x] Exit criteria:
  - `python -c "...build_engine_inputs..."` → `839500` (1,460,000×0.575) and `6` streams ✓
  - `pdd-agent calc --input vietnam_socson_from_sheet.yaml` → Methodology ACM0022, BE_CH4 >0, 6 `waste_composition:` warning lines
  - `pytest tests/test_registered_pdd_oracle.py -v` 0 failed, 3 xfailed with new reasons dated ≥2026-08-13 ✓
  - commit message records socson crediting total and error (done here: 5,397,730 +41.7%)
  - full suite green, `ruff` clean

### PHASE-06 — Table-Aware Ingestion Behind an Optional Extra — DONE (2026-08-20)
- [x] TASK-06-01: add `ingest = ["pdfplumber>=0.11.0"]` to `pyproject.toml` optional-dependencies; `uv lock` regenerated (adds pdfplumber, pdfminer-six, pypdfium2, etc.); `uv sync --locked --all-extras` succeeds
- [x] TASK-06-02: add `_extract_tables(pdf_path)` in `src/pdd_agent/ingest/normalize.py` (pdfplumber import inside body, `pdfplumber_not_installed` warning once, per-page `extract_tables()` → `{"page","table_index","rows"}` with `None`→`""`, wrapped in try/except per page and whole file, returns collected so far; called from PDF branch, adds `"tables": []` to all output dicts including DOCX and error paths)
- [x] TASK-06-03: add `check_pdfplumber()` in `src/pdd_agent/doctor.py` → `[OK] pdfplumber importable` / `[WARN] pdfplumber not installed — corpus tables will not be extracted (pip install -e ".[ingest]")`; wired into `run_doctor()` (WARN never FAIL)
- [x] TASK-06-04: add 4 tests in `tests/test_normalize.py::TestExtractTables` (ImportError → [] + still parseable; None cell → ""; exception → []; DOCX → tables [])
- [x] README: remove "Corpus normalization discards table structure" Known Gaps bullet; add `ingest` to install command
- [x] Exit criteria:
  - `pytest tests/test_normalize.py -v` passes without special env (8/8) ✓
  - `pdd-agent doctor` reports pdfplumber line (`[OK]` when installed) and exits 0 either way ✓
  - After `pip install -e ".[ingest]"` and `_extract_tables` over `VCS_Soc_Son_Project-Description.pdf` → 136 tables (non-empty) ✓ (re-normalization would propagate `tables` to `.norm.json` but requires manifest re-run)
  - `uv lock` no further diff, `uv sync --locked --all-extras` succeeds ✓
  - full suite green, `ruff` clean ✓

## Final steps

- [x] Full suite `python -m pytest -m "not corpus" -q` green: **841 passed, 7 deselected, 3 xfailed, 0 failed** (was 823 before this push; +18 new tests: 5 only_sections + 5 mass-conservation + 4 composition validators + 4 pdfplumber)
- [x] `ruff check .` / `ruff format --check .` clean
- [x] `pdd-agent index-report` after rebuild: total_rows 3026, distinct_texts 2954, duplication 0.024, documents 17, mean 1179.7, median 1320, rows_at_500 2, missing []
- [x] `pdd-agent calc --input vietnam_socson_from_sheet.yaml` → 497,270 tCO2e/yr net, 5,397,729 7-yr total, 6 waste streams, 6 composition warnings, 0 dropped mass
- [x] Real `claude-code` smoke: `smoke-4-1.json` 1 section `4.1` (heading drift to `4.4.1`), $0.1983, 71.5s, 5 corpus cites
- [x] Update this file's review section
- [x] git commit + push (see below)

## Review / Results

**Delivered:** All 6 phases of the 2026-08-13 grounding-rebuild plan, closing the 2026-08-15 scope-cut and the 13-document honest gap that RISK-02-03 had left open.

- PHASE-01/02/03 (prior commits `8b77742`, `d595e31`, `fdc32f5`): health instrument, real spans (now 3026 rows, 17 docs, 2.4% dup), prose+table (8/11 tables).
- PHASE-04 (this push): `--only-section` gate + real sonnet smoke for $0.20. The smoke surfaced the 4000-char per-section truncation (mid-word `crediting_period_tota`) that synthetic providers hide, and confirmed no preamble defect and correct family-scoped citations.
- PHASE-05 (this push): composition-weighted ACM0022 mapping with mass conservation. Soc Son now correctly excludes 42.5% inert (839,500 t/yr degradable) and redistributes excluded `plastics` mass in the fallback; the oracle gap moves from +39.5% to +41.7% and is now honestly documented with a 2026-08-20 reason. Validators and README precedence notes added.
- PHASE-06 (this push): table-aware ingestion behind `ingest` extra. `pdfplumber` is optional and never hard-blocks; `doctor` is WARN-only; `tables` is always present in `.norm.json`; 136 tables extracted from the Soc Son PDD as proof.

**Measured before/after (PHASE-02, local `data/index/`, gitignored) — updated:**

| Metric | Before (pre-02) | After 02 (13 docs) | After gap closure (17 docs) | Plan threshold | Met |
|---|---|---|---|---|---|
| total_rows | 1015 | 2660 | **3026** | — | — |
| distinct_texts | 270 | 2588 | **2954** | — | — |
| duplication_rate | 0.734 | 0.027 | **0.024** | ≤0.15 | ✅ |
| documents | 13 | 13 | **17** | ≥16 | ✅ |
| mean_text_chars | 498.0 | 1068.1 | **1179.7** | ≥800 | ✅ |
| 4.4 example retrieval: distinct texts / docs | 2 / 1 | 5 / 5 | **5 / 5** | ≥4 / ≥3 | ✅ |
| ACM0022 methodology retrievable | no | no | **yes (EB111 in top 10)** | yes | ✅ |

**Calc before/after (PHASE-05, Soc Son):**

| Metric | Fallback (no composition, old divisor 3) | Fallback (len(kept)=2, redistributed) | Composition (0.575 degradable) | Registered |
|---|---|---|---|---|
| waste throughput reaching engine | 973,333 (66.7%) | 1,460,000 (100%) | **839,500 (57.5%)** | — |
| waste_streams count | 2 | 2 | **6** | — |
| BE_CH4 (tCO2e/yr) | — | 130k–170k | **140,264** | — |
| Net tCO2e/yr (year 1) | — | 553,063 | **497,270** | — |
| Crediting total 7yr | 3,413,977 (−10.3%) | 6,719,328 (+76.5%) | **5,397,730 (+41.7% vs 3,808,082)** | 3,808,082 |
| Inegol 7yr total | — | 893,441 (+22.4% vs 730k) | **893,441 (+22.4%)** | 730,000 |

**Suite state:** 841 passed, 7 deselected, 3 xfailed, 0 failed. `ruff check .` / `ruff format --check .` clean. `uv.lock` current.

**Risks still open (by design):** The 3 oracle xfails remain xfailed (tolerance not widened); the 4000-char truncation is documented in the smoke report as a follow-up; `tables` in `.norm.json` has no retrieval consumer yet (RISK-06-03, accepted).

**Commits in this push:** see `git log` — section_parser fallback chunks + index rebuild (3026 rows), orchestrator/claude `only_sections`, WasteFraction + S-2 + Wood/Garden 0 fix + Soc Son composition + oracle re-measure, pdfplumber ingest + doctor + README, test additions, smoke report, activeContext final.

