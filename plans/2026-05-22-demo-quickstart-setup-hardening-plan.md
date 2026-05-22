---
title: "Demo Quickstart & Setup Hardening"
date: "2026-05-22"
status: "draft"
request: "Sprint 1 implementation for colleague-testable demo: quickstart docs, directory creation fixes, gws error guards (GAP-01, GAP-03, GAP-05)"
plan_type: "multi-phase"
research_inputs:
  - "reports/2026-05-22-colleague-demo-gap-analysis.md"
---

# Plan: Demo Quickstart & Setup Hardening

## Objective
Create a frictionless "clone → install → run → see DOCX" path so colleagues can test PDD Agent on their own laptops within 5 minutes, without needing Google Drive access, `gws`, Node.js, or API keys. This sprint covers documentation, directory safety, and error guard improvements.

## Context Snapshot
- **Current state:** Two working demo scripts (`scripts/run_demo.py`, `scripts/run_inegol_demo.py`) produce 36-section DOCX output using the deterministic `DemoProvider` with zero external dependencies. However, the README leads with infrastructure-heavy commands (`pdd-agent ingest --folder-id ...`) and has no quickstart for the demo path. Missing `gws` produces cryptic subprocess errors. Directory creation for `data/runs/` and `data/index/` is handled in code but `.gitignore` patterns prevent `.gitkeep` files from being tracked.
- **Desired state:** A colleague can follow a 4-step quickstart (clone, venv, install, run) and have a DOCX on disk. Running non-demo commands without `gws` produces a helpful error. All necessary directories are either auto-created or documented.
- **Key repo surfaces:** `README.md`, `scripts/run_demo.py`, `scripts/run_inegol_demo.py`, `src/pdd_agent/ingest/drive.py`, `.gitignore`, `pyproject.toml`
- **Out of scope:** Corpus bundling (Sprint 3), demo output UX improvements (Sprint 2), pre-built DOCX artifacts (Sprint 2), test cleanup (Sprint 3).

## Research Inputs
- `reports/2026-05-22-colleague-demo-gap-analysis.md` — Defines GAP-01 (no quickstart), GAP-03 (missing directories), GAP-05 (gws error). Confirms retrieval layer gracefully degrades when FTS5 index is absent. Confirms `DraftRun.save()` and `RetrievalIndex._open()` both call `mkdir(parents=True, exist_ok=True)`.

## Assumptions and Constraints
- **ASM-001:** Colleagues have Python 3.11+ and pip available on their laptops (Windows, macOS, or Linux).
- **ASM-002:** The demo path only needs `DemoProvider` — no LLM API keys, no corpus retrieval required for a valid demo experience.
- **ASM-003:** `DraftRun.save()` (`provider.py:274-277`) and `RetrievalIndex._open()` (`index.py:47-53`) already create `data/runs/` and `data/index/` directories at runtime, so the `.gitignore` issue is cosmetic rather than functional.
- **CON-001:** Must not break existing README content or the full-pipeline documentation for users who do have `gws` configured.
- **DEC-001:** QUICKSTART.md will be a standalone file rather than an inline README section, to keep it concise and focused for the demo audience.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Write QUICKSTART.md with 4-step demo path | None | `QUICKSTART.md` |
| PHASE-02 | Add `gws` missing guard with helpful error message | None | Updated `src/pdd_agent/ingest/drive.py` |
| PHASE-03 | Fix .gitignore for directory tracking + restructure README prerequisites | PHASE-01 | Updated `.gitignore`, `README.md` |
| PHASE-04 | Verify fresh-clone experience end to end | PHASE-01, PHASE-02, PHASE-03 | Test results, updated `activeContext.md` |

## Detailed Phases

### PHASE-01 — QUICKSTART.md for Demo Path
**Goal**
Create a standalone quickstart document that takes a colleague from zero to a working DOCX in 4 steps, with no assumptions beyond Python 3.11+ and git.

**Tasks**
- [ ] TASK-01-01: Create `QUICKSTART.md` at repo root with these sections: (1) Prerequisites (Python 3.11+, pip, git — explicitly state no Node/gws/API keys needed), (2) Setup (clone, create venv, `pip install -e .`), (3) Run Soc Son Demo (`python scripts/run_demo.py`), (4) Run Inegol Demo (`python scripts/run_inegol_demo.py`), (5) What You Get (expected output paths, what the DOCX contains), (6) Run Tests (`pytest`), (7) Next Steps (link to full README for production workflows).
- [ ] TASK-01-02: Add a prominent "Demo Quickstart" link at the very top of `README.md` (before the existing "What This Tool Does" section) pointing to `QUICKSTART.md`.
- [ ] TASK-01-03: Add a one-line note in the QUICKSTART explaining that 6-7 corpus-dependent tests skip gracefully on fresh clones and this is expected.

**Files / Surfaces**
- `QUICKSTART.md` — New file, primary demo entry point
- `README.md` — Add link to QUICKSTART.md near the top

**Dependencies**
- None

**Exit Criteria**
- [ ] `QUICKSTART.md` exists and contains all 7 sections
- [ ] `README.md` has a visible link to `QUICKSTART.md` before the "Quick Start" section
- [ ] The QUICKSTART instructions are valid: commands work on a fresh clone with Python 3.11+

**Phase Risks**
- **RISK-01-01:** QUICKSTART may go stale if demo scripts change. Mitigation: keep the QUICKSTART minimal (just commands and expected output) so it tracks script behavior rather than duplicating implementation details.

### PHASE-02 — `gws` Missing Guard
**Goal**
Replace the cryptic subprocess error when `gws` is not installed with a clear, actionable message that distinguishes demo paths (no `gws` needed) from full-pipeline paths.

**Tasks**
- [ ] TASK-02-01: Add a `_check_gws_available()` function in `src/pdd_agent/ingest/drive.py` that checks whether the resolved `GWS` path is executable (e.g., `shutil.which(GWS)` or a quick subprocess test). If not found, raise a `RuntimeError` with the message: `"gws CLI not found. Install it with 'npm install -g @googleworkspace/cli && gws auth setup'. Note: gws is only required for corpus ingestion and Drive upload — demo workflows (scripts/run_demo.py, scripts/run_inegol_demo.py) do not need it."`.
- [ ] TASK-02-02: Call `_check_gws_available()` at the top of `_run()` (the subprocess wrapper at `drive.py:26`) so every `gws`-dependent operation fails early with the helpful message.
- [ ] TASK-02-03: Add a unit test in `tests/test_drive_inventory.py` (or a new `tests/test_drive_guard.py`) that mocks `shutil.which` returning `None` and verifies the `RuntimeError` is raised with the expected message.

**Files / Surfaces**
- `src/pdd_agent/ingest/drive.py` — Add guard function, call it in `_run()`
- `tests/test_drive_inventory.py` or `tests/test_drive_guard.py` — New test

**Dependencies**
- None (independent of PHASE-01)

**Exit Criteria**
- [ ] Running `pdd-agent ingest` without `gws` installed produces a clear error mentioning demo alternatives
- [ ] Unit test for the guard passes
- [ ] Existing Drive-dependent tests (which already skip when `gws` is absent) continue to work

**Phase Risks**
- **RISK-02-01:** The guard might break CI if CI doesn't have `gws`. Mitigation: the guard only fires when `_run()` is actually called, not at import time. Existing tests mock subprocess calls and shouldn't trigger it.

### PHASE-03 — .gitignore Fixes and README Prerequisites Restructuring
**Goal**
Ensure `.gitkeep` sentinel files are actually tracked for `data/runs/` and `data/index/`, and restructure the README's prerequisites section to clearly separate demo vs. full-pipeline requirements.

**Tasks**
- [ ] TASK-03-01: Update `.gitignore` to add exception patterns for `.gitkeep` files: add `!data/runs/.gitkeep` after the `data/runs/` ignore line, and `!data/index/.gitkeep` after the `data/index/` ignore line.
- [ ] TASK-03-02: Verify that `data/runs/.gitkeep` and `data/index/.gitkeep` exist. Create them if missing.
- [ ] TASK-03-03: Run `git status` to confirm the `.gitkeep` files are now tracked.
- [ ] TASK-03-04: Restructure the README "Prerequisites" section into two subsections: "Demo Prerequisites" (Python 3.11+ only) and "Full Pipeline Prerequisites" (Python 3.11+, Node.js 18+, `gws` authenticated, Drive folder access).

**Files / Surfaces**
- `.gitignore` — Add `.gitkeep` exception patterns
- `data/runs/.gitkeep` — Ensure exists and is tracked
- `data/index/.gitkeep` — Ensure exists and is tracked
- `README.md` — Restructure prerequisites section

**Dependencies**
- PHASE-01 (README changes should be coordinated)

**Exit Criteria**
- [ ] `git ls-files data/runs/.gitkeep data/index/.gitkeep` shows both files as tracked
- [ ] README "Prerequisites" section has two clear subsections
- [ ] Fresh clone would have `data/runs/` and `data/index/` directories present

**Phase Risks**
- **RISK-03-01:** Changing `.gitignore` might accidentally track unwanted files. Mitigation: use specific exception patterns (`!data/runs/.gitkeep`) not broad directory un-ignores.

### PHASE-04 — Fresh-Clone Verification
**Goal**
Simulate a fresh clone experience and verify the entire quickstart flow works end to end.

**Tasks**
- [ ] TASK-04-01: Clone the repo into a temporary directory (or use `git worktree add`).
- [ ] TASK-04-02: Create a fresh venv, run `pip install -e .`, verify no errors.
- [ ] TASK-04-03: Run `python scripts/run_demo.py` and verify it produces a DOCX at the expected path.
- [ ] TASK-04-04: Run `python scripts/run_inegol_demo.py` and verify it produces a DOCX.
- [ ] TASK-04-05: Run `pytest` and verify tests pass with only corpus-dependent tests skipping (no unexpected failures).
- [ ] TASK-04-06: Run `pdd-agent ingest` without `gws` and verify the helpful error message appears.
- [ ] TASK-04-07: Update `activeContext.md` with Sprint 1 completion status.

**Files / Surfaces**
- Temporary clone directory — verification target
- `activeContext.md` — Update with completion status

**Dependencies**
- PHASE-01, PHASE-02, PHASE-03

**Exit Criteria**
- [ ] Fresh clone → install → `run_demo.py` → DOCX succeeds
- [ ] Fresh clone → install → `run_inegol_demo.py` → DOCX succeeds
- [ ] `pytest` shows 204+ passed, ~7 skipped, 0 failed
- [ ] `pdd-agent ingest` shows the new helpful error
- [ ] `activeContext.md` updated

**Phase Risks**
- **RISK-04-01:** Platform-specific issues (Windows vs macOS vs Linux) may surface. Mitigation: test on the developer's Windows machine first; note any platform-specific quirks in QUICKSTART.md.

## Verification Strategy
- **TEST-001:** Run `pytest tests/test_drive_guard.py` (or equivalent) to verify the `gws` guard test passes.
- **TEST-002:** Run `pytest` from a clean environment without `gws` to verify no unexpected failures.
- **MANUAL-001:** Follow QUICKSTART.md instructions verbatim on a machine without `gws`/Node.js.
- **MANUAL-002:** Open both generated DOCX files and confirm they contain 36 sections with readable content.

## Risks and Alternatives
- **RISK-001:** QUICKSTART.md may drift from actual behavior over time. Mitigation: keep it minimal and reference scripts by name rather than duplicating their behavior.
- **ALT-001:** Could add a `Makefile` or `justfile` with `make demo` / `just demo` targets. Not chosen because it adds another dependency (`make`/`just`) and the scripts already work as one-liners.

## Grill Me
No open clarification questions. All decisions are derivable from the gap analysis and repo state.

## Suggested Next Step
Begin PHASE-01 and PHASE-02 in parallel (they are independent), then PHASE-03, then PHASE-04 for verification.

## Target Timeline
- **2026-05-23:** PHASE-01 + PHASE-02 (parallel)
- **2026-05-24:** PHASE-03 + PHASE-04 (sequential)
