# Vietnam PDD Runbook

## Primary One-Command Path

1. Run `python scripts/run_vietnam_pdd.py` to fetch the workbook, regenerate the Soc Son mapping artifacts, draft the run, review it, publish the Word review package, and refresh the Vietnam reports.
2. Open `reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx` for the latest local review draft, or inspect the run-specific package under `reports/review-packages/soc-son-waste-to-power-plant-project/<run-id>/`.

## Equivalent CLI Steps

1. Run `pdd-agent fetch-workbook` to refresh the cached workbook under `data/source_inputs/spreadsheets/`.
2. Run `pdd-agent map-spreadsheet --candidate soc-son` to regenerate the workbook profile, row snapshot, project YAML, assumptions YAML, and source profile report.
3. Run `pdd-agent draft --input configs/projects/vietnam_socson_from_sheet.yaml --provider noop` to draft and review the current project input.
4. Run `pdd-agent export --run-id <run-id> --review-output-dir reports/review-packages` to publish a reviewer-facing DOCX package from a saved run.
5. Run `pdd-agent upload --review-docx reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx` when you want to upload the published review draft to Drive.

## When the Spreadsheet Changes

1. Re-run `pdd-agent fetch-workbook --force` if the Drive workbook changed.
2. Re-run `pdd-agent map-spreadsheet --candidate soc-son` and inspect `docs/source-profile-vietnam-wte.md` for header or row drift.
3. Review `configs/projects/vietnam_socson_from_sheet.assumptions.yaml` for any new blocked-review paths before sharing the draft.
4. Re-run `python scripts/run_vietnam_pdd.py` so the validation report, gap analysis, and published review package stay aligned to the latest row snapshot.

## Reusing the Flow for Another Vietnam Candidate

1. Add a new candidate entry to `configs/source_mappings/vietnam_wte_projects.yaml`.
2. Run `pdd-agent map-spreadsheet --candidate <candidate-key>` to generate the new project and assumptions artifacts.
3. Run `pdd-agent draft --input <new-project-yaml> --provider noop` followed by `pdd-agent export --run-id <run-id> --review-output-dir reports/review-packages`.
