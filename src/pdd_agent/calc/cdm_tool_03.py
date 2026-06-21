"""CDM Tool 03: Emission factor for fossil fuel combustion.

Implements the CO2 emission coefficient calculation for fossil fuels
used by the project activity (e.g., diesel generators).

Reference: CDM Tool 03 v04.0 — "Tool to calculate project or leakage CO2
emissions from fossil fuel combustion"
"""

from __future__ import annotations

from pdd_agent.calc.constants import FOSSIL_FUEL_EF, FOSSIL_FUEL_NCV


def co2_emission_coefficient(
    fuel_type: str,
    ncv_override: float | None = None,
    ef_override: float | None = None,
) -> float:
    """Calculate the CO2 emission coefficient for a fuel type (tCO2/tonne fuel).

    COEF_i = NCV_i × EF_CO2,i  (Equation 4, Tool 03)

    Args:
        fuel_type: Key into FOSSIL_FUEL_EF / FOSSIL_FUEL_NCV.
        ncv_override: Override net calorific value (GJ/tonne).
        ef_override: Override emission factor (tCO2/GJ).

    Returns:
        CO2 emission coefficient in tCO2 per tonne of fuel.
    """
    ncv = ncv_override if ncv_override is not None else FOSSIL_FUEL_NCV.get(fuel_type)
    ef = ef_override if ef_override is not None else FOSSIL_FUEL_EF.get(fuel_type)
    if ncv is None or ef is None:
        raise ValueError(f"Unknown fuel type '{fuel_type}'. Known: {list(FOSSIL_FUEL_EF)}")
    return ncv * ef


def fossil_fuel_emissions(
    fuel_type: str,
    annual_consumption_tonnes: float,
    ncv_override: float | None = None,
    ef_override: float | None = None,
) -> float:
    """Calculate annual CO2 emissions from fossil fuel combustion (tCO2/year).

    PE_FC,j,y = FC_i,j,y × COEF_i,y  (Equation 1, Tool 03)
    """
    coef = co2_emission_coefficient(fuel_type, ncv_override, ef_override)
    return annual_consumption_tonnes * coef
