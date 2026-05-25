"""One-command Vietnam WTE workflow and PHASE-05 reporting helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.export.docx_export import export_run_to_docx
from pdd_agent.export.drive_upload import upload_review_package_docx
from pdd_agent.export.review_package import publish_review_package
from pdd_agent.llm.provider import get_provider_registry
from pdd_agent.phase06.assumptions import load_assumption_register
from pdd_agent.phase06.spreadsheet_mapper import (
    DEFAULT_MAPPING_CONFIG,
    DEFAULT_SPREADSHEET_CACHE_DIR,
    SpreadsheetArtifacts,
    fetch_workbook,
    generate_project_artifacts,
)
from pdd_agent.review.states import ReviewStateStore
from schemas.project_input import ProjectInput

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GAP_ANALYSIS_PATH = REPO_ROOT / "reports" / "vietnam-pdd-gap-analysis.md"
DEFAULT_REVIEW_PACKAGE_DIR = REPO_ROOT / "reports" / "review-packages"
DEFAULT_RUNBOOK_PATH = REPO_ROOT / "reports" / "vietnam-pdd-runbook.md"
DEFAULT_VALIDATION_REPORT_PATH = REPO_ROOT / "reports" / "vietnam-pdd-validation.md"


@dataclass
class VietnamWorkflowArtifacts:
    workbook_path: Path
    profile_json_path: Path
    snapshot_json_path: Path
    project_yaml_path: Path
    assumptions_yaml_path: Path
    source_report_path: Path
    run_id: str
    draft_run_path: Path
    review_state_path: Path
    assumption_burden_path: Path
    docx_path: Path
    review_package_manifest_path: Path
    latest_docx_path: Path
    validation_report_path: Path
    gap_analysis_path: Path
    runbook_path: Path
    upload_result: dict[str, Any] | None = None


def run_vietnam_pdd_workflow(
    mapping_config_path: Path | str = DEFAULT_MAPPING_CONFIG,
    cache_dir: Path | str = DEFAULT_SPREADSHEET_CACHE_DIR,
    candidate_key: str = "soc-son",
    provider_name: str = "noop",
    gap_analysis_path: Path | str = DEFAULT_GAP_ANALYSIS_PATH,
    review_package_dir: Path | str | None = DEFAULT_REVIEW_PACKAGE_DIR,
    runbook_path: Path | str = DEFAULT_RUNBOOK_PATH,
    validation_report_path: Path | str = DEFAULT_VALIDATION_REPORT_PATH,
    upload_review_docx: bool = False,
    drive_folder_id: str | None = None,
) -> VietnamWorkflowArtifacts:
    """Run the full Vietnam spreadsheet-to-DOCX workflow and write PHASE-05 reports."""
    workbook_path = fetch_workbook(mapping_config_path=mapping_config_path, cache_dir=cache_dir)
    spreadsheet_artifacts = generate_project_artifacts(
        workbook_path=workbook_path,
        mapping_config_path=mapping_config_path,
        candidate_key=candidate_key,
    )

    with open(spreadsheet_artifacts.project_yaml_path, encoding="utf-8") as handle:
        project_input = ProjectInput.model_validate(yaml.safe_load(handle))

    assumption_register = load_assumption_register(spreadsheet_artifacts.assumptions_yaml_path) or {}
    provider = get_provider_registry().get(provider_name)
    orchestrator = SectionOrchestrator(provider=provider, project_input=project_input)
    orchestrator.attach_assumption_register(assumption_register)

    draft_run = orchestrator.run()
    draft_run_path = draft_run.save()
    review_summary = orchestrator.run_review()
    review_state_path = Path(review_summary["review_state_path"])
    assumption_burden_path = Path(review_summary["assumption_burden_path"])
    internal_docx_path = export_run_to_docx(run_id=orchestrator.run_id)

    run_data = draft_run.to_dict()
    review_state_data = ReviewStateStore.load(orchestrator.run_id).to_dict()
    review_output_root = Path(review_package_dir) if review_package_dir else DEFAULT_REVIEW_PACKAGE_DIR

    validation_report_path = write_validation_report(
        run_data=run_data,
        review_summary=review_summary,
        review_state_data=review_state_data,
        spreadsheet_artifacts=spreadsheet_artifacts,
        docx_path=internal_docx_path,
        output_path=validation_report_path,
    )
    gap_analysis_path = write_gap_analysis_report(
        run_data=run_data,
        review_state_data=review_state_data,
        assumption_register=assumption_register,
        output_path=gap_analysis_path,
    )
    runbook_path = write_vietnam_runbook(output_path=runbook_path)
    review_package = publish_review_package(
        run_id=orchestrator.run_id,
        project_name=project_input.project.project_name,
        docx_path=internal_docx_path,
        validation_report_path=validation_report_path,
        gap_analysis_path=gap_analysis_path,
        assumption_burden_path=assumption_burden_path,
        assumptions_yaml_path=spreadsheet_artifacts.assumptions_yaml_path,
        project_yaml_path=spreadsheet_artifacts.project_yaml_path,
        output_root=review_output_root,
    )
    validation_report_path = write_validation_report(
        run_data=run_data,
        review_summary=review_summary,
        review_state_data=review_state_data,
        spreadsheet_artifacts=spreadsheet_artifacts,
        docx_path=review_package.docx_path,
        output_path=validation_report_path,
    )
    upload_result = None
    if upload_review_docx:
        upload_result = upload_review_package_docx(
            review_package.docx_path,
            drive_folder_id=drive_folder_id,
        )

    return VietnamWorkflowArtifacts(
        workbook_path=spreadsheet_artifacts.workbook_path,
        profile_json_path=spreadsheet_artifacts.profile_json_path,
        snapshot_json_path=spreadsheet_artifacts.snapshot_json_path,
        project_yaml_path=spreadsheet_artifacts.project_yaml_path,
        assumptions_yaml_path=spreadsheet_artifacts.assumptions_yaml_path,
        source_report_path=spreadsheet_artifacts.report_path,
        run_id=orchestrator.run_id,
        draft_run_path=draft_run_path,
        review_state_path=review_state_path,
        assumption_burden_path=assumption_burden_path,
        docx_path=review_package.docx_path,
        review_package_manifest_path=review_package.manifest_path,
        latest_docx_path=review_package.latest_docx_path,
        validation_report_path=validation_report_path,
        gap_analysis_path=gap_analysis_path,
        runbook_path=runbook_path,
        upload_result=upload_result,
    )


def write_validation_report(
    run_data: dict[str, Any],
    review_summary: dict[str, Any],
    review_state_data: dict[str, Any],
    spreadsheet_artifacts: SpreadsheetArtifacts,
    docx_path: Path | str,
    output_path: Path | str = DEFAULT_VALIDATION_REPORT_PATH,
) -> Path:
    """Write a human-readable validation report for the latest Vietnam run."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sections = run_data.get("sections", [])
    confidence_counts = Counter(section.get("confidence", "UNKNOWN") for section in sections)
    state_counts = Counter(
        section_state.get("state", "unknown")
        for section_state in review_state_data.get("sections", {}).values()
    )
    corpus_backed = sum(1 for section in sections if section.get("provenance"))
    lines = [
        "# Vietnam PDD Validation Report",
        "",
        f"- Run ID: `{run_data.get('run_id', 'unknown')}`",
        f"- Project: `{run_data.get('project_name', 'unknown')}`",
        f"- Workbook: `{spreadsheet_artifacts.workbook_path}`",
        f"- Project YAML: `{spreadsheet_artifacts.project_yaml_path}`",
        f"- Assumptions YAML: `{spreadsheet_artifacts.assumptions_yaml_path}`",
        f"- Source profile report: `{spreadsheet_artifacts.report_path}`",
        f"- Draft run JSON: `{Path(review_summary['draft_run_path'])}`",
        f"- Review state JSON: `{Path(review_summary['review_state_path'])}`",
        f"- Assumption burden report: `{Path(review_summary['assumption_burden_path'])}`",
        f"- DOCX draft: `{Path(docx_path)}`",
        "",
        "## Workflow Outcome",
        "",
        f"- Review passed: `{review_summary['review']['passed']}`",
        f"- Consistency passed: `{review_summary['consistency']['passed']}`",
        f"- Blocking review issues: `{len(review_summary['review'].get('blocking_issues', []))}`",
        f"- Auto-approved sections: `{len(review_summary['review'].get('auto_approved_sections', []))}`",
        f"- Sections with retrieved corpus provenance: `{corpus_backed}` / `{len(sections)}`",
        "",
        "## Confidence Distribution",
        "",
    ]

    for confidence, count in sorted(confidence_counts.items()):
        lines.append(f"- `{confidence}`: `{count}`")

    lines.extend(["", "## Review State Distribution", ""])
    for state, count in sorted(state_counts.items()):
        lines.append(f"- `{state}`: `{count}`")

    lines.extend(["", "## Blocking States", ""])
    blocking_states = review_state_data.get("blocking_states", [])
    if blocking_states:
        for item in blocking_states:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.extend(["", "## Notes", ""])
    if corpus_backed == 0:
        lines.append(
            "- No corpus examples were retrieved for this run, so the current output remains a disclosure-first placeholder draft rather than a narrative-quality submission draft."
        )
    lines.append(
        "- The published review DOCX, review-state JSON, and assumption burden report were all generated from the same run to keep the review package deterministic."
    )
    if not Path(docx_path).exists():
        raise FileNotFoundError(f"Published DOCX draft not found at `{docx_path}`")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def write_gap_analysis_report(
    run_data: dict[str, Any],
    review_state_data: dict[str, Any],
    assumption_register: dict[str, Any] | None,
    output_path: Path | str = DEFAULT_GAP_ANALYSIS_PATH,
) -> Path:
    """Write a gap analysis focused on the missing facts that most reduced confidence."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_gap_analysis_report(run_data, review_state_data, assumption_register),
        encoding="utf-8",
    )
    return output_path


def render_gap_analysis_report(
    run_data: dict[str, Any],
    review_state_data: dict[str, Any],
    assumption_register: dict[str, Any] | None,
) -> str:
    sections = run_data.get("sections", [])
    assumption_map = {
        item.get("field_path", ""): item
        for item in (assumption_register or {}).get("assumptions", [])
        if item.get("field_path")
    }
    field_summary: dict[str, dict[str, Any]] = {}

    for section in sections:
        if section.get("confidence") not in {"LOW", "UNSUPPORTED"}:
            continue
        section_key = section.get("sub_section_id") or section.get("section_id", "")
        for item in section.get("synthetic_uses", []):
            field_path = item.get("field_path")
            if not field_path:
                continue
            summary = field_summary.setdefault(
                field_path,
                {
                    "count": 0,
                    "sections": set(),
                    "blocked": False,
                    "source_types": Counter(),
                },
            )
            summary["count"] += 1
            summary["sections"].add(section_key)
            if item.get("blocked_review"):
                summary["blocked"] = True
            source_type = str(item.get("source_type", "unknown"))
            summary["source_types"][source_type] += 1

    ordered_fields = sorted(
        field_summary.items(),
        key=lambda item: (
            not item[1]["blocked"],
            -item[1]["count"],
            item[0],
        ),
    )

    evidence_priority: Counter[str] = Counter()
    for field_path, summary in ordered_fields:
        evidence_priority[_recommended_evidence(field_path)] += summary["count"]

    lines = [
        "# Vietnam PDD Gap Analysis",
        "",
        f"- Run ID: `{run_data.get('run_id', 'unknown')}`",
        f"- Project: `{run_data.get('project_name', 'unknown')}`",
        f"- Blocking review states: `{len(review_state_data.get('blocking_states', []))}`",
        f"- Low/unsupported sections: `{sum(1 for section in sections if section.get('confidence') in {'LOW', 'UNSUPPORTED'})}`",
        "",
        "## Missing Data That Most Reduced Confidence",
        "",
    ]

    if ordered_fields:
        for field_path, summary in ordered_fields:
            assumption = assumption_map.get(field_path, {})
            source_counts = ", ".join(
                f"{key}={value}" for key, value in sorted(summary["source_types"].items())
            )
            rationale = assumption.get("rationale", "No rationale recorded.")
            sections_text = ", ".join(sorted(summary["sections"]))
            lines.append(
                f"- `{field_path}` blocked=`{summary['blocked']}` hits=`{summary['count']}` sections=`{sections_text}` sources=`{source_counts}`"
            )
            lines.append(f"  Rationale: {rationale}")
            lines.append(f"  Fastest evidence add: {_recommended_evidence(field_path)}")
    else:
        lines.append("- No low-confidence synthetic gaps were recorded in the latest run.")

    lines.extend(["", "## Highest-Leverage External Documents", ""])
    if evidence_priority:
        for recommendation, count in evidence_priority.most_common():
            lines.append(f"- `{recommendation}` impact=`{count}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Current Blocking Review States", ""])
    blocking_states = review_state_data.get("blocking_states", [])
    if blocking_states:
        for item in blocking_states:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def write_vietnam_runbook(output_path: Path | str = DEFAULT_RUNBOOK_PATH) -> Path:
    """Write the operator runbook for rerunning the Vietnam workflow."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Vietnam PDD Runbook",
        "",
        "## Primary One-Command Path",
        "",
        "1. Run `python scripts/run_vietnam_pdd.py` to fetch the workbook, regenerate the Soc Son mapping artifacts, draft the run, review it, publish the Word review package, and refresh the Vietnam reports.",
        "2. Open `reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx` for the latest local review draft, or inspect the run-specific package under `reports/review-packages/soc-son-waste-to-power-plant-project/<run-id>/`.",
        "",
        "## Equivalent CLI Steps",
        "",
        "1. Run `pdd-agent fetch-workbook` to refresh the cached workbook under `data/source_inputs/spreadsheets/`.",
        "2. Run `pdd-agent map-spreadsheet --candidate soc-son` to regenerate the workbook profile, row snapshot, project YAML, assumptions YAML, and source profile report.",
        "3. Run `pdd-agent draft --input configs/projects/vietnam_socson_from_sheet.yaml --provider noop` to draft and review the current project input.",
        "4. Run `pdd-agent export --run-id <run-id> --review-output-dir reports/review-packages` to publish a reviewer-facing DOCX package from a saved run.",
        "5. Run `pdd-agent upload --review-docx reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx` when you want to upload the published review draft to Drive.",
        "",
        "## When the Spreadsheet Changes",
        "",
        "1. Re-run `pdd-agent fetch-workbook --force` if the Drive workbook changed.",
        "2. Re-run `pdd-agent map-spreadsheet --candidate soc-son` and inspect `docs/source-profile-vietnam-wte.md` for header or row drift.",
        "3. Review `configs/projects/vietnam_socson_from_sheet.assumptions.yaml` for any new blocked-review paths before sharing the draft.",
        "4. Re-run `python scripts/run_vietnam_pdd.py` so the validation report, gap analysis, and published review package stay aligned to the latest row snapshot.",
        "",
        "## Reusing the Flow for Another Vietnam Candidate",
        "",
        "1. Add a new candidate entry to `configs/source_mappings/vietnam_wte_projects.yaml`.",
        "2. Run `pdd-agent map-spreadsheet --candidate <candidate-key>` to generate the new project and assumptions artifacts.",
        "3. Run `pdd-agent draft --input <new-project-yaml> --provider noop` followed by `pdd-agent export --run-id <run-id> --review-output-dir reports/review-packages`.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _recommended_evidence(field_path: str) -> str:
    if field_path.startswith("quantification."):
        return "Detailed GHG calculation workbook plus cited Vietnam grid-emission-factor source"
    if field_path.startswith("monitoring."):
        return "Monitoring plan, metering SOPs, and equipment calibration records"
    if field_path.startswith("safeguards."):
        return "EIA package, stakeholder consultation records, and safeguards evidence"
    if field_path.startswith("location."):
        return "Site coordinates, landfill map, and project permit drawings"
    if field_path.startswith("project.") or field_path.startswith("compliance_and_ownership."):
        return "Executed ownership, sponsor, and carbon-rights documentation"
    if field_path.startswith("technology."):
        return "Technical datasheet, EPC summary, and plant operating design documents"
    return "Project-specific documentary evidence to replace the current synthetic assumption"
