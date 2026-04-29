# PDD Agent — Agentic Low-Cost WTE Carbon-Credit PDD Drafting Tool

**Status:** PHASE-05 complete, with Vietnam PHASE-01 through PHASE-04 now implemented for the Soc Son row.

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
- `scripts/run_demo.py` — one-command benchmark runner
- `reports/demo-scorecard.md` — benchmark scorecard with review-burden and grounding metrics
- `reports/section-diff.md` — per-section comparison notes against the Soc Son reference

## Vietnam Spreadsheet Workflow

```bash
# One-command end-to-end run
python scripts/run_vietnam_pdd.py

# Equivalent CLI one-command workflow
pdd-agent run-vietnam-pdd

# Equivalent manual CLI workflow
pdd-agent fetch-workbook
pdd-agent map-spreadsheet --candidate soc-son

# Assumption-aware draft and review run
pdd-agent draft --input configs/projects/vietnam_socson_from_sheet.yaml --provider noop

# Export the saved run to Word
pdd-agent export --run-id <run-id>
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

## Demo Workflow

```bash
# One-command benchmark run
python scripts/run_demo.py

# Equivalent CLI workflow
pdd-agent demo-config
pdd-agent benchmark --input configs/projects/demo_socson_like.yaml
```

The benchmark workflow will:

1. Create or reuse the Soc Son-like demo config
2. Run the draft and review pipeline end-to-end
3. Compare the saved run against the normalized Soc Son reference
4. Write `reports/demo-scorecard.md` and `reports/section-diff.md`
5. Export DOCX when `python-docx` is installed locally

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
- No real LLM provider wired — benchmark runs currently measure workflow quality using the zero-cost `NoopProvider`
- The first benchmark is a workflow proof on one Soc Son-like case; a second project is still needed before claiming broader WTE coverage
- The Soc Son spreadsheet mapper intentionally blocks review-sensitive quantitative splits, coordinates, and safeguards fields when they rely on synthetic assumptions

## Key References

- [Verra VCS Program](https://verra.org/programs/verified-carbon-standard/)
- [gws CLI](https://github.com/googleworkspace/cli)
- [ACM0022 — Alternative waste treatment](https://verra.org/methodologies/)
