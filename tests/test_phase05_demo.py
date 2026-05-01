"""Tests for Phase 05 benchmark and demo workflow."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from pdd_agent.llm.provider import DraftRun, DraftSection
from pdd_agent.phase05.benchmark import (
    BenchmarkArtifacts,
    compare_run_to_reference,
    create_demo_project_input,
    generate_demo_reports,
    load_draft_run,
    run_demo_benchmark,
)


def _make_section(
    section_id: str, sub_section_id: str, text: str, confidence: str = "HIGH"
) -> DraftSection:
    return DraftSection(
        section_id=section_id,
        sub_section_id=sub_section_id,
        text=text,
        confidence=confidence,
        provenance=[f"[CORPUS: RefDoc, {section_id}.{sub_section_id}]"] if text else [],
        issues=[] if confidence == "HIGH" else ["REVIEW REQUIRED"],
        provider="noop",
    )


def _make_run(tmp_path: Path, run_id: str = "demo-run") -> Path:
    run = DraftRun(run_id=run_id, project_name="Soc Son-like Demo", provider="noop")
    run.add(
        _make_section("1", "1.1", "Summary Description of the Project for Soc Son-like facility.")
    )
    run.add(
        _make_section("3", "3.4", "Baseline Scenario assumes landfill disposal without project.")
    )
    run.add(_make_section("3", "3.5", "Additionality is supported by investment barriers.", "LOW"))
    run.add(
        _make_section("4", "4.4", "Net GHG Emission Reductions and Removals are 75,000 tCO2e/year.")
    )
    return run.save(output_dir=tmp_path)


def _make_reference_norm(tmp_path: Path) -> Path:
    ref = {
        "text": "\n".join(
            [
                "1.1 Summary Description of the Project",
                "Soc Son project summary narrative.",
                "3.4 Baseline Scenario",
                "Waste would have been disposed at landfill in the baseline scenario.",
                "3.5 Additionality",
                "The project faces financial and common practice barriers.",
                "4.4 Net GHG Emission Reductions and Removals",
                "The project is expected to reduce 75,000 tCO2e per year.",
            ]
        ),
        "headings": [
            {"text": "1.1 Summary Description of the Project", "level": 1, "page": 1},
            {"text": "3.4 Baseline Scenario", "level": 1, "page": 2},
            {"text": "3.5 Additionality", "level": 1, "page": 3},
            {"text": "4.4 Net GHG Emission Reductions and Removals", "level": 1, "page": 4},
        ],
        "pages": [
            {
                "page": 1,
                "text": "1.1 Summary Description of the Project\nSoc Son project summary narrative.",
            },
            {
                "page": 2,
                "text": "3.4 Baseline Scenario\nWaste would have been disposed at landfill in the baseline scenario.",
            },
            {
                "page": 3,
                "text": "3.5 Additionality\nThe project faces financial and common practice barriers.",
            },
            {
                "page": 4,
                "text": "4.4 Net GHG Emission Reductions and Removals\nThe project is expected to reduce 75,000 tCO2e per year.",
            },
        ],
        "text_blocks": [
            {
                "heading": "1.1 Summary Description of the Project",
                "text": "Soc Son project summary narrative.",
            },
            {
                "heading": "3.4 Baseline Scenario",
                "text": "Waste would have been disposed at landfill in the baseline scenario.",
            },
            {
                "heading": "3.5 Additionality",
                "text": "The project faces financial and common practice barriers.",
            },
            {
                "heading": "4.4 Net GHG Emission Reductions and Removals",
                "text": "The project is expected to reduce 75,000 tCO2e per year.",
            },
        ],
    }
    path = tmp_path / "VCS_Soc Son_Project-Description.norm.json"
    path.write_text(json.dumps(ref, indent=2), encoding="utf-8")
    return path


def test_create_demo_project_input_contains_expected_structure(tmp_path: Path):
    output_path = tmp_path / "demo_socson_like.yaml"
    created = create_demo_project_input(output_path)

    data = yaml.safe_load(created.read_text(encoding="utf-8"))

    assert created == output_path
    assert data["project"]["project_name"]
    assert data["technology"]["methodology_ids"] == ["ACM0022"]
    assert data["technology"]["installed_capacity_mw"] > 0
    assert data["quantification"]["crediting_period_total_tco2e"] > 0


def test_create_demo_project_input_writes_assumptions_companion(tmp_path: Path):
    output_path = tmp_path / "demo_socson_like.yaml"
    created = create_demo_project_input(output_path)
    assumptions_path = created.with_name("demo_socson_like.assumptions.yaml")

    assert assumptions_path.exists()

    assumptions = yaml.safe_load(assumptions_path.read_text(encoding="utf-8"))

    assert assumptions["candidate_key"] == "soc-son-demo"
    assert assumptions["guardrails"]["blocked_review_paths"] == []
    by_path = {entry["field_path"]: entry for entry in assumptions["assumptions"]}
    assert by_path["project.project_name"]["source_type"] == "demo_curated"
    assert by_path["quantification.baseline_emissions_tco2e_per_year"]["source_type"] == "demo_curated"
    assert by_path["monitoring.parameters_monitored"]["source_type"] == "demo_curated"


def test_create_demo_project_input_keeps_quantification_consistent_with_assumptions(tmp_path: Path):
    output_path = tmp_path / "demo_socson_like.yaml"
    created = create_demo_project_input(output_path)
    assumptions_path = created.with_name("demo_socson_like.assumptions.yaml")

    data = yaml.safe_load(created.read_text(encoding="utf-8"))
    assumptions = yaml.safe_load(assumptions_path.read_text(encoding="utf-8"))
    by_path = {entry["field_path"]: entry for entry in assumptions["assumptions"]}

    assert data["quantification"]["baseline_emissions_tco2e_per_year"] == by_path[
        "quantification.baseline_emissions_tco2e_per_year"
    ]["value"]
    assert data["quantification"]["project_emissions_tco2e_per_year"] == by_path[
        "quantification.project_emissions_tco2e_per_year"
    ]["value"]
    assert data["quantification"]["net_emissions_tco2e_per_year"] == by_path[
        "quantification.net_emissions_tco2e_per_year"
    ]["value"]
    assert data["quantification"]["crediting_period_total_tco2e"] == by_path[
        "quantification.crediting_period_total_tco2e"
    ]["value"]


def test_load_draft_run_round_trips_saved_json(tmp_path: Path):
    run_path = _make_run(tmp_path, run_id="roundtrip-run")

    loaded = load_draft_run(run_path)

    assert loaded.run_id == "roundtrip-run"
    assert loaded.project_name == "Soc Son-like Demo"
    assert len(loaded.sections) == 4


def test_compare_run_to_reference_scores_sections(tmp_path: Path):
    run_path = _make_run(tmp_path)
    run = load_draft_run(run_path)
    reference_path = _make_reference_norm(tmp_path)

    comparison = compare_run_to_reference(run, reference_path)

    assert comparison["reference_document"] == reference_path.stem
    assert comparison["section_count"] == 4
    assert comparison["matched_sections"] >= 3
    assert comparison["placeholder_sections"] == 0
    assert comparison["low_confidence_sections"] == 1
    assert comparison["average_grounding_score"] >= 0


def test_generate_demo_reports_writes_expected_markdown(tmp_path: Path):
    run_path = _make_run(tmp_path, run_id="report-run")
    run = load_draft_run(run_path)
    reference_path = _make_reference_norm(tmp_path)

    comparison = compare_run_to_reference(run, reference_path)
    artifacts = generate_demo_reports(
        run=run,
        comparison=comparison,
        output_dir=tmp_path / "reports",
        runtime_seconds=3.2,
        manual_interventions=0,
        export_path=tmp_path / "report-run.docx",
    )

    scorecard = artifacts.demo_scorecard.read_text(encoding="utf-8")
    diff = artifacts.section_diff.read_text(encoding="utf-8")

    assert "# Demo Scorecard" in scorecard
    assert "report-run" in scorecard
    assert "Average grounding score" in scorecard
    assert "# Section Comparison Notes" in diff
    assert "3.4" in diff


def test_run_demo_benchmark_executes_end_to_end_with_existing_run(tmp_path: Path):
    run_path = _make_run(tmp_path, run_id="existing-run")
    reference_path = _make_reference_norm(tmp_path)
    config_path = create_demo_project_input(tmp_path / "demo_input.yaml")

    artifacts = run_demo_benchmark(
        project_input_path=config_path,
        reference_norm_path=reference_path,
        reports_dir=tmp_path / "reports",
        existing_run_path=run_path,
        export_docx=False,
    )

    assert isinstance(artifacts, BenchmarkArtifacts)
    assert artifacts.run_id == "existing-run"
    assert artifacts.demo_scorecard.exists()
    assert artifacts.section_diff.exists()
    assert artifacts.comparison_summary["matched_sections"] >= 3


def test_run_demo_benchmark_can_draft_and_review_without_existing_run(tmp_path: Path):
    config_path = create_demo_project_input(tmp_path / "demo_input.yaml")
    reference_path = _make_reference_norm(tmp_path)

    artifacts = run_demo_benchmark(
        project_input_path=config_path,
        reference_norm_path=reference_path,
        reports_dir=tmp_path / "reports",
        export_docx=False,
    )

    assert artifacts.run_json.exists()
    assert artifacts.demo_scorecard.exists()
    assert artifacts.section_diff.exists()
