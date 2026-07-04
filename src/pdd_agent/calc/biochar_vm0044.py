"""VM0044 biochar carbon removal calculator.

Quantifies the long-term stable carbon in biochar produced from biomass
feedstock via pyrolysis.

Formula:

    Stable C (tonnes) = Dry_mass × Carbon_fraction × Stability_factor
    tCO2e = Stable C × (44 / 12) × Permanence_factor

The 44/12 factor converts atomic carbon to CO2 equivalent mass.  The permanence
factor accounts for uncertainty, reversibility risk, and/or project-specific
measurement of long-term storage.

References:
- VM0044 Methodology for Biochar Utilization in Soil and Non-Soil Applications,
  latest version.
- IPCC 2019 Refinement — biomass carbon fractions and biochar stability.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from pdd_agent.calc.methodology import ComputationResult, ValidationResult


# Default stability factors by pyrolysis temperature range.  Higher pyrolysis
# temperatures generally produce more stable (aromatic) carbon.
_STABILITY_BY_TEMPERATURE: dict[str, float] = {
    "low": 0.60,    # < 400 °C
    "medium": 0.75, # 400–500 °C
    "high": 0.85,   # > 500 °C
}

_C_TO_CO2: float = 44.0 / 12.0


class BiocharInput(BaseModel):
    """All inputs required for a VM0044 biochar quantification."""

    feedstock_type: str = Field(
        ..., description="Feedstock type (e.g. wood_chip, rice_husk, manure)"
    )
    dry_mass_tonnes: float = Field(
        ..., gt=0, description="Dry feedstock mass processed per year (tonnes)"
    )
    carbon_fraction: float = Field(
        ..., gt=0, le=1, description="Mass fraction of carbon in dry feedstock"
    )
    pyrolysis_temperature_c: float = Field(
        ..., gt=0, description="Pyrolysis peak temperature (°C)"
    )
    stability_factor: float | None = Field(
        None,
        gt=0,
        le=1,
        description="Optional measured/project-specific carbon stability fraction",
    )
    permanence_factor: float = Field(
        1.0,
        ge=0,
        le=1,
        description="Discount for uncertainty / reversibility risk",
    )
    crediting_period_years: int = Field(
        7, ge=1, le=40, description="Crediting period in years"
    )

    @field_validator("stability_factor")
    @classmethod
    def stability_in_range(cls, v: float | None) -> float | None:
        if v is None:
            return v
        return v

    @property
    def effective_stability_factor(self) -> float:
        if self.stability_factor is not None:
            return self.stability_factor
        if self.pyrolysis_temperature_c < 400:
            return _STABILITY_BY_TEMPERATURE["low"]
        if self.pyrolysis_temperature_c <= 500:
            return _STABILITY_BY_TEMPERATURE["medium"]
        return _STABILITY_BY_TEMPERATURE["high"]


class BiocharVm0044Engine:
    """Deterministic VM0044 biochar carbon removal engine."""

    def methodology_id(self) -> str:
        return "VM0044"

    def validate_inputs(self, inputs: dict[str, Any]) -> ValidationResult:
        try:
            BiocharInput(**inputs)
            return ValidationResult(ok=True, errors=[])
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(ok=False, errors=[str(exc)])

    def _parse(self, inputs: dict[str, Any]) -> BiocharInput:
        return BiocharInput(**inputs)

    def _stable_carbon_tonnes(self, inp: BiocharInput) -> float:
        return inp.dry_mass_tonnes * inp.carbon_fraction * inp.effective_stability_factor

    def compute_baseline(self, inputs: dict[str, Any]) -> ComputationResult:
        return ComputationResult(
            value=0.0,
            unit="tCO2e/year",
            formula="BE = 0",
            provenance=[],
            notes="Biochar is a carbon-removal activity; baseline emissions are zero",
        )

    def compute_project(self, inputs: dict[str, Any]) -> ComputationResult:
        # Project emissions are treated as zero in the simplified VM0044 carbon
        # accounting boundary; all sequestered carbon is captured in net.
        return ComputationResult(
            value=0.0,
            unit="tCO2e/year",
            formula="PE = 0",
            provenance=[],
            notes="Fossil energy and transport are outside the simplified boundary",
        )

    def compute_leakage(self, inputs: dict[str, Any]) -> ComputationResult:
        return ComputationResult(
            value=0.0,
            unit="tCO2e/year",
            formula="LE = 0",
            provenance=[],
            notes="No leakage term in the simplified VM0044 approach",
        )

    def compute_net(self, inputs: dict[str, Any]) -> ComputationResult:
        inp = self._parse(inputs)
        stable_c = self._stable_carbon_tonnes(inp)
        tco2e = stable_c * _C_TO_CO2 * inp.permanence_factor
        return ComputationResult(
            value=tco2e,
            unit="tCO2e/year",
            formula="Stable CO2e = Dry_mass × Carbon_fraction × Stability_factor × (44/12) × Permanence_factor",
            provenance=[
                {"param": "dry_mass_tonnes", "source": "user_input", "value": inp.dry_mass_tonnes},
                {"param": "carbon_fraction", "source": "user_input", "value": inp.carbon_fraction},
                {"param": "stability_factor", "source": "calc_engine", "value": inp.effective_stability_factor},
                {"param": "permanence_factor", "source": "user_input", "value": inp.permanence_factor},
            ],
            notes="Long-term carbon dioxide removal from stable biochar carbon",
        )

    def required_monitoring_params(self, inputs: dict[str, Any]) -> list[dict]:
        return [
            {"id": "VM0044-PARAM-01", "name": "Dry feedstock mass", "unit": "tonnes/year", "frequency": "Per batch / annual", "source": "Weighbridge / moisture records", "section_ref": "5.2"},
            {"id": "VM0044-PARAM-02", "name": "Feedstock carbon fraction", "unit": "fraction", "frequency": "Per batch / annual lab test", "source": "Laboratory analysis", "section_ref": "4.1"},
            {"id": "VM0044-PARAM-03", "name": "Pyrolysis temperature", "unit": "°C", "frequency": "Continuous", "source": "Kiln instrumentation", "section_ref": "5.2"},
            {"id": "VM0044-PARAM-04", "name": "Biochar stability factor", "unit": "fraction", "frequency": "Per assessment", "source": "Laboratory analysis / methodology default", "section_ref": "4.1"},
            {"id": "VM0044-PARAM-05", "name": "Permanence factor", "unit": "fraction", "frequency": "Per assessment", "source": "Risk assessment", "section_ref": "4.4"},
        ]
