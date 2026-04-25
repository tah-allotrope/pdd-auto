## Vietnam WTE Phase 03-04 Plan

- [x] Review the repo against `plans/2026-04-24-vietnam-wte-verra-pdd-plan.md` to confirm PHASE-01 and PHASE-02 are already implemented.
- [x] Add failing tests for assumption-aware drafting metadata, review gating, and DOCX appendices/disclaimer behavior.
- [x] Implement PHASE-03 provenance-rich drafting so sections can track spreadsheet, corpus, methodology, synthetic, and demo-default inputs.
- [x] Implement PHASE-03 review-state/report updates so synthetic-heavy HIGH/CRITICAL sections stay visibly review-gated.
- [x] Implement PHASE-04 DOCX export upgrades for cover disclaimer, Verra-style metadata, assumption appendix, and reviewer issues appendix.
- [x] Run targeted tests plus an end-to-end Vietnam draft/review/export flow and record the results.
- [ ] Commit the completed PHASE-03/04 work and push the branch.

## Review / Results

- PHASE-01 and PHASE-02 are already present in the repo via `src/pdd_agent/phase06/spreadsheet_mapper.py`, CLI commands, generated Soc Son YAML/assumptions artifacts, and Phase 01-02 tests.
- Added `src/pdd_agent/phase06/assumptions.py` to load companion assumption registers, route field-level provenance into sections, and write `reports/assumption-burden.md`.
- Upgraded `src/pdd_agent/llm/provider.py`, `src/pdd_agent/agent/section_orchestrator.py`, `src/pdd_agent/review/checks.py`, and `src/pdd_agent/phase05/benchmark.py` so drafted sections persist fact provenance, synthetic uses, output references, review sensitivity, and assumption-aware review-state/report behavior.
- Replaced `src/pdd_agent/export/docx_export.py` with a Verra-style review export that adds a front-matter disclaimer, cover metadata, section source summaries, an assumption appendix, and a reviewer issues appendix.
- Added Phase 03-04 regression coverage in `tests/test_section_orchestrator.py`, `tests/test_review_checks.py`, and `tests/test_docx_export.py`.
- Verification passed: `pytest tests/test_section_orchestrator.py tests/test_review_checks.py tests/test_docx_export.py tests/test_phase05_demo.py`.
- End-to-end Vietnam run passed: `python -m pdd_agent.cli draft --input configs/projects/vietnam_socson_from_sheet.yaml --provider noop` produced `data/runs/run-20260425150712-281eb4.json`, `data/runs/review-state-run-20260425150712-281eb4.json`, and `reports/assumption-burden.md`.
- DOCX export passed after installing `python-docx`: `python -m pdd_agent.cli export --run-id run-20260425150712-281eb4` produced `data/runs/run-20260425150712-281eb4.docx`.
