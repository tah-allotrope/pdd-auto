"""Tests for the Phase-05 Vietnam spreadsheet workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from pdd_agent.llm.provider import DraftRun, DraftSection
from pdd_agent.phase06.vietnam_workflow import (
    VietnamWorkflowArtifacts,
    render_gap_analysis_report,
    run_vietnam_pdd_workflow,
    write_vietnam_runbook,
)
from pdd_agent.phase06.spreadsheet_mapper import SpreadsheetArtifacts


def _section(
    section_id: str,
    sub_section_id: str,
    confidence: str,
    synthetic_uses: list[dict],
    issues: list[str] | None = None,
) -> DraftSection:
    return DraftSection(
        section_id=section_id,
        sub_section_id=sub_section_id,
        text=f"Draft text for {sub_section_id}",
        confidence=confidence,
        provenance=[],
        issues=issues or [],
        provider="noop",
        fact_provenance=[],
        synthetic_uses=synthetic_uses,
        review_sensitivity="HIGH",
        content_class="NARRATIVE",
    )


def test_render_gap_analysis_prioritizes_blocked_quant_fields():
    run = DraftRun(run_id="run-gap", project_name="Soc Son", provider="noop")
    run.add(
        _section(
            "4",
            "4.1",
            "LOW",
            [
                {
                    "field_path": "quantification.baseline_emissions_tco2e_per_year",
                    "source_type": "synthetic_assumption",
                    "blocked_review": True,
                }
            ],
            ["Needs real emissions split"],
        )
    )
    run.add(
        _section(
            "5",
            "5.1",
            "UNSUPPORTED",
            [
                {
                    "field_path": "monitoring.parameters_monitored",
                    "source_type": "synthetic_assumption",
                    "blocked_review": True,
                }
            ],
            ["Needs monitoring plan"],
        )
    )

    report = render_gap_analysis_report(
        run.to_dict(),
        {
            "blocking_states": [
                "4.4: Needs Domain Review",
                "5.1: Needs Domain Review",
            ]
        },
        {
            "assumptions": [
                {
                    "field_path": "quantification.baseline_emissions_tco2e_per_year",
                    "rationale": "Workbook only provides net annual emission reductions.",
                },
                {
                    "field_path": "monitoring.parameters_monitored",
                    "rationale": "Workbook does not include monitoring plan details.",
                },
            ]
        },
    )

    assert "# Vietnam PDD Gap Analysis" in report
    assert "quantification.baseline_emissions_tco2e_per_year" in report
    assert "Detailed GHG calculation workbook plus cited Vietnam grid-emission-factor source" in report
    assert "Monitoring plan, metering SOPs, and equipment calibration records" in report
    assert "4.4: Needs Domain Review" in report


def test_write_vietnam_runbook_lists_one_command_and_cli_paths(tmp_path: Path):
    runbook_path = write_vietnam_runbook(tmp_path / "vietnam-pdd-runbook.md")

    text = runbook_path.read_text(encoding="utf-8")

    assert runbook_path.exists()
    assert "python scripts/run_vietnam_pdd.py" in text
    assert "pdd-agent run-vietnam-pdd" not in text
    assert "pdd-agent fetch-workbook" in text
    assert "pdd-agent map-spreadsheet --candidate soc-son" in text


def test_run_vietnam_pdd_workflow_writes_phase05_reports(tmp_path: Path):
    workbook = tmp_path / "cache" / "workbook.xlsx"
    workbook.parent.mkdir(parents=True, exist_ok=True)
    workbook.write_bytes(b"xlsx")

    project_yaml = tmp_path / "configs" / "vietnam_socson_from_sheet.yaml"
    project_yaml.parent.mkdir(parents=True, exist_ok=True)
    project_yaml.write_text(
        yaml.safe_dump(
            {
                "project": {
                    "project_name": "Soc Son Test Project",
                    "project_id_vcs": "VCS-1234",
                    "proponent_name": "Synthetic Proponent",
                    "proponent_contact_email": "owner@example.com",
                    "other_entities": ["Entity"],
                    "ownership": "Ownership text",
                },
                "location": {
                    "country": "Vietnam",
                    "region": "Hanoi",
                    "city": "Soc Son",
                    "latitude": 21.261,
                    "longitude": 105.847,
                    "landfill_latitude": 21.275,
                    "landfill_longitude": 105.86,
                },
                "dates": {
                    "start_date": "2022-07-24",
                    "crediting_period_start": "2022-07-24",
                    "crediting_period_years": 7,
                    "project_scale_small": False,
                },
                "technology": {
                    "methodology_ids": ["ACM0022"],
                    "technology_type": "incineration_with_energy_recovery",
                    "waste_type": ["municipal_solid_waste"],
                    "annual_waste_throughput": 182500.0,
                    "installed_capacity_mw": 10.0,
                    "energy_generation_mwh_year": 74460.0,
                    "tip_fee_usd_per_tonne": 18.0,
                    "landfill_diversion_claim": True,
                    "fuel_substitution_claim": False,
                },
                "methodology_applicability": {
                    "eligibility_checklist": {"project treats municipal solid waste": True},
                    "deviation_from_methodology": None,
                },
                "quantification": {
                    "baseline_emissions_tco2e_per_year": 120000.0,
                    "project_emissions_tco2e_per_year": 50000.0,
                    "leakage_tco2e_per_year": 0.0,
                    "net_emissions_tco2e_per_year": 70000.0,
                    "grid_emission_factor": 0.92,
                    "grid_emission_factor_source": "placeholder source",
                    "methane_capture_rate": 0.2,
                    "methane_generation_factor": 0.06,
                    "crediting_period_total_tco2e": 490000.0,
                },
                "monitoring": {
                    "parameters_monitored": [
                        {
                            "name": "Waste throughput",
                            "unit": "tonnes/day",
                            "frequency": "daily",
                            "method": "weighbridge",
                            "data_source": "placeholder",
                        }
                    ],
                    "monitoring_equipment": ["weighbridge"],
                    "data_management": "placeholder",
                },
                "safeguards": {
                    "no_net_harm_statement": "placeholder",
                    "stakeholder_consultation_completed": False,
                    "stakeholder_consultation_date": None,
                    "environmental_impact_assessment": False,
                    "eia_reference": None,
                },
                "compliance_and_ownership": {
                    "no_participation_other_programs": True,
                    "no_other_forms_of_credit": True,
                    "other_ghg_programs": [],
                    "credit_ownership_statement": "placeholder",
                    "double_counting_risk": False,
                },
                "sustainable_development": {
                    "sd_contributions": ["Improves municipal waste handling"],
                    "sd_comments": "placeholder",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assumptions_yaml = tmp_path / "configs" / "vietnam_socson_from_sheet.assumptions.yaml"
    assumptions_payload = {
        "assumptions": [
            {
                "field_path": "quantification.baseline_emissions_tco2e_per_year",
                "source_type": "synthetic_assumption",
                "confidence": "low",
                "rationale": "Workbook only provides net annual emission reductions.",
                "value": 120000.0,
            }
        ],
        "guardrails": {
            "blocked_review_paths": ["quantification.baseline_emissions_tco2e_per_year"],
            "blocked_review_items": [
                {
                    "field_path": "quantification.baseline_emissions_tco2e_per_year",
                    "reason": "Synthetic split requires human review",
                }
            ],
            "notes": ["Synthetic assumptions must remain review-gated."],
        },
    }
    assumptions_yaml.write_text(
        yaml.safe_dump(assumptions_payload, sort_keys=False), encoding="utf-8"
    )

    source_report = tmp_path / "reports" / "source-profile-vietnam-wte.md"
    source_report.parent.mkdir(parents=True, exist_ok=True)
    source_report.write_text("# Source Profile\n", encoding="utf-8")

    spreadsheet_artifacts = SpreadsheetArtifacts(
        workbook_path=workbook,
        profile_json_path=tmp_path / "cache" / "profile.json",
        snapshot_json_path=tmp_path / "cache" / "snapshot.json",
        project_yaml_path=project_yaml,
        assumptions_yaml_path=assumptions_yaml,
        report_path=source_report,
    )

    internal_docx = tmp_path / "data" / "runs" / "viet-run.docx"
    internal_docx.parent.mkdir(parents=True, exist_ok=True)
    internal_docx.write_bytes(b"docx-binary")

    draft_run = DraftRun(run_id="viet-run", project_name="Soc Son Test Project", provider="noop")
    draft_run.assumption_register = assumptions_payload
    draft_run.add(
        _section(
            "4",
            "4.4",
            "LOW",
            [
                {
                    "field_path": "quantification.baseline_emissions_tco2e_per_year",
                    "source_type": "synthetic_assumption",
                    "confidence": "low",
                    "blocked_review": True,
                }
            ],
            ["REVIEW REQUIRED: 4.4 depends on review-gated synthetic inputs"],
        )
    )

    with patch("pdd_agent.phase06.vietnam_workflow.fetch_workbook", return_value=workbook), patch(
        "pdd_agent.phase06.vietnam_workflow.generate_project_artifacts",
        return_value=spreadsheet_artifacts,
    ), patch(
        "pdd_agent.phase06.vietnam_workflow.get_provider_registry"
    ) as mock_registry, patch(
        "pdd_agent.phase06.vietnam_workflow.SectionOrchestrator"
    ) as mock_orchestrator_cls, patch(
        "pdd_agent.phase06.vietnam_workflow.export_run_to_docx",
        return_value=internal_docx,
    ), patch(
        "pdd_agent.phase06.vietnam_workflow.ReviewStateStore.load"
    ) as mock_review_state_load:
        mock_registry.return_value.get.return_value = object()
        mock_orchestrator = mock_orchestrator_cls.return_value
        mock_orchestrator.run_id = "viet-run"
        mock_orchestrator.run.return_value = draft_run
        mock_orchestrator.run_review.return_value = {
            "run_id": "viet-run",
            "review": {
                "passed": False,
                "blocking_issues": ["REVIEW REQUIRED: 4.4 depends on review-gated synthetic inputs"],
                "auto_approved_sections": [],
            },
            "consistency": {"passed": True, "issues": []},
            "review_state_path": str(tmp_path / "data" / "runs" / "review-state-viet-run.json"),
            "draft_run_path": str(tmp_path / "data" / "runs" / "viet-run.json"),
            "assumption_burden_path": str(tmp_path / "reports" / "assumption-burden.md"),
        }
        mock_review_state_load.return_value.to_dict.return_value = {
            "blocking_states": ["4.4: Needs Domain Review"],
            "sections": {
                "4/4.4": {
                    "state": "needs-domain-review",
                }
            },
        }

        artifacts = run_vietnam_pdd_workflow(
            gap_analysis_path=tmp_path / "reports" / "vietnam-pdd-gap-analysis.md",
            review_package_dir=tmp_path / "reports" / "review-packages",
            runbook_path=tmp_path / "reports" / "vietnam-pdd-runbook.md",
            validation_report_path=tmp_path / "reports" / "vietnam-pdd-validation.md",
        )

    assert isinstance(artifacts, VietnamWorkflowArtifacts)
    assert artifacts.run_id == "viet-run"
    assert artifacts.docx_path == tmp_path / "reports" / "review-packages" / "soc-son-test-project" / "viet-run" / "viet-run.docx"
    assert artifacts.review_package_manifest_path == tmp_path / "reports" / "review-packages" / "soc-son-test-project" / "viet-run" / "manifest.json"
    assert artifacts.latest_docx_path == tmp_path / "reports" / "review-packages" / "soc-son-test-project" / "latest.docx"
    assert artifacts.gap_analysis_path.exists()
    assert artifacts.runbook_path.exists()
    assert artifacts.validation_report_path.exists()
    assert artifacts.docx_path.exists()
    assert artifacts.review_package_manifest_path.exists()
    assert artifacts.latest_docx_path.exists()
    assert "quantification.baseline_emissions_tco2e_per_year" in artifacts.gap_analysis_path.read_text(
        encoding="utf-8"
    )
    validation_text = artifacts.validation_report_path.read_text(encoding="utf-8")
    assert "Workflow Outcome" in validation_text
    assert "reports\\review-packages\\soc-son-test-project\\viet-run\\viet-run.docx" in validation_text
    assert "python scripts/run_vietnam_pdd.py" in artifacts.runbook_path.read_text(encoding="utf-8")
