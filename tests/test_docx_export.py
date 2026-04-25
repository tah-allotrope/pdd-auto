"""Tests for Phase 04 DOCX export behavior."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from pdd_agent.export.docx_export import export_run_to_docx


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
    if importlib.util.find_spec("docx") is None:
        pytest.skip("python-docx not installed in test environment")

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


def test_export_run_to_docx_raises_clear_error_when_run_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pdd_agent.export.docx_export._DRAFT_RUNS_DIR", tmp_path / "runs")

    try:
        export_run_to_docx("missing-run", output_path=tmp_path / "missing.docx")
    except FileNotFoundError as exc:
        assert "missing-run" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")
