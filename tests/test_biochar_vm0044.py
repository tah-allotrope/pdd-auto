"""Golden tests for the VM0044 biochar calc engine."""

from __future__ import annotations

import pytest

from pdd_agent.calc.biochar_vm0044 import BiocharVm0044Engine
from pdd_agent.calc.methodology import ComputationResult, MethodologyEngine, ValidationResult


@pytest.fixture
def engine() -> BiocharVm0044Engine:
    return BiocharVm0044Engine()


@pytest.fixture
def golden_input() -> dict:
    return {
        "feedstock_type": "wood_chip",
        "dry_mass_tonnes": 1000.0,
        "carbon_fraction": 0.45,
        "pyrolysis_temperature_c": 450.0,
        "stability_factor": 0.80,
        "permanence_factor": 1.0,
        "crediting_period_years": 7,
    }


class TestBiocharInterface:
    def test_is_instance_of_methodology_engine(self, engine):
        assert isinstance(engine, MethodologyEngine)

    def test_methodology_id(self, engine):
        assert engine.methodology_id() == "VM0044"

    def test_validate_inputs_ok(self, engine, golden_input):
        result = engine.validate_inputs(golden_input)
        assert isinstance(result, ValidationResult)
        assert result.ok is True

    def test_validate_inputs_rejects_negative_mass(self, engine, golden_input):
        golden_input["dry_mass_tonnes"] = -100.0
        result = engine.validate_inputs(golden_input)
        assert result.ok is False


class TestBiocharGolden:
    """Synthetic-but-documented numbers for 1,000 t/year wood-chip biochar."""

    def test_net_carbon_removal(self, engine, golden_input):
        net = engine.compute_net(golden_input)

        # Stable C = 1000 t × 0.45 × 0.80 = 360 t C
        # tCO2e = 360 × (44/12) × 1.0 = 1320 tCO2e/year
        expected_stable_c = 1000.0 * 0.45 * 0.80
        expected_tco2e = expected_stable_c * (44.0 / 12.0) * 1.0

        assert isinstance(net, ComputationResult)
        assert net.unit == "tCO2e/year"
        assert net.value == pytest.approx(expected_tco2e, rel=1e-9)

    def test_baseline_and_project_are_zero(self, engine, golden_input):
        assert engine.compute_baseline(golden_input).value == 0.0
        assert engine.compute_project(golden_input).value == 0.0
        assert engine.compute_leakage(golden_input).value == 0.0

    def test_permanence_factor_discounts(self, engine, golden_input):
        golden_input["permanence_factor"] = 0.9
        net = engine.compute_net(golden_input).value
        expected = 1000.0 * 0.45 * 0.80 * (44.0 / 12.0) * 0.9
        assert net == pytest.approx(expected, rel=1e-9)

    def test_temperature_default_stability(self, engine, golden_input):
        # Remove explicit stability factor to exercise temperature-based default.
        golden_input["stability_factor"] = None
        # 450 °C falls in the medium bucket (0.75).
        net = engine.compute_net(golden_input).value
        expected = 1000.0 * 0.45 * 0.75 * (44.0 / 12.0) * 1.0
        assert net == pytest.approx(expected, rel=1e-9)

    def test_required_monitoring_params(self, engine, golden_input):
        params = engine.required_monitoring_params(golden_input)
        assert len(params) >= 4
        ids = {p["id"] for p in params}
        assert "VM0044-PARAM-01" in ids
