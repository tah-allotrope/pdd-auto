"""Unit tests for PE_INC incineration emissions (S-5b)."""

from __future__ import annotations

from pathlib import Path

import structlog
import structlog.testing

from pdd_agent.calc.incineration import (
    combustion_ch4_n2o_eq27,
    combustion_co2_eq22,
    incineration_co2,
    incineration_emissions,
    incineration_n2o,
    wastewater_ch4_eq28,
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


def pytest_approx(value: float, abs: float = 0.01) -> object:
    import pytest

    return pytest.approx(value, abs=abs)


class TestCombustionCO2Eq22:
    def test_plastics_registered_fraction(self):
        assert combustion_co2_eq22(
            [{"waste_type": "plastics", "annual_tonnes": 43800.0}]
        ) == pytest_approx(136_510.0, abs=1.0)

    def test_registered_composition_matches_pdd(self):
        composition = [
            ("paper_cardboard", 39_420.0),
            ("textiles", 23_360.0),
            ("food_waste", 757_740.0),
            ("rubber_leather", 18_980.0),
            ("plastics", 43_800.0),
            ("metal", 13_140.0),
            ("glass", 7_300.0),
            ("inert", 556_260.0),
        ]
        streams = [{"waste_type": w, "annual_tonnes": t} for w, t in composition]
        assert combustion_co2_eq22(streams) == pytest_approx(272_843.0, abs=50.0)

    def test_biogenic_carbon_contributes_zero(self):
        assert combustion_co2_eq22([{"waste_type": "food_waste", "annual_tonnes": 1000.0}]) == 0.0

    def test_unknown_type_contributes_zero_without_raise(self):
        assert combustion_co2_eq22([{"waste_type": "unobtainium", "annual_tonnes": 1000.0}]) == 0.0


class TestCombustionCH4N2OEq27:
    def test_registered_scale_value(self):
        assert combustion_ch4_n2o_eq27(1_460_000.0) == pytest_approx(23_418.0, abs=5.0)


class TestWastewaterCH4Eq28:
    def test_registered_scale_value(self):
        assert wastewater_ch4_eq28(613_200.0, 0.035) == pytest_approx(120_187.0, abs=5.0)

    def test_zero_volume_returns_zero(self):
        assert wastewater_ch4_eq28(0.0, 0.035) == 0.0

    def _basic_input(self):
        from pdd_agent.calc.models import ACM0022CalcInput, WasteStream

        return ACM0022CalcInput(
            waste_streams=[
                WasteStream(waste_type="municipal_solid_waste", annual_tonnes=100_000),
            ],
            biomethanization_fraction=0.0,
            grid_emission_factor_tco2_per_mwh=0.5,
            grid_emission_factor_source="test default",
            crediting_period_years=10,
        )

    def test_no_wastewater_fields_gives_zero_pe_ww(self):
        from pdd_agent.calc.acm0022 import ACM0022Calculator

        result = ACM0022Calculator(self._basic_input()).calculate()
        pe_ww = next(c for c in result.components if c.name.startswith("PE_WW"))
        assert pe_ww.value_tco2e == 0.0

    def test_missing_wastewater_block_warns(self):
        import yaml

        from pdd_agent.calc.dispatch import _map_acm0022
        from schemas.project_input import ProjectInput

        root = Path(__file__).parent.parent
        with open(root / "configs/projects/vietnam_socson_from_sheet.yaml", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        data["technology"].pop("runoff_wastewater", None)
        mapped, warnings = _map_acm0022(ProjectInput.model_validate(data))
        assert mapped is not None
        assert "runoff_wastewater absent; PE_WW assumed zero" in warnings

    def test_inegol_declares_no_incineration_streams(self):
        import yaml

        from pdd_agent.calc.dispatch import _map_acm0022, compute_for
        from schemas.project_input import ProjectInput

        root = Path(__file__).parent.parent
        with open(root / "configs/demo/inegol_project_input.yaml", encoding="utf-8") as fh:
            pi = ProjectInput.model_validate(yaml.safe_load(fh))
        mapped, _warnings = _map_acm0022(pi)
        assert mapped is not None
        assert "incineration_streams" not in mapped
        assert compute_for(pi) is not None
