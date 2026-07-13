"""AMS-II.G / Gold Standard cookstove emission reduction calculator.

Formula (simplified, documented form):

    ER = Σ (fuel_saved_tonnes × NCV × EF_fuel × fNRB) / 1000   [tCO2e/year]

where:

    fuel_saved_tonnes = fuel_baseline_tonnes - fuel_project_tonnes
    fuel_baseline_tonnes = N_stoves × usage_baseline_kg/day × operating_days / 1000
    fuel_project_tonnes  = N_stoves × usage_project_kg/day × operating_days / 1000

NCV is in MJ/kg, EF_fuel in kg CO2/MJ, and fNRB is the non-renewable biomass
fraction.  The /1000 converts kg CO2 to tonnes CO2e.

References:
- AMS-II.G: "Energy efficiency measures in thermal applications of non-renewable
  biomass", version 12.0.
- Gold Standard cookstove methodologies (metered and default approaches).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from pdd_agent.calc.methodology import ComputationResult, ValidationResult


class StoveEntry(BaseModel):
    """A single stove/fuel cohort used in the AMS-II.G calculation."""

    fuel_type: str = Field(..., description="Baseline fuel type (e.g. wood, charcoal)")
    stove_count: int = Field(..., gt=0, description="Number of stoves / households")
    baseline_fuel_kg_per_day_per_stove: float = Field(
        ..., gt=0, description="Baseline fuel consumption per stove per day (kg/day)"
    )
    project_fuel_kg_per_day_per_stove: float = Field(
        ..., gt=0, description="Project fuel consumption per improved stove per day (kg/day)"
    )
    operating_days_per_year: int = Field(
        365, ge=1, le=366, description="Days the stove is used per year"
    )
    ncv_mj_per_kg: float = Field(..., gt=0, description="Net calorific value of the fuel (MJ/kg)")
    ef_kg_co2_per_mj: float = Field(
        ..., gt=0, description="CO2 emission factor of the fuel (kg CO2/MJ)"
    )
    fnrb: float = Field(..., ge=0.0, le=1.0, description="Non-renewable biomass fraction")

    @field_validator("project_fuel_kg_per_day_per_stove")
    @classmethod
    def project_not_greater_than_baseline(cls, v: float, info) -> float:
        baseline = info.data.get("baseline_fuel_kg_per_day_per_stove")
        if baseline is not None and v > baseline:
            raise ValueError("project fuel consumption must not exceed baseline fuel consumption")
        return v


class CookstoveInput(BaseModel):
    """All inputs required for an AMS-II.G cookstove quantification."""

    stoves: list[StoveEntry] = Field(..., min_length=1, description="Cookstove cohorts")
    crediting_period_years: int = Field(7, ge=1, le=21, description="Crediting period in years")


class CookstoveAmsiigEngine:
    """Deterministic AMS-II.G cookstove emission reduction engine."""

    def methodology_id(self) -> str:
        return "AMS-II.G"

    def validate_inputs(self, inputs: dict[str, Any]) -> ValidationResult:
        try:
            CookstoveInput(**inputs)
            return ValidationResult(ok=True, errors=[])
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(ok=False, errors=[str(exc)])

    def _parse(self, inputs: dict[str, Any]) -> CookstoveInput:
        return CookstoveInput(**inputs)

    def _fuel_and_emissions(self, stove: StoveEntry) -> tuple[float, float, float]:
        baseline_fuel_tonnes = (
            stove.stove_count
            * stove.baseline_fuel_kg_per_day_per_stove
            * stove.operating_days_per_year
            / 1000.0
        )
        project_fuel_tonnes = (
            stove.stove_count
            * stove.project_fuel_kg_per_day_per_stove
            * stove.operating_days_per_year
            / 1000.0
        )
        saved_fuel_tonnes = baseline_fuel_tonnes - project_fuel_tonnes
        # tCO2e = fuel_tonnes * (kg fuel per tonne) * NCV * EF * fNRB / 1000
        # The 1000 cancels with the tonnes->kg conversion.
        baseline_tco2e = (
            baseline_fuel_tonnes * stove.ncv_mj_per_kg * stove.ef_kg_co2_per_mj * stove.fnrb
        )
        project_tco2e = (
            project_fuel_tonnes * stove.ncv_mj_per_kg * stove.ef_kg_co2_per_mj * stove.fnrb
        )
        return baseline_fuel_tonnes, saved_fuel_tonnes, baseline_tco2e, project_tco2e

    def compute_baseline(self, inputs: dict[str, Any]) -> ComputationResult:
        parsed = self._parse(inputs)
        baseline_tco2e = sum(self._fuel_and_emissions(s)[2] for s in parsed.stoves)
        return ComputationResult(
            value=baseline_tco2e,
            unit="tCO2e/year",
            formula="BE = Σ(N × baseline_kg/day × days/1000 × NCV × EF × fNRB)",
            provenance=[{"param": "stoves", "source": "user_input"}],
            notes="Baseline emissions from non-renewable fuel use",
        )

    def compute_project(self, inputs: dict[str, Any]) -> ComputationResult:
        parsed = self._parse(inputs)
        project_tco2e = sum(self._fuel_and_emissions(s)[3] for s in parsed.stoves)
        return ComputationResult(
            value=project_tco2e,
            unit="tCO2e/year",
            formula="PE = Σ(N × project_kg/day × days/1000 × NCV × EF × fNRB)",
            provenance=[{"param": "stoves", "source": "user_input"}],
            notes="Project emissions from remaining non-renewable fuel use",
        )

    def compute_leakage(self, inputs: dict[str, Any]) -> ComputationResult:
        return ComputationResult(
            value=0.0,
            unit="tCO2e/year",
            formula="LE = 0",
            provenance=[],
            notes="No leakage term in the simplified AMS-II.G approach",
        )

    def compute_net(self, inputs: dict[str, Any]) -> ComputationResult:
        parsed = self._parse(inputs)
        total_saved = 0.0
        total_tco2e = 0.0
        for stove in parsed.stoves:
            _, saved_fuel_tonnes, _, _ = self._fuel_and_emissions(stove)
            # Direct formula from the methodology
            er_tco2e = saved_fuel_tonnes * stove.ncv_mj_per_kg * stove.ef_kg_co2_per_mj * stove.fnrb
            total_saved += saved_fuel_tonnes
            total_tco2e += er_tco2e
        return ComputationResult(
            value=total_tco2e,
            unit="tCO2e/year",
            formula="ER = Σ(fuel_saved_tonnes × NCV × EF_fuel × fNRB) / 1000",
            provenance=[
                {"param": "total_fuel_saved_tonnes", "source": "calc_engine", "value": total_saved},
                {"param": "stoves", "source": "user_input"},
            ],
            notes="Annual emission reductions from improved cookstoves",
        )

    def required_monitoring_params(self, inputs: dict[str, Any]) -> list[dict]:
        return [
            {
                "id": "AMSIIG-PARAM-01",
                "name": "Number of operating stoves",
                "unit": "stoves",
                "frequency": "Annual",
                "source": "Survey / distribution records",
                "section_ref": "5.2",
            },
            {
                "id": "AMSIIG-PARAM-02",
                "name": "Baseline fuel consumption",
                "unit": "kg/day/stove",
                "frequency": "Spot-check survey",
                "source": "Baseline household survey",
                "section_ref": "4.1",
            },
            {
                "id": "AMSIIG-PARAM-03",
                "name": "Project fuel consumption",
                "unit": "kg/day/stove",
                "frequency": "Spot-check survey",
                "source": "Project household survey",
                "section_ref": "4.2",
            },
            {
                "id": "AMSIIG-PARAM-04",
                "name": "Fuel net calorific value",
                "unit": "MJ/kg",
                "frequency": "Per batch or annual lab test",
                "source": "Laboratory analysis",
                "section_ref": "4.1",
            },
            {
                "id": "AMSIIG-PARAM-05",
                "name": "Fuel CO2 emission factor",
                "unit": "kg CO2/MJ",
                "frequency": "Annual update",
                "source": "IPCC / methodology default",
                "section_ref": "4.1",
            },
            {
                "id": "AMSIIG-PARAM-06",
                "name": "Non-renewable biomass fraction",
                "unit": "fraction",
                "frequency": "Per assessment",
                "source": "Wood fuel assessment",
                "section_ref": "4.1",
            },
        ]
