---
title: "Demo Output UX & Pre-built Artifacts"
date: "2026-05-22"
status: "draft"
request: "Sprint 2 implementation for colleague-testable demo: improve demo script output, copy DOCX to predictable paths, commit pre-built example DOCX (GAP-04, GAP-06)"
plan_type: "multi-phase"
research_inputs:
  - "reports/2026-05-22-colleague-demo-gap-analysis.md"
---

# Plan: Demo Output UX & Pre-built Artifacts

## Objective
Improve the demo experience so colleagues immediately know where to find their generated DOCX, understand what they're looking at, and can preview example output without running any code. This sprint upgrades both demo scripts with user-friendly output, adds a stable `output/` directory for generated artifacts, and commits a pre-built example DOCX.

## Context Snapshot
- **Current state:** `scripts/run_demo.py` prints 5-6 lines of raw paths (run ID, scorecard, diff, DOCX, manifest, latest). `scripts/run_inegol_demo.py` prints a richer summary including review results and Codex comparison but still uses raw paths. Demo packages land in deeply nested `reports/demo-packages/<slug>/<run-id>/` directories. No pre-built DOCX is committed.
- **Desired state:** Both demo scripts print a clear summary banner with the DOCX path prominently highlighted, copy/symlink the result to `output/latest-demo.docx`, and optionally auto-open the file. A pre-built example DOCX exists at `examples/example-inegol-demo.docx` for zero-install preview.
- **Key repo surfaces:** `scripts/run_demo.py`, `scripts/run_inegol_demo.py`, `README.md`, `QUICKSTART.md` (from Sprint 1), `.gitignore`
- **Out of scope:** Corpus bundling (Sprint 3), test cleanup (Sprint 3), `gws` guard (Sprint 1), core pipeline changes.

## Research Inputs
- `docs/2026-05-22-colleague-demo-gap-analysis.md` — Defines GAP-04 (demo output paths not obvious) and GAP-06 (no pre-built DOCX). Notes that `reports/demo-packages/<slug>/latest.docx` stable alias already exists. Recommends copying to a short predictable path.

## Assumptions and Constraints
- **ASM-001:** Sprint 1 (QUICKSTART.md) is complete, so `QUICKSTART.md` exists and can be updated to reference new output paths.
- **ASM-002:** The Inegol demo produces a representative 36-section DOCX (~225 KB) suitable for committing as an example.
- **ASM-003:** Auto-opening DOCX is a nice-to-have; the `--open` flag should be opt-in so CI/headless environments aren't affected.
- **CON-001:** Pre-built DOCX must carry the synthetic disclosure from the `DemoProvider` path — it must not be mistaken for a real PDD.
- **CON-002:** `output/` directory should be gitignored (generated artifacts) but `examples/` should be tracked (committed example).

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Upgrade demo script output with summary banner and stable output path | None | Updated `scripts/run_demo.py`, `scripts/run_inegol_demo.py`, new `output/` directory |
| PHASE-02 | Commit pre-built example DOCX for zero-install preview | None | `examples/example-inegol-demo.docx`, updated `README.md` |
| PHASE-03 | Update QUICKSTART.md and add optional auto-open flag | PHASE-01, PHASE-02 | Updated `QUICKSTART.md`, `.gitignore` |
| PHASE-04 | Verification and fresh-run test | PHASE-01, PHASE-02, PHASE-03 | Test results, updated `activeContext.md` |

## Detailed Phases

### PHASE-01 — Demo Script Output UX
**Goal**
Both demo scripts print a clear, user-friendly summary with the DOCX path prominently highlighted, and copy the generated DOCX to `output/latest-demo.docx` for easy discovery.

**Tasks**
- [ ] TASK-01-01: Add a `_print_demo_banner(docx_path, run_id, sections_count, runtime)` helper function in a shared `scripts/_demo_helpers.py` module (or inline in each script if keeping things simple). The banner should print:
  ```
  ╔══════════════════════════════════════════════╗
  ║  PDD Agent Demo Complete                      ║
  ╠══════════════════════════════════════════════╣
  ║  Sections: 36 | Runtime: 0.3s                ║
  ║  Review flags: 0 critical, 0 high            ║
  ║                                                ║
  ║  Your DOCX is at:                             ║
  ║  → output/latest-demo.docx                    ║
  ║                                                ║
  ║  Also saved to:                               ║
  ║    <full path>                                ║
  ╚══════════════════════════════════════════════╝
  ```
- [ ] TASK-01-02: In `scripts/run_demo.py`, after `run_demo_benchmark()` returns, copy `artifacts.demo_latest_docx` (or `artifacts.export_docx`) to `output/latest-demo.docx` using `shutil.copy2`. Create `output/` directory with `mkdir(parents=True, exist_ok=True)`.
- [ ] TASK-01-03: In `scripts/run_inegol_demo.py`, after DOCX export, copy `docx_path` to `output/latest-inegol-demo.docx` using `shutil.copy2`.
- [ ] TASK-01-04: Update both scripts to print the summary banner instead of raw path lines. Keep the detailed review/comparison output in Inegol script as secondary output below the banner.
- [ ] TASK-01-05: Add `output/` to `.gitignore` (generated runtime artifacts, not tracked).

**Files / Surfaces**
- `scripts/run_demo.py` — Add copy-to-output and banner printing
- `scripts/run_inegol_demo.py` — Add copy-to-output and banner printing
- `.gitignore` — Add `output/` directory

**Dependencies**
- None

**Exit Criteria**
- [ ] `python scripts/run_demo.py` produces `output/latest-demo.docx` and prints a banner with the path
- [ ] `python scripts/run_inegol_demo.py` produces `output/latest-inegol-demo.docx` and prints a banner
- [ ] Both scripts still produce the full artifact set under `reports/demo-packages/` and `data/runs/`
- [ ] `output/` is in `.gitignore`

**Phase Risks**
- **RISK-01-01:** Path copying may fail on Windows if the file is locked. Mitigation: use `shutil.copy2` which handles most cases; add a try/except with a note about the original path.

### PHASE-02 — Pre-built Example DOCX
**Goal**
Commit a representative demo DOCX so colleagues can preview the tool's output without installing Python or running anything.

**Tasks**
- [ ] TASK-02-01: Run `python scripts/run_inegol_demo.py` locally and capture the output DOCX.
- [ ] TASK-02-02: Create `examples/` directory at repo root.
- [ ] TASK-02-03: Copy the generated DOCX to `examples/example-inegol-demo.docx`.
- [ ] TASK-02-04: Create `examples/README.md` with a brief explanation: what the file is, that it's a synthetic demo (not a real PDD), when it was generated, and how to regenerate it (`python scripts/run_inegol_demo.py`).
- [ ] TASK-02-05: Add a line in the main `README.md` under a new "Example Output" section (before "Architecture"): "To preview what the tool produces without running it, open `examples/example-inegol-demo.docx`. This is a synthetic demo — see the cover page disclaimer."

**Files / Surfaces**
- `examples/example-inegol-demo.docx` — New committed binary artifact (~225 KB)
- `examples/README.md` — New file explaining the example
- `README.md` — Add "Example Output" section

**Dependencies**
- None (independent of PHASE-01)

**Exit Criteria**
- [ ] `examples/example-inegol-demo.docx` exists in the repo and opens in Word/LibreOffice showing 36 sections
- [ ] The DOCX cover page has the synthetic disclosure
- [ ] `README.md` references the example file

**Phase Risks**
- **RISK-02-01:** Binary DOCX in git inflates repo size. Mitigation: ~225 KB is negligible; only one file is committed. If the repo grows, move to Git LFS later.
- **RISK-02-02:** Example may go stale as the schema evolves. Mitigation: `examples/README.md` includes regeneration instructions.

### PHASE-03 — QUICKSTART Update and Optional Auto-Open
**Goal**
Update the QUICKSTART.md (from Sprint 1) to reference the new `output/` paths and example file, and add an optional `--open` flag to demo scripts.

**Tasks**
- [ ] TASK-03-01: Update `QUICKSTART.md` "What You Get" section to reference `output/latest-demo.docx` and `output/latest-inegol-demo.docx` as the primary output locations.
- [ ] TASK-03-02: Add a note in QUICKSTART.md: "To preview without running: open `examples/example-inegol-demo.docx`."
- [ ] TASK-03-03: Add an `--open` CLI flag to both demo scripts. When passed, use `os.startfile()` on Windows, `subprocess.run(["open", path])` on macOS, or `subprocess.run(["xdg-open", path])` on Linux to open the DOCX after generation. Default is off.
- [ ] TASK-03-04: Document the `--open` flag in QUICKSTART.md as an optional convenience.

**Files / Surfaces**
- `QUICKSTART.md` — Update output paths and add preview note
- `scripts/run_demo.py` — Add `--open` flag
- `scripts/run_inegol_demo.py` — Add `--open` flag

**Dependencies**
- PHASE-01 (needs `output/` paths to exist)
- PHASE-02 (needs example file to exist for the QUICKSTART note)

**Exit Criteria**
- [ ] QUICKSTART.md references `output/` paths
- [ ] `python scripts/run_demo.py --open` generates and opens the DOCX on the developer's machine
- [ ] Running without `--open` works silently as before

**Phase Risks**
- **RISK-03-01:** `os.startfile()` is Windows-only; cross-platform open requires platform detection. Mitigation: use `sys.platform` check with graceful fallback (print path if open fails).

### PHASE-04 — Verification
**Goal**
Run both demo scripts end to end, verify output locations, and confirm the pre-built example matches current pipeline output.

**Tasks**
- [ ] TASK-04-01: Run `python scripts/run_demo.py` and verify `output/latest-demo.docx` exists and is valid.
- [ ] TASK-04-02: Run `python scripts/run_inegol_demo.py` and verify `output/latest-inegol-demo.docx` exists and is valid.
- [ ] TASK-04-03: Open both DOCX files and confirm 36 sections, synthetic disclosure, no placeholders.
- [ ] TASK-04-04: Verify `examples/example-inegol-demo.docx` opens and matches current Inegol output.
- [ ] TASK-04-05: Run `pytest` to confirm no regressions.
- [ ] TASK-04-06: Update `activeContext.md` with Sprint 2 completion status.

**Files / Surfaces**
- `output/` — Verify generated files
- `examples/` — Verify committed file
- `activeContext.md` — Update

**Dependencies**
- PHASE-01, PHASE-02, PHASE-03

**Exit Criteria**
- [ ] Both `output/*.docx` files exist after demo runs
- [ ] Example DOCX is committed and opens correctly
- [ ] All tests pass
- [ ] `activeContext.md` updated

**Phase Risks**
- **RISK-04-01:** None significant — this is pure verification.

## Verification Strategy
- **TEST-001:** Run `python scripts/run_demo.py` and check `output/latest-demo.docx` exists and is a valid ZIP (DOCX format).
- **TEST-002:** Run `python scripts/run_inegol_demo.py` and check `output/latest-inegol-demo.docx` exists.
- **MANUAL-001:** Open all three DOCX files (two generated, one example) and confirm content quality.
- **MANUAL-002:** Verify `python scripts/run_demo.py --open` launches the DOCX viewer.

## Risks and Alternatives
- **RISK-001:** Binary example DOCX may go stale. Mitigation: include regeneration instructions in `examples/README.md`.
- **ALT-001:** Could generate a PDF instead of committing a DOCX. Not chosen because PDF generation requires additional dependencies (`libreoffice --headless` or similar) and the gap analysis notes no local converter is available.

## Grill Me
1. **Q-001:** Should the pre-built example be the Soc Son demo or the Inegol demo?
   - **Recommended default:** Inegol — it's a real project (VCS-3908) with richer data (boundary coordinates, engine specs, audit history).
   - **Why this matters:** The example represents the tool's capabilities to colleagues.
   - **If answered differently:** If Soc Son, the example will be a synthetic Vietnam case with simpler data.

## Suggested Next Step
Begin PHASE-01 and PHASE-02 in parallel (they are independent), then PHASE-03, then PHASE-04. Answer Q-001 before starting PHASE-02.

## Target Timeline
- **2026-05-25:** PHASE-01 + PHASE-02 (parallel)
- **2026-05-26:** PHASE-03 + PHASE-04 (sequential)
