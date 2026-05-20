---
title: "Codex Insights Integration and Inegol Demo Case"
date: "2026-05-20"
status: "draft"
request: "Improve the pdd-auto repo by incorporating insights from the staff Codex workflow (ref/ folder), upgrade DOCX export fidelity, strengthen review layer, and produce an end-to-end Inegol demo case."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-22_wte-pdd-ingestion.md"
  - "research/Waste to Energy Carbon Credits.md"
---

# Plan: Codex Insights Integration and Inegol Demo Case

## Objective
Incorporate the high-quality domain content and DOCX formatting patterns discovered in the staff Codex output (`ref/PDD staff test.../build_inegol_vcs_pd.py`) into the existing `pdd-auto` pipeline, close the gaps between the repo's thin DOCX export and the Codex script's rich VCS v4.4 table fidelity, and prove the integrated pipeline with an end-to-end Inegol demo that produces a reviewer-ready package exceeding what the standalone Codex script delivers.

## Context Snapshot
- **Current state:** The repo has a 5-phase agentic pipeline (`src/pdd_agent/`) with corpus ingestion (13 WTE PDFs), BM25/FTS5 retrieval, section orchestrator, LLM provider abstraction, consistency checker, and methodology rules. DOCX export (`src/pdd_agent/export/docx_export.py`, 411 lines) produces review-friendly output but uses only basic paragraph text and metadata tables — no VCS-specific structured tables (monitoring parameters, GHG boundary matrices, applicability conditions, risk assessments). The staff Codex output in `ref/` demonstrates a 1,010-line monolithic script that generates a 23-page Inegol VCS v4.4 DOCX with full table fidelity from a YAML intake, but has no retrieval, no compliance checks, no tests, and hardcoded paths.
- **Desired state:** A pipeline that (1) exports DOCX documents matching VCS v4.4 table structure and formatting quality, (2) accepts Inegol-style intake YAML through the existing `ProjectInput` schema, (3) grounds section content in corpus retrieval rather than pure template filling, (4) runs consistency and compliance checks on every draft, and (5) produces a demo package for the Inegol project (DOCX + review report + consistency report) that proves pipeline superiority over the standalone Codex script.
- **Key repo surfaces:**
  - `src/pdd_agent/export/docx_export.py` — DOCX export module, primary upgrade target
  - `schemas/project_input.py` — Pydantic input contract, needs Inegol-style field additions
  - `schemas/pdd_section_schema.yaml` — canonical section schema, may need sub-section additions for new table types
  - `src/pdd_agent/agent/section_orchestrator.py` — section drafting orchestrator
  - `src/pdd_agent/review/consistency.py` — cross-section numeric consistency checker
  - `src/pdd_agent/review/checks.py` — post-draft compliance checks
  - `src/pdd_agent/domain/methodology_rules.py` — methodology rule loader
  - `rules/verra/wte_methodology_rules.yaml` — WTE methodology rules
  - `rules/verra/wte_review_rules.yaml` — WTE review rules
  - `data/corpus/raw/verra/VCS_Inegol_Project-Description.pdf` — Inegol source PDF already in corpus
  - `ref/PDD staff test.../build_inegol_vcs_pd.py` — Codex reference script (read-only reference)
  - `ref/PDD staff test.../extracted_text/` — 4 extracted reference texts from Codex workflow
- **Out of scope:** Rewriting the pipeline to use the Codex monolithic approach; removing or replacing the existing retrieval/review architecture; supporting non-Verra standards; building a production UI; automatic registry submission.

## Research Inputs
- `research/2026-04-22_wte-pdd-ingestion.md` — Confirms section-level RAG with provenance is preferred over monolithic generation; validates that the pipeline should draft by section with citations and human-review gates. Reinforces that the Codex "template-only" approach (no retrieval) is architecturally inferior even when its output formatting is superior. Directly informs PHASE-01 (keep retrieval architecture, upgrade export layer only) and PHASE-04 (demo must show provenance per section).
- `research/Waste to Energy Carbon Credits.md` — Documents double-counting boundaries between landfill diversion, biogas utilization, RDF production, and cement fuel substitution. The Codex Inegol script handles some of these (sections 1.16, 1.17, 3.3 boundary table) but without validation. Informs PHASE-03 (add boundary-aware compliance checks the Codex script lacks).

## Assumptions and Constraints
- **ASM-001:** The Codex script's `build_inegol_vcs_pd.py` is used as a read-only reference for table structures and VCS section content patterns. No code is directly copy-pasted; instead, the patterns are re-implemented within the existing `docx_export.py` module architecture.
- **ASM-002:** The Inegol intake YAML referenced by the Codex script (`D:\Allotrope\PDD\intake.inegol_acm0022_from_pd.yaml`) is not present in the repo. A new `configs/demo/inegol_project_input.yaml` will be created by mapping known Inegol data from the corpus PDF and the Codex script's hardcoded values into the `ProjectInput` schema.
- **ASM-003:** The 4 extracted text files in `ref/.../extracted_text/` (Bergama, HEREKO, ACM0022 methodology, DraftProjectDescription) can be ingested into the corpus to improve retrieval quality for WTE sections.
- **CON-001:** The `python-docx` library is already a dependency (used by `docx_export.py`). The Codex script's low-level OOXML helpers (cell shading, cell margins, row repeat headers, cant-split rows) must be adapted to work within the existing lazy-import pattern (`_docx_attr()`).
- **CON-002:** The existing `ProjectInput` schema is the canonical input contract. The Codex script's flat YAML structure (with keys like `project_identity`, `parties`, `technical_design`, `location`, `methodology`) must be mapped to the existing Pydantic model hierarchy, not replace it.
- **DEC-001:** The Inegol project PDF (`VCS_Inegol_Project-Description.pdf`) is already in `data/corpus/raw/verra/` so no new ingestion is needed for the demo.
- **DEC-002:** Demo output goes to `data/runs/` (DOCX + JSON) consistent with the existing export path convention.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Upgrade DOCX export with VCS v4.4 table structures from Codex reference | None | Enhanced `docx_export.py` with table renderers, tests |
| PHASE-02 | Create Inegol ProjectInput and backport Codex reference texts to corpus | None | `configs/demo/inegol_project_input.yaml`, corpus text files, tests |
| PHASE-03 | Strengthen review layer with TBD tracking and boundary-aware compliance | PHASE-01 | Updated consistency checker, new TBD tracker, review rules |
| PHASE-04 | End-to-end Inegol demo with pipeline vs Codex comparison | PHASE-01, PHASE-02, PHASE-03 | Inegol demo DOCX, review report, comparison report |

## Detailed Phases

### PHASE-01 - DOCX Export Upgrade
**Goal**
Upgrade `src/pdd_agent/export/docx_export.py` to produce VCS v4.4-faithful structured tables matching the quality demonstrated in the Codex script, while preserving the existing review-friendly metadata layers (confidence badges, provenance, assumption appendices).

**Tasks**
- [ ] TASK-01-01: Add a `_table_helpers.py` module at `src/pdd_agent/export/table_helpers.py` implementing the Codex script's low-level OOXML patterns: `set_cell_shading()`, `set_cell_margin()`, `set_cell_text()` (with multi-line support), `set_row_cant_split()`, `set_row_repeat_header()`, and `add_styled_table()` (with header row formatting, column widths, and font size control). Use the existing `_docx_attr()` lazy-import pattern from `docx_export.py`.
- [ ] TASK-01-02: Implement table renderer functions for each VCS v4.4 structured table type observed in the Codex output:
  - `render_cover_metadata_table()` — project title, ID, crediting period, version, prepared by (replaces current `_add_cover_metadata`)
  - `render_audit_history_table()` — audit type, period, program, VVB name, years
  - `render_proponent_table()` — organization, contact, title, address, phone, email
  - `render_ghg_boundary_table()` — scenario/source/gas/included/justification matrix
  - `render_applicability_table()` — methodology ID, condition, justification of compliance
  - `render_monitoring_fixed_params_table()` — data/parameter, unit, description, value, source, comments
  - `render_monitoring_tracked_params_table()` — data/parameter, unit, description, frequency, equipment, QA/QC
  - `render_risk_assessment_table()` — risk category, risks identified, mitigation measures
  - `render_emissions_summary_table()` — vintage period, baseline, project, leakage, reductions, removals, VCUs
  - `render_sustainable_development_table()` — SD area, contribution, monitoring approach
  - `render_data_gaps_table()` — topic, gap/assumption, needed evidence
- [ ] TASK-01-03: Refactor `export_run_to_docx()` to detect structured table data in `DraftSection` objects (keyed by `section.table_data` or `section.structured_content`) and dispatch to the appropriate table renderer instead of rendering all content as plain paragraphs.
- [ ] TASK-01-04: Update `_set_base_styles()` to use Arial font (VCS standard) instead of Calibri, matching the Codex output's formatting. Add VCS-standard margins (1.7cm top, 1.6cm bottom, 1.8cm left/right).
- [ ] TASK-01-05: Write unit tests in `tests/test_docx_export_tables.py` that verify each table renderer produces the expected row/column counts, header text, and cell shading for sample input data.

**Files / Surfaces**
- `src/pdd_agent/export/table_helpers.py` — New module for OOXML table primitives
- `src/pdd_agent/export/docx_export.py` — Major expansion with table rendering dispatch
- `tests/test_docx_export_tables.py` — New test file for table renderer coverage

**Dependencies**
- None (uses existing `python-docx` dependency)

**Exit Criteria**
- [ ] `table_helpers.py` exports all listed helper functions and each can produce a valid `docx.table.Table` object without errors.
- [ ] Each of the 11 table renderer functions produces output matching the Codex reference's column count and header labels for sample input data.
- [ ] `export_run_to_docx()` can produce a DOCX where at least sections 1.1 (cover), 3.2 (applicability), 3.3 (boundary), 4.4 (emissions summary), 5.1 (fixed params), and 5.2 (monitored params) contain structured tables rather than plain text.
- [ ] All tests in `tests/test_docx_export_tables.py` pass.

**Phase Risks**
- **RISK-01-01:** The existing `DraftSection` dataclass may not have a `table_data` field, requiring changes to `src/pdd_agent/llm/provider.py`. Mitigation: add an optional `structured_content: dict[str, Any] | None` field with a default of `None` so existing runs are not broken.
- **RISK-01-02:** Cell margin and shading OOXML manipulation can be fragile across `python-docx` versions. Mitigation: pin `python-docx>=1.1.0` and test on the installed version before committing.

### PHASE-02 - Inegol ProjectInput and Corpus Expansion
**Goal**
Create a validated Inegol `ProjectInput` YAML that maps the Codex script's project data into the existing Pydantic schema, and backport the Codex-extracted reference texts into the corpus for retrieval grounding.

**Tasks**
- [ ] TASK-02-01: Create `configs/demo/inegol_project_input.yaml` by extracting project facts from the Codex script's hardcoded data (project identity, location coordinates, technical design parameters, gas engine commissioning schedule, capacity figures, crediting period dates, methodology references) and mapping them to the `ProjectInput` schema fields. Mark fields not available in the Codex output with explicit `null` values and document why in inline YAML comments.
- [ ] TASK-02-02: Extend `schemas/project_input.py` to support Inegol-specific fields that the current schema lacks but the Codex output demonstrates are needed for VCS v4.4 completeness:
  - `ProjectIdentity`: add `vcs_standard_version: str`, `prepared_by: str`, `audit_history: list[AuditHistoryEntry]`
  - `ProjectTechnology`: add `gas_engine_commissioning: list[EngineEntry]`, `rdf_capacity: RDFCapacity | None`, `biomethanization_suitable_fraction: float | None`
  - `ProjectLocation`: add `site_area_m2: float | None`, `grid_connection_point: str | None`, `boundary_coordinates: list[Coordinate]`
  - New sub-model `AuditHistoryEntry(audit_type, period, program, vvb_name, number_of_years)`
  - New sub-model `EngineEntry(engine_id, model, commissioning_date)`
  - New sub-model `RDFCapacity(max_capacity_tph, planned_2024_tpd, planned_2035_tpd)`
  - New sub-model `Coordinate(lat, lon)`
- [ ] TASK-02-03: Write a validation test in `tests/test_inegol_input.py` that loads `configs/demo/inegol_project_input.yaml` and confirms it passes `ProjectInput` validation without errors.
- [ ] TASK-02-04: Copy the 4 extracted text files from `ref/.../extracted_text/` to `data/corpus/normalized/` with standardized filenames: `bergama_vcs_joint_pd_v4.2.txt`, `hereko_vcs_pd_v4.1.txt`, `acm0022_v03.0_methodology.txt`, `inegol_draft_pd.txt`. Add entries for each to `data/corpus/manifest.jsonl` with source metadata.
- [ ] TASK-02-05: Update `configs/corpus_buckets/verra-wte-initial.yaml` to include the newly added normalized text files in the WTE bucket, noting their provenance as "extracted via Codex staff workflow 2026-05-20."

**Files / Surfaces**
- `configs/demo/inegol_project_input.yaml` — New Inegol demo input file
- `schemas/project_input.py` — Schema extensions for Inegol-specific fields
- `tests/test_inegol_input.py` — New validation test
- `data/corpus/normalized/` — 4 new text files backported from Codex ref
- `data/corpus/manifest.jsonl` — Updated with new corpus entries
- `configs/corpus_buckets/verra-wte-initial.yaml` — Updated bucket definition

**Dependencies**
- None (parallel with PHASE-01)

**Exit Criteria**
- [ ] `configs/demo/inegol_project_input.yaml` exists and `ProjectInput.model_validate(yaml.safe_load(open(...)))` succeeds.
- [ ] `schemas/project_input.py` includes all new sub-models and fields with backward-compatible defaults.
- [ ] All 4 normalized text files exist in `data/corpus/normalized/` and are listed in `manifest.jsonl`.
- [ ] `tests/test_inegol_input.py` passes.
- [ ] Existing tests (`test_input_schema.py`, `test_bucket.py`) still pass with the schema changes.

**Phase Risks**
- **RISK-02-01:** Adding fields to `ProjectInput` may break existing demo configs (Soc Son, Vietnam). Mitigation: all new fields must have defaults (`None`, `[]`, or `""`) so existing inputs remain valid.
- **RISK-02-02:** The Codex YAML intake structure is not available in the repo — project facts must be reverse-engineered from the Python script's hardcoded values. Mitigation: cross-reference with `data/corpus/raw/verra/VCS_Inegol_Project-Description.pdf` for verification.

### PHASE-03 - Review Layer Strengthening
**Goal**
Add section-level TBD tracking (inspired by the Codex script's `[TBD]` markers) and boundary-aware compliance checks that the Codex output lacks, making the pipeline's review output strictly more informative than the Codex script's static markers.

**Tasks**
- [ ] TASK-03-01: Add a `TBDTracker` class to `src/pdd_agent/review/tbd_tracker.py` that scans drafted section text for TBD/placeholder patterns (regex: `\[TBD.*?\]`, `\[PLACEHOLDER\]`, `\[INSERT.*?\]`, `\[SOURCE.*?\]`, `\[EVIDENCE.*?\]`) and produces a structured report mapping each TBD to its section ID, surrounding context, and suggested evidence type (from the section schema's `evidence_required` field).
- [ ] TASK-03-02: Integrate `TBDTracker` into the `SectionOrchestrator.run()` method in `src/pdd_agent/agent/section_orchestrator.py` so that every draft run automatically produces a TBD report alongside the consistency report.
- [ ] TASK-03-03: Add a `_check_ghg_boundary_completeness()` function to `src/pdd_agent/review/consistency.py` that verifies all GHG sources listed in the section schema's boundary definition (section 3.3) are addressed in the drafted boundary table, flagging any missing source/gas combinations as HIGH severity.
- [ ] TASK-03-04: Add a `_check_monitoring_parameter_coverage()` function to `src/pdd_agent/review/consistency.py` that cross-references the monitoring parameters in section 5.1/5.2 against the methodology rules' required parameter list from `rules/verra/wte_methodology_rules.yaml`, flagging missing parameters as MEDIUM severity.
- [ ] TASK-03-05: Add a `render_tbd_appendix()` function to `src/pdd_agent/export/docx_export.py` that renders the TBD tracker output as "Appendix C - Data Gaps and Evidence Requirements" in the exported DOCX, mirroring but improving upon the Codex script's static Appendix 2.
- [ ] TASK-03-06: Write tests in `tests/test_tbd_tracker.py` covering: detection of `[TBD]` markers, correct section attribution, and correct evidence type suggestion from schema.

**Files / Surfaces**
- `src/pdd_agent/review/tbd_tracker.py` — New module
- `src/pdd_agent/review/consistency.py` — 2 new check functions
- `src/pdd_agent/agent/section_orchestrator.py` — TBD tracker integration
- `src/pdd_agent/export/docx_export.py` — TBD appendix renderer
- `tests/test_tbd_tracker.py` — New test file

**Dependencies**
- PHASE-01 (table rendering functions used by TBD appendix)

**Exit Criteria**
- [ ] `TBDTracker` correctly identifies all `[TBD...]` patterns in sample text and maps them to section IDs.
- [ ] `_check_ghg_boundary_completeness()` flags missing GHG source/gas entries against the schema definition.
- [ ] `_check_monitoring_parameter_coverage()` flags missing monitoring parameters against the methodology rules.
- [ ] Exported DOCX includes "Appendix C" with a structured data gaps table when TBDs are detected.
- [ ] All tests in `tests/test_tbd_tracker.py` pass.

**Phase Risks**
- **RISK-03-01:** TBD detection regex may produce false positives on legitimate bracketed content. Mitigation: use a narrow pattern anchored on known marker words (`TBD`, `INSERT`, `PLACEHOLDER`, `SOURCE`, `EVIDENCE`) and test against real corpus text.

### PHASE-04 - Inegol End-to-End Demo and Comparison
**Goal**
Execute the full pipeline (input validation → retrieval → section drafting → consistency check → TBD tracking → compliance review → DOCX export) for the Inegol project and produce a comparison report proving the pipeline output exceeds the standalone Codex script.

**Tasks**
- [ ] TASK-04-01: Create `scripts/run_inegol_demo.py` — a CLI script that:
  1. Loads `configs/demo/inegol_project_input.yaml` into `ProjectInput`
  2. Runs the `SectionOrchestrator` with the `demo` provider against the full section schema
  3. Runs the consistency checker against the draft
  4. Runs the TBD tracker against the draft
  5. Runs methodology compliance checks
  6. Exports the draft to DOCX at `data/runs/inegol-demo-{timestamp}.docx`
  7. Exports a JSON review package at `data/runs/inegol-demo-{timestamp}-review.json`
  8. Prints a summary comparing pipeline output metrics against baseline (Codex script output)
- [ ] TASK-04-02: Create `scripts/compare_codex_vs_pipeline.py` that generates a structured comparison report (Markdown) covering:
  - Section coverage: number of VCS sections populated in each output
  - Table fidelity: structured tables vs plain text by section
  - Provenance: sections with corpus citations vs sections without
  - Review layers: consistency flags, TBD items, compliance check results (pipeline only)
  - Formatting: font, margins, page count comparison
  - Save to `reports/2026-05-20-codex-vs-pipeline-comparison.md`
- [ ] TASK-04-03: Run the Inegol demo script and verify the output DOCX opens correctly, contains structured tables in the key sections, and includes all three appendices (Assumptions, Reviewer Issues, Data Gaps).
- [ ] TASK-04-04: Generate a phase report using the `/report` skill documenting the integration results, demo output, and comparison findings.

**Files / Surfaces**
- `scripts/run_inegol_demo.py` — New demo runner script
- `scripts/compare_codex_vs_pipeline.py` — New comparison script
- `data/runs/inegol-demo-*.docx` — Demo output DOCX
- `data/runs/inegol-demo-*-review.json` — Demo review package
- `reports/2026-05-20-codex-vs-pipeline-comparison.md` — Comparison report

**Dependencies**
- PHASE-01 (DOCX table rendering)
- PHASE-02 (Inegol ProjectInput + corpus expansion)
- PHASE-03 (TBD tracker + enhanced review)

**Exit Criteria**
- [ ] `scripts/run_inegol_demo.py` runs without errors and produces both DOCX and JSON outputs.
- [ ] The Inegol demo DOCX contains structured VCS v4.4 tables in at least: cover page, section 3.2 (applicability), section 3.3 (boundary), section 4.4 (emissions), section 5.1 (fixed params), section 5.2 (monitored params).
- [ ] The comparison report shows the pipeline output has: (a) equal or greater section coverage, (b) structured tables where the Codex output has them, (c) provenance citations that the Codex output lacks, and (d) three review appendices that the Codex output lacks.
- [ ] The demo DOCX opens cleanly in Microsoft Word / LibreOffice Writer without rendering errors.

**Phase Risks**
- **RISK-04-01:** The `demo` provider produces synthetic content that may not match Inegol-specific facts closely enough for a convincing comparison. Mitigation: use the `DemoProvider` with explicit assumption overrides from the Inegol `ProjectInput` so factual fields (capacity, location, dates) are accurate even if narrative content is synthetic.
- **RISK-04-02:** Comparison report may be subjective without quantitative metrics. Mitigation: use countable metrics (section count, table count, provenance count, TBD count, compliance flag count) rather than qualitative judgments.

## Verification Strategy
- **TEST-001:** Run `pytest tests/` after each phase to confirm no regressions. All existing tests plus new phase-specific tests must pass.
- **TEST-002:** After PHASE-01, manually open a test DOCX in Word/LibreOffice and verify table rendering (shading, headers, column widths) matches VCS v4.4 expectations.
- **TEST-003:** After PHASE-02, run `python -c "from schemas.project_input import ProjectInput; import yaml; ProjectInput.model_validate(yaml.safe_load(open('configs/demo/inegol_project_input.yaml')))"` to confirm schema validation.
- **TEST-004:** After PHASE-03, run the TBD tracker against a sample section with known `[TBD]` markers and verify the output report contains the expected entries.
- **MANUAL-001:** After PHASE-04, open the Inegol demo DOCX side-by-side with the Codex output (`ref/.../INEGOL_VCS_Project_Description_v4.4_draft.docx`) and visually confirm equivalent or better formatting in every section.
- **MANUAL-002:** Review the comparison report to confirm all claimed improvements are substantiated by the metrics.

## Risks and Alternatives
- **RISK-001:** The Codex intake YAML is not in the repo, so Inegol project data must be reverse-engineered. If critical fields are missing, the demo may have more TBD markers than the Codex output. Mitigation: extract maximum data from the Inegol PDF already in corpus + the Codex script's hardcoded values.
- **RISK-002:** Extending `ProjectInput` with many new optional fields increases schema surface area and maintenance burden. Mitigation: group new fields into dedicated sub-models (`AuditHistoryEntry`, `EngineEntry`, etc.) to keep the root model clean, and ensure all new fields default to `None`.
- **ALT-001:** Instead of upgrading the existing `docx_export.py`, we could import the Codex script wholesale as a separate "legacy exporter." Rejected because this would create two parallel export paths with different architectures, doubling maintenance and testing cost.
- **ALT-002:** Instead of creating a new Inegol demo, we could upgrade an existing demo (Soc Son). Rejected because the Codex reference is specifically Inegol, and a direct comparison requires the same project.

## Grill Me
1. **Q-001:** Do you have the Inegol intake YAML file (`intake.inegol_acm0022_from_pd.yaml`) that the Codex script references at `D:\Allotrope\PDD\intake.inegol_acm0022_from_pd.yaml`?
   - **Recommended default:** Assume it is not available and reverse-engineer project facts from the Codex script's hardcoded values + the corpus PDF.
   - **Why this matters:** Having the actual YAML would make PHASE-02 faster and more accurate — every field would map directly instead of being extracted from Python source code.
   - **If answered differently:** If the YAML is available, TASK-02-01 becomes a straightforward format conversion instead of reverse engineering, saving ~2 hours.

2. **Q-002:** Should the new DOCX table structures also be retrofitted to the Soc Son and Vietnam demo outputs, or is Inegol-only sufficient for this plan?
   - **Recommended default:** Inegol-only for this plan; Soc Son/Vietnam can be upgraded in a follow-up.
   - **Why this matters:** Retrofitting all demos triples the testing surface for PHASE-04.
   - **If answered differently:** Add TASK-04-05 to regenerate Soc Son and Vietnam demos with the upgraded exporter and verify no regressions.

3. **Q-003:** Is the official VCS v4.4 DOCX template file (`VCS-Project-Description-Template-v4.4-FINAL2.docx`) available to use as a base document for the export, as the Codex script does?
   - **Recommended default:** Generate the document from scratch using `python-docx` (as the current `docx_export.py` does) rather than modifying a template DOCX, to avoid licensing/distribution concerns with the official Verra template.
   - **Why this matters:** Using the official template as a base gives exact style inheritance (headers, footers, TOC styles) but requires distributing a Verra-owned file in the repo.
   - **If answered differently:** If the template is available and cleared for repo inclusion, modify TASK-01-04 to load the template with `Document(template_path)` instead of `Document()`, which would give closer formatting fidelity.

## Suggested Next Step
Answer the Grill Me questions (especially Q-001 about the intake YAML availability), then begin implementation starting with PHASE-01 and PHASE-02 in parallel. PHASE-03 follows PHASE-01, and PHASE-04 requires all three prior phases.
