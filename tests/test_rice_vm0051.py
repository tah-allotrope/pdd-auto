"""Golden tests for the VM0051 rice cultivation calc engine.

Formula reference: Verra VM0051 "Methodology for Improved Agricultural Land Management"
and IPCC 2019 Refinement Wetlands Supplement default EF for flooded rice.

    Baseline CH4 = area_ha × cultivation_days × EF_kg_CH4_per_ha_per_day
    Project CH4  = Baseline CH4 × scaling_factor(practices)
    ER tCO2e     = (Baseline CH4 - Project CH4) × GWP_CH4 / 1000

Scaling factors for alternate wetting and drying (AWD) and dry seeding are
taken from the VM0051 guidance range. The golden numbers below are
synthetic-but-documented; replacing them with a registered VM0051 PDD's
published emission reductions is deferred until registry corpus ingestion
is complete.
"""

from __future__ import annotations

import pytest

from pdd_agent.calc.methodology import ComputationResult, MethodologyEngine, ValidationResult
from pdd_agent.calc.rice_vm0051 import RiceVm0051Engine


@pytest.fixture
def engine() -> RiceVm0051Engine:
    return RiceVm0051Engine()


@pytest.fixture
def golden_input() -> dict:
    return {
        "area_ha": 1000.0,
        "cultivation_days": 120,
        "baseline_water_regime": "continuously_flooded",
        "baseline_ef_kg_ch4_per_ha_per_day": 1.30,
        "project_practices": [
            {"practice": "alternate_wetting_drying"},
        ],
        "gwp_ch4": 28.0,
        "crediting_period_years": 7,
    }


class TestRiceInterface:
    def test_is_instance_of_methodology_engine(self, engine):
        assert isinstance(engine, MethodologyEngine)

    def test_methodology_id(self, engine):
        assert engine.methodology_id() == "VM0051"

    def test_validate_inputs_ok(self, engine, golden_input):
        result = engine.validate_inputs(golden_input)
        assert isinstance(result, ValidationResult)
        assert result.ok is True

    def test_validate_inputs_rejects_unknown_practice(self, engine, golden_input):
        golden_input["project_practices"].append({"practice": "alien_technology"})
        result = engine.validate_inputs(golden_input)
        assert result.ok is False


class TestRiceGolden:
    """Synthetic-but-documented numbers for AWD on 1,000 ha of flooded rice."""

    def test_baseline_and_net(self, engine, golden_input):
        baseline = engine.compute_baseline(golden_input)
        project = engine.compute_project(golden_input)
        net = engine.compute_net(golden_input)

        # Baseline CH4 = 1.30 kg/ha/day × 1000 ha × 120 days = 156,000 kg CH4
        # Baseline tCO2e = 156,000 × 28 / 1000 = 4,368 tCO2e/year
        expected_baseline_tco2e = 1.30 * 1000.0 * 120 * 28.0 / 1000.0
        # AWD scaling factor = 0.5
        expected_project_tco2e = expected_baseline_tco2e * 0.5
        expected_net_tco2e = expected_baseline_tco2e - expected_project_tco2e

        assert isinstance(baseline, ComputationResult)
        assert baseline.unit == "tCO2e/year"
        assert baseline.value == pytest.approx(expected_baseline_tco2e, rel=1e-9)
        assert project.value == pytest.approx(expected_project_tco2e, rel=1e-9)
        assert net.value == pytest.approx(expected_net_tco2e, rel=1e-9)

    def test_dry_seeding_and_awd_are_multiplicative(self, engine, golden_input):
        golden_input["project_practices"] = [
            {"practice": "alternate_wetting_drying"},
            {"practice": "dry_seeding"},
        ]
        baseline = engine.compute_baseline(golden_input).value
        project = engine.compute_project(golden_input).value
        # AWD 0.5 × dry_seeding 0.3 = 0.15
        assert project == pytest.approx(baseline * 0.5 * 0.3, rel=1e-9)

    def test_required_monitoring_params(self, engine, golden_input):
        params = engine.required_monitoring_params(golden_input)
        assert len(params) >= 4
        ids = {p["id"] for p in params}
        assert "VM0051-PARAM-01" in ids
