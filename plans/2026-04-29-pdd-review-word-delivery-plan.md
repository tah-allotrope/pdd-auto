---
title: "PDD Review Word Delivery Gap Closure"
date: "2026-04-29"
status: "draft"
request: "Despite implementation so far I've yet to see any Word documents on PDD for review; reconcile this gap with a multi-phase plan."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-04-22_wte-pdd-ingestion.md"
  - "research/2026-04-26_pdd-auto-commercial-ideas.md"
---

# Plan: PDD Review Word Delivery Gap Closure

## Objective
Close the gap between successful internal DOCX generation and reviewer-visible Word artifacts. After this work, the PDD workflow should leave behind a stable, easy-to-find Word review package in a reviewer-facing location, with the exact local path and optional Drive URL surfaced in the CLI and human-readable reports.

## Context Snapshot
- **Current state:** `src/pdd_agent/export/docx_export.py` can generate a `.docx`, and `src/pdd_agent/phase06/vietnam_workflow.py` already calls it during `run-vietnam-pdd`, but the default output lands in `data/runs/`, which is gitignored in `.gitignore`; the current workspace has no `data/runs/*.docx` files even though `activeContext.md` and `reports/vietnam-pdd-validation.md` reference a prior run artifact.
- **Desired state:** Running `python scripts/run_vietnam_pdd.py` or `pdd-agent run-vietnam-pdd` should publish a current Word draft into a stable, reviewer-facing directory under the workspace, keep the supporting review artifacts aligned to that published package, and optionally upload the published Word file to Drive for external review.
- **Key repo surfaces:** `.gitignore`, `src/pdd_agent/export/docx_export.py`, `src/pdd_agent/export/drive_upload.py`, `src/pdd_agent/phase06/vietnam_workflow.py`, `src/pdd_agent/cli.py`, `scripts/run_vietnam_pdd.py`, `reports/vietnam-pdd-validation.md`, `reports/vietnam-pdd-runbook.md`, `tests/test_docx_export.py`, `tests/test_vietnam_workflow.py`, `tests/test_phase06_cli.py`, `activeContext.md`.
- **Out of scope:** Improving narrative drafting quality, reducing assumption burden, changing the core review-state model, introducing a web UI, or treating the generated Word draft as a final audited submission.

## Research Inputs
- `research/2026-04-22_wte-pdd-ingestion.md` - Confirms the system should remain provenance-first and review-gated, which means the reviewable Word artifact must expose uncertainty clearly rather than hiding low-confidence content behind a polished export step.
- `research/2026-04-26_pdd-auto-commercial-ideas.md` - Emphasizes that the highest-value surface is pre-validation reviewability, which raises the priority of making review packages visible and shareable instead of leaving them as internal run artifacts.

## Assumptions and Constraints
- **ASM-001:** The exporter itself is not the main missing capability; the primary gap is artifact publication and discoverability, because export code and tests already exist while no current review-visible `.docx` is present in the workspace.
- **ASM-002:** Reviewers need a package, not only a Word file: at minimum the `.docx`, validation report, gap analysis, assumptions context, and run identifier must stay aligned.
- **ASM-003:** The current Vietnam Soc Son workflow is the right first path to fix, because it already claims end-to-end review-package behavior in `README.md`, `activeContext.md`, and `reports/vietnam-pdd-validation.md`.
- **CON-001:** `data/runs/` should remain the internal run-artifact surface for JSON/state persistence; reviewer-facing publication should not require humans to inspect internal storage conventions.
- **CON-002:** Published Word drafts must remain explicitly marked as internal review artifacts when sections are low-confidence or blocked for domain review.
- **DEC-001:** Existing commands `pdd-agent export`, `pdd-agent upload`, and `pdd-agent run-vietnam-pdd` remain the core interaction surfaces rather than adding a new top-level workflow.
- **DEC-002:** `reports/` is already the repo's human-facing artifact area, so the default local publication target should be a new subdirectory beneath `reports/` rather than another top-level folder.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Define the reviewer-facing artifact contract and trace the current visibility failure | None | Publication contract, output-path decision, package contents, stale-path rules |
| PHASE-02 | Publish Word review packages to a stable local workspace surface | PHASE-01 | Published `.docx`, package manifest, stable latest alias, updated workflow path handling |
| PHASE-03 | Make the published package discoverable from CLI, reports, and optional Drive upload | PHASE-02 | Surfaced local path, relative report links, optional Drive URL, updated operator docs |
| PHASE-04 | Verify end-to-end publication and leave behind a real reviewable Word package | PHASE-03 | Passing tests, fresh published review package, refreshed validation artifacts |

## Detailed Phases

### PHASE-01 - Review Artifact Contract And Gap Trace
**Goal**
Define what counts as a reviewer-visible PDD package and close the ambiguity between internal run storage and actual review delivery.

**Tasks**
- [ ] TASK-01-01: Trace the current `run-vietnam-pdd` output path from `run_vietnam_pdd_workflow()` through `export_run_to_docx()` and `reports/vietnam-pdd-validation.md`, and document where the path becomes invisible or stale for a reviewer.
- [ ] TASK-01-02: Decide the reviewer-facing local publication directory, with `reports/review-packages/` as the default target, and specify naming for both an immutable run-scoped copy and a stable latest alias.
- [ ] TASK-01-03: Define the minimum review package contents: published `.docx`, validation report, gap analysis, assumptions burden or assumptions YAML, project YAML, and a small manifest that ties them to one `run_id`.
- [ ] TASK-01-04: Define whether human-facing reports should reference only published relative paths, or published paths plus internal `data/runs/` paths for debugging.
- [ ] TASK-01-05: Document the publication contract in repo docs so "Word document for review" has one deterministic meaning.

**Files / Surfaces**
- `.gitignore` - Confirms why `data/runs/` is not an appropriate reviewer-facing default.
- `src/pdd_agent/phase06/vietnam_workflow.py` - Current end-to-end path that exports the DOCX but does not publish it to a reviewer-facing surface.
- `reports/vietnam-pdd-validation.md` - Current human-readable report that points to an internal DOCX path and should become the canonical review entry point.
- `README.md` - Current user promise that the workflow produces review artifacts and needs to match the real publication contract.
- `reports/vietnam-pdd-runbook.md` - Current operator path that still assumes reviewers will follow internal run IDs.

**Dependencies**
- None

**Exit Criteria**
- [ ] The repo contains one explicit local publication contract for reviewable Word drafts.
- [ ] The package contents and naming rules are concrete enough that another agent can implement them without guessing.
- [ ] Human-facing reports no longer conceptually treat `data/runs/` as the review surface.

**Phase Risks**
- **RISK-01-01:** If the publication contract stays ambiguous, implementation may add another output path without solving discoverability; mitigate by choosing one canonical reviewer-facing directory before editing workflow code.

### PHASE-02 - Local Review Package Publication
**Goal**
Make every successful review workflow publish a current Word draft into a stable, reviewer-facing location inside the workspace.

**Tasks**
- [ ] TASK-02-01: Add a thin publication helper, likely under `src/pdd_agent/export/review_package.py`, that copies or materializes the final `.docx` and companion artifacts into `reports/review-packages/<project-slug>/<run-id>/`.
- [ ] TASK-02-02: Add a stable latest alias such as `reports/review-packages/<project-slug>/latest.docx` plus a small `latest.md` or `manifest.json` that points to the matching run-scoped package.
- [ ] TASK-02-03: Update `run_vietnam_pdd_workflow()` so publication is part of the default success path, not an undocumented follow-up step.
- [ ] TASK-02-04: Ensure the validation report records the published review-package paths and fails loudly if the published `.docx` does not exist after workflow completion.
- [ ] TASK-02-05: Keep `data/runs/` as the internal source of truth for raw run JSON and review state, but treat the published package as the canonical review surface.

**Files / Surfaces**
- `src/pdd_agent/export/docx_export.py` - May need a small extension to support explicit publication-oriented output control.
- `src/pdd_agent/export/review_package.py` - New thin helper for packaging and publishing review artifacts.
- `src/pdd_agent/phase06/vietnam_workflow.py` - Must call the publication helper and return published artifact paths.
- `reports/review-packages/` - New reviewer-facing local publication directory.
- `reports/vietnam-pdd-validation.md` - Must point at the published package rather than only internal run storage.

**Dependencies**
- PHASE-01 publication contract and package definition.

**Exit Criteria**
- [ ] A successful Vietnam workflow leaves at least one `.docx` under a stable non-internal review path.
- [ ] The latest review draft can be found without knowing the internal `run_id` convention.
- [ ] The validation report references the published `.docx` that actually exists on disk.

**Phase Risks**
- **RISK-02-01:** Publishing every run-specific binary into a tracked area may create artifact churn; mitigate with a clear latest alias and an explicit decision about whether immutable archives stay visible, ignored, or optional.

### PHASE-03 - Discoverability, CLI Surfacing, And Optional Drive Delivery
**Goal**
Make published review packages easy to find from the command surface and easy to share beyond the local workspace.

**Tasks**
- [ ] TASK-03-01: Update `scripts/run_vietnam_pdd.py` and `pdd-agent run-vietnam-pdd` output so they print the published review-package path separately from internal run artifact paths.
- [ ] TASK-03-02: Add CLI options for reviewer delivery behavior, such as `--review-output-dir`, `--publish-latest`, or an opt-in `--upload-review-docx`, without breaking the existing default workflow.
- [ ] TASK-03-03: Integrate `src/pdd_agent/export/drive_upload.py` with the published package path so optional uploads share the reviewer-facing `.docx`, not only the internal `data/runs` copy.
- [ ] TASK-03-04: Update validation and runbook reports to use relative local paths where possible and add the Drive URL when an upload occurs.
- [ ] TASK-03-05: Update `pdd-agent export` so manual export can target the same review-package publication path instead of only defaulting to `data/runs/{run_id}.docx`.

**Files / Surfaces**
- `src/pdd_agent/cli.py` - Needs argument surface and output/logging changes.
- `scripts/run_vietnam_pdd.py` - Needs to print reviewer-facing paths explicitly.
- `src/pdd_agent/export/drive_upload.py` - Needs to accept the published review path as the upload source.
- `reports/vietnam-pdd-runbook.md` - Needs updated operator instructions for local review and optional remote sharing.
- `README.md` - Needs revised examples showing where the Word review draft actually appears.

**Dependencies**
- PHASE-02 published package path and naming scheme.

**Exit Criteria**
- [ ] A reviewer can find the latest Word draft from CLI output or a file under `reports/` without digging through `data/runs/`.
- [ ] Optional Drive upload uses the published review artifact and reports back a URL when successful.
- [ ] Manual and one-command workflows describe the same review-delivery behavior.

**Phase Risks**
- **RISK-03-01:** Auto-uploading draft PDDs may share review-incomplete material too early; mitigate by making upload opt-in or clearly separated from local publication.

### PHASE-04 - End-To-End Verification And Artifact Backfill
**Goal**
Prove the new publication contract works and leave behind an actual Word package that is immediately reviewable in this workspace.

**Tasks**
- [ ] TASK-04-01: Add regression tests covering published review-package paths, latest-alias behavior, missing-file failures, and CLI surfacing of the published path.
- [ ] TASK-04-02: Re-run the Vietnam workflow end to end with `python-docx` available and verify that the published `.docx` exists in the reviewer-facing directory.
- [ ] TASK-04-03: Refresh `reports/vietnam-pdd-validation.md`, `reports/vietnam-pdd-gap-analysis.md`, and `reports/vietnam-pdd-runbook.md` so they reference the current published package rather than stale internal-only paths.
- [ ] TASK-04-04: Manually open the published Word draft and confirm it is the same document described by the latest validation report.
- [ ] TASK-04-05: Record the final published artifact paths in `activeContext.md` during implementation so the next agent can confirm the delivery gap is actually closed.

**Files / Surfaces**
- `tests/test_docx_export.py` - Needs assertions for publication-aware export behavior.
- `tests/test_vietnam_workflow.py` - Needs to prove end-to-end publication and report alignment.
- `tests/test_phase06_cli.py` - Needs to prove CLI surfacing of reviewer-facing artifact paths.
- `reports/vietnam-pdd-validation.md` - Must become a trustworthy pointer to the current review package.
- `activeContext.md` - Should record the concrete published outputs once implementation is complete.

**Dependencies**
- PHASE-03 CLI/report contract.

**Exit Criteria**
- [ ] The workspace contains a real, current Word review document in the published review-package location.
- [ ] Targeted automated tests pass for publication, surfacing, and upload-path behavior.
- [ ] Human-readable reports and actual filesystem artifacts point to the same current review package.

**Phase Risks**
- **RISK-04-01:** Reports may still reference stale files if verification stops after unit tests; mitigate by requiring one fresh end-to-end run as part of completion.

## Verification Strategy
- **TEST-001:** Extend `tests/test_docx_export.py` to verify that export and publication logic writes or references the reviewer-facing package path correctly.
- **TEST-002:** Extend `tests/test_vietnam_workflow.py` to assert that `run_vietnam_pdd_workflow()` returns published package paths and that the validation report references them.
- **TEST-003:** Extend `tests/test_phase06_cli.py` to verify `run-vietnam-pdd` and `export` surface reviewer-facing paths and optional Drive URLs.
- **MANUAL-001:** Run `python scripts/run_vietnam_pdd.py` and confirm a `.docx` exists under `reports/review-packages/` and can be opened directly from there.
- **MANUAL-002:** Compare the published `.docx` path shown in CLI output, `reports/vietnam-pdd-validation.md`, and the actual filesystem to ensure they all match the same run.
- **OBS-001:** Log both the internal run artifact path and the published review-package path, plus upload success or failure when remote delivery is enabled.

## Risks and Alternatives
- **RISK-001:** Publishing binary `.docx` artifacts into a human-facing repo area can create churn and larger diffs; mitigate with a stable latest alias, optional immutable archives, and explicit retention rules.
- **RISK-002:** A published Word file may give a false sense of readiness when every section still needs domain review; mitigate by preserving the current disclaimer, validation report, and gap-analysis linkage in the package.
- **ALT-001:** Keep using `data/runs/` as the only DOCX location and rely on users to run `pdd-agent export` or `pdd-agent upload` manually; not chosen because that is the current behavior pattern that failed the discoverability goal.
- **ALT-002:** Publish only markdown validation artifacts and skip local Word publication; not chosen because the explicit missing deliverable is a reviewable Word document.
- **ALT-003:** Upload every generated Word file directly to Drive and stop caring about local publication; not chosen because local deterministic review and local-path verification still matter for development and debugging.

## Grill Me
1. **Q-001:** Should the canonical reviewer surface be local workspace only, Google Drive only, or both? (agree default)
   - **Recommended default:** Both, with mandatory local publication under `reports/review-packages/` and optional Drive upload.
   - **Why this matters:** It determines whether upload is part of the core workflow or an add-on, and changes CLI/report outputs.
   - **If answered differently:** Local-only simplifies implementation and tests; Drive-only shifts more effort into upload retries, URLs, and remote verification.
2. **Q-002:** Should the published review artifact keep immutable run history, or should the workflow only maintain a single latest draft? (agree default)
   - **Recommended default:** Keep both an immutable run-scoped package and a stable latest alias.
   - **Why this matters:** Reviewers need a stable entry point, while engineers still need traceability back to one `run_id`.
   - **If answered differently:** Latest-only reduces artifact churn; immutable-only preserves traceability but still makes reviewers hunt for the newest file.
3. **Q-003:** Should the workflow publish Word drafts even when all sections remain in `Needs Domain Review`? (yes)
   - **Recommended default:** Yes, with the existing disclaimer and companion validation artifacts preserved.
   - **Why this matters:** Your current request is to see Word drafts for review even though the evidence base is still incomplete.
   - **If answered differently:** Publication would need a review-threshold gate, which may continue to leave you without a visible Word artifact during early runs.

## Suggested Next Step
Accept the recommended defaults in `## Grill Me`, then implement PHASE-01 and PHASE-02 first so the next workflow run leaves behind a visible Word document before any Drive-sharing polish is added.
