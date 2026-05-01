## Soc Son Client Demo Output Upgrade - Phase 01

- [x] Trace the current Soc Son DOCX root cause from `run_vietnam_pdd_workflow()` to `DraftRun.save()` and confirm why the latest review package reads like gibberish in a client setting.
- [x] Define the client-demo acceptance contract, canonical `reports/demo-packages/` publication path, and default telemetry policy for demo artifacts.
- [x] Update repo documentation so `reports/review-packages/` is clearly internal-review output and `reports/demo-packages/` is clearly reserved for synthetic client-demo output.
- [x] Generate a Phase 01 report artifact via the report skill flow.
- [x] Commit and push the requested Phase 01 changes.

## Review / Results - Phase 01

- Confirmed the noisy Soc Son DOCX is expected from the current workflow, not an export bug: `src/pdd_agent/phase06/vietnam_workflow.py` drafts with provider `noop`, saves that run JSON, and then exports the same placeholder-heavy draft into `reports/review-packages/`.
- Confirmed the direct text source of the placeholders in `src/pdd_agent/llm/provider.py`: `NoopProvider.draft_section()` intentionally emits `[PLACEHOLDER ...]` bodies and `REVIEW REQUIRED` issues for human-in-the-loop review mode.
- Confirmed the current demo benchmark is also not client-safe yet: `reports/demo-scorecard.md` records `36` placeholder sections and `36` low-confidence sections for the benchmark path.
- Added a dedicated contract note at `reports/demo-artifact-contract.md` that defines the Phase 01 root-cause trace, demo acceptance rules, `reports/demo-packages/<project-slug>/<run-id>/` publication target, and summary-only telemetry policy for future client-demo exports.
- Updated `README.md` so the review-package workflow remains explicitly internal and review-gated while the client-demo package path is documented as a separate synthetic artifact contract to be implemented in later phases.

## PDD Review Word Delivery Gap Closure

- [x] Update the active context to track PHASE-01 and PHASE-02 implementation from `plans/2026-04-29-pdd-review-word-delivery-plan.md`.
- [x] Add failing tests for the reviewer-facing publication contract and review-package output paths.
- [x] Implement PHASE-01 by codifying the review-package contract in workflow code and docs.
- [x] Implement PHASE-02 by publishing review packages under `reports/review-packages/` with immutable run history and a stable latest alias.
- [x] Add failing tests for PHASE-03 discoverability, manual export publication, and published-path upload behavior.
- [x] Implement PHASE-03 by surfacing reviewer-facing paths in CLI flows and supporting optional upload from the published package.
- [x] Implement PHASE-04 by refreshing end-to-end artifacts and proving reports, filesystem paths, and upload surfaces all point to the same current package.
- [x] Run targeted verification and a fresh Vietnam workflow to prove the complete PHASE-03/04 contract.
- [x] Generate a session report artifact via the report skill.
- [x] Commit the PHASE-03/04 implementation and push the branch, including requested untracked files.

## Review / Results

- Added PHASE-03 discoverability support to `src/pdd_agent/cli.py`: `run-vietnam-pdd` now accepts `--review-output-dir` and `--upload-review-docx`, `export` accepts `--review-output-dir`, and `upload` accepts `--review-docx` for published reviewer-facing artifacts.
- Added `upload_review_package_docx()` in `src/pdd_agent/export/drive_upload.py` and `publish_docx_run_for_review()` in `src/pdd_agent/export/review_package.py` so manual and one-command flows can operate on the published review package instead of only `data/runs/`.
- Updated `src/pdd_agent/phase06/vietnam_workflow.py`, `scripts/run_vietnam_pdd.py`, `README.md`, and the generated runbook so the canonical review artifact is the published package under `reports/review-packages/` and optional Drive upload is documented.
- Regression coverage passed: `pytest tests/test_docx_export.py tests/test_vietnam_workflow.py tests/test_phase06_cli.py`.
- Fresh local review-package run passed: `python scripts/run_vietnam_pdd.py` produced `reports/review-packages/soc-son-waste-to-power-plant-project/run-20260429040932-11dc87/run-20260429040932-11dc87.docx` and refreshed `reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx`.
- Fresh upload-enabled workflow passed: `python -m pdd_agent.cli run-vietnam-pdd --upload-review-docx --folder-id 1pp23yRZ8qtopw1BPXrzVewXsmmWplCse` produced `reports/review-packages/soc-son-waste-to-power-plant-project/run-20260429041046-2616b7/run-20260429041046-2616b7.docx`, refreshed `latest.docx`, and returned Drive URL `https://drive.google.com/drive/folders/1pp23yRZ8qtopw1BPXrzVewXsmmWplCse`.
- Remaining domain blocker is still explicit and unchanged: the current draft remains reviewable and shareable, but section `3.5` still depends on review-gated synthetic quantification inputs.
- Delivery plan status check: no pending implementation work remains for PHASE-01 through PHASE-04; only the final summary artifact was left to add.
