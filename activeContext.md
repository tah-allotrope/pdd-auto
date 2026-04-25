## Phase 01-02 Plan

- [x] Review current ingestion, CLI, schema, config, and test surfaces for spreadsheet intake and mapping.
- [x] Add failing tests for workbook profiling, row selection, spreadsheet download pathing, ProjectInput mapping, and synthetic assumptions.
- [x] Implement Phase 01 workbook fetch/profile/select/snapshot flow for the Vietnam WTE spreadsheet.
- [x] Implement Phase 02 ProjectInput mapping, assumption registry generation, and guardrails for unsupported critical claims.
- [x] Add CLI commands and a one-command runner for the Soc Son spreadsheet path.
- [x] Generate tracked artifacts for source mapping, row snapshot, project YAML, assumptions YAML, and workbook profile report.
- [x] Run targeted tests and one end-to-end Soc Son generation command.
- [ ] Produce a completion report, then commit and push the changes.

## Review / Results

- Added `src/pdd_agent/phase06/spreadsheet_mapper.py` and `src/pdd_agent/phase06/__init__.py` for workbook caching, profiling, row selection, ProjectInput generation, and assumptions-register output.
- Added CLI commands `pdd-agent fetch-workbook` and `pdd-agent map-spreadsheet`, plus `scripts/run_vietnam_pdd.py` for the one-command Phase 01-02 flow.
- Added tracked mapping/config and source artifacts at `configs/source_mappings/vietnam_wte_projects.yaml`, `data/source_inputs/spreadsheets/WtE_plants_carbon_model_early_draft.xlsx`, `data/source_inputs/spreadsheets/vietnam_wte_profile.json`, and `data/source_inputs/spreadsheets/vietnam_socson_snapshot.json`.
- Added generated project artifacts at `configs/projects/vietnam_socson_from_sheet.yaml`, `configs/projects/vietnam_socson_from_sheet.assumptions.yaml`, and `reports/source-profile-vietnam-wte.md`.
- Added regression coverage in `tests/test_spreadsheet_mapper.py`, `tests/test_spreadsheet_intake.py`, and `tests/test_phase06_cli.py`.
- Updated `README.md`, `docs/provenance-policy.md`, `.gitignore`, and `pyproject.toml` to document the workflow, codify synthetic-assumption rules, keep spreadsheet source inputs tracked, and declare `openpyxl`.
- Verification passed: `pytest tests/test_input_schema.py tests/test_drive_inventory.py tests/test_spreadsheet_mapper.py tests/test_spreadsheet_intake.py tests/test_phase06_cli.py`.
- End-to-end smoke path passed: `python scripts/run_vietnam_pdd.py` generated the workbook profile, snapshot JSON, project YAML, assumptions YAML, and source profile report for the Soc Son row.
