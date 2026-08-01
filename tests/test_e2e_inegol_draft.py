"""End-to-end test: Inegol PDD generation through orchestrator with demo provider.

Tests the full pipeline: schema loading -> prompt assembly -> section drafting ->
review checks -> budget tracking -> calc injection path (using DemoProvider for
deterministic, zero-cost output).
"""

import pytest
from pathlib import Path

import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.llm.provider import DemoProvider, NoopProvider
from pdd_agent.llm.budget import TokenBudget
from schemas.project_input import ProjectInput


_INEGOL_YAML = Path("configs/demo/inegol_project_input.yaml")
_SCHEMA_PATH = Path("schemas/pdd_section_schema.yaml")
_PROMPTS_DIR = Path("prompts")


@pytest.fixture
def inegol_input():
    if not _INEGOL_YAML.exists():
        pytest.skip(f"Inegol input YAML not found at {_INEGOL_YAML}")
    with open(_INEGOL_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ProjectInput(**data)


@pytest.fixture
def calc_result():
    """Build a mock ACM0022CalcResult for injection testing."""
    from unittest.mock import MagicMock

    cr = MagicMock()
    cr.baseline_emissions_tco2e = 75432.15
    cr.baseline_methane_swds_tco2e = 62100.50
    cr.baseline_electricity_tco2e = 13331.65
    cr.project_emissions_tco2e = 18500.00
    cr.project_electricity_consumption_tco2e = 4200.00
    cr.project_fossil_fuel_tco2e = 2800.00
    cr.project_methane_leakage_tco2e = 7500.00
    cr.project_flaring_tco2e = 4000.00
    cr.leakage_tco2e = 8200.00
    cr.leakage_rdf_combustion_tco2e = 7500.00
    cr.leakage_digestate_tco2e = 700.00
    cr.net_emission_reductions_tco2e = 48732.15
    cr.crediting_period_total_tco2e = 341125.05
    cr.crediting_period_years = 7
    cr.organic_waste_to_ad_tonnes = 55000.0
    cr.annual_biogas_m3 = 7150000.0
    cr.annual_methane_m3 = 4004000.0
    cr.annual_methane_tonnes = 2677.0
    cr.electricity_generated_mwh = 16400.0
    cr.methodology_version = "ACM0022 v3.0"
    return cr


class TestE2EInegolDraft:
    def test_demo_run_completes(self, inegol_input):
        """Full DemoProvider run should complete without errors."""
        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        run = orch.run()
        assert len(run.sections) > 0
        assert run.provider == "demo"
        assert run.project_name == inegol_input.project.project_name

    def test_noop_run_completes(self, inegol_input):
        """Full NoopProvider run should complete with UNSUPPORTED placeholders."""
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        run = orch.run()
        assert len(run.sections) > 0
        for section in run.sections:
            assert section.confidence == "UNSUPPORTED" or section.provider == "noop"

    def test_budget_tracking_through_run(self, inegol_input):
        """Budget should be attached and report zero usage for demo provider."""
        budget = TokenBudget(max_tokens=500_000)
        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            token_budget=budget,
        )
        run = orch.run()
        assert budget.total_tokens == 0
        assert any("token_budget" in note for note in run.notes)

    def test_calc_injection_wiring(self, inegol_input, calc_result):
        """Calc results should inject into Section 4 prompts."""
        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc_result,
        )
        assert orch.calc_result is not None
        text = orch._format_calc_injection()
        assert "ACM0022 Calculation Engine Results" in text
        assert "75,432.15" in text
        assert "[CALC: baseline_total]" in text

    def test_calc_injection_in_prompt(self, inegol_input, calc_result):
        """Section 4 prompt should include calc results when available."""
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc_result,
        )
        orch._use_v2_prompt = True
        examples = []
        prompt = orch._build_prompt("4", "4.1", examples, inegol_input)
        assert "ACM0022 Calculation Engine Results" in prompt

    def test_section_1_calc_injection(self, inegol_input, calc_result):
        """Section 1 prompt SHOULD include calc results (S-3: injection scope widened
        to Sections 1 and 4 in PHASE-05 of the calc-correctness-and-audit-trail plan)."""
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc_result,
        )
        orch._use_v2_prompt = True
        examples = []
        prompt = orch._build_prompt("1", "1.1", examples, inegol_input)
        assert "ACM0022 Calculation Engine Results" in prompt

    def test_review_run_completes(self, inegol_input, tmp_path):
        """Review pipeline should complete without errors."""
        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            assumption_burden_path=tmp_path / "assumption-burden.md",
        )
        orch.run()
        result = orch.run_review()
        assert "run_id" in result
        assert "review" in result
        assert "consistency" in result

    def test_v2_prompt_active_for_noop_with_override(self, inegol_input):
        """v2 prompt should be active when explicitly enabled."""
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = []
        prompt = orch._build_prompt("1", "1.1", examples, inegol_input)
        assert "Authority Order" in prompt
        assert "[MISSING]" in prompt

    def test_all_sections_have_provider(self, inegol_input):
        """Every section should report its provider."""
        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        run = orch.run()
        for section in run.sections:
            assert section.provider in ("demo", "noop", "openai")

    def test_run_save_and_load(self, inegol_input, tmp_path):
        """DraftRun should serialize to JSON and be loadable."""
        import json

        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=inegol_input,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        run = orch.run()
        path = run.save(output_dir=tmp_path)
        assert path.exists()

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["project_name"] == inegol_input.project.project_name
        assert len(data["sections"]) == len(run.sections)
