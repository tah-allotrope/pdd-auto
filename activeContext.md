## PDD Review Word Delivery Gap Closure

- [x] Update the active context to track PHASE-01 and PHASE-02 implementation from `plans/2026-04-29-pdd-review-word-delivery-plan.md`.
- [x] Add failing tests for the reviewer-facing publication contract and review-package output paths.
- [x] Implement PHASE-01 by codifying the review-package contract in workflow code and docs.
- [x] Implement PHASE-02 by publishing review packages under `reports/review-packages/` with immutable run history and a stable latest alias.
- [x] Run targeted verification and, if feasible, an end-to-end Vietnam workflow to prove a visible Word review package is produced.
- [x] Generate a session report artifact via the report skill.
- [ ] Commit the PHASE-01/02 implementation and push the branch.

## Review / Results

- Root cause confirmed: the workflow already exported DOCX successfully, but it only wrote to `data/runs/`, which is gitignored and not a reviewer-facing surface.
- Added `src/pdd_agent/export/review_package.py` to publish immutable run-scoped review packages under `reports/review-packages/<project-slug>/<run-id>/`, along with `latest.docx` as a stable reviewer entry point.
- Updated `src/pdd_agent/phase06/vietnam_workflow.py` so publication is part of the default Vietnam workflow contract, and the returned artifact model now exposes the published DOCX, latest alias, and review-package manifest.
- Updated `scripts/run_vietnam_pdd.py`, `src/pdd_agent/cli.py`, and `README.md` so the reviewer-facing DOCX path is surfaced and documented as the canonical review artifact.
- Added regression coverage in `tests/test_docx_export.py`, `tests/test_vietnam_workflow.py`, and `tests/test_phase06_cli.py` for review-package publication and published-path reporting.
- Verification passed: `pytest tests/test_docx_export.py tests/test_vietnam_workflow.py tests/test_phase06_cli.py`.
- End-to-end Vietnam run passed: `python scripts/run_vietnam_pdd.py` produced `reports/review-packages/soc-son-waste-to-power-plant-project/run-20260429035927-42a1ea/run-20260429035927-42a1ea.docx`, `reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx`, and `reports/review-packages/soc-son-waste-to-power-plant-project/run-20260429035927-42a1ea/manifest.json`.
- Remaining domain blocker is unchanged and explicit: section `3.5` still depends on review-gated synthetic quantification inputs, but the draft is now published for review instead of hidden in internal storage.
