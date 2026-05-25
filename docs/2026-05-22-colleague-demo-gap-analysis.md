# Gap Analysis: Colleague-Testable Laptop Demo

**Date:** 2026-05-22
**Scope:** Make the PDD Agent tool runnable as a self-contained demo by colleagues on their own laptops — no specialized infrastructure, no Google Drive auth, no external APIs.
**Status:** Draft for Review

---

## Executive Summary

The core drafting, review, and DOCX export pipeline is mature (204+ tests, two completed project demos, deterministic DemoProvider producing zero-placeholder output). However, a colleague cloning this repo today would face **three critical blockers**: (1) gitignored corpus/index data that the FTS retrieval layer needs is not bundled, (2) `data/runs/` output directory isn't obviously pre-created, and (3) there is no single "clone → install → run one command → see output" quickstart path documented for non-developers. The `gws` (Google Workspace CLI) dependency is hard-wired into `ingest` and `fetch-workbook` commands but does **not** block the demo path since `DemoProvider` and the Inegol demo script bypass retrieval and use bundled YAML configs. Estimated total effort: 1 plan with 3-4 phases, primarily configuration and documentation work with one moderate data-bundling task.

---

## Current Capabilities (What We Have)

| Capability | Status | Key Surfaces |
|---|---|---|
| Deterministic demo drafting (DemoProvider) | Mature | `src/pdd_agent/llm/provider.py:117-144` |
| Soc Son benchmark demo (one-command) | Working | `scripts/run_demo.py`, `pdd-agent benchmark --provider demo` |
| Inegol end-to-end demo (one-command) | Working | `scripts/run_inegol_demo.py` |
| DOCX export with VCS v4.4 template | Mature | `src/pdd_agent/export/docx_export.py`, `templates/VCS-Project-Description-Template-v4.4-FINAL2.docx` |
| 4-layer review pipeline (consistency, TBD, compliance, review states) | Mature | `src/pdd_agent/review/` |
| 36-section canonical schema | Mature | `schemas/pdd_section_schema.yaml` |
| Inegol project config (reverse-engineered) | Working | `configs/demo/inegol_project_input.yaml` |
| Soc Son demo config (deterministic) | Working | `configs/projects/demo_socson_like.yaml` |
| Assumptions companion (Soc Son) | Working | `configs/projects/demo_socson_like.assumptions.yaml` |
| FTS5 BM25 retrieval index | Working (requires build step) | `src/pdd_agent/retrieval/index.py` |
| Normalized corpus (18 docs) | Working (gitignored) | `data/corpus/normalized/*.norm.json` |
| Test suite (211 tests) | Mature | `tests/` |
| CLI entry point | Mature | `src/pdd_agent/cli.py`, `pdd-agent` console script |
| pyproject.toml with editable install | Working | `pyproject.toml` |
| Python 3.11+ only deps (no C extensions) | Working | `pyproject.toml` dependencies |
| Google Drive integration (gws) | Working (needs Node+auth) | `src/pdd_agent/ingest/drive.py` |
| Vietnam spreadsheet workflow | Working (needs gws) | `src/pdd_agent/phase06/vietnam_workflow.py` |

---

## Target State

> A colleague with a standard developer laptop (Python 3.11+, pip, git) can clone this repo, run 2-3 commands, and within 5 minutes have a working Verra VCS PDD draft (DOCX) on their filesystem — without needing Google Drive access, `gws`, Node.js, or any API keys. They should also be able to run the test suite and see the benchmark scorecard. The experience should be documented in a clear quickstart that doesn't require reading the full README or understanding the architecture.

---

## Gap Analysis

### GAP-01: No Zero-Config Demo Quickstart for Fresh Clones

**Severity:** CRITICAL — A colleague cloning the repo has no documented path from `git clone` to a DOCX on disk without reading the full README and understanding which commands are demo-safe vs. require infrastructure.

**Current state:** The README documents 15+ CLI commands covering ingestion, drafting, benchmarking, Vietnam workflow, and upload. The demo workflows (`python scripts/run_demo.py`, `python scripts/run_inegol_demo.py`) are buried in the middle of the README. No "quickstart for demo" section exists that tells a colleague exactly which 2-3 commands to run. The README's "Quick Start" section leads with `pdd-agent ingest --folder-id ...` which requires `gws` auth — an immediate dead end for a colleague without Drive access.

**What's needed:**
- A `QUICKSTART.md` or prominent "Demo Quickstart" section at the top of the README
- Clear "clone → `pip install -e .` → `python scripts/run_demo.py` or `python scripts/run_inegol_demo.py` → open the DOCX" flow
- Explicit statement that no API keys, Drive access, or Node.js are needed for the demo path
- Expected output paths and what the colleague should see when they open the DOCX

**Existing assets to reuse:**
- `scripts/run_demo.py` — already works as a one-command demo runner
- `scripts/run_inegol_demo.py` — already works for the Inegol case
- `README.md` "Demo Workflow" and "Inegol Demo Workflow" sections — content exists, just needs reorganization

**Effort estimate:** Small — 1 phase, documentation-only

---

### GAP-02: Retrieval Index Not Available on Fresh Clone (Degrades Demo Quality Silently)

**Severity:** HIGH — The retrieval layer gracefully returns empty results when the FTS5 index isn't built (`search.py:112-113`, `search.py:150-151`, `search.py:183-184`), so demos still run. But colleagues won't see corpus-backed provenance or retrieval examples in their output, and there's no warning that the demo is running in degraded mode. The Inegol and Soc Son demos use `DemoProvider` which generates deterministic text regardless of retrieval, so actual output quality is unaffected — but provenance citations will be empty.

**Current state:** `data/corpus/normalized/` and `data/index/` are both gitignored. The normalized corpus (18 JSON files) exists only on the developer's machine. Building the index requires having the normalized corpus first. The `pdd-agent build-index` command exists but can't run without corpus data.

**What's needed:**
- Either: bundle a small demo corpus subset (e.g., 2-3 normalized docs relevant to Soc Son and Inegol) and a pre-built FTS5 index in the repo under a `demo/` data directory
- Or: add a `pdd-agent demo-setup` command that creates a minimal index from configs/demo data already in the repo
- Or: at minimum, add a clear log message when running demos without an index explaining what's missing and why it's OK for demo purposes

**Existing assets to reuse:**
- `src/pdd_agent/retrieval/index.py` — `RetrievalIndex.build()` and `is_built()` already exist
- `data/corpus/normalized/*.norm.json` — 18 normalized docs exist locally (gitignored); a subset could be committed under `demo/corpus/`
- The retrieval layer's graceful degradation (`if not index.is_built(): return []`) means demos work without it

**Effort estimate:** Medium — 1 phase. Bundling a demo corpus subset requires deciding which docs to include and whether they contain sensitive content. The simplest fix is just adding a clear warning log.

---

### GAP-03: Missing `data/runs/` and `data/index/` Directories on Fresh Clone

**Severity:** MEDIUM — `DraftRun.save()` calls `mkdir(parents=True, exist_ok=True)` so `data/runs/` is auto-created at runtime (`provider.py:277`). However, `data/index/` is not auto-created when the index is queried — `RetrievalIndex.__init__` uses a default path of `data/index/corpus.fts.db`, and `_open()` will create the SQLite file but may fail if the parent directory doesn't exist. The `.gitkeep` files exist for `data/runs/` and `data/index/` but since the parent directories are gitignored, they won't be present after a fresh clone.

**Current state:** `.gitignore` ignores `data/runs/` and `data/index/`. A `.gitkeep` exists for `data/runs/` (visible in Glob results) but the gitignore pattern `data/runs/` should exclude the whole directory from git. The `!data/source_inputs/` exception pattern handles the spreadsheet cache but not `runs/` or `index/`.

**What's needed:**
- Ensure `data/runs/` and `data/index/` directories are either: (a) auto-created by all code paths that write to them, or (b) created as part of a `pip install -e .` post-install step, or (c) documented as a setup step
- Verify `.gitkeep` files are actually tracked (the gitignore pattern may be preventing this)
- Add `data/runs/.gitkeep` and `data/index/.gitkeep` exceptions to `.gitignore` if needed

**Existing assets to reuse:**
- `DraftRun.save()` already handles `data/runs/` with `mkdir(parents=True, exist_ok=True)`
- `RetrievalIndex.build()` likely handles `data/index/` directory creation too

**Effort estimate:** Small — 1 task, a few lines of code or gitignore fixes

---

### GAP-04: Demo Output Paths Not Obvious to First-Time Users

**Severity:** MEDIUM — After running `python scripts/run_demo.py`, the script prints paths to stdout (`Run ID: ...`, `DOCX: ...`, `Latest demo DOCX: ...`) but a colleague unfamiliar with the project won't know where to look for the generated DOCX, what to do with it, or how to interpret the scorecard. The Inegol demo script has a better summary but still assumes familiarity.

**Current state:**
- `scripts/run_demo.py` prints 5-6 lines of output with absolute paths
- `scripts/run_inegol_demo.py` prints a structured summary with pipeline-vs-Codex comparison
- Neither script opens the DOCX or provides a "next steps" hint
- Demo packages land in `reports/demo-packages/<slug>/<run-id>/` which is deeply nested

**What's needed:**
- Print a clear "Your demo DOCX is at: ..." message at the end of each demo script
- Copy or symlink the latest DOCX to a predictable, short path (e.g., `output/demo.docx`)
- Add a brief "What you're looking at" section explaining the DOCX structure
- Optionally: auto-open the DOCX on Windows/macOS after generation

**Existing assets to reuse:**
- `scripts/run_demo.py` and `scripts/run_inegol_demo.py` — already print paths
- `reports/demo-packages/<slug>/latest.docx` — stable alias already exists
- `reports/demo-scorecard.md` — benchmark output exists

**Effort estimate:** Small — 1 phase, script enhancement

---

### GAP-05: `gws` Dependency Error on Non-Configured Machines

**Severity:** MEDIUM — `src/pdd_agent/ingest/drive.py:20-22` hardcodes a `gws` path lookup (`GWS = str(Path.home() / "AppData" / "Roaming" / "npm" / "gws.cmd")`). If a colleague runs `pdd-agent ingest` or `pdd-agent fetch-workbook` without `gws` installed, they'll get a cryptic subprocess error, not a helpful message. While the demo path doesn't use these commands, the CLI doesn't prevent accidentally running them, and the README's "Quick Start" leads with `pdd-agent ingest`.

**Current state:** The README "Prerequisites" section lists `gws` and Node.js 18+ as requirements, but doesn't distinguish between demo and full-pipeline prerequisites. No runtime guard or helpful error message exists for missing `gws`.

**What's needed:**
- Add a clear error message in `drive.py` when `gws` is not found: "gws CLI not found. This is only needed for corpus ingestion and Drive upload — demo workflows don't require it."
- Separate README prerequisites into "Demo prerequisites" (Python only) and "Full pipeline prerequisites" (Python + Node + gws + Drive access)

**Existing assets to reuse:**
- `drive.py:21-22` — already has fallback logic, just needs a better error
- README "Prerequisites" section — needs reorganization, not rewrite

**Effort estimate:** Small — 1 task

---

### GAP-06: No Pre-Built Demo DOCX in the Repo for Zero-Setup Preview

**Severity:** LOW — A colleague who just wants to see what the tool produces shouldn't need to install Python and run the pipeline. A pre-built demo DOCX committed to the repo (e.g., `demo/example-output.docx`) would let anyone preview the output by just opening a file.

**Current state:** Demo DOCX files are generated at runtime and saved under `reports/demo-packages/`. The gitignore doesn't explicitly exclude `reports/demo-packages/` but these generated files haven't been committed. The `latest.docx` alias under each project slug is a stable path.

**What's needed:**
- Commit one representative demo DOCX (Soc Son or Inegol) to the repo under `demo/` or `examples/`
- Add a note in README: "To preview output without running the tool, open `demo/example-output.docx`"

**Existing assets to reuse:**
- `reports/demo-packages/soc-son-like-waste-to-power-demonstration-project/latest.docx` — already generated locally
- `scripts/run_inegol_demo.py` — produces a clean 36-section DOCX (225 KB)

**Effort estimate:** Small — 1 task, commit a generated file

---

### GAP-07: Test Suite May Confuse Demo Users with Skipped Tests

**Severity:** LOW — The test suite (211 tests) includes 7 skipped tests that require the normalized corpus (`test_section_parser.py:97-140`) and potentially python-docx (`test_docx_export.py:140-159`). A colleague running `pytest` will see "7 skipped" without understanding why. Since `python-docx` is now a core dependency (not just optional), those skip guards may be stale.

**Current state:** Skip conditions in `test_section_parser.py` check for `data/corpus/normalized/` existence; skip conditions in `test_docx_export.py` check for `python-docx` import.

**What's needed:**
- Remove the `python-docx` skip guard since it's now a core dependency in `pyproject.toml`
- Add a clear docstring or README note explaining that corpus-dependent tests skip gracefully on fresh clones
- Optionally: add a `pytest -m "not corpus"` marker to make it easy to run only standalone tests

**Existing assets to reuse:**
- Test skip conditions already work correctly
- `pyproject.toml` already lists `python-docx` in core dependencies

**Effort estimate:** Small — 1 task

---

## Second-Tier Gaps

| Gap | Severity | Summary | Existing Assets |
|---|---|---|---|
| GAP-06 | LOW | No pre-built demo DOCX committed for zero-setup preview | `reports/demo-packages/*/latest.docx` exists locally |
| GAP-07 | LOW | Stale python-docx skip guards and unexplained test skips | Skip conditions work; `python-docx` is now a core dep |

---

## Recommended Sprint Sequencing

| Priority | Gap | Rationale |
|---|---|---|
| Sprint 1 | GAP-01 (Quickstart docs) | Highest leverage — unblocks colleagues immediately with existing working code |
| Sprint 1 | GAP-03 (Directory creation) | Tiny fix, removes a potential first-run failure |
| Sprint 1 | GAP-05 (gws error message) | Quick guard against wrong-path confusion |
| Sprint 2 | GAP-04 (Demo output UX) | Improves the "aha moment" after running the demo |
| Sprint 2 | GAP-06 (Pre-built DOCX) | Zero-setup preview for non-technical colleagues |
| Sprint 3 | GAP-02 (Demo corpus bundle) | Adds provenance depth to demos; biggest effort item |
| Sprint 3 | GAP-07 (Test cleanup) | Polish; low urgency |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Corpus PDFs contain Verra-copyrighted content | Bundling normalized corpus in repo may have IP implications | Medium | Only bundle project descriptions that are publicly available on Verra registry; add provenance notes |
| Python 3.11+ not available on colleague laptops | Demo won't install | Low | Document minimum version clearly; Python 3.11 has been stable since 2022 |
| `pip install -e .` fails on Windows with path issues | First-run failure | Low | Test on clean Windows machine; document venv creation step |
| Colleague runs `pdd-agent ingest` instead of demo command | Confusing `gws` error | Medium | GAP-05 addresses this with a clear error message; GAP-01 addresses with docs |
| Demo DOCX file size grows if corpus is bundled | Repo bloat | Low | Keep demo corpus small (2-3 docs, ~100KB); use `.gitattributes` for LFS if needed |

---

## Suggested Next Step

Review this report, then invoke `/plan` targeting GAP-01 + GAP-03 + GAP-04 + GAP-05 as a single sprint — these are all small changes that collectively create a smooth "clone → demo → DOCX" experience. GAP-02 (corpus bundling) and GAP-06 (pre-built DOCX) can be a separate follow-up plan.
