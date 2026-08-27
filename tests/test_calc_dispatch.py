"""Tests for family-agnostic calc dispatch."""

import json
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


class TestAnnualSchedule:
    def test_soc_son_schedule_length_and_bounds(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        assert pi.dates.crediting_period_years == 7
        assert len(result.annual_schedule) == 7
        assert result.annual_schedule[0].year == 1
        assert result.annual_schedule[-1].year == 7

    def test_soc_son_baseline_monotonic_increase(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        assert result.annual_schedule[6].baseline_tco2e > result.annual_schedule[0].baseline_tco2e

    def test_schedule_sum_matches_crediting_period_total(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        assert (
            abs(
                sum(e.net_tco2e for e in result.annual_schedule)
                - result.crediting_period_total_tco2e
            )
            < 0.01
        )

    def test_scalar_fields_describe_year_one(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        assert result.baseline_emissions_tco2e == pytest.approx(
            result.annual_schedule[0].baseline_tco2e
        )

    def test_rice_flat_schedule(self):
        pi = _load_pi("configs/projects/rice_vm0051_pilot.yaml")
        result = compute_for(pi)
        assert result is not None
        values = [e.net_tco2e for e in result.annual_schedule]
        assert all(abs(v - values[0]) < 0.01 for v in values)
        assert abs(sum(values) - result.crediting_period_total_tco2e) < 0.01

    def test_monitoring_params_populated_for_acm0022(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        assert len(result.monitoring_params) == 4
        assert [p["id"] for p in result.monitoring_params] == [
            "ACM0022-PARAM-01",
            "ACM0022-PARAM-02",
            "ACM0022-PARAM-03",
            "ACM0022-PARAM-04",
        ]

    def test_prompt_block_contains_schedule_heading(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        assert "Year-by-Year Emission Reductions" in result.to_prompt_block()

    def test_single_year_crediting_period(self):
        pi = _load_pi("configs/projects/rice_vm0051_pilot.yaml")
        pi.dates.crediting_period_years = 1
        result = compute_for(pi)
        assert result is not None
        assert len(result.annual_schedule) == 1
        assert result.crediting_period_total_tco2e == pytest.approx(
            result.annual_schedule[0].net_tco2e
        )


class TestPddCalcResultSerialization:
    def test_to_dict_json_safe(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        json.dumps(result.to_dict())  # must not raise TypeError (raw_result excluded)

    def test_round_trip_preserves_scalars_and_schedule(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        restored = PddCalcResult.from_dict(result.to_dict())
        assert restored.methodology_id == result.methodology_id
        assert restored.net_emission_reductions_tco2e == pytest.approx(
            result.net_emission_reductions_tco2e
        )
        assert len(restored.annual_schedule) == len(result.annual_schedule)
        assert restored.raw_result is None

    def test_from_dict_tolerates_missing_keys(self):
        restored = PddCalcResult.from_dict({"methodology_id": "ACM0022"})
        assert restored.methodology_id == "ACM0022"
        assert restored.components == []
        assert restored.annual_schedule == []


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


class TestWasteCompositionMassConservation:
    """PHASE-05 (2026-08-13 plan): S-2 mass conservation and composition weighting."""

    def test_mass_conservation_fallback_path(self):
        import copy

        from pdd_agent.calc.dispatch import build_engine_inputs

        data = yaml.safe_load(
            open(
                Path(__file__).parent.parent / "configs/projects/vietnam_socson_from_sheet.yaml",
                encoding="utf-8",
            )
        )
        data2 = copy.deepcopy(data)
        data2["technology"]["waste_composition"] = []
        pi = ProjectInput.model_validate(data2)
        _mid, inputs, warnings = build_engine_inputs(pi)  # type: ignore
        total = sum(s["annual_tonnes"] for s in inputs["waste_streams"])
        assert total == pytest.approx(1_460_000.0)
        assert any("plastics" in w and "redistributed" in w for w in warnings)

    def test_composition_path_five_mapped_streams(self):
        from pdd_agent.calc.dispatch import build_engine_inputs

        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        _mid, inputs, _warnings = build_engine_inputs(pi)  # type: ignore
        streams = {s["waste_type"]: s["annual_tonnes"] for s in inputs["waste_streams"]}
        assert len(inputs["waste_streams"]) == 4
        assert streams["food_waste"] == pytest.approx(1_460_000.0 * 0.519)
        assert streams["rubber_leather"] == pytest.approx(1_460_000.0 * 0.013)

    def test_inert_mass_not_rescaled(self):
        from pdd_agent.calc.dispatch import build_engine_inputs

        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        _mid, inputs, _warnings = build_engine_inputs(pi)  # type: ignore
        total = sum(s["annual_tonnes"] for s in inputs["waste_streams"])
        # Degradable: 0.519 + 0.027 + 0.016 + 0.013 = 0.575.
        # plastics (3.0%) and inert (39.5%) reach PE via Eq22 instead of BE_CH4.
        assert total == pytest.approx(1_460_000.0 * 0.575)

    def test_unmapped_composition_entry_warns(self):
        import copy

        from pdd_agent.calc.dispatch import build_engine_inputs

        data = yaml.safe_load(
            open(
                Path(__file__).parent.parent / "configs/projects/vietnam_socson_from_sheet.yaml",
                encoding="utf-8",
            )
        )
        data2 = copy.deepcopy(data)
        data2["technology"]["waste_composition"] = [
            {"waste_type": "food_waste", "mass_fraction": 0.519, "source": "test"},
            {"waste_type": "paper_cardboard", "mass_fraction": 0.027, "source": "test"},
            {"waste_type": "textiles", "mass_fraction": 0.016, "source": "test"},
            {"waste_type": "plastics", "mass_fraction": 0.03, "source": "test"},
            {"waste_type": "inert", "mass_fraction": 0.403, "source": "test"},
            {"waste_type": "glass", "mass_fraction": 0.005, "source": "test"},
        ]
        pi = ProjectInput.model_validate(data2)
        _mid, inputs, warnings = build_engine_inputs(pi)  # type: ignore
        assert not any(s["waste_type"] == "glass" for s in inputs["waste_streams"])
        assert any("glass" in w and "PE_INC" in w for w in warnings)

    def test_inegol_unchanged(self):
        from pdd_agent.calc.dispatch import build_engine_inputs

        pi = _load_pi("configs/demo/inegol_project_input.yaml")
        _mid, inputs, _warnings = build_engine_inputs(pi)  # type: ignore
        assert len(inputs["waste_streams"]) == 1
        assert inputs["waste_streams"][0]["waste_type"] == "municipal_solid_waste"
        assert inputs["waste_streams"][0]["annual_tonnes"] == pytest.approx(262_970.37)


class TestCapacityRamp:
    def _socson_with_ramp(self, ramp):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        pi.technology.capacity_ramp = ramp
        return pi

    def test_ramp_reduces_year1_and_leaves_later_years(self):
        base = compute_for(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        ramped = compute_for(self._socson_with_ramp([0.5, 1.0]))
        assert base is not None and ramped is not None
        assert ramped.annual_schedule[0].baseline_tco2e < base.annual_schedule[0].baseline_tco2e
        assert ramped.annual_schedule[1].baseline_tco2e == pytest.approx(
            base.annual_schedule[1].baseline_tco2e
        )

    def test_ramp_last_value_carried_forward(self):
        from pdd_agent.calc.dispatch import _ramp_factor

        assert _ramp_factor(None, 1) == 1.0
        assert _ramp_factor([], 3) == 1.0
        assert _ramp_factor([0.5, 0.8, 1.0], 1) == 0.5
        assert _ramp_factor([0.5, 0.8, 1.0], 3) == 1.0
        assert _ramp_factor([0.5, 0.8, 1.0], 7) == 1.0

    def test_pre_change_composition_regression_guard(self):
        """Configs without capacity_ramp/incineration_streams must be unchanged.

        Reconstructs the pre-2026-08-21 Soc Son composition inline (with the
        since-removed rubber_leather entry) under a non-incineration technology
        type so no incineration_streams are mapped — reproducing the exact
        pre-phase crediting total.
        """
        data = yaml.safe_load(
            (
                Path(__file__).parent.parent / "configs/projects/vietnam_socson_from_sheet.yaml"
            ).read_text(encoding="utf-8")
        )
        data["technology"]["technology_type"] = "anaerobic_digestion"
        data["technology"]["waste_composition"] = [
            {"waste_type": "food_waste", "mass_fraction": 0.519, "source": "pre-change"},
            {"waste_type": "paper_cardboard", "mass_fraction": 0.027, "source": "pre-change"},
            {"waste_type": "textiles", "mass_fraction": 0.016, "source": "pre-change"},
            {"waste_type": "wood", "mass_fraction": 0.0, "source": "pre-change"},
            {"waste_type": "garden_waste", "mass_fraction": 0.0, "source": "pre-change"},
            {"waste_type": "rubber_leather", "mass_fraction": 0.013, "source": "pre-change"},
        ]
        result = compute_for(ProjectInput.model_validate(data))
        assert result is not None
        assert result.crediting_period_total_tco2e == pytest.approx(5_706_620.59, abs=1.0)


class TestIncinerationStreamMapping:
    def test_unmapped_composition_types_become_incineration_streams(self):
        pi = _load_pi("configs/projects/vietnam_socson_from_sheet.yaml")
        result = compute_for(pi)
        assert result is not None
        pe_com = next(c for c in result.components if c.name.startswith("PE_COM_CO2"))
        assert pe_com.value_tco2e > 0.0
        assert any("plastics" in w and "PE_INC" in w for w in result.warnings)
        assert any("inert" in w and "PE_INC" in w for w in result.warnings)

    def test_non_incineration_technology_gets_no_incineration_streams(self):
        data = yaml.safe_load(
            (
                Path(__file__).parent.parent / "configs/projects/vietnam_socson_from_sheet.yaml"
            ).read_text(encoding="utf-8")
        )
        data["technology"]["technology_type"] = "anaerobic_digestion"
        result = compute_for(ProjectInput.model_validate(data))
        assert result is not None
        assert not any(
            c.name.startswith("PE_COM_CO2") and c.value_tco2e > 0 for c in result.components
        )
