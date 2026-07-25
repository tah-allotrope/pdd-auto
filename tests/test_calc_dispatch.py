"""Tests for family-agnostic calc dispatch."""

from pathlib import Path

import pytest
import yaml

from pdd_agent.calc.dispatch import PddCalcResult, compute_for
from schemas.project_input import ProjectInput


def _load_pi(path: str) -> ProjectInput:
    root = Path(__file__).parent.parent
    with open(root / path, encoding="utf-8") as f:
        return ProjectInput.model_validate(yaml.safe_load(f))


class TestComputeFor:
    def test_rice_project_returns_result(self):
        pi = _load_pi("configs/projects/rice_vm0051_pilot.yaml")
        result = compute_for(pi)
        assert result is not None
        assert result.methodology_id == "VM0051"
        assert result.baseline_emissions_tco2e == pytest.approx(1.30 * 5000.0 * 220 * 28.0 / 1000.0)
        assert result.leakage_tco2e == 0.0
        assert result.net_emission_reductions_tco2e > 0
        assert result.crediting_period_total_tco2e == pytest.approx(
            result.net_emission_reductions_tco2e * result.crediting_period_years
        )
        assert len(result.components) == 4

    def test_inegol_computes_after_grid_ef_populated(self):
        # The config carried a null grid_emission_factor until the combined
        # margin (0.5410 tCO2/MWh) was read out of the VCS-3908 registered PDD.
        pi = _load_pi("configs/demo/inegol_project_input.yaml")
        result = compute_for(pi)
        assert result is not None
        assert result.methodology_id == "ACM0022"
        assert result.net_emission_reductions_tco2e > 0

    def test_socson_returns_acm0022_with_warning(self):
        pi = _load_pi("configs/projects/demo_socson_like.yaml")
        result = compute_for(pi)
        assert result is not None
        assert result.methodology_id == "ACM0022"
        assert result.raw_result is not None
        assert any("biomethanization_suitable_fraction absent" in w for w in result.warnings)
        assert result.crediting_period_years == 10

    def test_unsupported_methodology_returns_none(self):
        pi = _load_pi("configs/projects/rice_vm0051_pilot.yaml")
        pi.technology.methodology_ids = ["VM0033"]
        assert compute_for(pi) is None

    def test_vm0051_without_rice_cultivation_returns_none(self):
        pi = _load_pi("configs/projects/rice_vm0051_pilot.yaml")
        pi.technology.rice_cultivation = None
        assert compute_for(pi) is None


class TestPddCalcResultPromptBlock:
    def test_vm0051_prompt_block(self):
        result = PddCalcResult(
            methodology_id="VM0051",
            baseline_emissions_tco2e=40040.0,
            project_emissions_tco2e=28028.0,
            leakage_tco2e=0.0,
            net_emission_reductions_tco2e=12012.0,
            crediting_period_total_tco2e=84084.0,
            crediting_period_years=7,
        )
        block = result.to_prompt_block()
        assert "## VM0051 Calculation Engine Results" in block
        assert "[CALC: net_ER]" in block
        assert "40,040.00 tCO2e/year" in block
        assert "BE_CH4" not in block
        assert "organic waste" not in block.lower()

    def test_no_warnings_omits_section(self):
        result = PddCalcResult(
            methodology_id="VM0051",
            baseline_emissions_tco2e=100.0,
            project_emissions_tco2e=50.0,
            leakage_tco2e=0.0,
            net_emission_reductions_tco2e=50.0,
            crediting_period_total_tco2e=350.0,
            crediting_period_years=7,
            warnings=[],
        )
        assert "### Calculation Warnings" not in result.to_prompt_block()

    def test_with_warnings_includes_section(self):
        result = PddCalcResult(
            methodology_id="VM0051",
            baseline_emissions_tco2e=100.0,
            project_emissions_tco2e=50.0,
            leakage_tco2e=0.0,
            net_emission_reductions_tco2e=50.0,
            crediting_period_total_tco2e=350.0,
            crediting_period_years=7,
            warnings=["test warning"],
        )
        assert "### Calculation Warnings" in result.to_prompt_block()
        assert "test warning" in result.to_prompt_block()
