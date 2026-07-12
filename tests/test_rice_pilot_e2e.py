"""End-to-end demo-provider pilot for the VM0051 rice cultivation methodology.

PHASE-06 of plans/2026-07-12-pdd-reality-gap-plan.md: proves the pipeline
drafts, reviews, and exports a non-WTE project end-to-end with no unhandled
exceptions. Marker-free, no corpus dependency (matches the graceful-degradation
convention every other demo run relies on).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.export.docx_export import export_run_to_docx
from pdd_agent.llm.provider import DemoProvider
from schemas.project_input import ProjectInput

_PILOT_INPUT_PATH = Path("configs/projects/rice_vm0051_pilot.yaml")


@pytest.fixture()
def rice_project_input() -> ProjectInput:
    with open(_PILOT_INPUT_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ProjectInput.model_validate(data)


class TestRicePilotEndToEnd:
    def test_draft_all_sections_have_nonempty_text(
        self, rice_project_input: ProjectInput, tmp_path: Path
    ):
        orchestrator = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=rice_project_input,
            run_id="rice-pilot-e2e-test",
            assumption_burden_path=tmp_path / "assumption-burden.md",
            runs_dir=tmp_path,
        )
        run = orchestrator.run()

        assert len(run.sections) == 36
        for section in run.sections:
            assert section.text.strip() != ""

    def test_review_checks_run_without_raising(
        self, rice_project_input: ProjectInput, tmp_path: Path
    ):
        orchestrator = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=rice_project_input,
            run_id="rice-pilot-e2e-review",
            assumption_burden_path=tmp_path / "assumption-burden.md",
            runs_dir=tmp_path,
        )
        orchestrator.run()
        review = orchestrator.run_review()

        assert review["review"]["passed"] is True
        assert review["consistency"]["passed"] is True

    def test_consistency_check_holds_on_rice_quantification_numbers(
        self, rice_project_input: ProjectInput, tmp_path: Path
    ):
        """baseline - project - leakage == net must hold for non-WTE numbers too
        (review/consistency.py must be methodology-neutral)."""
        q = rice_project_input.quantification
        assert q.baseline_emissions_tco2e_per_year - q.project_emissions_tco2e_per_year - q.leakage_tco2e_per_year == pytest.approx(
            q.net_emissions_tco2e_per_year
        )

        orchestrator = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=rice_project_input,
            run_id="rice-pilot-e2e-consistency",
            assumption_burden_path=tmp_path / "assumption-burden.md",
            runs_dir=tmp_path,
        )
        orchestrator.run()
        review = orchestrator.run_review()
        assert review["consistency"]["passed"] is True
        assert review["consistency"]["critical_count"] == 0

    def test_docx_export_writes_file_over_20kb(
        self, rice_project_input: ProjectInput, tmp_path: Path
    ):
        orchestrator = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=rice_project_input,
            run_id="rice-pilot-e2e-export",
            assumption_burden_path=tmp_path / "assumption-burden.md",
            runs_dir=tmp_path,
        )
        orchestrator.run()
        orchestrator.run_review()

        output_path = export_run_to_docx(
            "rice-pilot-e2e-export",
            output_path=tmp_path / "rice-pilot.docx",
            project_input=rice_project_input,
            runs_dir=tmp_path,
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 20_000

    def test_demo_provider_text_is_methodology_aware(
        self, rice_project_input: ProjectInput, tmp_path: Path
    ):
        """Regression test: DemoProvider must not emit hardcoded WTE-specific
        narrative (landfill, biogas, waste-to-energy) for a rice project —
        see docs/2026-07-12-rice-pilot-findings.md."""
        orchestrator = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=rice_project_input,
            run_id="rice-pilot-e2e-wording",
            assumption_burden_path=tmp_path / "assumption-burden.md",
            runs_dir=tmp_path,
        )
        run = orchestrator.run()

        full_text = " ".join(s.text for s in run.sections).lower()
        assert "landfill" not in full_text
        assert "biogas" not in full_text
        assert "alternate wetting and drying" in full_text
