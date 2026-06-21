"""Integration tests for the ACM0022 calc engine.

Covers the QuantificationInputs.from_calc_result() bridge
and synthetic edge-case scenarios.
"""

from __future__ import annotations

import pytest

from pdd_agent.calc.acm0022 import ACM0022Calculator
from pdd_agent.calc.models import ACM0022CalcInput, ACM0022CalcResult, FossilFuelInput, WasteStream
from schemas.project_input import QuantificationInputs


# ===== from_calc_result bridge =====


class TestFromCalcResult:
    @pytest.fixture
    def calc_result(self) -> ACM0022CalcResult:
        inp = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000)],
            biomethanization_fraction=0.5,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            crediting_period_years=10,
        )
        return ACM0022Calculator(inp).calculate()

    def test_returns_quantification_inputs(self, calc_result):
        qi = QuantificationInputs.from_calc_result(calc_result)
        assert isinstance(qi, QuantificationInputs)

    def test_baseline_mapped(self, calc_result):
        qi = QuantificationInputs.from_calc_result(calc_result)
        assert qi.baseline_emissions_tco2e_per_year == calc_result.baseline_emissions_tco2e

    def test_project_mapped(self, calc_result):
        qi = QuantificationInputs.from_calc_result(calc_result)
        assert qi.project_emissions_tco2e_per_year == calc_result.project_emissions_tco2e

    def test_leakage_mapped(self, calc_result):
        qi = QuantificationInputs.from_calc_result(calc_result)
        assert qi.leakage_tco2e_per_year == calc_result.leakage_tco2e

    def test_net_mapped(self, calc_result):
        qi = QuantificationInputs.from_calc_result(calc_result)
        assert qi.net_emissions_tco2e_per_year == calc_result.net_emission_reductions_tco2e

    def test_crediting_total_mapped(self, calc_result):
        qi = QuantificationInputs.from_calc_result(calc_result)
        assert qi.crediting_period_total_tco2e == calc_result.crediting_period_total_tco2e


# ===== Edge-case scenarios =====


class TestEdgeCaseSmallScale:
    """Small-scale project: 10,000 t/year waste, low grid EF."""

    def test_positive_net(self):
        inp = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="food_waste", annual_tonnes=10_000)],
            biomethanization_fraction=0.8,
            grid_emission_factor_tco2_per_mwh=0.2,
            grid_emission_factor_source="small island grid",
            crediting_period_years=10,
            calculation_year=1,
        )
        result = ACM0022Calculator(inp).calculate()
        assert result.net_emission_reductions_tco2e > 0

    def test_smaller_than_large_scale(self):
        small = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="food_waste", annual_tonnes=10_000)],
            biomethanization_fraction=0.8,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            crediting_period_years=10,
        )
        large = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="food_waste", annual_tonnes=500_000)],
            biomethanization_fraction=0.8,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            crediting_period_years=10,
        )
        r_small = ACM0022Calculator(small).calculate()
        r_large = ACM0022Calculator(large).calculate()
        assert r_large.net_emission_reductions_tco2e > r_small.net_emission_reductions_tco2e


class TestEdgeCaseHighLeakage:
    """Scenario with high methane leakage and undocumented RDF export."""

    def test_high_leakage_reduces_net(self):
        base_inp = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000)],
            biomethanization_fraction=0.5,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            methane_leakage_fraction=0.05,
            crediting_period_years=10,
        )
        high_leak_inp = base_inp.model_copy(update={"methane_leakage_fraction": 0.15})

        r_base = ACM0022Calculator(base_inp).calculate()
        r_high = ACM0022Calculator(high_leak_inp).calculate()

        assert r_high.project_methane_leakage_tco2e > r_base.project_methane_leakage_tco2e
        assert r_high.net_emission_reductions_tco2e < r_base.net_emission_reductions_tco2e


class TestEdgeCaseZeroGridEF:
    """Grid with zero-carbon electricity."""

    def test_zero_grid_ef_still_has_methane_baseline(self):
        inp = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000)],
            biomethanization_fraction=0.5,
            grid_emission_factor_tco2_per_mwh=0.001,
            grid_emission_factor_source="hydro-dominated grid",
            crediting_period_years=10,
        )
        result = ACM0022Calculator(inp).calculate()
        assert result.baseline_methane_swds_tco2e > 0
        assert result.baseline_electricity_tco2e < 100  # near-zero


class TestEdgeCaseMultipleWasteStreams:
    """Project processing multiple waste types."""

    def test_multiple_streams(self):
        inp = ACM0022CalcInput(
            waste_streams=[
                WasteStream(waste_type="food_waste", annual_tonnes=50_000),
                WasteStream(waste_type="garden_waste", annual_tonnes=30_000),
                WasteStream(waste_type="paper_cardboard", annual_tonnes=20_000),
            ],
            biomethanization_fraction=0.6,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            crediting_period_years=10,
            calculation_year=3,
        )
        result = ACM0022Calculator(inp).calculate()
        total_waste = 100_000
        assert result.organic_waste_to_ad_tonnes == pytest.approx(total_waste * 0.6)
        assert result.net_emission_reductions_tco2e > 0

    def test_single_vs_multi_stream_same_total(self):
        """Single MSW stream vs. multi-stream with same total should differ
        because each waste type has different DOC and decay rate."""
        single = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000)],
            biomethanization_fraction=0.5,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            crediting_period_years=10,
            calculation_year=3,
        )
        multi = ACM0022CalcInput(
            waste_streams=[
                WasteStream(waste_type="food_waste", annual_tonnes=60_000),
                WasteStream(waste_type="paper_cardboard", annual_tonnes=40_000),
            ],
            biomethanization_fraction=0.5,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            crediting_period_years=10,
            calculation_year=3,
        )
        r_single = ACM0022Calculator(single).calculate()
        r_multi = ACM0022Calculator(multi).calculate()
        assert r_single.baseline_methane_swds_tco2e != pytest.approx(
            r_multi.baseline_methane_swds_tco2e, rel=0.01,
        )


class TestEdgeCaseFODTimeSeries:
    """Verify that FOD model ramps up over crediting period."""

    def test_year_by_year_ramp(self):
        inp = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000)],
            biomethanization_fraction=0.5,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            crediting_period_years=10,
        )
        values = []
        for yr in range(1, 11):
            inp_yr = inp.model_copy(update={"calculation_year": yr})
            result = ACM0022Calculator(inp_yr).calculate()
            values.append(result.baseline_methane_swds_tco2e)

        # Each year should produce more methane than the previous (FOD accumulation)
        for i in range(1, len(values)):
            assert values[i] > values[i - 1], f"Year {i + 1} should exceed year {i}"


class TestEdgeCaseRDFLeakage:
    """Undocumented RDF export creates leakage."""

    def test_rdf_leakage_calculation(self):
        inp = ACM0022CalcInput(
            waste_streams=[WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000)],
            biomethanization_fraction=0.5,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test",
            rdf_exported_tonnes_per_year=20_000,
            rdf_ncv_gj_per_tonne=10.5,
            rdf_fossil_carbon_ef_tco2_per_gj=0.05,
            rdf_end_use_documented=False,
            crediting_period_years=10,
        )
        result = ACM0022Calculator(inp).calculate()
        expected_rdf_leakage = 20_000 * 10.5 * 0.05  # 10,500 tCO2
        assert result.leakage_rdf_combustion_tco2e == pytest.approx(expected_rdf_leakage)
        assert result.leakage_tco2e > 0
