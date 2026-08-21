"""Incineration project emissions (PE_INC) for ACM0022.

Implements the two IPCC 2006 Volume 5 Chapter 5 equations specified in S-5b
of the 2026-08-21 real-output-fidelity plan:

- Equation 5.1 (per-stream form): fossil CO2 from combustion,
  PE_INC_CO2,y = Σ_j (MSW_j × dm_j × CF_j × FCF_j × OF) × 44/12
- Equation 5.4: N2O from combustion,
  PE_INC_N2O,y = (Σ_j MSW_j) × EF_N2O × 0.001 × GWP_N2O
"""

from __future__ import annotations

import structlog

from pdd_agent.calc.constants import (
    CO2_PER_C_RATIO,
    EF_N2O_INCINERATION_KG_PER_TONNE,
    GWP_N2O,
    INCINERATION_CARBON_BY_WASTE_TYPE,
    OXIDATION_FACTOR_INCINERATION,
)

logger = structlog.get_logger()


def _carbon_factors(waste_type: str, stream: dict[str, object]) -> tuple[float, float, float]:
    factors = INCINERATION_CARBON_BY_WASTE_TYPE.get(waste_type)
    if factors is None:
        logger.warning("incineration_waste_type_unknown", waste_type=waste_type)
        return (0.0, 0.0, 0.0)
    dm = stream.get("dm_override", None)
    cf = stream.get("cf_override", None)
    fcf = stream.get("fcf_override", None)
    return (
        float(dm) if dm is not None else factors["dm"],
        float(cf) if cf is not None else factors["CF"],
        float(fcf) if fcf is not None else factors["FCF"],
    )


def incineration_co2(
    streams: list[dict[str, object]], oxidation_factor: float = OXIDATION_FACTOR_INCINERATION
) -> float:
    """Fossil CO2 from combustion in tCO2/year (IPCC 2006 V5 Eq. 5.1)."""
    total = 0.0
    for stream in streams:
        tonnes = float(stream.get("annual_tonnes", 0.0))
        if tonnes <= 0:
            continue
        waste_type = str(stream.get("waste_type", ""))
        dm, cf, fcf = _carbon_factors(waste_type, stream)
        total += tonnes * dm * cf * fcf * oxidation_factor * CO2_PER_C_RATIO
    return total


def incineration_n2o(
    total_tonnes: float,
    ef_kg_per_tonne: float = EF_N2O_INCINERATION_KG_PER_TONNE,
    gwp_n2o: float = GWP_N2O,
) -> float:
    """N2O emissions expressed in tCO2e/year (IPCC 2006 V5 Eq. 5.4)."""
    return total_tonnes * ef_kg_per_tonne * 0.001 * gwp_n2o


def incineration_emissions(
    streams: list[dict[str, object]],
    oxidation_factor: float = OXIDATION_FACTOR_INCINERATION,
    ef_n2o_kg_per_tonne: float = EF_N2O_INCINERATION_KG_PER_TONNE,
) -> float:
    """Total PE_INC in tCO2e/year; 0.0 for an empty stream list."""
    if not streams:
        return 0.0
    co2 = incineration_co2(streams, oxidation_factor=oxidation_factor)
    total_tonnes = sum(float(s.get("annual_tonnes", 0.0)) for s in streams)
    n2o = incineration_n2o(total_tonnes, ef_kg_per_tonne=ef_n2o_kg_per_tonne)
    return co2 + n2o
