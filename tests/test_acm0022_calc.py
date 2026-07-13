"""Unit tests for the ACM0022 emission calculation engine."""

from __future__ import annotations

import pytest

from pdd_agent.calc.acm0022 import ACM0022Calculator
from pdd_agent.calc.models import (
    ACM0022CalcInput,
    ACM0022CalcResult,
    FossilFuelInput,
    WasteStream,
)


@pytest.fixture
def basic_input() -> ACM0022CalcInput:
    """A minimal valid ACM0022 input for testing."""
    return ACM0022CalcInput(
        waste_streams=[
            WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000),
        ],
        biomethanization_fraction=0.5,
        grid_emission_factor_tco2_per_mwh=0.5,
        grid_emission_factor_source="test default",
        crediting_period_years=10,
    )


@pytest.fixture
def inegol_like_input() -> ACM0022CalcInput:
    """Inputs approximating the Inegol VCS-3908 project."""
    return ACM0022CalcInput(
        waste_streams=[
            WasteStream(waste_type="municipal_solid_waste", annual_tonnes=262_970),
        ],
        biomethanization_fraction=0.45,
        biogas_yield_m3_per_tonne=130.0,
        methane_fraction_biogas=0.56,
        engine_electrical_efficiency=0.41,
        electricity_exported_mwh_per_year=49_935.0,
        electricity_consumed_from_grid_mwh_per_year=3_500.0,
        grid_emission_factor_tco2_per_mwh=0.48,
        grid_emission_factor_source="Turkish Ministry of Energy (combined margin)",
        tdl_factor=0.0,
        baseline_methane_captured_fraction=0.0,
        mcf=1.0,
        oxidation_factor=0.0,
        model_correction_factor=0.9,
        doc_f=0.5,
        f_ch4=0.5,
        rate_compliance=0.0,
        fossil_fuels=[
            FossilFuelInput(
                fuel_type="diesel",
                annual_consumption_tonnes=15.0,
            ),
        ],
        methane_leakage_fraction=0.05,
        flare_type="open",
        fraction_biogas_to_flare=0.02,
        rdf_exported_tonnes_per_year=30_000.0,
        rdf_end_use_documented=True,
        digestate_stored_anaerobically=False,
        crediting_period_years=7,
        calculation_year=4,
    )


class TestACM0022CalculatorBasic:
    def test_returns_result(self, basic_input):
        calc = ACM0022Calculator(basic_input)
        result = calc.calculate()
        assert isinstance(result, ACM0022CalcResult)

    def test_net_equals_baseline_minus_project_minus_leakage(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        expected = (
            result.baseline_emissions_tco2e - result.project_emissions_tco2e - result.leakage_tco2e
        )
        assert result.net_emission_reductions_tco2e == pytest.approx(expected, abs=0.01)

    def test_crediting_total_equals_net_times_years(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        expected = result.net_emission_reductions_tco2e * basic_input.crediting_period_years
        assert result.crediting_period_total_tco2e == pytest.approx(expected, abs=0.01)

    def test_baseline_is_positive(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.baseline_emissions_tco2e > 0

    def test_project_emissions_are_non_negative(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.project_emissions_tco2e >= 0

    def test_leakage_is_non_negative(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.leakage_tco2e >= 0

    def test_components_list_populated(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert len(result.components) >= 7

    def test_methodology_version(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.methodology_version == "ACM0022 v3.0"


class TestACM0022CalculatorIntermediate:
    def test_organic_waste_fraction(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.organic_waste_to_ad_tonnes == pytest.approx(50_000)

    def test_biogas_production(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        expected = 50_000 * 130.0  # organic_waste × yield
        assert result.annual_biogas_m3 == pytest.approx(expected)

    def test_methane_production(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        expected_m3 = 50_000 * 130.0 * 0.56  # × CH4 fraction
        assert result.annual_methane_m3 == pytest.approx(expected_m3)

    def test_electricity_estimated_from_biogas(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.electricity_generated_mwh > 0

    def test_electricity_override(self, basic_input):
        basic_input.electricity_exported_mwh_per_year = 42_000.0
        result = ACM0022Calculator(basic_input).calculate()
        assert result.electricity_generated_mwh == pytest.approx(42_000.0)


class TestACM0022BaselineComponents:
    def test_be_ch4_positive(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.baseline_methane_swds_tco2e > 0

    def test_be_electricity_positive(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.baseline_electricity_tco2e > 0

    def test_baseline_is_sum_of_components(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        expected = result.baseline_methane_swds_tco2e + result.baseline_electricity_tco2e
        assert result.baseline_emissions_tco2e == pytest.approx(expected, abs=0.01)

    def test_rate_compliance_reduces_baseline(self, basic_input):
        result_no_compliance = ACM0022Calculator(basic_input).calculate()
        basic_input.rate_compliance = 0.3
        result_with_compliance = ACM0022Calculator(basic_input).calculate()
        assert (
            result_with_compliance.baseline_emissions_tco2e
            < result_no_compliance.baseline_emissions_tco2e
        )

    def test_higher_grid_ef_increases_baseline(self, basic_input):
        result_low = ACM0022Calculator(basic_input).calculate()
        basic_input.grid_emission_factor_tco2_per_mwh = 0.9
        result_high = ACM0022Calculator(basic_input).calculate()
        assert result_high.baseline_electricity_tco2e > result_low.baseline_electricity_tco2e


class TestACM0022ProjectComponents:
    def test_pe_ec_from_grid_consumption(self, basic_input):
        basic_input.electricity_consumed_from_grid_mwh_per_year = 5000.0
        result = ACM0022Calculator(basic_input).calculate()
        expected = 5000.0 * 0.5  # MWh × grid EF
        assert result.project_electricity_consumption_tco2e == pytest.approx(expected)

    def test_pe_fc_from_diesel(self, basic_input):
        basic_input.fossil_fuels = [
            FossilFuelInput(fuel_type="diesel", annual_consumption_tonnes=10.0),
        ]
        result = ACM0022Calculator(basic_input).calculate()
        assert result.project_fossil_fuel_tco2e > 0

    def test_pe_ch4_methane_leakage(self, basic_input):
        result = ACM0022Calculator(basic_input).calculate()
        assert result.project_methane_leakage_tco2e > 0

    def test_higher_leakage_fraction_increases_pe_ch4(self, basic_input):
        result_low = ACM0022Calculator(basic_input).calculate()
        basic_input.methane_leakage_fraction = 0.10
        result_high = ACM0022Calculator(basic_input).calculate()
        assert result_high.project_methane_leakage_tco2e > result_low.project_methane_leakage_tco2e

    def test_pe_flare_zero_when_no_flaring(self, basic_input):
        basic_input.fraction_biogas_to_flare = 0.0
        result = ACM0022Calculator(basic_input).calculate()
        assert result.project_flaring_tco2e == 0.0

    def test_pe_flare_positive_when_flaring(self, basic_input):
        basic_input.fraction_biogas_to_flare = 0.1
        result = ACM0022Calculator(basic_input).calculate()
        assert result.project_flaring_tco2e > 0


class TestACM0022LeakageComponents:
    def test_le_rdf_zero_when_documented(self, basic_input):
        basic_input.rdf_exported_tonnes_per_year = 10_000
        basic_input.rdf_end_use_documented = True
        result = ACM0022Calculator(basic_input).calculate()
        assert result.leakage_rdf_combustion_tco2e == 0.0

    def test_le_rdf_zero_when_no_export(self, basic_input):
        basic_input.rdf_exported_tonnes_per_year = 0
        result = ACM0022Calculator(basic_input).calculate()
        assert result.leakage_rdf_combustion_tco2e == 0.0

    def test_le_rdf_positive_when_undocumented(self, basic_input):
        basic_input.rdf_exported_tonnes_per_year = 10_000
        basic_input.rdf_end_use_documented = False
        basic_input.rdf_fossil_carbon_ef_tco2_per_gj = 0.05
        result = ACM0022Calculator(basic_input).calculate()
        assert result.leakage_rdf_combustion_tco2e > 0

    def test_le_digestate_zero_when_aerobic(self, basic_input):
        basic_input.digestate_stored_anaerobically = False
        result = ACM0022Calculator(basic_input).calculate()
        assert result.leakage_digestate_tco2e == 0.0


class TestACM0022InegolValidation:
    """Validate against Inegol VCS-3908 published values.

    Published: 730,000 tCO2e over 7 years = 104,285 tCO2e/year average.
    Year-by-year values ramp up due to FOD model, so the year 4 value
    should be in the range of ~60,000-90,000 tCO2e.
    """

    def test_net_reductions_positive(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        assert result.net_emission_reductions_tco2e > 0

    def test_baseline_components_present(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        assert result.baseline_methane_swds_tco2e > 0
        assert result.baseline_electricity_tco2e > 0

    def test_electricity_matches_input(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        assert result.electricity_generated_mwh == pytest.approx(49_935.0)

    def test_baseline_electricity_reasonable(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        expected_approx = 49_935 * 0.48  # ~23,968 tCO2
        assert result.baseline_electricity_tco2e == pytest.approx(expected_approx, rel=0.01)

    def test_organic_waste_to_ad(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        expected = 262_970 * 0.45  # ~118,337 tonnes
        assert result.organic_waste_to_ad_tonnes == pytest.approx(expected, rel=0.01)

    def test_project_emissions_reasonable(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        # Project emissions should be much smaller than baseline
        assert result.project_emissions_tco2e < result.baseline_emissions_tco2e
        # But not zero (there's grid consumption, diesel, and AD leakage)
        assert result.project_emissions_tco2e > 100

    def test_leakage_zero_for_inegol(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        assert result.leakage_tco2e == 0.0

    def test_net_in_plausible_range(self, inegol_like_input):
        """Year 4 of a 7-year ramp should produce significant reductions."""
        result = ACM0022Calculator(inegol_like_input).calculate()
        assert result.net_emission_reductions_tco2e > 10_000
        assert result.net_emission_reductions_tco2e < 300_000

    def test_crediting_period_years(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        assert result.crediting_period_years == 7

    def test_diesel_project_emissions(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        assert result.project_fossil_fuel_tco2e > 0

    def test_result_serialization(self, inegol_like_input):
        result = ACM0022Calculator(inegol_like_input).calculate()
        data = result.model_dump()
        roundtrip = ACM0022CalcResult(**data)
        assert roundtrip.net_emission_reductions_tco2e == result.net_emission_reductions_tco2e
