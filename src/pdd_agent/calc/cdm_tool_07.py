"""CDM Tool 07 helper for fossil-fuel displacement emission factors."""

from __future__ import annotations

from pdd_agent.calc.constants import FOSSIL_FUEL_EF, FOSSIL_FUEL_NCV


def fossil_fuel_displacement_factor(
    fuel_type: str,
    *,
    conversion_efficiency: float = 1.0,
    ncv_override: float | None = None,
    ef_override: float | None = None,
) -> float:
    """Return ``NCV * EF_CO2 / efficiency`` in tCO2/tonne displaced."""
    if not 0 < conversion_efficiency <= 1:
        raise ValueError("conversion_efficiency must be greater than 0 and at most 1")
    ncv = ncv_override if ncv_override is not None else FOSSIL_FUEL_NCV.get(fuel_type)
    ef = ef_override if ef_override is not None else FOSSIL_FUEL_EF.get(fuel_type)
    if ncv is None or ef is None:
        raise ValueError(f"Unknown fuel type '{fuel_type}'. Known: {list(FOSSIL_FUEL_EF)}")
    if ncv < 0 or ef < 0:
        raise ValueError("net calorific value and emission factor must be non-negative")
    return ncv * ef / conversion_efficiency


def fossil_fuel_displacement_emissions(
    displaced_fuel_tonnes: float,
    fuel_type: str,
    *,
    conversion_efficiency: float = 1.0,
    ncv_override: float | None = None,
    ef_override: float | None = None,
) -> float:
    """Return annual baseline emissions avoided, in tCO2/year."""
    if displaced_fuel_tonnes < 0:
        raise ValueError("displaced_fuel_tonnes must be non-negative")
    return displaced_fuel_tonnes * fossil_fuel_displacement_factor(
        fuel_type,
        conversion_efficiency=conversion_efficiency,
        ncv_override=ncv_override,
        ef_override=ef_override,
    )


emission_factor_for_fossil_fuel_displacement = fossil_fuel_displacement_factor
