"""Tests for the tiered DOCX export gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pdd_agent.export.docx_export import (
    ExportBlockedError,
    ExportGateResult,
    check_export_gate,
    export_run_to_docx,
)
from pdd_agent.llm.provider import DraftRun, DraftSection
from schemas.project_input import ProjectInput


_PROJECT_YAML = Path(__file__).parent.parent / "configs" / "projects" / "demo_socson_like.yaml"


def _load_project_input() -> ProjectInput:
    with open(_PROJECT_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    project_input = ProjectInput.model_validate(data)
    from schemas.project_input import EvidenceItem, EvidenceRegistry

    project_input.evidence_registry = EvidenceRegistry(
        items=[
            EvidenceItem(
                evidence_id="E001",
                source_type="user_input",
                description="Approved evidence item",
            )
        ]
    )
    return project_input


def _make_section(section_id: str, sub_section_id: str, text: str, **kwargs) -> DraftSection:
    defaults = {
        "confidence": "HIGH",
        "provenance": [],
        "issues": [],
        "provider": "noop",
        "review_sensitivity": "LOW",
        "content_class": "NARRATIVE",
    }
    defaults.update(kwargs)
    return DraftSection(
        section_id=section_id,
        sub_section_id=sub_section_id,
        text=text,
        **defaults,
    )


def _make_run(*sections: DraftSection) -> DraftRun:
    run = DraftRun(run_id="gate-test", project_name="Gate Test")
    for section in sections:
        run.add(section)
    return run


class TestExportGateResult:
    def test_result_passed_alias(self):
        result = ExportGateResult(blocked=False)
        assert result.passed is True
        assert result.blocked is False


class TestCalcContradiction:
    def test_blocks_when_section_1_10_number_contradicts_project_input(self):
        project_input = _load_project_input()
        run = _make_run(
            _make_section(
                "1",
                "1.10",
                "The project is expected to generate 1,000 tCO2e/year.",
                content_class="QUANTITATIVE",
                review_sensitivity="HIGH",
            )
        )
        result = check_export_gate(run, project_input=project_input)
        assert result.blocked is True
        assert any("1,000" in msg or "ProjectInput" in msg for msg in result.hard_blocks)


class TestEvidenceCitation:
    def test_blocks_fabricated_evidence_id(self):
        project_input = _load_project_input()
        run = _make_run(
            _make_section(
                "3",
                "3.2",
                "Applicability is supported by registry evidence [E999].",
                content_class="METHODOLOGY_DEPENDENT",
            )
        )
        result = check_export_gate(run, project_input=project_input)
        assert result.blocked is True
        assert any("E999" in msg for msg in result.hard_blocks)

    def test_allows_valid_evidence_id(self):
        project_input = _load_project_input()
        run = _make_run(
            _make_section(
                "3",
                "3.2",
                "Applicability is supported by registry evidence [E001].",
                content_class="METHODOLOGY_DEPENDENT",
            )
        )
        result = check_export_gate(run, project_input=project_input)
        assert result.blocked is False


class TestMissingMarkerGate:
    def test_blocks_unresolved_missing_in_section_3(self):
        run = _make_run(
            _make_section(
                "3",
                "3.3",
                "The project boundary is [MISSING] the required detail.",
                content_class="METHODOLOGY_DEPENDENT",
            )
        )
        result = check_export_gate(run)
        assert result.blocked is True
        assert any("[MISSING]" in msg and "3.3" in msg for msg in result.hard_blocks)

    def test_allows_missing_marker_in_non_quant_section(self):
        run = _make_run(
            _make_section(
                "1",
                "1.1",
                "Summary [MISSING] stakeholder detail.",
            )
        )
        result = check_export_gate(run)
        assert result.blocked is False


class TestAdvisoryExport:
    def test_clean_run_exports_as_draft(self):
        project_input = _load_project_input()
        run = _make_run(
            _make_section("1", "1.1", "Clean summary text."),
            _make_section(
                "4",
                "4.4",
                "Net reductions are 75,000 tCO2e/year.",
                content_class="QUANTITATIVE",
            ),
        )
        result = check_export_gate(run, project_input=project_input)
        assert result.blocked is False
        assert result.passed is True


class TestForceOverride:
    def test_force_records_override_but_keeps_hard_blocks(self):
        run = _make_run(
            _make_section(
                "3",
                "3.3",
                "Boundary [MISSING] detail.",
            )
        )
        result = check_export_gate(run, force=True)
        assert result.blocked is True
        assert result.force_used is True


class TestDocxExportIntegration:
    def test_export_raises_when_gate_blocked(self, tmp_path: Path, monkeypatch):
        run_dir = tmp_path / "data" / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        run = _make_run(
            _make_section(
                "3",
                "3.3",
                "Boundary [MISSING] detail.",
            )
        )
        run_path = run_dir / f"{run.run_id}.json"
        run_path.write_text(json.dumps(run.to_dict()), encoding="utf-8")
        monkeypatch.setattr("pdd_agent.export.docx_export._DRAFT_RUNS_DIR", run_dir)

        with pytest.raises(ExportBlockedError):
            export_run_to_docx(run.run_id, output_path=tmp_path / "out.docx")

    def test_export_succeeds_with_force_override(self, tmp_path: Path, monkeypatch):
        run_dir = tmp_path / "data" / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        run = _make_run(
            _make_section(
                "3",
                "3.3",
                "Boundary [MISSING] detail.",
            )
        )
        run_path = run_dir / f"{run.run_id}.json"
        run_path.write_text(json.dumps(run.to_dict()), encoding="utf-8")
        monkeypatch.setattr("pdd_agent.export.docx_export._DRAFT_RUNS_DIR", run_dir)

        output = export_run_to_docx(
            run.run_id,
            output_path=tmp_path / "forced.docx",
            force=True,
        )
        assert output.exists()
