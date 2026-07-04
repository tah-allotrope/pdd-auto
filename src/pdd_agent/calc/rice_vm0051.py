"""VM0051 rice cultivation methane reduction calculator.

Quantifies baseline methane emissions from flooded rice cultivation and the
reductions achieved by alternative wetting and drying (AWD), dry seeding, and
improved organic matter management.

Formula:

    Baseline CH4 (kg/year) = EF_baseline × Area_ha × Cultivation_days
    Project CH4 (kg/year) = Baseline CH4 × Π(scaling_factor_i)
    Net tCO2e/year = (Baseline CH4 - Project CH4) × GWP_CH4 / 1000

References:
- VM0051 Methodology for Sustainable Agricultural Land Management, v2.0.
- IPCC 2006 Guidelines, Vol. 4, Ch. 5 (Cropland) — default EF for flooded rice.
- IPCC 2019 Refinement — water-regime and organic-amendment scaling factors.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from pdd_agent.calc.methodology import ComputationResult, ValidationResult


# IPCC default emission factor for continuously flooded rice without organic
# amendments (kg CH4 / ha / day).
DEFAULT_EF_KG_CH4_PER_HA_PER_DAY: float = 1.30

GWP_CH4: float = 28.0  # AR5 100-year GWP

# Simplified scaling factors relative to continuously flooded baseline.
# AWD and dry seeding are multiplicative; organic matter management assumes a
# shift to lower-emitting practice (e.g. composted vs. fresh manure).
PRACTICE_SCALING_FACTORS: dict[str, float] = {
    "alternate_wetting_drying": 0.50,
    "dry_seeding": 0.30,
    "organic_matter_management": 0.90,
}


class RiceProjectPractice(BaseModel):
    """A project activity that reduces methane emissions from rice."""

    practice: str = Field(
        ..., description="Project practice (e.g. alternate_wetting_drying)"
    )
    scaling_factor: float | None = Field(
        None,
        gt=0.0,
        le=1.0,
        description="Optional project-specific scaling factor override",
    )


class RiceInput(BaseModel):
    """All inputs required for a VM0051 rice cultivation quantification."""

    area_ha: float = Field(..., gt=0, description="Cultivated rice area (ha)")
    cultivation_days: int = Field(
        ..., ge=1, le=366, description="Average flooded/cultivated days per year"
    )
    baseline_water_regime: str = Field(
        "continuously_flooded",
        description="Baseline water regime (e.g. continuously_flooded)",
    )
    baseline_ef_kg_ch4_per_ha_per_day: float = Field(
        DEFAULT_EF_KG_CH4_PER_HA_PER_DAY,
        gt=0,
        description="Baseline CH4 emission factor (kg CH4/ha/day)",
    )
    project_practices: list[RiceProjectPractice] = Field(
        default_factory=list,
        description="List of project mitigation practices",
    )
    gwp_ch4: float = Field(
        GWP_CH4, gt=0, description="Methane global warming potential"
    )
    crediting_period_years: int = Field(
        7, ge=1, le=30, description="Crediting period in years"
    )

    @field_validator("project_practices")
    @classmethod
    def known_practices(cls, practices: list[RiceProjectPractice]) -> list[RiceProjectPractice]:
        for p in practices:
            if p.scaling_factor is None and p.practice not in PRACTICE_SCALING_FACTORS:
                raise ValueError(f"unknown rice practice: {p.practice}")
        return practices


class RiceVm0051Engine:
    """Deterministic VM0051 rice cultivation emission reduction engine."""

    def methodology_id(self) -> str:
        return "VM0051"

    def validate_inputs(self, inputs: dict[str, Any]) -> ValidationResult:
        try:
            RiceInput(**inputs)
            return ValidationResult(ok=True, errors=[])
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(ok=False, errors=[str(exc)])

    def _parse(self, inputs: dict[str, Any]) -> RiceInput:
        return RiceInput(**inputs)

    def _scaling_factor(self, practice: RiceProjectPractice) -> float:
        if practice.scaling_factor is not None:
            return practice.scaling_factor
        return PRACTICE_SCALING_FACTORS[practice.practice]

    def _compute_baseline_kg(self, inp: RiceInput) -> float:
        return inp.baseline_ef_kg_ch4_per_ha_per_day * inp.area_ha * inp.cultivation_days

    def _compute_project_kg(self, inp: RiceInput) -> float:
        baseline_kg = self._compute_baseline_kg(inp)
        factor = 1.0
        for practice in inp.project_practices:
            factor *= self._scaling_factor(practice)
        return baseline_kg * factor

    def compute_baseline(self, inputs: dict[str, Any]) -> ComputationResult:
        inp = self._parse(inputs)
        baseline_tco2e = self._compute_baseline_kg(inp) * inp.gwp_ch4 / 1000.0
        return ComputationResult(
            value=baseline_tco2e,
            unit="tCO2e/year",
            formula="BE = EF_baseline × Area × Days × GWP_CH4 / 1000",
            provenance=[
                {"param": "area_ha", "source": "user_input"},
                {"param": "cultivation_days", "source": "user_input"},
                {"param": "baseline_ef_kg_ch4_per_ha_per_day", "source": "user_input"},
                {"param": "gwp_ch4", "source": "methodology_default", "value": inp.gwp_ch4},
            ],
            notes="Baseline methane emissions from continuously flooded rice",
        )

    def compute_project(self, inputs: dict[str, Any]) -> ComputationResult:
        inp = self._parse(inputs)
        project_tco2e = self._compute_project_kg(inp) * inp.gwp_ch4 / 1000.0
        return ComputationResult(
            value=project_tco2e,
            unit="tCO2e/year",
            formula="PE = BE × Π(scaling_factor_i)",
            provenance=[
                {"param": "project_practices", "source": "user_input"},
                {"param": "baseline_emissions", "source": "calc_engine"},
            ],
            notes="Project methane emissions after AWD/dry-seeding/OM practices",
        )

    def compute_leakage(self, inputs: dict[str, Any]) -> ComputationResult:
        return ComputationResult(
            value=0.0,
            unit="tCO2e/year",
            formula="LE = 0",
            provenance=[],
            notes="No leakage term in the simplified VM0051 approach",
        )

    def compute_net(self, inputs: dict[str, Any]) -> ComputationResult:
        inp = self._parse(inputs)
        baseline_kg = self._compute_baseline_kg(inp)
        project_kg = self._compute_project_kg(inp)
        net_tco2e = (baseline_kg - project_kg) * inp.gwp_ch4 / 1000.0
        return ComputationResult(
            value=net_tco2e,
            unit="tCO2e/year",
            formula="ER = (BE_CH4 - PE_CH4) × GWP_CH4 / 1000",
            provenance=[
                {"param": "baseline_ch4_kg", "source": "calc_engine", "value": baseline_kg},
                {"param": "project_ch4_kg", "source": "calc_engine", "value": project_kg},
                {"param": "gwp_ch4", "source": "methodology_default", "value": inp.gwp_ch4},
            ],
            notes="Annual emission reductions from rice cultivation mitigation practices",
        )

    def required_monitoring_params(self, inputs: dict[str, Any]) -> list[dict]:
        return [
            {"id": "VM0051-PARAM-01", "name": "Rice cultivated area", "unit": "ha", "frequency": "Annual", "source": "Field records / remote sensing", "section_ref": "5.2"},
            {"id": "VM0051-PARAM-02", "name": "Cultivation period", "unit": "days", "frequency": "Per season", "source": "Agronomic records", "section_ref": "5.2"},
            {"id": "VM0051-PARAM-03", "name": "Water regime practice", "unit": "practice", "frequency": "Per season", "source": "Field monitoring", "section_ref": "5.2"},
            {"id": "VM0051-PARAM-04", "name": "Organic matter management", "unit": "practice", "frequency": "Per season", "source": "Agronomic records", "section_ref": "5.2"},
            {"id": "VM0051-PARAM-05", "name": "Baseline CH4 emission factor", "unit": "kg CH4/ha/day", "frequency": "Per assessment", "source": "IPCC default / field measurement", "section_ref": "4.1"},
        ]
