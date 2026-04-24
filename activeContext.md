## Phase 05 Plan

- [x] Review current drafting, review, export, and persistence surfaces relevant to benchmark execution.
- [x] Add failing tests for Phase 05 benchmark and demo artifacts.
- [x] Implement a reproducible demo project config and one-command benchmark runner.
- [x] Generate `reports/demo-scorecard.md` and `reports/section-diff.md` from a completed run.
- [x] Update README guidance to cover the repeatable demo workflow.
- [x] Run targeted tests and an end-to-end smoke path.

## Review / Results

- Added `src/pdd_agent/phase05/benchmark.py` and `src/pdd_agent/phase05/__init__.py` for demo input creation, run loading, reference comparison, scorecard generation, and benchmark orchestration.
- Added CLI commands `pdd-agent demo-config` and `pdd-agent benchmark`, plus the one-command runner `scripts/run_demo.py`.
- Added reproducible demo input at `configs/projects/demo_socson_like.yaml` and updated `README.md` with Phase 05 workflow guidance.
- Added regression coverage in `tests/test_phase05_demo.py` for config creation, run loading, comparison scoring, markdown artifact generation, and full benchmark execution.
- Verification passed: `pytest tests/test_phase05_demo.py tests/test_section_orchestrator.py tests/test_review_checks.py`.
- End-to-end smoke path passed: `python scripts/run_demo.py` generated `reports/demo-scorecard.md` and `reports/section-diff.md` plus a real run JSON and review-state JSON.
- Runtime caveat: DOCX export was skipped in the smoke run because `python-docx` is not installed in the current environment even though it is declared in `pyproject.toml`.
