"""Tests for Phase 04 DOCX export behavior."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pdd_agent.export.docx_export import export_run_to_docx


def test_publish_review_package_creates_run_archive_and_latest_alias(tmp_path: Path):
    from pdd_agent.export.review_package import publish_review_package

    source_docx = tmp_path / "data" / "runs" / "run-123.docx"
    source_docx.parent.mkdir(parents=True, exist_ok=True)
    source_docx.write_bytes(b"docx-binary")

    validation_report = tmp_path / "reports" / "vietnam-pdd-validation.md"
    validation_report.parent.mkdir(parents=True, exist_ok=True)
    validation_report.write_text("validation", encoding="utf-8")

    gap_analysis = tmp_path / "reports" / "vietnam-pdd-gap-analysis.md"
    gap_analysis.write_text("gap", encoding="utf-8")

    assumption_burden = tmp_path / "reports" / "assumption-burden.md"
    assumption_burden.write_text("assumptions", encoding="utf-8")

    assumptions_yaml = tmp_path / "configs" / "project.assumptions.yaml"
    assumptions_yaml.parent.mkdir(parents=True, exist_ok=True)
    assumptions_yaml.write_text("assumptions: []\n", encoding="utf-8")

    project_yaml = tmp_path / "configs" / "project.yaml"
    project_yaml.write_text("project: {}\n", encoding="utf-8")

    package = publish_review_package(
        run_id="run-123",
        project_name="Soc Son Test Project",
        docx_path=source_docx,
        validation_report_path=validation_report,
        gap_analysis_path=gap_analysis,
        assumption_burden_path=assumption_burden,
        assumptions_yaml_path=assumptions_yaml,
        project_yaml_path=project_yaml,
        output_root=tmp_path / "reports" / "review-packages",
    )

    assert package.docx_path == tmp_path / "reports" / "review-packages" / "soc-son-test-project" / "run-123" / "run-123.docx"
    assert package.latest_docx_path == tmp_path / "reports" / "review-packages" / "soc-son-test-project" / "latest.docx"
    assert package.manifest_path.exists()
    assert package.docx_path.read_bytes() == b"docx-binary"
    assert package.latest_docx_path.read_bytes() == b"docx-binary"


def _write_run(tmp_path: Path, run_id: str = "docx-run") -> Path:
    run_dir = tmp_path / "data" / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "project_name": "Soc Son waste to power plant project",
        "provider": "noop",
        "assumption_register": {
            "assumptions": [
                {
                    "field_path": "quantification.baseline_emissions_tco2e_per_year",
                    "value": 594076.0,
                    "source_type": "synthetic_assumption",
                    "confidence": "low",
                },
                {
                    "field_path": "project.project_name",
                    "value": "Soc Son waste to power plant project",
                    "source_type": "spreadsheet",
                    "confidence": "high",
                },
            ],
            "guardrails": {
                "blocked_review_items": [
                    {
                        "field_path": "quantification.baseline_emissions_tco2e_per_year",
                        "reason": "Synthetic or demo-derived value requires human review before PDD use",
                    }
                ],
                "notes": ["Synthetic assumptions must not silently clear critical review gates."],
            },
        },
        "sections": [
            {
                "section_id": "1",
                "sub_section_id": "1.1",
                "text": "Draft summary text.",
                "confidence": "MEDIUM",
                "provenance": ["[CORPUS: VCS_Soc Son, 1.1 Summary Description of the Project]"],
                "issues": [
                    "ASSUMPTION DISCLOSURE: 1 synthetic/demo-backed field(s) affect this section."
                ],
                "provider": "noop",
                "fact_provenance": [
                    {
                        "field_path": "project.project_name",
                        "source_type": "spreadsheet",
                    },
                    {
                        "field_path": "quantification.baseline_emissions_tco2e_per_year",
                        "source_type": "synthetic_assumption",
                    },
                ],
                "synthetic_uses": [
                    {
                        "field_path": "quantification.baseline_emissions_tco2e_per_year",
                        "source_type": "synthetic_assumption",
                        "blocked_review": True,
                    }
                ],
                "output_references": [
                    {"type": "section narrative", "description": "section draft content"}
                ],
                "review_sensitivity": "LOW",
                "content_class": "BOILERPLATE",
            }
        ],
        "notes": [],
    }
    run_path = run_dir / f"{run_id}.json"
    run_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return run_path


def _read_docx_xml(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def test_export_run_to_docx_includes_disclaimer_and_appendices(tmp_path: Path, monkeypatch):
    run_path = _write_run(tmp_path)
    monkeypatch.setattr("pdd_agent.export.docx_export._DRAFT_RUNS_DIR", run_path.parent)

    output = export_run_to_docx("docx-run", output_path=tmp_path / "out.docx")
    xml = _read_docx_xml(output)

    assert output.exists()
    assert (
        "Internal draft for review; contains synthetic assumptions for missing project data" in xml
    )
    assert "Appendix A - Assumption Register" in xml
    assert "Appendix B - Reviewer Issues" in xml
    assert "quantification.baseline_emissions_tco2e_per_year" in xml


def test_export_run_to_docx_demo_mode_suppresses_reviewer_noise(tmp_path: Path, monkeypatch):
    run_path = _write_run(tmp_path, run_id="demo-docx-run")
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["provider"] = "demo"
    payload["assumption_register"]["assumptions"][0]["source_type"] = "demo_curated"
    payload["assumption_register"]["guardrails"]["blocked_review_items"] = []
    payload["sections"][0]["text"] = "This synthetic client-demo summary describes the Soc Son-like project in readable prose."
    payload["sections"][0]["issues"] = ["ASSUMPTION DISCLOSURE: demo fixture only."]
    payload["sections"][0]["synthetic_uses"][0]["source_type"] = "demo_curated"
    payload["sections"][0]["synthetic_uses"][0]["blocked_review"] = False
    run_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    monkeypatch.setattr("pdd_agent.export.docx_export._DRAFT_RUNS_DIR", run_path.parent)

    output = export_run_to_docx("demo-docx-run", output_path=tmp_path / "demo.docx")
    xml = _read_docx_xml(output)

    assert "synthetic client-demo sample" in xml
    assert "Appendix A - Assumption Summary" in xml
    assert "Appendix B - Reviewer Issues" not in xml
    assert "Review notes:" not in xml


def test_export_run_to_docx_raises_clear_error_when_run_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pdd_agent.export.docx_export._DRAFT_RUNS_DIR", tmp_path / "runs")

    try:
        export_run_to_docx("missing-run", output_path=tmp_path / "missing.docx")
    except FileNotFoundError as exc:
        assert "missing-run" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_upload_review_package_docx_prefers_published_artifact(tmp_path: Path):
    from pdd_agent.export.drive_upload import upload_review_package_docx

    latest_docx = tmp_path / "reports" / "review-packages" / "soc-son" / "latest.docx"
    latest_docx.parent.mkdir(parents=True, exist_ok=True)
    latest_docx.write_bytes(b"docx")

    with patch("pdd_agent.export.drive_upload.upload_file") as mock_upload:
        mock_upload.return_value = {"success": True, "drive_url": "https://drive.google.com/file/d/abc", "file_id": "abc", "error": None}
        result = upload_review_package_docx(
            review_docx_path=latest_docx,
            drive_folder_id="folder-123",
        )

    assert result["success"] is True
    mock_upload.assert_called_once_with(latest_docx, drive_folder_id="folder-123", drive_name=None)
