# Real-Output Fidelity — Full Plan Completion (PHASE-01 through PHASE-05)

**Plan:** `plans/2026-08-21-real-output-fidelity-plan.md` (5 phases)
**Scope:** Full plan. Render real model output faithfully in DOCX, replace the uniform 4,000-char cap with per-section budgets and honest truncation reporting, split the export gate's two meanings, repair the review UI/product surface, and charge the ACM0022 engine for incineration emissions measured against a year-by-year registered oracle.

## Checklist

### PHASE-01 — Render Markdown Model Output Faithfully — DONE
- [x] TASK-01-01/02/03: `src/pdd_agent/export/markdown_docx.py` (S-1 block scanner, `_split_inline_runs`, `clean_math_text`, `parse_pipe_table`)
- [x] TASK-01-04: `_add_section_prose` calls `render_markdown_body()`; LOW/UNSUPPORTED highlighting + placeholder preserved
- [x] TASK-01-05: display-math sources collected across the document → "Appendix — Formulas (verbatim source)"
- [x] TASK-01-06: `_split_paragraphs` kept (Markdown-naive docstring) for other call sites
- [x] TASK-01-07/08: 23 unit tests in `tests/test_markdown_docx.py` + end-to-end `TestMarkdownRendering` in `tests/test_docx_export.py`
- [x] Exit criteria: real `smoke-4-1` export → 135 paragraphs / **7 tables**, zero literal `|---`/`$$` artifacts

### PHASE-02 — Per-Section Character Budgets and Honest Truncation — DONE
- [x] TASK-02-01: `max_chars` on all 36 subsections in `schemas/pdd_section_schema.yaml` (sum **297,000**)
- [x] TASK-02-02/03: `_CONTENT_CLASS_BUDGETS` + `section_budget_chars()` + `_enforce_budget`; `max_chars=` passed at both provider call sites
- [x] TASK-02-04: `max_tokens_per_section` le=40000, documented as a global character ceiling
- [x] TASK-02-05/06: `TRUNCATED:` issue + one-step confidence downgrade + `section_truncated` warning
- [x] TASK-02-07: `tests/test_section_budgets.py` (13 tests)
- [x] Exit criteria: demo draft stores 36 sections; budget resolution verified incl. global-ceiling capping

### PHASE-03 — Split the Export Gate's Two Meanings — DONE
- [x] TASK-03-01/02/03: `required_inputs` on `ExportGateResult`; `_collect_required_inputs` collects every `[MISSING]` occurrence in every section (200-char collapsed context); no longer a hard block
- [x] TASK-03-04: "Appendix — Required Inputs" table (capped at 100 entries), rendered before reviewer issues
- [x] TASK-03-05: `(EXPORT GATE OVERRIDE)` only when force=True AND hard blocks existed
- [x] TASK-03-07: gate tests rewritten (`tests/test_export_gate.py`); export of MISSING-only runs succeeds without --force
- [x] Real-run proof: `pdd-agent export --run-id smoke-4-1` now exports unforced (previously required --force)

### PHASE-04 — Repair the Review UI and Product Surface — DONE
- [x] TASK-04-01/02: `path_to_approved()` + `api_approve_all` walks the legal path; needs-input skipped; partial approval → HTTP 409 with skip detail; dashboard template updated to fetch-based call
- [x] TASK-04-03: `configs/corpus_families.yaml` maps all 17 normalized stems explicitly (Ödemiş stem copied from filesystem)
- [x] TASK-04-04/05: `RetrievalResult.from_fallback_family` + `GROUNDING:` section issue when fallback family used
- [x] TASK-04-06: `/api/runs` + `/dashboard` paginated (default 50, clamp 200, total/limit/offset in body)
- [x] TASK-04-07/08: `claude-code` resolved in service `_get_provider`; CLI help strings + README CLI row
- [x] TASK-04-09/10: `get_active_index_row_count()` (+ deprecated alias); `reachable_rows`/`reachable_documents` in `index_health` and `index-report` → **889 rows / 13 documents** (vs headline 3026/17)
- [x] TASK-04-11: CI installs the `ingest` extra

### PHASE-05 — Charge the Emissions an Incinerator Causes — DONE
- [x] TASK-05-01: `GWP_N2O`, `EF_N2O_INCINERATION_KG_PER_TONNE`, `OXIDATION_FACTOR_INCINERATION`, `CO2_PER_C_RATIO`, `INCINERATION_CARBON_BY_WASTE_TYPE` in `calc/constants.py` (IPCC 2006 V5 citations)
- [x] TASK-05-02/03: `IncinerationStream` model + `incineration.py` (Eq. 5.1 fossil CO2, Eq. 5.4 N2O)
- [x] TASK-05-04: `PE_INC (waste incineration)` component wired into `ACM0022Calculator.calculate()`
- [x] TASK-05-05: unmapped composition entries become `incineration_streams` for incineration tech, with per-entry warnings
- [x] TASK-05-06: `capacity_ramp` consumed in `compute_for()` year loop via `_ramp_factor()`; field description updated
- [x] TASK-05-07: Soc Son composition corrected to Table 8's exact 1.000 (rubber_leather removed; plastics 0.030 + inert 0.408 split from the 43.8% bucket with applicability-section provenance)
- [x] TASK-05-08/09: seven-row registered schedule constants + `TestSocSonAnnualSchedule` (D-1/D-2 xfails with 2026-08-21 measurements); Soc Son crediting-total xfail **flipped to passing**
- [x] TASK-05-10: `tests/test_incineration.py` (10) + ramp/mapping/regression-guard tests in `test_calc_dispatch.py`

## Final steps

- [x] Full suite `python -m pytest -m "not corpus" -q`: **909 passed, 7 deselected, 4 xfailed, 0 failed** (was 841/3)
- [x] `ruff check .` / `ruff format --check .` clean; `uv lock --check` exit 0
- [x] `pdd-agent calc --input vietnam_socson_from_sheet.yaml`: Project emissions **187,895.43 tCO2e/yr**, PE_INC component present
- [x] `git status --short reports/` empty before commit (budget-check side effect reverted)
- [x] README: status line, Known Gaps, Quantification precedence + Section length budgets, CLI table, export-gate description
- [x] Verify report: `reports/verify-2026-08-21-real-output-fidelity.md`

## Review / Results

**Delivered:** all 5 phases of the 2026-08-21 plan.

**Measured before/after (Soc Son oracle):**

| Metric | Before this push | After | Registered |
|---|---|---|---|
| Crediting total 7yr | 5,397,730 (+41.7%) | **4,010,142 (+5.3%) — inside tolerance, xfail flipped** | 3,808,082 |
| Project emissions | 0.00 tCO2e/yr | **187,895 tCO2e/yr (PE_INC)** | ~82,277 net charge |
| D-1: 7yr BE_CH4 sum | 2,898,688 (−33.9%) | **2,826,368 (−35.5%) — xfail recorded** | 4,384,018 |
| D-2: non-methane net charge | +357,006 | **+169,110.6 — xfail recorded** | −82,276.5 |
| Inegol 7yr total | 893,441 (+22.4%) | unchanged (no composition declared) | 730,000 |

**Export/review surface:** real Markdown renders natively (smoke-4-1: 7 tables, no artifacts); budgets sum 297,000 chars vs the previous uniform 144,000 ceiling; MISSING-only runs export without --force; approve-all approves 36/36 on a fresh demo run and returns 409 with reasons when a section awaits input; index-report now prints honest reachability (889/13).

**Suite state:** 909 passed, 4 xfailed (Inegol year-1 ×2, D-1, D-2 — all with dated measured residuals). TOLERANCE untouched at 0.20.

**Risks still open:** D-1 FOD parameter gap (out of scope, RISK-05-03); OMML math not generated (ALT-003); `docs/vietnam-pdd-*.md` reports are stale until `run-vietnam-pdd` is re-run after the composition change (RISK-05-04).
