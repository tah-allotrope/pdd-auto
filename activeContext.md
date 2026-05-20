## Codex Insights Integration and Inegol Demo Case — Grill Me Answers

- **Q-001:** Inegol intake YAML not available → reverse-engineer from Codex script + corpus PDF (default).
- **Q-002:** Retrofit new DOCX table structures to Soc Son and Vietnam demos as well (not just Inegol).
- **Q-003:** Official VCS v4.4 DOCX template FOUND and downloaded from Verra (`VCS-Project-Description-Template-v4.4-FINAL2.docx`, 277 KB). Will use as base document for export; if unavailable at runtime, fall back to scratch generation.

## PHASE-01 — DOCX Export Upgrade with VCS v4.4 Table Structures

- [ ] TASK-01-01: Create `src/pdd_agent/export/table_helpers.py` with OOXML primitives.
- [ ] TASK-01-02: Implement 11 VCS v4.4 table renderer functions.
- [ ] TASK-01-03: Refactor `export_run_to_docx()` to dispatch structured tables.
- [ ] TASK-01-04: Update base styles (Arial, VCS margins) and support template-based export.
- [ ] TASK-01-05: Write unit tests in `tests/test_docx_export_tables.py`.

## Soc Son Client Demo Output Upgrade - Phase 04 (Verification & Fresh Client Demo Artifact)

- [x] TASK-04-01: Add regression tests covering zero-placeholder demo output (all sections), aligned quantification numbers, demo-package publication, and CLI/script surfacing of the published path.
- [x] TASK-04-02: Run the refreshed demo workflow end to end and publish a fresh DOCX under `reports/demo-packages/`.
- [x] TASK-04-03: PDF conversion skipped (no local converter available — DOCX remains the guaranteed surface per CON-003).
- [x] TASK-04-04: Refresh README examples and Known Gaps so the repo points users to the client-demo package rather than the old "not implemented yet" note.
- [x] TASK-04-05: Manually inspect the generated artifact — confirmed no placeholders, strong disclosure, aligned numbers, and clean appendix.
- [x] Generate Phase 04 report artifact via the report skill flow.
- [x] Commit and push the requested Phase 04 changes.

## Review / Results - Phase 04

- Added three new regression tests in `tests/test_phase05_demo.py`:
  - `test_run_demo_benchmark_with_demo_provider_all_sections_no_placeholders` — validates ALL 36 sections contain no `[PLACEHOLDER` markers and no `REVIEW REQUIRED` issues.
  - `test_demo_provider_quantification_arithmetic_is_consistent` — validates net = baseline - project - leakage and crediting_total = net * years.
  - `test_run_demo_benchmark_with_demo_package_publishes_end_to_end` — validates run JSON, scorecard, diff, DOCX, manifest, and latest alias all exist with zero placeholders and zero low-confidence sections.
- All 25 tests pass: `pytest tests/test_phase05_demo.py tests/test_docx_export.py tests/test_phase06_cli.py` (6.31s).
- Fresh demo workflow run published: `reports/demo-packages/soc-son-like-waste-to-power-demonstration-project/run-20260504104319-5e2a70/` with 36 sections, 0 placeholders, 36/36 matched reference, average grounding 0.7.
- DOCX verification: zero `[PLACEHOLDER` markers, strong cover disclosure, `Appendix A - Assumption Summary` present, `Appendix B - Reviewer Issues` absent, key numbers (98,000 / 21,000 / 2,000 / 75,000 / 750,000 / 9.0 MW / 182,500) all present.
- README updated: status line, demo workflow section, Known Gaps for demo-packages and provider description.
- Added the Phase 04 HTML report artifact at `reports/2026-05-04-phase-04-demo-verification.html`.

## Soc Son Client Demo Output Upgrade - Phase 03

- [x] Update the active context to track Phase 03 implementation from `plans/2026-05-01-soc-son-client-demo-output-plan.md`.
- [x] Add failing tests for deterministic demo prose, demo-aware DOCX export, and publication to `reports/demo-packages/`.
- [x] Implement a demo drafting path that replaces noop placeholders with readable synthetic prose while preserving structured provenance.
- [x] Implement demo-aware DOCX export and demo package publication with clear path surfacing.
- [x] Verify the Phase 03 contract with targeted tests and a fresh local demo package run.
- [x] Generate a Phase 03 report artifact via the report skill flow.
- [x] Commit and push the requested Phase 03 changes.

## Review / Results - Phase 03

- Added failing coverage in `tests/test_phase05_demo.py`, `tests/test_docx_export.py`, and `tests/test_phase06_cli.py` to lock the Phase 03 contract around readable demo prose, demo-aware DOCX export, benchmark CLI provider defaults, and publication into `reports/demo-packages/`.
- Added a deterministic `DemoProvider` in `src/pdd_agent/llm/provider.py` and updated `src/pdd_agent/agent/section_orchestrator.py` so demo runs save `provider="demo"`, emit structured synthetic prose, keep provenance, and suppress reviewer-noise escalation that is appropriate only for the internal `noop` review path.
- Updated `src/pdd_agent/export/docx_export.py` so demo exports keep a strong synthetic disclosure, suppress reviewer notes in the main body, rename the appendix to `Appendix A - Assumption Summary`, and omit the reviewer-issues appendix for demo runs.
- Added `publish_demo_package()` to `src/pdd_agent/export/review_package.py`, extended `src/pdd_agent/phase05/benchmark.py` so benchmark runs can publish immutable demo packages plus `latest.docx`, and updated `scripts/run_demo.py` to generate the client-demo package in one command.
- Updated `src/pdd_agent/cli.py` so `pdd-agent benchmark` now defaults to `--provider demo`, accepts `--demo-output-dir`, and surfaces the published demo package paths directly in logs.
- Targeted verification passed: `pytest tests/test_phase05_demo.py tests/test_docx_export.py tests/test_phase06_cli.py`.
- Fresh local demo package run passed with `provider_name='demo'`: `run_demo_benchmark()` published `reports/demo-packages/soc-son-like-waste-to-power-demonstration-project/run-20260501172928-45b866/run-20260501172928-45b866.docx`, `manifest.json`, and refreshed `reports/demo-packages/soc-son-like-waste-to-power-demonstration-project/latest.docx`.
- Added the Phase 03 HTML report artifact at `reports/2026-05-02-phase-03-demo-output.html`.

## Soc Son Client Demo Output Upgrade - Phase 02

- [x] Update the active context to track Phase 02 implementation from `plans/2026-05-01-soc-son-client-demo-output-plan.md`.
- [x] Add failing tests for a spreadsheet-backed demo input + assumptions companion that avoid review-gated gaps and stay quantitatively consistent.
- [x] Implement Phase 02 by generating a deterministic Soc Son demo assumptions companion alongside the existing demo config and classifying demo-safe synthetic facts distinctly from review-gated spreadsheet assumptions.
- [x] Verify the Phase 02 demo input contract with targeted tests and a fresh local demo-config write.
- [x] Generate a Phase 02 report artifact via the report skill flow.
- [x] Commit and push the requested Phase 02 changes.

## Review / Results - Phase 02

- Added failing coverage in `tests/test_phase05_demo.py` to prove the demo path writes a structured assumptions companion and keeps quantification values aligned between the demo config and its assumptions register.
- Updated `src/pdd_agent/phase05/benchmark.py` so `create_demo_project_input()` now writes `configs/projects/demo_socson_like.assumptions.yaml` next to the existing demo config.
- Introduced `demo_curated` provenance for the demo fixture and populated a deterministic assumptions register covering project identity, location, safeguards, monitoring, and key quantitative fields without any `blocked_review_paths`.
- Updated `src/pdd_agent/phase06/assumptions.py` so later phases treat `demo_curated` entries as synthetic/demo-backed inputs for provenance routing without conflating them with the spreadsheet mapper's review-gated assumptions.
- Updated `README.md` so the demo workflow and artifact-contract sections document the new demo assumptions companion and its role in the future client-demo path.
- Targeted verification passed: `pytest tests/test_phase05_demo.py`.
- Fresh local demo fixture write passed: `create_demo_project_input()` refreshed `configs/projects/demo_socson_like.yaml` and created `configs/projects/demo_socson_like.assumptions.yaml` with `candidate_key: soc-son-demo` and no blocked-review paths.
- Added the Phase 02 HTML report artifact at `reports/2026-05-02-phase-02-demo-inputs.html`.

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
