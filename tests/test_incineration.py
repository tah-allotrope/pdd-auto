"""Unit tests for PE_INC incineration emissions (S-5b)."""

from __future__ import annotations

import structlog
import structlog.testing

from pdd_agent.calc.incineration import (
    incineration_co2,
    incineration_emissions,
    incineration_n2o,
)


class TestIncinerationCO2:
    def test_plastics_fully_fossil(self):
        assert incineration_co2([{"waste_type": "plastics", "annual_tonnes": 1000.0}]) == (
            pytest_approx(2750.0)
        )

    def test_food_waste_biogenic_excluded(self):
        assert incineration_co2([{"waste_type": "food_waste", "annual_tonnes": 1000.0}]) == 0.0

    def test_textiles_partial_fossil(self):
        assert incineration_co2([{"waste_type": "textiles", "annual_tonnes": 1000.0}]) == (
            pytest_approx(293.3333)
        )

    def test_oxidation_factor_override(self):
        assert incineration_co2(
            [{"waste_type": "plastics", "annual_tonnes": 1000.0}], oxidation_factor=0.98
        ) == pytest_approx(2695.0)

    def test_unknown_type_warns_and_contributes_zero(self, caplog):
        with structlog.testing.capture_logs() as logs:
            result = incineration_co2([{"waste_type": "unknown_type", "annual_tonnes": 1000.0}])
        assert result == 0.0
        assert any(
            e.get("event") == "incineration_waste_type_unknown"
            and e.get("waste_type") == "unknown_type"
            for e in logs
        )

    def test_overrides_applied(self):
        result = incineration_co2(
            [
                {
                    "waste_type": "food_waste",
                    "annual_tonnes": 1000.0,
                    "dm_override": 1.0,
                    "cf_override": 1.0,
                    "fcf_override": 1.0,
                }
            ]
        )
        assert result == pytest_approx(1000.0 * 44.0 / 12.0)


class TestIncinerationN2O:
    def test_full_scale_value(self):
        assert incineration_n2o(1_460_000.0) == pytest_approx(19_345.0)

    def test_custom_ef(self):
        assert incineration_n2o(1000.0, ef_kg_per_tonne=0.1) == pytest_approx(26.5)


class TestIncinerationEmissions:
    def test_empty_streams_return_zero(self):
        assert incineration_emissions([]) == 0.0

    def test_co2_plus_n2o(self):
        streams = [{"waste_type": "plastics", "annual_tonnes": 1000.0}]
        expected = 2750.0 + incineration_n2o(1000.0)
        assert incineration_emissions(streams) == pytest_approx(expected)


def pytest_approx(value: float) -> object:
    import pytest

    return pytest.approx(value, abs=0.01)
