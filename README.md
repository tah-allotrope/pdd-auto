# PDD Agent — Agentic Low-Cost WTE Carbon-Credit PDD Drafting Tool

**Status:** PHASE-04 complete. Pipeline is ready for end-to-end benchmarking (PHASE-05).

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

### Retrieval & Drafting (PHASE-03)
- **`src/pdd_agent/retrieval/index.py`** — SQLite FTS5 BM25 index. `RetrievalIndex.build()` indexes the corpus once; `search()` and `get_section_examples()` query it.
- **`src/pdd_agent/retrieval/search.py`** — Query cleaning, BM25 ranking, centered excerpt highlighting.
- **`src/pdd_agent/llm/provider.py`** — `BaseProvider` ABC, `NoopProvider` (placeholder), `DraftRun` persistence, `ProviderRegistry`.
- **`src/pdd_agent/agent/section_orchestrator.py`** — Per-section retrieval → prompt assembly → provider call → review gate pipeline. `run()` and `run_review()` methods.

### Review & Export (PHASE-04)
- **`src/pdd_agent/review/checks.py`** — DC-01 to DC-04 double-counting guards, quantitative cross-refs (1.10↔4.4), evidence requirements, auto-approval logic.
- **`src/pdd_agent/review/consistency.py`** — Cross-section numeric consistency: net tCO2e arithmetic, baseline/project/leakage relation, crediting period total.
- **`src/pdd_agent/review/states.py`** — 5-state review workflow (drafted→needs-input→drafted, drafted→needs-domain-review→ready-for-human-edit→approved). JSON persistence to `data/runs/review-state-{run_id}.json`.
- **`src/pdd_agent/export/docx_export.py`** — python-docx export with title page, per-section headings, provenance citations, yellow highlights for LOW/UNSUPPORTED confidence.
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
| PHASE-05 | End-to-end benchmark and demo | Pending |

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

- `python-docx` must be installed (`pip install python-docx`) before `pdd-agent export` will work
- No real LLM provider wired — only `NoopProvider` is operational
- 4 corpus PDFs (Yanjiang, Linfen, Shunping, Yingoku) have malformed JSON after normalization; fixing them expands coverage to 13/13

## Key References

- [Verra VCS Program](https://verra.org/programs/verified-carbon-standard/)
- [gws CLI](https://github.com/googleworkspace/cli)
- [ACM0022 — Alternative waste treatment](https://verra.org/methodologies/)
