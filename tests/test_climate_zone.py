"""Climate-zone FOD decay rates (PHASE-02, Specification S-1)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pdd_agent.calc.cdm_tool_04 import methane_from_swds
from pdd_agent.calc.constants import (
    DECAY_RATE_BY_CLIMATE_ZONE,
    DECAY_RATE_BY_WASTE_TYPE,
    climate_zone_for,
)
from pdd_agent.calc.dispatch import compute_for
from schemas.project_input import ProjectInput


def _load_pi(path: str) -> ProjectInput:
    root = Path(__file__).parent.parent
    with open(root / path, encoding="utf-8") as handle:
        return ProjectInput.model_validate(yaml.safe_load(handle))


class TestClimateZoneFor:
    def test_soc_son_latitude_is_tropical_wet(self):
        assert climate_zone_for(21.261) == "tropical_wet"

    def test_inegol_latitude_is_boreal_temperate_wet(self):
        assert climate_zone_for(40.1505) == "boreal_temperate_wet"

    def test_declared_zone_wins(self):
        assert climate_zone_for(40.1505, declared="tropical_dry") == "tropical_dry"

    def test_boundary_latitudes(self):
        assert climate_zone_for(-23.4) == "tropical_wet"
        assert climate_zone_for(23.6) == "boreal_temperate_wet"


class TestDecayRateTable:
    def test_legacy_table_equals_boreal_temperate_wet(self):
        assert DECAY_RATE_BY_CLIMATE_ZONE["boreal_temperate_wet"] == DECAY_RATE_BY_WASTE_TYPE

    def test_tropical_wet_food_waste(self):
        assert DECAY_RATE_BY_CLIMATE_ZONE["tropical_wet"]["food_waste"] == 0.40


class TestMethaneResolution:
    def test_tropical_zone_raises_food_waste_methane(self):
        default = methane_from_swds("food_waste", 1000.0, 1)
        tropical = methane_from_swds("food_waste", 1000.0, 1, climate_zone="tropical_wet")
        # NOTE (plan spec predicted 2.0–2.5): year-1 FOD scales as (1 − e^−k),
        # giving 0.330/0.169 ≈ 1.95. Assert the measured factor, not the prediction.
        assert tropical / default == pytest.approx(1.95, abs=0.05)

    def test_decay_rate_override_wins_over_zone(self):
        assert methane_from_swds(
            "food_waste", 1000.0, 1, decay_rate_override=0.1, climate_zone="tropical_wet"
        ) == methane_from_swds("food_waste", 1000.0, 1, decay_rate_override=0.1)

    def test_unknown_zone_names_all_valid_zones(self):
        with pytest.raises(ValueError) as excinfo:
            methane_from_swds("food_waste", 1000.0, 1, climate_zone="atlantis")
        message = str(excinfo.value)
        for zone in (
            "boreal_temperate_dry",
            "boreal_temperate_wet",
            "tropical_dry",
            "tropical_wet",
        ):
            assert zone in message


class TestComputeForSmoke:
    def test_soc_son_and_inegol_configs_compute(self):
        socson = compute_for(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        inegol = compute_for(_load_pi("configs/demo/inegol_project_input.yaml"))
        assert socson is not None
        assert inegol is not None
        assert socson.crediting_period_total_tco2e > 0
        assert inegol.crediting_period_total_tco2e > 0
