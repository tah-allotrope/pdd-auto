"""CDM Tool 05: Baseline, project and/or leakage emissions from electricity.

Calculates emissions associated with electricity generation and consumption
using grid emission factors.

Reference: CDM Tool 05 v03.0 — "Baseline, project and/or leakage emissions
from electricity consumption and monitoring of electricity generation"
"""

from __future__ import annotations


def baseline_electricity_emissions(
    electricity_mwh: float,
    grid_ef_tco2_per_mwh: float,
    tdl_factor: float = 0.0,
) -> float:
    """Baseline emissions from displaced grid electricity (tCO2/year).

    BE_EC,y = Σ EC_BL,k,y × EF_EF,k,y × (1 + TDL_k,y)  (Equation 2, Tool 05)

    Args:
        electricity_mwh: Electricity generated/exported by project (MWh/year).
        grid_ef_tco2_per_mwh: Grid emission factor (tCO2/MWh).
        tdl_factor: Transmission and distribution losses (fraction).

    Returns:
        Baseline electricity emissions in tCO2/year.
    """
    return electricity_mwh * grid_ef_tco2_per_mwh * (1 + tdl_factor)


def project_electricity_emissions(
    electricity_consumed_mwh: float,
    grid_ef_tco2_per_mwh: float,
    tdl_factor: float = 0.0,
) -> float:
    """Project emissions from grid electricity consumption (tCO2/year).

    PE_EC,y = Σ EC_PJ,j,y × EF_EF,j,y × (1 + TDL_j,y)  (Equation 1, Tool 05)

    Args:
        electricity_consumed_mwh: Electricity consumed from grid (MWh/year).
        grid_ef_tco2_per_mwh: Grid emission factor (tCO2/MWh).
        tdl_factor: Transmission and distribution losses (fraction).

    Returns:
        Project electricity emissions in tCO2/year.
    """
    return electricity_consumed_mwh * grid_ef_tco2_per_mwh * (1 + tdl_factor)
