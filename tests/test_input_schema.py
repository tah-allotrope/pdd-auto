"""Validation tests for the Pydantic ProjectInput model."""

from typing import Any
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from schemas.project_input import (
    ProjectInput,
    ProjectIdentity,
    ProjectLocation,
    ProjectDates,
    ProjectTechnology,
    MethodologyApplicability,
    QuantificationInputs,
    MonitoringPlan,
    SafeguardsEvidence,
    ComplianceAndOwnership,
    SustainableDevelopment,
)


def make_minimal_tech() -> dict:
    return {
        "methodology_ids": ["ACM0022"],
        "technology_type": "incineration_with_energy_recovery",
        "waste_type": ["municipal_solid_waste"],
        "annual_waste_throughput": 100_000.0,
        "installed_capacity_mw": 10.0,
        "landfill_diversion_claim": False,
        "fuel_substitution_claim": False,
    }


def make_minimal_quant() -> dict:
    return {
        "baseline_emissions_tco2e_per_year": 50_000.0,
        "project_emissions_tco2e_per_year": 5_000.0,
        "leakage_tco2e_per_year": 0.0,
        "net_emissions_tco2e_per_year": 45_000.0,
        "grid_emission_factor": 0.5,
        "grid_emission_factor_source": "ACM0022 default",
        "crediting_period_total_tco2e": 450_000.0,
    }


def make_minimal_input(**overrides) -> dict:
    base = {
        "project": {
            "project_name": "Test WTE Project",
            "proponent_name": "Test Proponent",
            "proponent_contact_email": "test@example.com",
            "ownership": "Test ownership structure",
        },
        "location": {
            "country": "Vietnam",
            "region": "Hanoi",
            "city": "Hanoi",
            "latitude": 21.0,
            "longitude": 105.8,
        },
        "dates": {
            "start_date": "2020-01-01",
            "crediting_period_start": "2020-01-01",
            "crediting_period_years": 10,
        },
        "technology": make_minimal_tech(),
        "methodology_applicability": {
            "eligibility_checklist": {"ACM0022-AC-01": True, "ACM0022-AC-02": True},
        },
        "quantification": make_minimal_quant(),
        "monitoring": {
            "parameters_monitored": [{"name": "waste_throughput", "unit": "tonnes"}],
            "data_management": "Manual recording",
        },
        "safeguards": {
            "no_net_harm_statement": "No net harm confirmed.",
            "stakeholder_consultation_completed": True,
            "environmental_impact_assessment": True,
        },
        "compliance_and_ownership": {
            "credit_ownership_statement": "Credits owned by proponent.",
        },
        "sustainable_development": {"sd_contributions": ["SDG 7"]},
    }
    for k, v in overrides.items():
        parts = k.split(".")
        d = base
        for p in parts[:-1]:
            d = d[p]
        d[parts[-1]] = v
    return base


class TestDoubleCountingValidator:
    def test_passes_when_one_claim_only_landfill(self):
        data = make_minimal_input()
        data["technology"]["landfill_diversion_claim"] = True
        data["technology"]["fuel_substitution_claim"] = False
        obj = ProjectInput(**data)
        assert obj.technology.landfill_diversion_claim is True
        assert obj.technology.fuel_substitution_claim is False

    def test_passes_when_one_claim_only_fuel_sub(self):
        data = make_minimal_input()
        data["technology"]["landfill_diversion_claim"] = False
        data["technology"]["fuel_substitution_claim"] = True
        obj = ProjectInput(**data)
        assert obj.technology.fuel_substitution_claim is True

    def test_fails_when_both_claims_true(self):
        data = make_minimal_input()
        data["technology"]["landfill_diversion_claim"] = True
        data["technology"]["fuel_substitution_claim"] = True
        with pytest.raises(ValidationError) as exc_info:
            ProjectInput(**data)
        assert "double-counting" in str(exc_info.value).lower()

    def test_fails_both_claims_true_fuel_sub_first(self):
        data = make_minimal_input()
        data["technology"]["fuel_substitution_claim"] = True
        data["technology"]["landfill_diversion_claim"] = True
        with pytest.raises(ValidationError) as exc_info:
            ProjectInput(**data)
        assert "double-counting" in str(exc_info.value).lower()


class TestNetEmissionsValidator:
    def test_passes_correct_net(self):
        data = make_minimal_input()
        data["quantification"]["net_emissions_tco2e_per_year"] = 45_000.0
        data["quantification"]["baseline_emissions_tco2e_per_year"] = 50_000.0
        data["quantification"]["project_emissions_tco2e_per_year"] = 5_000.0
        data["quantification"]["leakage_tco2e_per_year"] = 0.0
        obj = ProjectInput(**data)
        assert obj.quantification.net_emissions_tco2e_per_year == 45_000.0

    def test_fails_net_does_not_match(self):
        data = make_minimal_input()
        data["quantification"]["net_emissions_tco2e_per_year"] = 99_000.0
        data["quantification"]["baseline_emissions_tco2e_per_year"] = 50_000.0
        data["quantification"]["project_emissions_tco2e_per_year"] = 5_000.0
        data["quantification"]["leakage_tco2e_per_year"] = 0.0
        with pytest.raises(ValidationError) as exc_info:
            ProjectInput(**data)
        assert "net emissions" in str(exc_info.value).lower()

    def test_fails_negative_net(self):
        data = make_minimal_input()
        data["quantification"]["net_emissions_tco2e_per_year"] = -1_000.0
        data["quantification"]["baseline_emissions_tco2e_per_year"] = 50_000.0
        data["quantification"]["project_emissions_tco2e_per_year"] = 60_000.0
        data["quantification"]["leakage_tco2e_per_year"] = 0.0
        with pytest.raises(ValidationError) as exc_info:
            ProjectInput(**data)
        assert "negative" in str(exc_info.value).lower()

    def test_fails_with_leakage_mismatch(self):
        data = make_minimal_input()
        data["quantification"]["leakage_tco2e_per_year"] = 1_000.0
        data["quantification"]["net_emissions_tco2e_per_year"] = 45_000.0
        data["quantification"]["baseline_emissions_tco2e_per_year"] = 50_000.0
        data["quantification"]["project_emissions_tco2e_per_year"] = 5_000.0
        with pytest.raises(ValidationError) as exc_info:
            ProjectInput(**data)
        assert "net emissions" in str(exc_info.value).lower()


def _ov(data: dict, key: str, value: Any) -> dict:
    d = data.copy()
    parts = key.split(".")
    m = d
    for p in parts[:-1]:
        m = m[p]
    m[parts[-1]] = value
    return d


class TestLocationValidation:
    def test_latitude_valid(self):
        data = _ov(make_minimal_input(), "location.latitude", 21.5)
        obj = ProjectInput(**data)
        assert obj.location.latitude == 21.5

    def test_latitude_out_of_range(self):
        data = _ov(make_minimal_input(), "location.latitude", 91.0)
        with pytest.raises(ValidationError):
            ProjectInput(**data)

    def test_longitude_out_of_range(self):
        data = _ov(make_minimal_input(), "location.longitude", -181.0)
        with pytest.raises(ValidationError):
            ProjectInput(**data)


class TestProjectDatesValidation:
    def test_crediting_period_years_valid(self):
        data = _ov(make_minimal_input(), "dates.crediting_period_years", 10)
        obj = ProjectInput(**data)
        assert obj.dates.crediting_period_years == 10

    def test_crediting_period_years_zero_invalid(self):
        data = _ov(make_minimal_input(), "dates.crediting_period_years", 0)
        with pytest.raises(ValidationError):
            ProjectInput(**data)

    def test_crediting_period_years_negative_invalid(self):
        data = _ov(make_minimal_input(), "dates.crediting_period_years", -1)
        with pytest.raises(ValidationError):
            ProjectInput(**data)


class TestProjectScaleValidation:
    def test_small_scale_false_by_default(self):
        data = make_minimal_input()
        obj = ProjectInput(**data)
        assert obj.dates.project_scale_small is False

    def test_small_scale_true(self):
        data = _ov(make_minimal_input(), "dates.project_scale_small", True)
        obj = ProjectInput(**data)
        assert obj.dates.project_scale_small is True


class TestComplianceFlags:
    def test_no_other_programs_default_true(self):
        data = make_minimal_input()
        obj = ProjectInput(**data)
        assert obj.compliance_and_ownership.no_participation_other_programs is True

    def test_double_counting_risk_flag(self):
        data = make_minimal_input()
        data["compliance_and_ownership"]["double_counting_risk"] = True
        obj = ProjectInput(**data)
        assert obj.compliance_and_ownership.double_counting_risk is True


class TestSummary:
    def test_summary_contains_key_fields(self):
        data = make_minimal_input()
        obj = ProjectInput(**data)
        summary = obj.summary()
        assert "Test WTE Project" in summary
        assert "Vietnam" in summary
        assert "ACM0022" in summary
        assert "45,000" in summary
