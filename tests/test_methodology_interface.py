"""Regression tests that ACM0022 still works behind the pluggable interface."""

from __future__ import annotations

import pytest

from pdd_agent.calc.acm0022 import ACM0022Calculator
from pdd_agent.calc.methodology import ComputationResult, MethodologyEngine, ValidationResult
from pdd_agent.calc.models import ACM0022CalcInput


ACM0022_VALID_DICT = {
    "waste_streams": [{"waste_type": "municipal_solid_waste", "annual_tonnes": 100_000}],
    "biomethanization_fraction": 0.5,
    "grid_emission_factor_tco2_per_mwh": 0.5,
    "grid_emission_factor_source": "test default",
    "crediting_period_years": 10,
}


@pytest.fixture
def acm0022_engine() -> ACM0022Calculator:
    return ACM0022Calculator(ACM0022CalcInput(**ACM0022_VALID_DICT))


class TestACM0022BehindInterface:
    def test_is_instance_of_methodology_engine(self, acm0022_engine):
        assert isinstance(acm0022_engine, MethodologyEngine)

    def test_methodology_id(self, acm0022_engine):
        assert acm0022_engine.methodology_id() == "ACM0022"

    def test_validate_inputs_ok(self, acm0022_engine):
        result = acm0022_engine.validate_inputs(ACM0022_VALID_DICT)
        assert isinstance(result, ValidationResult)
        assert result.ok is True
        assert result.errors == []

    def test_validate_inputs_rejects_missing_required(self, acm0022_engine):
        result = acm0022_engine.validate_inputs({})
        assert isinstance(result, ValidationResult)
        assert result.ok is False
        assert any("waste_streams" in err for err in result.errors)

    def test_compute_baseline_shape(self, acm0022_engine):
        result = acm0022_engine.compute_baseline(ACM0022_VALID_DICT)
        assert isinstance(result, ComputationResult)
        assert result.unit == "tCO2e/year"
        assert result.value > 0
        assert "BE" in result.formula

    def test_compute_project_shape(self, acm0022_engine):
        result = acm0022_engine.compute_project(ACM0022_VALID_DICT)
        assert isinstance(result, ComputationResult)
        assert result.unit == "tCO2e/year"
        assert result.value >= 0

    def test_compute_leakage_shape(self, acm0022_engine):
        result = acm0022_engine.compute_leakage(ACM0022_VALID_DICT)
        assert isinstance(result, ComputationResult)
        assert result.unit == "tCO2e/year"
        assert result.value >= 0

    def test_compute_net_shape(self, acm0022_engine):
        result = acm0022_engine.compute_net(ACM0022_VALID_DICT)
        assert isinstance(result, ComputationResult)
        assert result.unit == "tCO2e/year"
        assert result.value > 0

    def test_compute_net_equals_baseline_minus_project_minus_leakage(self, acm0022_engine):
        baseline = acm0022_engine.compute_baseline(ACM0022_VALID_DICT).value
        project = acm0022_engine.compute_project(ACM0022_VALID_DICT).value
        leakage = acm0022_engine.compute_leakage(ACM0022_VALID_DICT).value
        net = acm0022_engine.compute_net(ACM0022_VALID_DICT).value
        assert net == pytest.approx(baseline - project - leakage, abs=0.01)

    def test_required_monitoring_params(self, acm0022_engine):
        params = acm0022_engine.required_monitoring_params(ACM0022_VALID_DICT)
        assert isinstance(params, list)
        assert len(params) >= 4
        for p in params:
            assert "id" in p
            assert "name" in p
            assert "unit" in p
