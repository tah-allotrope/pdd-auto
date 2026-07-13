"""Per-family ProjectInput fixtures for the methodology-parametrized test matrix.

Each factory returns a valid ProjectInput for the given family slug, reusing
the existing YAML configs where present (WTE via demo_socson_like, rice via
rice_vm0051_pilot) and constructing minimal synthetic inputs for biochar and
cookstove.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from schemas.project_input import ProjectInput

_PROJECTS_DIR = Path(__file__).parent.parent.parent / "configs" / "projects"


def _load_yaml(name: str) -> dict:
    path = _PROJECTS_DIR / name
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _make_wte() -> ProjectInput:
    data = _load_yaml("demo_socson_like.yaml")
    return ProjectInput.model_validate(data)


def _make_rice() -> ProjectInput:
    data = _load_yaml("rice_vm0051_pilot.yaml")
    return ProjectInput.model_validate(data)


def _make_biochar() -> ProjectInput:
    data = _load_yaml("rice_vm0051_pilot.yaml")
    data["project"]["project_name"] = "Biochar VM0044 Test Project"
    data["project"]["proponent_name"] = "Biochar Test Company"
    data["technology"]["methodology_ids"] = ["VM0044"]
    data["technology"]["technology_type"] = "biochar_production"
    data["technology"]["rice_cultivation"] = None
    data["technology"]["biochar_production"] = {
        "feedstock_type": "wood_chip",
        "dry_mass_tonnes": 10000.0,
        "carbon_fraction": 0.50,
        "pyrolysis_temperature_c": 550.0,
        "permanence_factor": 0.9,
    }
    data["quantification"] = {
        "baseline_emissions_tco2e_per_year": 5000.0,
        "project_emissions_tco2e_per_year": 500.0,
        "leakage_tco2e_per_year": 100.0,
        "net_emissions_tco2e_per_year": 4400.0,
        "crediting_period_total_tco2e": 30800.0,
        "grid_emission_factor": None,
        "grid_emission_factor_source": None,
        "methane_capture_rate": None,
        "methane_generation_factor": None,
    }
    data["methodology_applicability"] = {
        "eligibility_checklist": {
            "feedstock_is_biomass": True,
            "biochar_is_applied_to_soil": True,
            "carbon_content_measured": True,
        },
        "deviation_from_methodology": None,
    }
    return ProjectInput.model_validate(data)


def _make_cookstove() -> ProjectInput:
    data = _load_yaml("rice_vm0051_pilot.yaml")
    data["project"]["project_name"] = "Improved Cookstove AMS-II.G Test Project"
    data["project"]["proponent_name"] = "Clean Cooking Alliance"
    data["technology"]["methodology_ids"] = ["AMS-II.G"]
    data["technology"]["technology_type"] = "improved_cookstoves"
    data["technology"]["rice_cultivation"] = None
    data["technology"]["cookstove_fleet"] = [
        {
            "fuel_type": "fuelwood",
            "stove_count": 5000,
            "baseline_fuel_kg_per_day_per_stove": 5.0,
            "project_fuel_kg_per_day_per_stove": 2.5,
            "operating_days_per_year": 365,
            "ncv_mj_per_kg": 15.0,
            "ef_kg_co2_per_mj": 0.098,
            "fnrb": 0.75,
        }
    ]
    data["quantification"] = {
        "baseline_emissions_tco2e_per_year": 12000.0,
        "project_emissions_tco2e_per_year": 6000.0,
        "leakage_tco2e_per_year": 200.0,
        "net_emissions_tco2e_per_year": 5800.0,
        "crediting_period_total_tco2e": 40600.0,
        "grid_emission_factor": None,
        "grid_emission_factor_source": None,
        "methane_capture_rate": None,
        "methane_generation_factor": None,
    }
    data["methodology_applicability"] = {
        "eligibility_checklist": {
            "baseline_uses_traditional_stoves": True,
            "project_distributes_improved_stoves": True,
            "fuel_consumption_measured": True,
        },
        "deviation_from_methodology": None,
    }
    return ProjectInput.model_validate(data)


_FACTORIES = {
    "wte": _make_wte,
    "rice": _make_rice,
    "biochar": _make_biochar,
    "cookstove": _make_cookstove,
}


def make_project_input(family: str) -> ProjectInput:
    """Return a valid ProjectInput for the given family slug."""
    factory = _FACTORIES.get(family)
    if factory is None:
        raise ValueError(f"Unknown family: {family!r}. Expected one of {list(_FACTORIES)}")
    return factory()
