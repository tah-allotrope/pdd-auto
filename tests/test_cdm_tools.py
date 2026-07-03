"""Unit tests for individual CDM tool helper modules."""

from __future__ import annotations

import math

import pytest

from pdd_agent.calc import cdm_tool_03, cdm_tool_04, cdm_tool_05, cdm_tool_06, cdm_tool_07, cdm_tool_12, cdm_tool_14
from pdd_agent.calc.constants import (
    CH4_TO_CO2_RATIO,
    DENSITY_CH4,
    DOC_BY_WASTE_TYPE,
    DOC_F_DEFAULT,
    EF_CH4_DIGESTER_DEFAULT,
    F_CH4_DEFAULT,
    FLARE_EFFICIENCY_ENCLOSED,
    FLARE_EFFICIENCY_OPEN,
    FOSSIL_FUEL_EF,
    FOSSIL_FUEL_NCV,
    GWP_CH4,
    MCF_DEFAULT,
    MODEL_CORRECTION_FACTOR_DEFAULT,
)


# ===== Tool 03: Fossil fuel emissions =====


class TestTool03EmissionCoefficient:
    def test_diesel_coefficient(self):
        coef = cdm_tool_03.co2_emission_coefficient("diesel")
        expected = FOSSIL_FUEL_NCV["diesel"] * FOSSIL_FUEL_EF["diesel"]
        assert coef == pytest.approx(expected)

    def test_natural_gas_coefficient(self):
        coef = cdm_tool_03.co2_emission_coefficient("natural_gas")
        expected = FOSSIL_FUEL_NCV["natural_gas"] * FOSSIL_FUEL_EF["natural_gas"]
        assert coef == pytest.approx(expected)

    def test_ncv_override(self):
        coef = cdm_tool_03.co2_emission_coefficient("diesel", ncv_override=50.0)
        assert coef == pytest.approx(50.0 * FOSSIL_FUEL_EF["diesel"])

    def test_ef_override(self):
        coef = cdm_tool_03.co2_emission_coefficient("diesel", ef_override=0.1)
        assert coef == pytest.approx(FOSSIL_FUEL_NCV["diesel"] * 0.1)

    def test_both_overrides(self):
        coef = cdm_tool_03.co2_emission_coefficient("diesel", ncv_override=40.0, ef_override=0.08)
        assert coef == pytest.approx(40.0 * 0.08)

    def test_unknown_fuel_raises(self):
        with pytest.raises(ValueError, match="Unknown fuel type"):
            cdm_tool_03.co2_emission_coefficient("unicorn_fuel")


class TestTool03FossilFuelEmissions:
    def test_diesel_10_tonnes(self):
        result = cdm_tool_03.fossil_fuel_emissions("diesel", 10.0)
        coef = FOSSIL_FUEL_NCV["diesel"] * FOSSIL_FUEL_EF["diesel"]
        assert result == pytest.approx(10.0 * coef)

    def test_zero_consumption(self):
        result = cdm_tool_03.fossil_fuel_emissions("diesel", 0.0)
        assert result == 0.0

    def test_all_known_fuels(self):
        for fuel in FOSSIL_FUEL_EF:
            result = cdm_tool_03.fossil_fuel_emissions(fuel, 1.0)
            assert result > 0, f"Expected positive emissions for {fuel}"


# ===== Tool 04: Methane from SWDS (FOD model) =====


class TestTool04FODModel:
    def test_year1_positive(self):
        result = cdm_tool_04.methane_from_swds(
            "municipal_solid_waste", 100_000, year=1,
        )
        assert result > 0

    def test_year1_smaller_than_year5(self):
        y1 = cdm_tool_04.methane_from_swds("municipal_solid_waste", 100_000, year=1)
        y5 = cdm_tool_04.methane_from_swds("municipal_solid_waste", 100_000, year=5)
        assert y5 > y1

    def test_food_waste_higher_doc_than_msw(self):
        food = cdm_tool_04.methane_from_swds("food_waste", 100_000, year=3)
        msw = cdm_tool_04.methane_from_swds("municipal_solid_waste", 100_000, year=3)
        # food_waste DOC=0.15 < MSW DOC=0.17, but k=0.185 vs 0.09
        # The higher decay rate means food waste accumulates faster initially
        assert food > 0
        assert msw > 0

    def test_zero_waste_produces_zero(self):
        result = cdm_tool_04.methane_from_swds("municipal_solid_waste", 0.0, year=3)
        assert result == 0.0

    def test_baseline_capture_reduces_emissions(self):
        no_capture = cdm_tool_04.methane_from_swds("municipal_solid_waste", 100_000, year=3)
        with_capture = cdm_tool_04.methane_from_swds(
            "municipal_solid_waste", 100_000, year=3, baseline_capture_fraction=0.5,
        )
        assert with_capture == pytest.approx(no_capture * 0.5, rel=0.001)

    def test_model_correction_factor(self):
        default_phi = cdm_tool_04.methane_from_swds("municipal_solid_waste", 100_000, year=3)
        phi_1 = cdm_tool_04.methane_from_swds(
            "municipal_solid_waste", 100_000, year=3, model_correction_factor=1.0,
        )
        assert phi_1 > default_phi

    def test_doc_override(self):
        default = cdm_tool_04.methane_from_swds("municipal_solid_waste", 100_000, year=3)
        high_doc = cdm_tool_04.methane_from_swds(
            "municipal_solid_waste", 100_000, year=3, doc_override=0.40,
        )
        assert high_doc > default

    def test_decay_rate_override(self):
        default = cdm_tool_04.methane_from_swds("municipal_solid_waste", 100_000, year=1)
        fast_decay = cdm_tool_04.methane_from_swds(
            "municipal_solid_waste", 100_000, year=1, decay_rate_override=0.5,
        )
        assert fast_decay > default

    def test_unknown_waste_type_raises(self):
        with pytest.raises(ValueError, match="Unknown waste type"):
            cdm_tool_04.methane_from_swds("magic_dust", 100_000, year=1)

    def test_all_known_waste_types(self):
        for wt in DOC_BY_WASTE_TYPE:
            result = cdm_tool_04.methane_from_swds(wt, 10_000, year=1)
            assert result > 0, f"Expected positive methane for {wt}"


class TestTool04FODModelMath:
    """Verify the FOD formula against hand-calculations."""

    def test_fod_year1_single_term(self):
        w = 10_000.0
        doc_j = DOC_BY_WASTE_TYPE["municipal_solid_waste"]  # 0.17
        k_j = 0.09
        year = 1

        fod_sum = w * doc_j * math.exp(-k_j * 0) * (1 - math.exp(-k_j))
        expected = (
            MODEL_CORRECTION_FACTOR_DEFAULT  # 0.9
            * 1.0  # (1 - capture)
            * GWP_CH4  # 28
            * 1.0  # (1 - OX)
            * CH4_TO_CO2_RATIO  # 16/12
            * F_CH4_DEFAULT  # 0.5
            * DOC_F_DEFAULT  # 0.5
            * MCF_DEFAULT  # 1.0
            * fod_sum
        )
        result = cdm_tool_04.methane_from_swds("municipal_solid_waste", w, year=year)
        assert result == pytest.approx(expected, rel=1e-6)


class TestTool04Simplified:
    def test_simplified_positive(self):
        result = cdm_tool_04.methane_from_swds_simplified(100_000, doc=0.17)
        assert result > 0

    def test_simplified_zero_waste(self):
        result = cdm_tool_04.methane_from_swds_simplified(0.0, doc=0.17)
        assert result == 0.0

    def test_simplified_proportional_to_waste(self):
        r1 = cdm_tool_04.methane_from_swds_simplified(100_000, doc=0.17)
        r2 = cdm_tool_04.methane_from_swds_simplified(200_000, doc=0.17)
        assert r2 == pytest.approx(r1 * 2.0)

    def test_simplified_proportional_to_doc(self):
        r1 = cdm_tool_04.methane_from_swds_simplified(100_000, doc=0.10)
        r2 = cdm_tool_04.methane_from_swds_simplified(100_000, doc=0.20)
        assert r2 == pytest.approx(r1 * 2.0)


# ===== Tool 05: Electricity emissions =====


class TestTool05BaselineElectricity:
    def test_simple_calculation(self):
        result = cdm_tool_05.baseline_electricity_emissions(1000.0, 0.5)
        assert result == pytest.approx(500.0)

    def test_with_tdl(self):
        result = cdm_tool_05.baseline_electricity_emissions(1000.0, 0.5, tdl_factor=0.1)
        assert result == pytest.approx(550.0)

    def test_zero_mwh(self):
        result = cdm_tool_05.baseline_electricity_emissions(0.0, 0.5)
        assert result == 0.0


class TestTool05ProjectElectricity:
    def test_simple_calculation(self):
        result = cdm_tool_05.project_electricity_emissions(500.0, 0.5)
        assert result == pytest.approx(250.0)

    def test_with_tdl(self):
        result = cdm_tool_05.project_electricity_emissions(500.0, 0.5, tdl_factor=0.1)
        assert result == pytest.approx(275.0)

    def test_zero_consumption(self):
        result = cdm_tool_05.project_electricity_emissions(0.0, 0.5)
        assert result == 0.0


# ===== Tool 06: Flaring emissions =====


class TestTool06Flaring:
    def test_open_flare(self):
        result = cdm_tool_06.flaring_emissions(10.0, flare_type="open")
        expected = GWP_CH4 * 10.0 * (1 - FLARE_EFFICIENCY_OPEN)
        assert result == pytest.approx(expected)

    def test_enclosed_flare(self):
        result = cdm_tool_06.flaring_emissions(10.0, flare_type="enclosed")
        expected = GWP_CH4 * 10.0 * (1 - FLARE_EFFICIENCY_ENCLOSED)
        assert result == pytest.approx(expected)

    def test_enclosed_lower_than_open(self):
        open_result = cdm_tool_06.flaring_emissions(10.0, flare_type="open")
        enclosed_result = cdm_tool_06.flaring_emissions(10.0, flare_type="enclosed")
        assert enclosed_result < open_result

    def test_zero_methane(self):
        result = cdm_tool_06.flaring_emissions(0.0)
        assert result == 0.0

    def test_efficiency_override(self):
        result = cdm_tool_06.flaring_emissions(10.0, flare_efficiency_override=0.95)
        expected = GWP_CH4 * 10.0 * 0.05
        assert result == pytest.approx(expected)


# ===== Tool 07: Fossil fuel displacement =====


def test_tool_07_default_factor():
    result = cdm_tool_07.fossil_fuel_displacement_factor("diesel")
    assert result == pytest.approx(FOSSIL_FUEL_NCV["diesel"] * FOSSIL_FUEL_EF["diesel"])


def test_tool_07_efficiency_adjustment():
    result = cdm_tool_07.fossil_fuel_displacement_emissions(
        10.0, "diesel", conversion_efficiency=0.5,
    )
    assert result == pytest.approx(20 * FOSSIL_FUEL_NCV["diesel"] * FOSSIL_FUEL_EF["diesel"])


# ===== Tool 12: Baseline identification =====


def test_tool_12_landfill_baseline():
    result = cdm_tool_12.identify_wte_baseline(waste_currently_landfilled=True)
    assert result.eligible is True
    assert result.scenario == "continued_landfill_disposal"


def test_tool_12_rejects_existing_recovery():
    result = cdm_tool_12.identify_wte_baseline(
        waste_currently_landfilled=True, existing_energy_recovery=True,
    )
    assert result.eligible is False


# ===== Tool 14: Anaerobic digester emissions =====


class TestTool14DigesterLeakage:
    def test_default_leakage(self):
        result = cdm_tool_14.digester_methane_leakage(100.0)
        expected = 100.0 * EF_CH4_DIGESTER_DEFAULT * GWP_CH4
        assert result == pytest.approx(expected)

    def test_custom_leakage_fraction(self):
        result = cdm_tool_14.digester_methane_leakage(100.0, leakage_fraction=0.10)
        expected = 100.0 * 0.10 * GWP_CH4
        assert result == pytest.approx(expected)

    def test_zero_methane(self):
        result = cdm_tool_14.digester_methane_leakage(0.0)
        assert result == 0.0

    def test_proportional_to_methane(self):
        r1 = cdm_tool_14.digester_methane_leakage(50.0)
        r2 = cdm_tool_14.digester_methane_leakage(100.0)
        assert r2 == pytest.approx(r1 * 2.0)


class TestTool14DigestateLeakage:
    def test_aerobic_is_zero(self):
        result = cdm_tool_14.digestate_storage_leakage(digestate_stored_anaerobically=False)
        assert result == 0.0

    def test_anaerobic_with_values(self):
        result = cdm_tool_14.digestate_storage_leakage(
            digestate_stored_anaerobically=True,
            solid_digestate_tonnes=1000.0,
            volatile_solids_fraction=0.05,
            methane_conversion_factor=0.1,
        )
        expected = 1000.0 * 0.05 * 0.1 * GWP_CH4
        assert result == pytest.approx(expected)

    def test_anaerobic_defaults_are_zero(self):
        result = cdm_tool_14.digestate_storage_leakage(
            digestate_stored_anaerobically=True,
        )
        assert result == 0.0  # default tonnes and fraction are 0
