"""Golden tests for the AMS-II.G cookstove calc engine.

Formula reference: AMS-II.G "Efficient and clean renewable fuel-burning cookstoves"
(UNFCCC small-scale CDM methodology). Baseline/project emissions are computed as:

    E = Σ (fuel_mass_tonnes × NCV_MJ_per_kg × EF_kg_CO2_per_MJ × fNRB) / 1000

where fNRB is the fraction of non-renewable biomass. The golden numbers below are
synthetic-but-documented; replacing them with values from a registered Verra/GS
PDD is deferred until registry corpus ingestion is complete.
"""

from __future__ import annotations

import pytest

from pdd_agent.calc.cookstove_amsiig import CookstoveAmsiigEngine
from pdd_agent.calc.methodology import ComputationResult, MethodologyEngine, ValidationResult


@pytest.fixture
def engine() -> CookstoveAmsiigEngine:
    return CookstoveAmsiigEngine()


@pytest.fixture
def golden_input() -> dict:
    return {
        "stoves": [
            {
                "fuel_type": "wood",
                "stove_count": 10_000,
                "baseline_fuel_kg_per_day_per_stove": 2.0,
                "project_fuel_kg_per_day_per_stove": 1.2,
                "operating_days_per_year": 365,
                "ncv_mj_per_kg": 15.0,
                "ef_kg_co2_per_mj": 0.068,
                "fnrb": 0.9,
            }
        ],
        "crediting_period_years": 7,
    }


class TestCookstoveInterface:
    def test_is_instance_of_methodology_engine(self, engine):
        assert isinstance(engine, MethodologyEngine)

    def test_methodology_id(self, engine):
        assert engine.methodology_id() == "AMS-II.G"

    def test_validate_inputs_ok(self, engine, golden_input):
        result = engine.validate_inputs(golden_input)
        assert isinstance(result, ValidationResult)
        assert result.ok is True

    def test_validate_inputs_rejects_project_fuel_above_baseline(self, engine, golden_input):
        golden_input["stoves"][0]["project_fuel_kg_per_day_per_stove"] = 3.0
        result = engine.validate_inputs(golden_input)
        assert result.ok is False


class TestCookstoveGolden:
    """Synthetic-but-documented numbers for a 10,000-stove wood-fuel programme."""

    def test_baseline_fuel_and_emissions(self, engine, golden_input):
        baseline = engine.compute_baseline(golden_input)
        project = engine.compute_project(golden_input)
        net = engine.compute_net(golden_input)

        # 10,000 stoves × 2.0 kg/day × 365 d / 1000 = 7,300 tonnes fuel/year
        expected_baseline_fuel = 10_000 * 2.0 * 365 / 1000.0
        # project fuel = 10,000 × 1.2 × 365 / 1000 = 4,380 tonnes/year
        expected_project_fuel = 10_000 * 1.2 * 365 / 1000.0
        saved_fuel = expected_baseline_fuel - expected_project_fuel  # 2,920 t

        # emissions = fuel_tonnes × NCV × EF × fNRB
        expected_baseline_tco2e = expected_baseline_fuel * 15.0 * 0.068 * 0.9
        expected_project_tco2e = expected_project_fuel * 15.0 * 0.068 * 0.9
        expected_net_tco2e = saved_fuel * 15.0 * 0.068 * 0.9

        assert isinstance(baseline, ComputationResult)
        assert baseline.unit == "tCO2e/year"
        assert baseline.value == pytest.approx(expected_baseline_tco2e, rel=1e-9)
        assert project.value == pytest.approx(expected_project_tco2e, rel=1e-9)
        assert net.value == pytest.approx(expected_net_tco2e, rel=1e-9)

    def test_net_equals_baseline_minus_project(self, engine, golden_input):
        baseline = engine.compute_baseline(golden_input).value
        project = engine.compute_project(golden_input).value
        leakage = engine.compute_leakage(golden_input).value
        net = engine.compute_net(golden_input).value
        assert leakage == 0.0
        assert net == pytest.approx(baseline - project - leakage, abs=0.001)

    def test_required_monitoring_params(self, engine, golden_input):
        params = engine.required_monitoring_params(golden_input)
        assert len(params) >= 4
        ids = {p["id"] for p in params}
        assert "AMSIIG-PARAM-01" in ids

    def test_registered_pdd_reference_shape(self, engine):
        """Shape check for a real registered PDD once registry data is available.

        When a registered cookstove PDD is ingested, this test should be
        replaced with an assertion against the PDD's published annual ERs.
        For now it verifies the engine accepts a realistic multi-stove fleet.
        """
        multi_stove_input = {
            "stoves": [
                {
                    "fuel_type": "wood",
                    "stove_count": 5_000,
                    "baseline_fuel_kg_per_day_per_stove": 2.5,
                    "project_fuel_kg_per_day_per_stove": 1.5,
                    "operating_days_per_year": 350,
                    "ncv_mj_per_kg": 15.0,
                    "ef_kg_co2_per_mj": 0.068,
                    "fnrb": 0.85,
                },
                {
                    "fuel_type": "charcoal",
                    "stove_count": 2_500,
                    "baseline_fuel_kg_per_day_per_stove": 1.0,
                    "project_fuel_kg_per_day_per_stove": 0.6,
                    "operating_days_per_year": 350,
                    "ncv_mj_per_kg": 30.0,
                    "ef_kg_co2_per_mj": 0.091,
                    "fnrb": 0.6,
                },
            ],
            "crediting_period_years": 7,
        }
        net = engine.compute_net(multi_stove_input)
        assert net.value > 0
        assert net.unit == "tCO2e/year"
