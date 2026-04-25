---
title: "Vietnam WTE Verra PDD Word Workflow"
date: "2026-04-24"
status: "draft"
request: "Create a multi-phase plan for a workflow that can produce a Verra-template Word PDD using Vietnam waste-to-energy project information from the provided Drive spreadsheet, while using synthetic assumptions for missing information."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-22_wte-pdd-ingestion.md"
  - "research/Waste to Energy Carbon Credits.md"
---

# Plan: Vietnam WTE Verra PDD Word Workflow

## Objective
Create a reproducible workflow in this repo that turns Vietnam waste-to-energy project information from the provided Drive spreadsheet into a reviewable Verra-style PDD Word document. Use retrieved spreadsheet facts where available, generate explicitly labeled synthetic assumptions for missing data, and preserve provenance so the resulting DOCX is useful for internal drafting but clearly not mistaken for a final audited filing.

## Context Snapshot
- **Current state:** The repo already inventories Drive files, drafts section-by-section PDD content from a structured `ProjectInput`, and exports a generic Verra-style DOCX via `src/pdd_agent/export/docx_export.py`; the current demo input in `configs/projects/demo_socson_like.yaml` is synthetic and the benchmark still produces unsupported placeholders rather than a review-ready Vietnam project document.
- **Desired state:** A user can point the tool at the provided spreadsheet `WtE plants carbon model early draft.xlsx`, select a Vietnam WTE candidate such as the Soc Son row, map spreadsheet fields into `ProjectInput`, fill unresolved fields through an explicit synthetic-assumption layer, and export a Verra-template-aligned Word PDD with citations and assumption disclosures.
- **Key repo surfaces:** `src/pdd_agent/ingest/drive.py`, `src/pdd_agent/cli.py`, `schemas/project_input.py`, `schemas/pdd_section_schema.yaml`, `docs/provenance-policy.md`, `src/pdd_agent/agent/section_orchestrator.py`, `src/pdd_agent/export/docx_export.py`, `configs/projects/demo_socson_like.yaml`, `reports/demo-scorecard.md`, `template/VCS_Soc Son_Project-Description.pdf`, `data/runs/`, and a new spreadsheet-mapping/config area under `configs/` or `src/pdd_agent/phase06/`.
- **Out of scope:** Registry submission, legal or validator sign-off, broad non-Vietnam project support, automated extraction from arbitrary spreadsheets with no configuration, and silent invention of critical methodology facts without an assumption register.

## Research Inputs
- `research/2026-04-22_wte-pdd-ingestion.md` - Confirms the repo should stay provenance-first, section-scoped, and `gws`-based; this directly affects sequencing by putting spreadsheet ingestion and explicit evidence tiers ahead of any polished DOCX work.
- `research/Waste to Energy Carbon Credits.md` - Highlights ACM0022-centered Vietnam/WTE patterns and the double-counting boundary between landfill diversion and fuel substitution, which constrains what synthetic assumptions may safely fill versus what must remain review-gated.

## Assumptions and Constraints
- **ASM-001:** The provided spreadsheet is the main project-fact seed, and its `Projects` sheet currently contains at least one explicit Vietnam candidate row: `Soc Son waste to power plant project` with ACM0022, treatment capacity, electricity generation, estimated annual emission reductions, crediting period text, and a Verra registry reference.
- **ASM-002:** Missing fields required by `schemas/project_input.py` will not all be recoverable from the spreadsheet alone, so the workflow must generate a machine-readable assumption register instead of burying synthetic values directly inside the final prose.
- **ASM-003:** The first implementation target should be one Vietnam project path, preferably Soc Son, because it aligns with the existing repo sample `template/VCS_Soc Son_Project-Description.pdf` and current demo input shape.
- **CON-001:** The final output must be a Word document produced locally through `python-docx` and shaped to a Verra-style template structure rather than a plain markdown dump.
- **CON-002:** Synthetic values may support drafting continuity, but CRITICAL and HIGH_REVIEW sections in `schemas/pdd_section_schema.yaml` still require visible review markers and provenance disclosures.
- **DEC-001:** Spreadsheet ingestion should use the existing `gws` Drive path for file acquisition and a deterministic parser for workbook/tab extraction rather than manual copy/paste.
- **DEC-002:** The workbook should be treated as Tier 4 project-specific evidence only for fields it actually contains; it must not be treated as authoritative for methodology interpretation beyond the provided ACM0022/project metadata.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Ingest and profile the provided Vietnam WTE spreadsheet into a stable internal source format | None | Workbook manifest, sheet profiler, row-selection config, source snapshot |
| PHASE-02 | Map spreadsheet fields and assumption rules into a validated `ProjectInput` contract for one Vietnam project | PHASE-01 | Spreadsheet-to-project mapper, assumption register schema, Vietnam project YAML |
| PHASE-03 | Improve drafting so missing data becomes explicit synthetic assumptions with provenance-aware section output | PHASE-02 | Assumption-aware draft pipeline, section provenance updates, review-state rules |
| PHASE-04 | Align DOCX export to a Verra-template-oriented Word deliverable with assumption appendix and reviewer cues | PHASE-03 | Enhanced DOCX exporter, template-aligned headings/tables, assumption appendix |
| PHASE-05 | Run an end-to-end Soc Son-or-similar Vietnam workflow and produce a review package for later human refinement | PHASE-04 | Draft run JSON, DOCX PDD, assumption log, validation report, operator guidance |

## Detailed Phases

### PHASE-01 - Spreadsheet Intake and Vietnam Candidate Profiling
**Goal**
Bring the provided Drive spreadsheet into the repo as a reproducible source artifact, inspect its workbook structure, and formalize how Vietnam candidate rows are selected for downstream PDD generation.

**Tasks**
- [ ] TASK-01-01: Add a spreadsheet acquisition path that downloads the workbook `1tMcKxUGE5aIs-3BQ7sJtjKHeOdSLUhKG` through `gws` into a stable local cache such as `data/source_inputs/spreadsheets/`.
- [ ] TASK-01-02: Create a workbook profiling utility that records sheet names, dimensions, header rows, and sample cells so the repo can detect tab drift without manually opening Excel.
- [ ] TASK-01-03: Add a row-selection config for the `Projects` sheet that identifies Vietnam WTE candidates, starting with the `Soc Son waste to power plant project` row and its ACM0022 / annual ER / electricity / capacity columns.
- [ ] TASK-01-04: Persist a normalized JSON snapshot of the chosen row plus workbook metadata so later phases can run offline and deterministically.
- [ ] TASK-01-05: Capture which workbook tabs are informative but non-authoritative for PDD drafting, including `Model`, `Projects`, `DOXACO`, and `Claude Log`, and document which of them may feed facts versus assumptions versus audit notes.

**Files / Surfaces**
- `src/pdd_agent/ingest/drive.py` - Existing Drive download logic should be extended or reused for workbook acquisition.
- `src/pdd_agent/cli.py` - Needs a command surface for spreadsheet fetch/profile/select flows.
- `data/source_inputs/spreadsheets/` - Stable cache location for the downloaded workbook and normalized row snapshots.
- `configs/source_mappings/vietnam_wte_projects.yaml` - Deterministic workbook/tab/header mapping rules for the provided file.
- `reports/source-profile-vietnam-wte.md` - Human-readable workbook profile and candidate-row summary.
- `tmp_wte_model.xlsx` - Temporary evidence from this planning session confirms workbook structure and should be replaced by a tracked cache path in implementation.

**Dependencies**
- Continued Drive access to file `1tMcKxUGE5aIs-3BQ7sJtjKHeOdSLUhKG`.
- A Python Excel parser such as `openpyxl` available in the runtime environment.

**Exit Criteria**
- [ ] A repeatable command can fetch the workbook and profile its sheets without manual spreadsheet editing.
- [ ] The selected Vietnam candidate row is saved in normalized JSON with source workbook, sheet, row index, and raw field values.
- [ ] The repo contains a documented rule set explaining which workbook cells feed direct facts and which do not.

**Phase Risks**
- **RISK-01-01:** Spreadsheet headers or row offsets may drift over time; mitigate by keying mappings to header labels plus sanity checks rather than hard-coded cell coordinates alone.
- **RISK-01-02:** The workbook mixes commercial modeling notes with project facts; mitigate by separating source profiling from factual mapping and treating `Claude Log` as contextual only.

### PHASE-02 - ProjectInput Mapping and Synthetic Assumption Layer
**Goal**
Convert one Vietnam workbook row into a valid `ProjectInput` payload while making every missing or inferred field explicit through an assumption registry instead of hidden defaults.

**Tasks**
- [ ] TASK-02-01: Create a spreadsheet-to-`ProjectInput` mapper that fills available fields such as project name, country, methodology, throughput/capacity-like metrics, electricity generation, annual ER, and crediting period.
- [ ] TASK-02-02: Define an `assumption register` structure for unresolved fields required by `schemas/project_input.py`, including location precision, proponent identity, contact email, ownership wording, landfill coordinates, grid emission factor source text, safeguards evidence, and monitoring-plan details.
- [ ] TASK-02-03: Implement tiered fill rules: direct spreadsheet values first, reusable repo/demo defaults second when clearly generic, synthetic assumptions third with a label, rationale, and confidence tag.
- [ ] TASK-02-04: Produce a first Vietnam project YAML such as `configs/projects/vietnam_socson_from_sheet.yaml` plus a companion assumptions file.
- [ ] TASK-02-05: Add validation tests showing that the generated project YAML passes `ProjectInput.model_validate()` while preserving machine-readable traceability for every inferred value.
- [ ] TASK-02-06: Encode rules that prohibit synthetic assumptions from silently resolving double-counting-sensitive claims, methodology deviations, or unsupported quantitative formulas.

**Files / Surfaces**
- `schemas/project_input.py` - Existing required-field contract that the spreadsheet mapper must satisfy.
- `configs/projects/vietnam_socson_from_sheet.yaml` - Primary generated project config for the Vietnam case.
- `configs/projects/vietnam_socson_from_sheet.assumptions.yaml` - Companion file listing synthetic fills, rationale, confidence, and source gaps.
- `src/pdd_agent/phase06/spreadsheet_mapper.py` - New deterministic workbook-row to `ProjectInput` mapping logic.
- `src/pdd_agent/phase06/assumptions.py` - Rule engine for generating and labeling synthetic assumptions.
- `tests/test_spreadsheet_mapper.py` - Regression coverage for workbook parsing and field mapping.
- `tests/test_assumptions_layer.py` - Regression coverage for assumption generation and guardrails.

**Dependencies**
- PHASE-01 workbook profile, normalized row snapshot, and mapping config.
- Existing project schema and provenance rules already in the repo.

**Exit Criteria**
- [ ] One Vietnam project config is produced from the spreadsheet and validates against `ProjectInput`.
- [ ] Every non-source-backed field is captured in an assumptions file with rationale and confidence metadata.
- [ ] Guardrails prevent synthetic assumptions from bypassing CRITICAL schema sections or double-counting checks.

**Phase Risks**
- **RISK-02-01:** `ProjectInput` currently demands fields that may be impossible to infer credibly from the workbook alone; mitigate by adding explicit assumption metadata rather than weakening validation silently.
- **RISK-02-02:** Over-reliance on the current demo config may accidentally copy Soc Son-like filler into unrelated facts; mitigate by tagging any reused value as synthetic and source-linked to the template/demo origin.

### PHASE-03 - Assumption-Aware Drafting and Review Rules
**Goal**
Make the drafting pipeline understand the difference between real project facts, retrieved corpus patterns, and synthetic assumptions so the produced PDD text remains reviewable rather than deceptively complete.

**Tasks**
- [ ] TASK-03-01: Extend the drafting input model so each fact can carry provenance type such as `spreadsheet`, `corpus`, `methodology`, `synthetic_assumption`, or `demo_default`.
- [ ] TASK-03-02: Update section prompt assembly to surface assumption-backed fields explicitly and instruct the provider to label them in output prose or notes when they influence a section.
- [ ] TASK-03-03: Add review checks that downgrade confidence or force issue flags when HIGH_REVIEW or CRITICAL sections depend on synthetic assumptions.
- [ ] TASK-03-04: Modify run persistence so section outputs store which sentences or tables relied on synthetic inputs.
- [ ] TASK-03-05: Add a report artifact summarizing assumption burden by section, distinguishing harmless boilerplate fills from material domain gaps.
- [ ] TASK-03-06: Re-run the existing demo benchmark style checks with the new Vietnam config to verify the pipeline produces better disclosure even if final factual support remains incomplete.

**Files / Surfaces**
- `src/pdd_agent/agent/section_orchestrator.py` - Needs provenance-rich prompt assembly and section output persistence.
- `prompts/section_draft.md` - Needs updated instructions for assumption disclosure and anti-hallucination behavior.
- `docs/provenance-policy.md` - Should be extended to define how synthetic assumptions are permitted, labeled, and review-gated.
- `src/pdd_agent/review/checks.py` - Should add assumption-aware blocking/non-blocking rules.
- `src/pdd_agent/review/states.py` - Should persist state transitions caused by unresolved synthetic dependence.
- `reports/assumption-burden.md` - New reviewer-focused artifact listing where the draft still depends on assumptions.
- `tests/test_review_checks.py` - Needs coverage for synthetic-assumption review flags.

**Dependencies**
- PHASE-02 validated project YAML plus assumption register.
- Existing section schema and review-state model.

**Exit Criteria**
- [ ] Draft sections identify when they rely on synthetic assumptions rather than presenting those values as plain facts.
- [ ] HIGH_REVIEW and CRITICAL sections fail closed into warnings, placeholders, or review issues when synthetic coverage is too heavy.
- [ ] Draft run JSON preserves enough provenance to audit each assumption-dependent section later.

**Phase Risks**
- **RISK-03-01:** The current `noop` provider may still produce placeholder-heavy output even with better inputs; mitigate by treating this phase as a disclosure-quality upgrade first, not a promise of polished language.
- **RISK-03-02:** Over-labeling every sentence could make the document unreadable; mitigate by using inline provenance sparingly in body text and moving detailed assumption traces to appendices/tables.

### PHASE-04 - Verra-Template-Oriented DOCX Export
**Goal**
Turn the assumption-aware draft into a Word document that looks and navigates like a Verra-style PDD, while exposing synthetic content and review issues in a controlled reviewer-friendly format.

**Tasks**
- [ ] TASK-04-01: Inspect `template/VCS_Soc Son_Project-Description.pdf` and the Verra section schema to define a stronger DOCX layout contract for title page, numbered sections, subsection headings, metadata tables, and appendices.
- [ ] TASK-04-02: Enhance `src/pdd_agent/export/docx_export.py` so it can render a Vietnam project PDD with clearer heading hierarchy, cover metadata, methodology labels, and section-level provenance formatting.
- [ ] TASK-04-03: Add an assumption appendix that lists each synthetic field, its rationale, and where it affects the document.
- [ ] TASK-04-04: Add a reviewer issues appendix summarizing unresolved evidence gaps, CRITICAL sections needing domain sign-off, and any sections that still mirror placeholder/demo language.
- [ ] TASK-04-05: Ensure the exporter can optionally insert a front-matter disclaimer such as `Internal draft for review; contains synthetic assumptions for missing project data`.
- [ ] TASK-04-06: Verify `python-docx` installation and add runtime checks/documentation so Word export is not skipped silently.

**Files / Surfaces**
- `src/pdd_agent/export/docx_export.py` - Primary DOCX rendering surface to upgrade.
- `template/VCS_Soc Son_Project-Description.pdf` - Best available local reference for Verra-style structure and section ordering.
- `schemas/pdd_section_schema.yaml` - Canonical numbering source for headings and review sensitivity.
- `README.md` - Needs updated operator guidance for Word-PDD generation from spreadsheet inputs.
- `tests/test_docx_export.py` - New export regression tests for heading order, appendices, and disclaimer rendering.
- `data/runs/{run_id}.docx` - Final Word output artifact location.

**Dependencies**
- PHASE-03 assumption-aware section outputs.
- Working local `python-docx` installation.

**Exit Criteria**
- [ ] A generated `.docx` follows the repo’s Verra-style heading structure and is usable as a review draft in Word.
- [ ] The DOCX contains an explicit assumption appendix and reviewer issue summary.
- [ ] Export fails with a clear actionable error if `python-docx` is missing.

**Phase Risks**
- **RISK-04-01:** Without the official editable Verra template, the DOCX may only be structurally similar rather than pixel-faithful; mitigate by optimizing for section fidelity and review utility first.
- **RISK-04-02:** Too much appendix material can overwhelm the main draft; mitigate by keeping the body clean and pushing detailed assumption audit data to back matter.

### PHASE-05 - End-to-End Vietnam Draft Run and Review Package
**Goal**
Run the full workflow on one Vietnam WTE project and leave behind a concrete review package that you can inspect later, including Word output, assumptions, and validation artifacts.

**Tasks**
- [ ] TASK-05-01: Create a single command or script that performs workbook fetch/profile, project mapping, assumption generation, drafting, review, and DOCX export for the selected Vietnam project.
- [ ] TASK-05-02: Execute the workflow for Soc Son first, using the spreadsheet row plus the existing repo corpus/template context.
- [ ] TASK-05-03: Generate a review bundle containing project YAML, assumption YAML, draft run JSON, review-state JSON, Word PDD, and at least one human-readable validation report.
- [ ] TASK-05-04: Add a gap analysis that lists which missing data points most reduced document confidence and which new external documents would improve the draft fastest.
- [ ] TASK-05-05: Document the exact operator steps for rerunning the Vietnam PDD workflow on later spreadsheet revisions or a second Vietnam candidate.

**Files / Surfaces**
- `scripts/run_vietnam_pdd.py` - One-command runner for the spreadsheet-to-DOCX flow.
- `configs/projects/vietnam_socson_from_sheet.yaml` - Reused end-to-end config artifact.
- `configs/projects/vietnam_socson_from_sheet.assumptions.yaml` - Reused assumption source of truth.
- `reports/vietnam-pdd-gap-analysis.md` - Follow-up report on missing evidence and next-best data sources.
- `reports/vietnam-pdd-runbook.md` - Operator instructions for later reuse.
- `data/runs/` - Stores run JSON, review state, and DOCX output.

**Dependencies**
- PHASE-04 completed export and disclosure surfaces.
- One stable Vietnam project row selected from the workbook.

**Exit Criteria**
- [ ] One command produces a Word PDD draft for the Vietnam project plus its assumptions and review artifacts.
- [ ] The resulting package is transparent about what came from the spreadsheet, what came from corpus/template patterns, and what was synthetic.
- [ ] The repo contains enough guidance to rerun the process after spreadsheet updates without reopening this conversation.

**Phase Risks**
- **RISK-05-01:** The spreadsheet may not contain enough project-specific evidence to make the end document truly persuasive; mitigate by treating this as an internal draft accelerator and by outputting a focused missing-evidence list.
- **RISK-05-02:** Benchmark/demo limitations shown in `reports/demo-scorecard.md` may carry over; mitigate by measuring success on transparency and workflow completeness, not only prose quality.

## Verification Strategy
- **TEST-001:** Add automated tests for workbook profiling, header/row selection, spreadsheet-to-`ProjectInput` mapping, and assumption generation.
- **TEST-002:** Add regression tests ensuring synthetic assumptions are surfaced as provenance and trigger review flags in HIGH_REVIEW and CRITICAL sections.
- **TEST-003:** Add DOCX export tests that verify section ordering, disclaimer presence, assumption appendix creation, and review issue appendix creation.
- **MANUAL-001:** Open the generated `.docx` in Word and compare its structure against `template/VCS_Soc Son_Project-Description.pdf` for section ordering, readability, and reviewer usability.
- **MANUAL-002:** Inspect the Vietnam project YAML and assumptions file to confirm that no required `ProjectInput` field was filled silently without either a real source or an explicit synthetic marker.
- **OBS-001:** Track counts for spreadsheet-sourced fields, synthetic assumptions, blocked CRITICAL sections, and total review issues per run.

## Risks and Alternatives
- **RISK-001:** Treating workbook model outputs as project facts could leak commercial assumptions into the PDD; mitigate by separating factual row extraction from modeling tabs and by storing assumption provenance explicitly.
- **RISK-002:** The current repo’s unsupported-placeholder benchmark behavior may still limit narrative quality; mitigate by prioritizing reviewable structure, provenance, and Word output first, then iterate on language quality.
- **RISK-003:** Missing `python-docx` at runtime currently blocks export; mitigate by making dependency verification part of the run path and documentation.
- **ALT-001:** Manually copy spreadsheet facts into `configs/projects/demo_socson_like.yaml` and export from there; not chosen because it is not reproducible and loses source-to-field auditability.
- **ALT-002:** Skip synthetic assumptions and require only fully evidenced inputs; not chosen because the user explicitly wants a draftable PDD path even when source data is incomplete.
- **ALT-003:** Generate a markdown PDD only and let a human reformat it in Word later; not chosen because the requested outcome is a Verra-style Word document for later review.

## Grill Me
No open clarification questions.

## Suggested Next Step
Implement PHASE-01 and PHASE-02 together for the Soc Son Vietnam row first, because that will expose the real spreadsheet-to-`ProjectInput` gaps before any DOCX-template polishing work begins.
