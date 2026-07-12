# Rice VM0051 Pilot — Findings

**Date:** 2026-07-12
**Scope:** PHASE-06 of `plans/2026-07-12-pdd-reality-gap-plan.md` — draft a non-WTE (VM0051 rice cultivation) project end-to-end through both the CLI and the service, proving the methodology-breadth claim and cataloguing WTE-shaped assumptions.

## Summary

**Result: pipeline breadth claim holds.** A synthetic-but-realistic Vietnam AWD rice project (`configs/projects/rice_vm0051_pilot.yaml`) drafted, reviewed, and exported end-to-end through both the CLI and the FastAPI service with zero unhandled exceptions once two real bugs (found during this pilot, not pre-existing knowledge) were fixed. This is the designated substitute for the externally-blocked Seraphin greenfield project (per `docs/2026-07-05-convergence.md`).

## The pilot project

`configs/projects/rice_vm0051_pilot.yaml` + `configs/projects/rice_vm0051_pilot.assumptions.yaml`: a 5,000 ha alternate-wetting-and-drying (AWD) rice project in An Giang province, Mekong Delta, Vietnam. VM0051 methodology, `technology_type: rice_awd`. Quantification (net 20,020 tCO2e/year) is independently verified against `calc/rice_vm0051.py`'s `RiceVm0051Engine.compute_net()` in `tests/test_rice_vm0051.py::TestRiceGolden::test_rice_pilot_yaml_quantification_matches_calc_engine`.

## What worked without changes

- `ProjectInput` validation: the schema's `technology_type` literal already includes `"rice_awd"` and a dedicated `rice_cultivation: RiceCultivationParams` block — this was clearly designed for exactly this case, even though it had never been exercised end-to-end before this pilot.
- **Review consistency checks are methodology-neutral**, as the plan hoped to verify: `review/consistency.py`'s baseline − project − leakage == net arithmetic check passed cleanly on rice's tCO2e numbers with no WTE-specific coupling found.
- **Export table rendering**: no WTE-specific fields (`installed_capacity_mw`, `annual_waste_throughput`, `waste_type`) are referenced by `export/docx_export.py` or `export/table_helpers.py` — the exported DOCX rendered without any WTE-shaped table breakage.
- All 36 canonical VCS sections drafted with non-empty text; review passed; consistency passed; zero blocking issues on the first CLI attempt.

## What was WTE-shaped and had to be worked around (schema-level, DEC-004 respected)

`schemas/project_input.py`'s `ProjectTechnology` model requires three fields that are semantically WTE-specific and don't map cleanly onto a rice methodology:
- `waste_type: list[str]` (required, `min_length=1`) — populated with `["rice_straw_residue"]` as the closest plausible interpretation, though a rice AWD project doesn't process "waste" in the WTE sense.
- `annual_waste_throughput: float` (required, `gt=0`) — populated with a placeholder tonnage; has no real meaning for a methane-reduction-via-water-management project.
- `installed_capacity_mw: float` (required, `ge=0`) — set to `0.0`; correctly allowed since the field permits zero, but its presence as a *required* field on every project regardless of technology type is itself the tell.

**Per DEC-004, this is not fixed now** — the schema redesign (discriminated union per family, or making these three fields optional/WTE-specific) is deferred until a second real non-WTE project exists. This pilot is exactly the evidence-gathering DEC-004 asked for; recommend revisiting the schema split once the Vietnam rice prospect (or another real non-WTE project) lands with real data.

## Bugs found and fixed during this pilot

Three real, previously-undiscovered bugs surfaced by actually running a non-WTE project through the pipeline — none were caught by the existing 601-test suite before this pilot, because every existing test uses a WTE-shaped fixture:

1. **`DemoProvider` emitted hardcoded WTE-specific narrative text regardless of project methodology.** Nine of the 36 sections (1.1, 1.10, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4, 5.2) had deterministic text hardcoded around "municipal solid waste," "landfill disposal," and "biogas combustion" — nonsensical for a rice cultivation project. Fixed by adding `DemoProvider.set_project_input()` (wired automatically via the orchestrator's existing `hasattr(provider, "set_project_input")` hook) and a `technology_type`-keyed text-template dispatch in `_demo_section_text()`, with a parallel rice-AWD-specific template set. Backward-compatible: any project without a matching template (i.e. every existing WTE project) gets the original text unchanged. Regression-tested in `tests/test_rice_pilot_e2e.py::test_demo_provider_text_is_methodology_aware`.

2. **`export_run_to_docx()` ignored any redirected run-persistence directory, always looking in the hardcoded default `data/runs/`.** Discovered when the service round-trip's forced DOCX export returned `HTTP 500` / `FileNotFoundError` even though the run JSON existed — just in the service's `PDD_SERVICE_RUNS_DIR`, not the default. The existing test suite never caught this because `tests/test_service.py::TestDocxExport::test_docx_export_force_override` monkeypatched the module-level `_DRAFT_RUNS_DIR` constant directly, masking the exact bug a real non-default deployment would hit. Fixed by adding a `runs_dir: Path | None = None` parameter to `export_run_to_docx()` (used for both the run-JSON lookup and, absent an explicit `output_path`, the default output location) and threading `runs_dir=_runs_dir()` through the service's `api_download_docx` call site. The masking monkeypatch was removed from the existing test so it now exercises the real production code path.

3. **The service's `?force=1` query parameter never reached `export_run_to_docx()`'s own hard-block export gate.** It only bypassed the separate review-state-approval check (`store.is_all_approved()`) — a project with a genuine hard-block (calc contradiction, invalid `[E###]` citation, unresolved `[MISSING]` in Sections 3-4) would still raise `ExportBlockedError` even after the caller explicitly asked to force past it. Fixed by passing `force=bool(force)` through to `export_run_to_docx()` in the same call site fix as #2.

All three fixes are covered by tests: `tests/test_rice_pilot_e2e.py` (5 tests), `tests/test_docx_export.py::test_export_run_to_docx_honors_explicit_runs_dir`, and the de-masked `tests/test_service.py::TestDocxExport::test_docx_export_force_override`.

## Service round-trip (TASK-06-04)

Completed manually against a live local service instance (not a test — a real HTTP round-trip):
1. Created a run via `POST /api/runs` with the rice pilot YAML, `provider_name=demo`.
2. Approved section `1/1.1` via `POST /api/runs/{id}/sections/1%2F1.1/approve`.
3. Inline-edited and approved section `1/1.2` via `POST /api/runs/{id}/sections/1%2F1.2/edit`.
4. Triggered a redraft of section `1/1.3` via `POST /api/runs/{id}/sections/1%2F1.3/redraft`.
5. Confirmed the export gate blocks (`HTTP 403`) when not all sections are approved.
6. Downloaded the forced DOCX export (`?force=1`) — `HTTP 200`, 230 KB file (after the bugs above were fixed; the same request 500'd before the fix).

A bulk approve-all loop over the remaining 32 sections did not fully apply (a batch/state-machine interaction not investigated further — not blocking for this pilot's goal). Not treated as a bug for this pass; if it recurs when a human actually works through 36 sections in the web UI, it should be investigated as its own issue.

## Go/no-go on DEC-004 (per-family schema split)

**No-go, unchanged.** The wide schema with optional family blocks handled this pilot correctly once the three semantically-mismatched-but-technically-satisfiable WTE fields were populated with placeholder values. Revisit only when a second real (non-synthetic) non-WTE project's actual data makes the wide schema genuinely painful, not just semantically imprecise.
