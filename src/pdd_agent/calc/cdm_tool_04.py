"""CDM Tool 04: Emissions from solid waste disposal sites (FOD model).

Implements the first-order decay model to calculate methane generation
from waste disposed in a solid waste disposal site (SWDS).

Reference: CDM Tool 04 v08.0 — "Emissions from solid waste disposal sites"
Application B: waste diverted from SWDS during the crediting period.
"""

from __future__ import annotations

import math

from pdd_agent.calc.constants import (
    CH4_TO_CO2_RATIO,
    DECAY_RATE_BY_WASTE_TYPE,
    DOC_BY_WASTE_TYPE,
    DOC_F_DEFAULT,
    F_CH4_DEFAULT,
    GWP_CH4,
    MCF_DEFAULT,
    MODEL_CORRECTION_FACTOR_DEFAULT,
    OX_DEFAULT,
)


def methane_from_swds(
    waste_type: str,
    annual_waste_tonnes: float,
    year: int,
    crediting_start_year: int = 1,
    doc_override: float | None = None,
    decay_rate_override: float | None = None,
    model_correction_factor: float = MODEL_CORRECTION_FACTOR_DEFAULT,
    baseline_capture_fraction: float = 0.0,
    mcf: float = MCF_DEFAULT,
    oxidation_factor: float = OX_DEFAULT,
    doc_f: float = DOC_F_DEFAULT,
    f_ch4: float = F_CH4_DEFAULT,
) -> float:
    """Calculate baseline methane emissions from SWDS using the FOD model (tCO2e/year).

    Implements Equation (2) of Tool 04 — Application B (waste diverted
    from SWDS during crediting period).

    The FOD model calculates cumulative methane from waste disposed in
    all years from x=1 to x=year, reflecting the exponential decay of
    degradable organic carbon.

    Args:
        waste_type: Waste classification key.
        annual_waste_tonnes: Constant annual waste input (tonnes/year).
        year: Crediting period year to calculate for (1-based).
        crediting_start_year: First year of waste disposal (usually 1).
        doc_override: Override DOC fraction for this waste type.
        decay_rate_override: Override decay rate k (1/year).
        model_correction_factor: φ (default 0.9).
        baseline_capture_fraction: f_y — fraction captured at baseline SWDS.
        mcf: Methane correction factor.
        oxidation_factor: OX — oxidation in cover material.
        doc_f: Fraction of DOC that decomposes.
        f_ch4: Volume fraction of CH4 in SWDS gas.

    Returns:
        Methane emissions in tCO2e for the given year.
    """
    doc_j = doc_override if doc_override is not None else DOC_BY_WASTE_TYPE.get(waste_type)
    k_j = (
        decay_rate_override
        if decay_rate_override is not None
        else DECAY_RATE_BY_WASTE_TYPE.get(waste_type)
    )

    if doc_j is None or k_j is None:
        raise ValueError(f"Unknown waste type '{waste_type}'. Known: {list(DOC_BY_WASTE_TYPE)}")

    # Sum over all disposal years x from crediting_start_year to year
    fod_sum = 0.0
    for x in range(crediting_start_year, year + 1):
        w_j_x = annual_waste_tonnes  # constant annual input
        term = w_j_x * doc_j * math.exp(-k_j * (year - x)) * (1 - math.exp(-k_j))
        fod_sum += term

    be_ch4 = (
        model_correction_factor
        * (1 - baseline_capture_fraction)
        * GWP_CH4
        * (1 - oxidation_factor)
        * CH4_TO_CO2_RATIO
        * f_ch4
        * doc_f
        * mcf
        * fod_sum
    )

    return be_ch4


def methane_from_swds_simplified(
    annual_waste_tonnes: float,
    doc: float,
    mcf: float = MCF_DEFAULT,
    doc_f: float = DOC_F_DEFAULT,
    f_ch4: float = F_CH4_DEFAULT,
    oxidation_factor: float = OX_DEFAULT,
    model_correction_factor: float = MODEL_CORRECTION_FACTOR_DEFAULT,
    baseline_capture_fraction: float = 0.0,
) -> float:
    """Simplified (steady-state) methane from SWDS, ignoring FOD time dynamics.

    Useful for quick estimates or when year-by-year data is not needed.
    Assumes all waste decomposes in the year it is disposed.

    Returns tCO2e/year.
    """
    be_ch4 = (
        model_correction_factor
        * (1 - baseline_capture_fraction)
        * GWP_CH4
        * (1 - oxidation_factor)
        * CH4_TO_CO2_RATIO
        * f_ch4
        * doc_f
        * mcf
        * annual_waste_tonnes
        * doc
    )
    return be_ch4
