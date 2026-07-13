"""Deterministic baseline identification for waste-to-energy projects."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BaselineIdentificationResult:
    scenario: str
    eligible: bool
    rationale: str
    alternatives_considered: list[str] = field(default_factory=list)


def identify_wte_baseline(
    *,
    waste_currently_landfilled: bool,
    landfill_gas_captured: bool = False,
    existing_energy_recovery: bool = False,
    mandatory_treatment_or_energy_recovery: bool = False,
    plausible_alternatives: list[str] | None = None,
) -> BaselineIdentificationResult:
    """Apply the WTE baseline eligibility decision tree."""
    alternatives = list(plausible_alternatives or [])
    if existing_energy_recovery:
        return BaselineIdentificationResult(
            "existing_energy_recovery",
            False,
            "The project would replace existing energy recovery; landfill disposal is not the baseline.",
            alternatives,
        )
    if mandatory_treatment_or_energy_recovery:
        return BaselineIdentificationResult(
            "mandatory_treatment",
            False,
            "Applicable regulation already requires treatment or energy recovery.",
            alternatives,
        )
    if not waste_currently_landfilled:
        return BaselineIdentificationResult(
            "non_landfill_current_practice",
            False,
            "Landfill disposal is not demonstrated as current practice.",
            alternatives,
        )
    capture = (
        "with partial landfill-gas capture"
        if landfill_gas_captured
        else "without landfill-gas capture"
    )
    return BaselineIdentificationResult(
        "continued_landfill_disposal",
        True,
        f"Continued landfill disposal {capture} is the identified baseline.",
        alternatives,
    )


identify_baseline = identify_wte_baseline
