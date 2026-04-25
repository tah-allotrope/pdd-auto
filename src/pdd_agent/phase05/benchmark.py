"""Phase 05 benchmark and demo workflow.

Creates a reproducible Soc Son-like demo input, runs or reuses a draft run,
compares it to a normalized reference document, and emits benchmark artifacts.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.export.docx_export import export_run_to_docx
from pdd_agent.llm.provider import DraftRun, DraftSection, get_provider_registry
from pdd_agent.phase06.assumptions import load_assumption_register, resolve_assumptions_path
from pdd_agent.parse.section_parser import parse_document
from schemas.project_input import ProjectInput

logger = structlog.get_logger()

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "configs" / "projects" / "demo_socson_like.yaml"
_DEFAULT_REPORTS_DIR = _REPO_ROOT / "reports"
_DEFAULT_REFERENCE_PATH = _REPO_ROOT / "template" / "VCS_Soc Son_Project-Description.pdf"
_DEFAULT_RUNS_DIR = _REPO_ROOT / "data" / "runs"


@dataclass
class BenchmarkArtifacts:
    run_id: str
    run_json: Path
    demo_scorecard: Path
    section_diff: Path
    export_docx: Path | None
    comparison_summary: dict[str, Any]
    runtime_seconds: float


def create_demo_project_input(output_path: Path | None = None) -> Path:
    """Write a reproducible Soc Son-like ProjectInput YAML."""
    output_path = output_path or _DEFAULT_CONFIG_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "project": {
            "project_name": "Soc Son-like Waste-to-Power Demonstration Project",
            "project_id_vcs": None,
            "proponent_name": "Soc Son Demo Project Company",
            "proponent_contact_email": "climate-demo@example.com",
            "other_entities": ["Municipal waste collection authority"],
            "ownership": "The project proponent owns and operates the WTE facility and the resulting carbon credits.",
        },
        "location": {
            "country": "Vietnam",
            "region": "Hanoi",
            "city": "Soc Son",
            "latitude": 21.259,
            "longitude": 105.848,
            "landfill_latitude": 21.275,
            "landfill_longitude": 105.86,
        },
        "dates": {
            "start_date": "2024-01-01",
            "crediting_period_start": "2026-01-01",
            "crediting_period_years": 10,
            "project_scale_small": False,
        },
        "technology": {
            "methodology_ids": ["ACM0022"],
            "technology_type": "incineration_with_energy_recovery",
            "waste_type": ["municipal_solid_waste"],
            "annual_waste_throughput": 182500.0,
            "installed_capacity_mw": 9.0,
            "energy_generation_mwh_year": 54000.0,
            "tip_fee_usd_per_tonne": 18.0,
            "landfill_diversion_claim": True,
            "fuel_substitution_claim": False,
        },
        "methodology_applicability": {
            "eligibility_checklist": {
                "waste would otherwise be landfilled": True,
                "project treats municipal solid waste": True,
                "electricity displacement is eligible": True,
            },
            "deviation_from_methodology": None,
        },
        "quantification": {
            "baseline_emissions_tco2e_per_year": 98000.0,
            "project_emissions_tco2e_per_year": 21000.0,
            "leakage_tco2e_per_year": 2000.0,
            "net_emissions_tco2e_per_year": 75000.0,
            "grid_emission_factor": 0.92,
            "grid_emission_factor_source": "national grid authority 2025 emission factor report",
            "methane_capture_rate": 0.2,
            "methane_generation_factor": 0.06,
            "crediting_period_total_tco2e": 750000.0,
        },
        "monitoring": {
            "parameters_monitored": [
                {
                    "name": "Waste throughput",
                    "unit": "tonnes/day",
                    "frequency": "daily",
                    "method": "weighbridge",
                    "data_source": "facility operations log",
                },
                {
                    "name": "Net electricity exported",
                    "unit": "MWh",
                    "frequency": "monthly",
                    "method": "revenue meter",
                    "data_source": "grid export statement",
                },
            ],
            "monitoring_equipment": ["Calibrated weighbridge", "Revenue-grade electricity meter"],
            "data_management": "Operations and monitoring data are logged digitally, reviewed monthly, and archived for verification.",
        },
        "safeguards": {
            "no_net_harm_statement": "A no-net-harm assessment has been completed for the demonstration case.",
            "stakeholder_consultation_completed": True,
            "stakeholder_consultation_date": "2025-09-15",
            "environmental_impact_assessment": True,
            "eia_reference": "Hanoi WTE EIA permit 2025-SS-17",
        },
        "compliance_and_ownership": {
            "no_participation_other_programs": True,
            "no_other_forms_of_credit": True,
            "other_ghg_programs": [],
            "credit_ownership_statement": "The project proponent retains exclusive ownership of the environmental attributes and carbon credits.",
            "double_counting_risk": False,
        },
        "sustainable_development": {
            "sd_contributions": [
                "Improves municipal waste handling",
                "Reduces landfill methane emissions",
                "Supplies lower-carbon electricity to the grid",
            ],
            "sd_comments": "This demonstration input is intentionally conservative and reviewable.",
        },
    }

    output_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return output_path


def load_draft_run(run_path: Path | str) -> DraftRun:
    """Load a persisted DraftRun JSON into the dataclass structure."""
    run_path = Path(run_path)
    with open(run_path, encoding="utf-8") as handle:
        data = json.load(handle)

    run = DraftRun(
        run_id=data["run_id"],
        project_name=data.get("project_name", "Unknown Project"),
        provider=data.get("provider", "noop"),
        notes=data.get("notes", []),
        assumption_register=data.get("assumption_register"),
    )
    for raw_section in data.get("sections", []):
        run.add(
            DraftSection(
                section_id=raw_section.get("section_id", ""),
                sub_section_id=raw_section.get("sub_section_id", ""),
                text=raw_section.get("text", ""),
                confidence=raw_section.get("confidence", "UNSUPPORTED"),
                provenance=raw_section.get("provenance", []),
                issues=raw_section.get("issues", []),
                provider=raw_section.get("provider", data.get("provider", "noop")),
                fact_provenance=raw_section.get("fact_provenance", []),
                synthetic_uses=raw_section.get("synthetic_uses", []),
                output_references=raw_section.get("output_references", []),
                review_sensitivity=raw_section.get("review_sensitivity", "LOW"),
                content_class=raw_section.get("content_class", "NARRATIVE"),
            )
        )
    return run


def compare_run_to_reference(run: DraftRun, reference_norm_path: Path | str) -> dict[str, Any]:
    """Compare run sections to a normalized reference document."""
    reference_norm_path = Path(reference_norm_path)
    parsed = parse_document(reference_norm_path)

    ref_by_key: dict[str, dict[str, Any]] = {}
    for entry in parsed.get("sections_mapped", []):
        sid = entry["canonical_section_id"]
        ssid = entry.get("canonical_sub_section_id") or ""
        ref_by_key[_make_key(sid, ssid)] = entry

    section_rows: list[dict[str, Any]] = []
    matched_sections = 0
    placeholder_sections = 0
    low_confidence_sections = 0
    supported_sections = 0
    total_grounding = 0.0

    for section in run.sections:
        key = _make_key(section.section_id, section.sub_section_id)
        ref = ref_by_key.get(key)
        matched = ref is not None
        matched_sections += 1 if matched else 0
        placeholder = "[PLACEHOLDER" in section.text
        placeholder_sections += 1 if placeholder else 0
        low_conf = 1 if section.confidence in {"LOW", "UNSUPPORTED"} else 0
        low_confidence_sections += low_conf
        if section.provenance:
            supported_sections += 1

        grounding_score = _grounding_score(section, ref.get("text_preview", "") if ref else "")
        total_grounding += grounding_score

        section_rows.append(
            {
                "key": key,
                "matched_reference": matched,
                "reference_heading": ref.get("canonical_heading", "") if ref else "",
                "grounding_score": grounding_score,
                "confidence": section.confidence,
                "issues": len(section.issues),
                "placeholder": placeholder,
                "provenance_count": len(section.provenance),
            }
        )

    total_sections = len(run.sections)
    average_grounding = round(total_grounding / total_sections, 3) if total_sections else 0.0

    return {
        "reference_document": parsed.get("document_name", reference_norm_path.stem),
        "section_count": total_sections,
        "matched_sections": matched_sections,
        "placeholder_sections": placeholder_sections,
        "low_confidence_sections": low_confidence_sections,
        "supported_sections": supported_sections,
        "average_grounding_score": average_grounding,
        "section_rows": section_rows,
    }


def generate_demo_reports(
    run: DraftRun,
    comparison: dict[str, Any],
    output_dir: Path | str | None = None,
    runtime_seconds: float = 0.0,
    manual_interventions: int = 0,
    export_path: Path | None = None,
) -> BenchmarkArtifacts:
    """Write the Phase 05 markdown artifacts to the reports directory."""
    output_dir = Path(output_dir or _DEFAULT_REPORTS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    scorecard_path = output_dir / "demo-scorecard.md"
    diff_path = output_dir / "section-diff.md"

    summary = run.summary()
    scorecard_path.write_text(
        _render_demo_scorecard(
            run=run,
            run_summary=summary,
            comparison=comparison,
            runtime_seconds=runtime_seconds,
            manual_interventions=manual_interventions,
            export_path=export_path,
        ),
        encoding="utf-8",
    )
    diff_path.write_text(_render_section_diff(run, comparison), encoding="utf-8")

    return BenchmarkArtifacts(
        run_id=run.run_id,
        run_json=_DEFAULT_RUNS_DIR / f"{run.run_id}.json",
        demo_scorecard=scorecard_path,
        section_diff=diff_path,
        export_docx=export_path,
        comparison_summary=comparison,
        runtime_seconds=runtime_seconds,
    )


def run_demo_benchmark(
    project_input_path: Path | str | None = None,
    reference_norm_path: Path | str | None = None,
    reports_dir: Path | str | None = None,
    existing_run_path: Path | str | None = None,
    provider_name: str = "noop",
    export_docx: bool = True,
) -> BenchmarkArtifacts:
    """Run or reuse the full Phase 05 benchmark workflow."""
    start = time.perf_counter()

    project_input_path = Path(project_input_path or create_demo_project_input())
    if not project_input_path.exists():
        project_input_path = create_demo_project_input(project_input_path)

    reference_norm_path = _resolve_reference_norm_path(reference_norm_path)

    if existing_run_path is not None:
        run_json_path = Path(existing_run_path)
        run = load_draft_run(run_json_path)
    else:
        with open(project_input_path, encoding="utf-8") as handle:
            project_input = ProjectInput.model_validate(yaml.safe_load(handle))

        provider = get_provider_registry().get(provider_name)
        orchestrator = SectionOrchestrator(provider=provider, project_input=project_input)
        assumptions_path = resolve_assumptions_path(project_input_path)
        if assumptions_path:
            orchestrator.attach_assumption_register(load_assumption_register(assumptions_path))
        run = orchestrator.run()
        run_json_path = run.save()
        orchestrator.run_review()

    docx_path = export_run_to_docx(run.run_id) if export_docx else None
    comparison = compare_run_to_reference(run, reference_norm_path)
    runtime_seconds = round(time.perf_counter() - start, 3)

    artifacts = generate_demo_reports(
        run=run,
        comparison=comparison,
        output_dir=reports_dir,
        runtime_seconds=runtime_seconds,
        manual_interventions=0,
        export_path=docx_path,
    )
    artifacts.run_json = run_json_path
    return artifacts


def _resolve_reference_norm_path(reference_norm_path: Path | str | None) -> Path:
    if reference_norm_path is not None:
        path = Path(reference_norm_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    normalized_candidate = (
        _REPO_ROOT / "data" / "corpus" / "normalized" / "VCS_Soc Son_Project-Description.norm.json"
    )
    if normalized_candidate.exists():
        return normalized_candidate

    pdf_candidate = _DEFAULT_REFERENCE_PATH
    if not pdf_candidate.exists():
        raise FileNotFoundError("No Soc Son reference document available for Phase 05 benchmark")

    from pdd_agent.ingest.normalize import _extract_text

    normalized_candidate.parent.mkdir(parents=True, exist_ok=True)
    extracted = _extract_text(pdf_candidate, "application/pdf", dry_run=False)
    normalized_candidate.write_text(
        json.dumps(extracted, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return normalized_candidate


def _make_key(section_id: str, sub_section_id: str) -> str:
    return sub_section_id or str(section_id)


def _normalize_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _grounding_score(section: DraftSection, reference_text: str) -> float:
    draft_tokens = _normalize_tokens(section.text)
    ref_tokens = _normalize_tokens(reference_text)
    overlap = len(draft_tokens & ref_tokens)
    score = 0.0
    if section.provenance:
        score += 0.4
    if ref_tokens:
        score += min(0.4, overlap / max(len(ref_tokens), 1))
    if section.confidence == "HIGH":
        score += 0.2
    elif section.confidence == "MEDIUM":
        score += 0.1
    return round(min(score, 1.0), 3)


def _render_demo_scorecard(
    run: DraftRun,
    run_summary: dict[str, Any],
    comparison: dict[str, Any],
    runtime_seconds: float,
    manual_interventions: int,
    export_path: Path | None,
) -> str:
    by_confidence = run_summary.get("by_confidence", {})
    strongest = sorted(
        comparison["section_rows"], key=lambda row: (-row["grounding_score"], row["key"])
    )[:3]
    weakest = sorted(
        comparison["section_rows"], key=lambda row: (row["grounding_score"], row["key"])
    )[:3]

    lines = [
        "# Demo Scorecard",
        "",
        f"- Run ID: `{run.run_id}`",
        f"- Project: `{run.project_name}`",
        f"- Provider: `{run.provider}`",
        f"- Reference: `{comparison['reference_document']}`",
        f"- Runtime seconds: `{runtime_seconds}`",
        f"- Manual interventions: `{manual_interventions}`",
        f"- DOCX export: `{export_path}`" if export_path else "- DOCX export: `not requested`",
        "",
        "## Coverage and Review Burden",
        "",
        f"- Total sections drafted: `{run_summary['total_sections']}`",
        f"- Matched reference sections: `{comparison['matched_sections']}`",
        f"- Supported sections with provenance: `{comparison['supported_sections']}`",
        f"- Placeholder sections: `{comparison['placeholder_sections']}`",
        f"- Low-confidence sections: `{comparison['low_confidence_sections']}`",
        f"- Total section issues: `{run_summary['total_issues']}`",
        f"- Average grounding score: `{comparison['average_grounding_score']}`",
        "",
        "## Confidence Breakdown",
        "",
    ]
    for confidence in sorted(by_confidence):
        lines.append(f"- `{confidence}`: `{by_confidence[confidence]}`")

    lines.extend(
        [
            "",
            "## Strongest Sections",
            "",
        ]
    )
    for row in strongest:
        lines.append(
            f"- `{row['key']}` grounding=`{row['grounding_score']}` confidence=`{row['confidence']}` matched_reference=`{row['matched_reference']}`"
        )

    lines.extend(
        [
            "",
            "## Weakest Sections",
            "",
        ]
    )
    for row in weakest:
        lines.append(
            f"- `{row['key']}` grounding=`{row['grounding_score']}` confidence=`{row['confidence']}` issues=`{row['issues']}`"
        )

    recommendation = "harden the same bucket"
    if comparison["low_confidence_sections"] > max(5, comparison["section_count"] // 3):
        recommendation = "pause and revisit architecture"
    elif comparison["matched_sections"] >= max(10, comparison["section_count"] // 2):
        recommendation = "add a second WTE bucket"

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- Recommended next step: `{recommendation}`.",
            "- This benchmark is still a workflow proof, not a claim of production-ready domain quality.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_section_diff(run: DraftRun, comparison: dict[str, Any]) -> str:
    rows_by_key = {row["key"]: row for row in comparison["section_rows"]}
    lines = [
        "# Section Comparison Notes",
        "",
        f"Reference document: `{comparison['reference_document']}`",
        "",
    ]
    for section in run.sections:
        key = _make_key(section.section_id, section.sub_section_id)
        row = rows_by_key[key]
        lines.extend(
            [
                f"## {key}",
                "",
                f"- Confidence: `{section.confidence}`",
                f"- Matched reference: `{row['matched_reference']}`",
                f"- Grounding score: `{row['grounding_score']}`",
                f"- Provenance count: `{len(section.provenance)}`",
                f"- Placeholder: `{row['placeholder']}`",
                f"- Issues: `{len(section.issues)}`",
                f"- Reference heading: `{row['reference_heading']}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"
