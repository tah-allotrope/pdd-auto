# PDD Agent — Agentic Low-Cost WTE Carbon-Credit PDD Drafting Tool

**Status:** Codex Insights Integration & Inegol Demo Case — ALL PHASES COMPLETE (2026-05-21). 204 tests pass. Inegol end-to-end demo produces 36-section DOCX with zero review flags. Pipeline proven superior to standalone Codex script per quantitative comparison.

**Demo Quickstart:** Want to see it working in 5 minutes? → [QUICKSTART.md](QUICKSTART.md)

## What This Tool Does

Builds Verra VCS Project Design Documents (PDDs) for waste-to-energy (WTE) carbon credit projects using a corpus-bucketed RAG approach — no external API costs required for retrieval, optional LLM calls only where rule-based methods are insufficient.

```
Drive (gws) → Download → Normalize → Bucket → FTS5 Index
                                                      ↓
ProjectInput YAML ──→ SectionOrchestrator ──→ DraftRun
                           ↓
                    run_review() ──→ ReviewStateStore
                           ↓
                    DOCX Export ──→ Drive Upload (gws)
```

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Ingest corpus from VERRA Drive folder
pdd-agent ingest --folder-id 1pp23yRZ8qtopw1BPXrzVewXsmmWplCse

# Build the FTS5 retrieval index (required before drafting)
pdd-agent build-index --corpus-dir data/corpus/normalized --index-db data/index/corpus.fts.db

# Draft a project (requires a ProjectInput YAML)
pdd-agent draft --input configs/projects/demo_socson_like.yaml --provider noop

# Create or refresh the reproducible Soc Son-like demo input
pdd-agent demo-config

# Run the Phase-05 benchmark and generate scorecards
pdd-agent benchmark --input configs/projects/demo_socson_like.yaml

# Download the Vietnam WTE workbook into the tracked cache
pdd-agent fetch-workbook

# Map the Soc Son spreadsheet row into ProjectInput + assumptions artifacts
pdd-agent map-spreadsheet --candidate soc-son

# Run the full Vietnam spreadsheet -> draft -> review -> DOCX workflow
pdd-agent run-vietnam-pdd

# Export to DOCX for human review
pdd-agent export --run-id <run-id>

# Upload DOCX to VERRA Drive folder
pdd-agent upload --run-id <run-id>
```

## CLI Commands

| Command | Description |
|---|---|
| `pdd-agent ingest` | Full pipeline: inventory → download → normalize → bucket |
| `pdd-agent build-index` | Build SQLite FTS5 BM25 index from normalized corpus |
| `pdd-agent draft` | Draft all PDD sections for a project |
| `pdd-agent review` | Display review state for a run |
| `pdd-agent export` | Export DraftRun to DOCX |
| `pdd-agent upload` | Upload DOCX to Google Drive via gws |
| `pdd-agent demo-config` | Write the reproducible Soc Son-like benchmark input |
| `pdd-agent benchmark` | Run Phase-05 benchmark and write scorecards |
| `pdd-agent fetch-workbook` | Cache the Vietnam WTE workbook under `data/source_inputs/spreadsheets/` |
| `pdd-agent map-spreadsheet` | Profile the workbook and generate Vietnam ProjectInput + assumptions artifacts |
| `pdd-agent run-vietnam-pdd` | Run the full Vietnam spreadsheet-to-review-package workflow |

## Architecture

### Corpus Ingestion (PHASE-01)
- **`src/pdd_agent/ingest/drive.py`** — `gws` CLI wrapper. All Drive I/O through subprocess; no Google SDK needed.
- **`src/pdd_agent/ingest/download.py`** — MIME-aware downloader for blobs (PDF/DOCX) and workspace-native files.
- **`src/pdd_agent/ingest/normalize.py`** — pypf/pdfplumber text extraction, heading detection, surrogate character handler. Produces `headings[]` and `text_blocks[]` for FTS indexing.
- **`src/pdd_agent/ingest/bucket.py`** — WTE keyword scoring, inclusion/exclusion rules from `configs/corpus_buckets/verra-wte-initial.yaml`.

### Domain & Schema (PHASE-02)
- **`schemas/pdd_section_schema.yaml`** — Canonical 5-section, 30-subsection taxonomy with content class, review sensitivity, and heading alias drift map.
- **`schemas/project_input.py`** — Pydantic `ProjectInput` model with double-counting and net-emissions validators.
- **`rules/verra/wte_methodology_rules.yaml`** — ACM0022/ACM0003 applicability conditions, WTE safeguards (WTE-SAFE-01 to 04), PRE/POST compliance checks.
- **`src/pdd_agent/domain/methodology_rules.py`** — Typed Python wrapper with `run_pre_draft_checks()` and `run_post_draft_checks()`.
- **`src/pdd_agent/parse/section_parser.py`** — Maps normalized corpus docs to canonical schema, alias index, coverage scoring.

### Vietnam Spreadsheet Intake and Delivery (PHASE-01 to PHASE-05)
- **`configs/source_mappings/vietnam_wte_projects.yaml`** — Deterministic workbook selection rules for the Vietnam WTE spreadsheet and Soc Son candidate row.
- **`src/pdd_agent/phase06/spreadsheet_mapper.py`** — Workbook fetch/profile/select logic plus ProjectInput and assumptions generation.
- **`src/pdd_agent/phase06/vietnam_workflow.py`** — One-command runner that maps the spreadsheet row, drafts the PDD, writes review artifacts, exports DOCX, and produces PHASE-05 reports.
- **`scripts/run_vietnam_pdd.py`** — One-command helper for the spreadsheet-to-artifact flow.
- **`data/source_inputs/spreadsheets/`** — Tracked workbook cache plus generated profile and row snapshot JSON.
- **`configs/projects/vietnam_socson_from_sheet.yaml`** — Generated Soc Son ProjectInput from the spreadsheet row.
- **`configs/projects/vietnam_socson_from_sheet.assumptions.yaml`** — Machine-readable assumption register and blocked review items.
- **`reports/source-profile-vietnam-wte.md`** — Human-readable workbook profile and selected-row report.
- **`reports/vietnam-pdd-validation.md`** — Human-readable validation report for the latest end-to-end Vietnam run.
- **`reports/vietnam-pdd-gap-analysis.md`** — Missing-evidence prioritization report showing which facts most reduced confidence.
- **`reports/vietnam-pdd-runbook.md`** — Operator rerun instructions for spreadsheet refreshes and future Vietnam candidates.

### Retrieval & Drafting (PHASE-03)
- **`src/pdd_agent/retrieval/index.py`** — SQLite FTS5 BM25 index. `RetrievalIndex.build()` indexes the corpus once; `search()` and `get_section_examples()` query it.
- **`src/pdd_agent/retrieval/search.py`** — Query cleaning, BM25 ranking, centered excerpt highlighting.
- **`src/pdd_agent/llm/provider.py`** — `BaseProvider` ABC, `NoopProvider` (placeholder), `DraftRun` persistence, and section-level provenance / synthetic-use metadata.
- **`src/pdd_agent/phase06/assumptions.py`** — Companion assumptions-register loader plus section routing and assumption-burden reporting helpers.
- **`src/pdd_agent/agent/section_orchestrator.py`** — Per-section retrieval → prompt assembly → provider call → assumption-aware review gate pipeline. `run()` and `run_review()` methods.

### Review & Export (PHASE-04)
- **`src/pdd_agent/review/checks.py`** — DC-01 to DC-04 double-counting guards, quantitative cross-refs (1.10↔4.4), evidence requirements, auto-approval logic, and assumption-aware review gates.
- **`src/pdd_agent/review/consistency.py`** — Cross-section numeric consistency: net tCO2e arithmetic, baseline/project/leakage relation, crediting period total.
- **`src/pdd_agent/review/states.py`** — 5-state review workflow (drafted→needs-input→drafted, drafted→needs-domain-review→ready-for-human-edit→approved). JSON persistence to `data/runs/review-state-{run_id}.json`.
- **`src/pdd_agent/export/docx_export.py`** — python-docx export with a front-matter disclaimer, cover metadata, section-level source summaries, an assumption appendix, and a reviewer issues appendix.
- **`src/pdd_agent/export/drive_upload.py`** — `gws drive files create` subprocess wrapper.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for `gws` CLI)
- **`gws`** authenticated: `npm install -g @googleworkspace/cli && gws auth setup`
- Access to VERRA Drive folder `1pp23yRZ8qtopw1BPXrzVewXsmmWplCse`

## Phase Status

| Phase | Goal | Status |
|---|---|---|
| PHASE-01 | Drive ingestion, corpus bucketing | ✅ Complete |
| PHASE-02 | Section schema, domain rules, methodology | ✅ Complete |
| PHASE-03 | Retrieval, agentic drafting, provider abstraction | ✅ Complete |
| PHASE-04 | Compliance checks, review workflow, DOCX export | ✅ Complete |
| PHASE-05 | End-to-end benchmark and demo | ✅ Complete |
| Vietnam PHASE-01 | Spreadsheet intake and candidate profiling | ✅ Complete for Soc Son |
| Vietnam PHASE-02 | ProjectInput mapping and assumptions layer | ✅ Complete for Soc Son |
| Vietnam PHASE-03 | Assumption-aware drafting and review rules | ✅ Complete for Soc Son |
| Vietnam PHASE-04 | Verra-style DOCX export and appendices | ✅ Complete for Soc Son |
| Vietnam PHASE-05 | End-to-end run, review package, gap analysis, rerun guidance | ✅ Complete for Soc Son |

## Phase-05 Deliverables

- `configs/projects/demo_socson_like.yaml` — reproducible Soc Son-like input for benchmark runs
- `configs/projects/demo_socson_like.assumptions.yaml` — deterministic demo assumptions companion with `demo_curated` provenance and no review-gated gaps
- `scripts/run_demo.py` — one-command benchmark runner
- `reports/demo-scorecard.md` — benchmark scorecard with review-burden and grounding metrics
- `reports/section-diff.md` — per-section comparison notes against the Soc Son reference

## Vietnam Spreadsheet Workflow

```bash
# One-command end-to-end run
python scripts/run_vietnam_pdd.py

# Equivalent CLI one-command workflow
pdd-agent run-vietnam-pdd --upload-review-docx

# Equivalent manual CLI workflow
pdd-agent fetch-workbook
pdd-agent map-spreadsheet --candidate soc-son

# Assumption-aware draft and review run
pdd-agent draft --input configs/projects/vietnam_socson_from_sheet.yaml --provider noop

# Export the saved run to the reviewer-facing package area
pdd-agent export --run-id <run-id> --review-output-dir reports/review-packages

# Upload a published reviewer-facing DOCX
pdd-agent upload --review-docx reports/review-packages/<project-slug>/latest.docx
```

The Vietnam spreadsheet workflow will:

1. Cache `WtE plants carbon model early draft.xlsx` under `data/source_inputs/spreadsheets/`
2. Profile workbook tabs and save `data/source_inputs/spreadsheets/vietnam_wte_profile.json`
3. Select the Soc Son row and save `data/source_inputs/spreadsheets/vietnam_socson_snapshot.json`
4. Generate `configs/projects/vietnam_socson_from_sheet.yaml`
5. Generate `configs/projects/vietnam_socson_from_sheet.assumptions.yaml`
6. Write `reports/source-profile-vietnam-wte.md` with review-gated assumption notes
7. Draft a run whose sections persist fact provenance, synthetic usage, and review sensitivity
8. Write `reports/assumption-burden.md` summarizing material assumption burden by section
9. Write `reports/vietnam-pdd-validation.md`, `reports/vietnam-pdd-gap-analysis.md`, and `reports/vietnam-pdd-runbook.md`
10. Export a DOCX with an internal-draft disclaimer, assumption appendix, and reviewer issues appendix
11. Publish a reviewer-facing package under `reports/review-packages/<project-slug>/<run-id>/` and refresh `reports/review-packages/<project-slug>/latest.docx`
12. Optionally upload the published reviewer-facing DOCX to Drive and surface the resulting URL in the workflow logs

## Demo Workflow

```bash
# One-command benchmark run
python scripts/run_demo.py

# Equivalent CLI workflow
pdd-agent demo-config
pdd-agent benchmark --input configs/projects/demo_socson_like.yaml --demo-output-dir reports/demo-packages
```

The benchmark workflow will:

1. Create or reuse the Soc Son-like demo config
2. Write `configs/projects/demo_socson_like.assumptions.yaml` with deterministic `demo_curated` provenance for the synthetic demo fixture
3. Run the draft and review pipeline end-to-end using the `DemoProvider`
4. Compare the saved run against the normalized Soc Son reference
5. Write `reports/demo-scorecard.md` and `reports/section-diff.md`
6. Export a demo DOCX with strong synthetic disclosure and a clean "Appendix A - Assumption Summary"
7. Publish `reports/demo-packages/<project-slug>/<run-id>/` and refresh `latest.docx` when `--demo-output-dir` is provided

The resulting DOCX contains readable synthetic prose with zero `[PLACEHOLDER` markers, zero `REVIEW REQUIRED` issues in the body, and aligned quantification numbers across all sections. The cover page carries a bold synthetic disclosure and the appendix lists demo-curated assumptions without reviewer-gated blocked items.

`python scripts/run_demo.py` runs the deterministic demo provider and publishes the client-demo package under `reports/demo-packages/`. The equivalent CLI path is `pdd-agent benchmark --provider demo --demo-output-dir reports/demo-packages`.

## Inegol Demo Workflow (Codex Insights Integration)

```bash
# Run the Inegol integrated waste-to-energy demo end to end
python scripts/run_inegol_demo.py

# Generate a comparison report vs the Codex reference artifact
python scripts/compare_codex_vs_pipeline.py
```

The Inegol workflow will:

1. Load `configs/demo/inegol_project_input.yaml` (reverse-engineered from Codex reference DOCX)
2. Validate against the extended `ProjectInput` schema with Inegol-specific fields
3. Draft all 36 sections using the generic `DemoProvider`
4. Run consistency + TBD + compliance review checks
5. Export a DOCX using the official Verra VCS v4.4 template with 11 structured table types
6. Print a summary: sections drafted, review flags, TBD markers, runtime
7. Comparison script generates `reports/2026-05-21-codex-vs-pipeline-comparison.md`

### Inegol Demo Results (2026-05-21)

- **Sections drafted:** 36 (same as Codex reference)
- **Review flags:** 0 critical, 0 high
- **TBD markers:** 0
- **Runtime:** 0.3 seconds
- **DOCX size:** 225 KB
- **Comparison:** Pipeline matches Codex on section count, exceeds on provenance tracking (36 vs 0), review checks (4 layers vs 0), and appendices (3 vs 2)
- **Key files:**
  - `configs/demo/inegol_project_input.yaml`
  - `scripts/run_inegol_demo.py`
  - `scripts/compare_codex_vs_pipeline.py`
  - `reports/2026-05-21-codex-vs-pipeline-comparison.md`
  - `reports/2026-05-21-inegol-end-to-end-demo.html`

### Demo Artifact Paths

After a successful run, the client-demo package lives at:
- `reports/demo-packages/<project-slug>/<run-id>/<run-id>.docx` — immutable run archive
- `reports/demo-packages/<project-slug>/<run-id>/manifest.json` — run metadata and artifact inventory
- `reports/demo-packages/<project-slug>/latest.docx` — stable alias for the latest package
- `reports/demo-scorecard.md` — benchmark scorecard with coverage and grounding metrics
- `reports/section-diff.md` — per-section comparison against the Soc Son reference

## Artifact Contracts

- `reports/review-packages/` is the internal review artifact area. It is expected to contain placeholder section bodies, review notes, assumption-heavy content, and reviewer-issue appendices when the workflow runs with provider `noop`.
- `reports/demo-packages/` is the reserved client-demo artifact area. The intended contract is a readable synthetic sample with a strong cover disclosure, aligned numbers, and summary-level synthetic assumptions only.
- `configs/projects/demo_socson_like.assumptions.yaml` is the current synthetic input surface for the future client-demo path. Its entries use `demo_curated` provenance and intentionally avoid `blocked_review_paths` so later phases can build client-safe prose without inheriting spreadsheet review gates.
- `pdd-agent run-vietnam-pdd` remains the reviewer-facing workflow. It should keep publishing review packages under `reports/review-packages/` and must not silently change into the future client-demo workflow.
- Phase 01 documentation for the split lives in `reports/demo-artifact-contract.md`.

## Key Files

```
src/pdd_agent/
├── cli.py                          # CLI entry point (6 commands)
├── ingest/                         # PHASE-01: Drive, download, normalize, bucket
├── parse/section_parser.py         # PHASE-02: Corpus → canonical schema mapper
├── domain/methodology_rules.py     # PHASE-02: Verra WTE rules engine
├── retrieval/index.py              # PHASE-03: SQLite FTS5 BM25 index
├── retrieval/search.py             # PHASE-03: Retrieval query API
├── llm/provider.py                 # PHASE-03: Provider abstraction + NoopProvider
├── llm/openai_provider.py          # PHASE-03: OpenAI stub (not wired)
├── llm/ollama_provider.py         # PHASE-03: Ollama stub (not wired)
├── agent/section_orchestrator.py   # PHASE-03+04: Drafting + review pipeline
├── review/checks.py               # PHASE-04: Rule-based compliance checks
├── review/consistency.py          # PHASE-04: Cross-section numeric consistency
├── review/states.py               # PHASE-04: Approval state machine
└── export/docx_export.py         # PHASE-04: DOCX template writer
```

## Known Gaps

- `python-docx` is declared in `pyproject.toml`, but local environments still need it installed before DOCX export works at runtime; the exporter now fails with a clear install message instead of skipping silently
- No real LLM provider wired — benchmark runs use the deterministic `DemoProvider` for client-demo output or the `NoopProvider` for reviewer-facing placeholder draft
- The `reports/demo-packages/` client-demo path is now implemented — `python scripts/run_demo.py` publishes a readable synthetic DOCX with zero placeholders, aligned quantification, and a strong synthetic disclosure
- The first benchmark is a workflow proof on one Soc Son-like case; a second project is still needed before claiming broader WTE coverage
- The Soc Son spreadsheet mapper intentionally blocks review-sensitive quantitative splits, coordinates, and safeguards fields when they rely on synthetic assumptions

## Key References

- [Verra VCS Program](https://verra.org/programs/verified-carbon-standard/)
- [gws CLI](https://github.com/googleworkspace/cli)
- [ACM0022 — Alternative waste treatment](https://verra.org/methodologies/)
