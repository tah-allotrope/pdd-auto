"""Incineration project emissions (PE_INC) for ACM0022.

Implements the two IPCC 2006 Volume 5 Chapter 5 equations specified in S-5b
of the 2026-08-21 real-output-fidelity plan plus ACM0022 Eq.22/27/28:

- Equation 5.1 (per-stream form): fossil CO2 from combustion,
  PE_INC_CO2,y = Σ_j (MSW_j × dm_j × CF_j × FCF_j × OF) × 44/12
- Equation 5.4: N2O from combustion,
  PE_INC_N2O,y = (Σ_j MSW_j) × EF_N2O × 0.001 × GWP_N2O
- ACM0022 Eq.22: PE_COM,CO2 = EFF × 44/12 × Σ Q_j × FCC_j × FFC_j
- ACM0022 Eq.27: PE_COM,CH4,N2O = Q_waste × (EF_N2O×GWP_N2O + EF_CH4×GWP_CH4)
- ACM0022 Eq.28: PE_WW = Q_ww × P_COD × B_o × MCF_ww × GWP_CH4
"""

from __future__ import annotations

import structlog

from pdd_agent.calc.constants import (
    ACM0022_CARBON_BY_WASTE_TYPE,
    B_O_DEFAULT_T_CH4_PER_T_COD,
    CO2_PER_C_RATIO,
    EF_CH4_INCINERATION_T_PER_TONNE,
    EF_N2O_INCINERATION_KG_PER_TONNE,
    EF_N2O_INCINERATION_T_PER_TONNE,
    GWP_CH4,
    GWP_N2O,
    INCINERATION_CARBON_BY_WASTE_TYPE,
    MCF_WASTEWATER_DEFAULT,
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


# --- ACM0022 Eq.22 / Eq.27 / Eq.28 helpers ---


def combustion_co2_eq22(
    streams: list[dict[str, object]], combustion_efficiency: float = 1.0
) -> float:
    """Fossil CO2 from combustion in tCO2/year (ACM0022 Eq.22).

    PE_COM,CO2 = EFF × 44/12 × Σ Q_j × FCC_j × FFC_j
    """
    total_c = 0.0
    for stream in streams:
        tonnes = float(stream.get("annual_tonnes", 0.0))
        if tonnes <= 0:
            continue
        waste_type = str(stream.get("waste_type", ""))
        factors = ACM0022_CARBON_BY_WASTE_TYPE.get(waste_type)
        if factors is None:
            logger.warning("acm0022_carbon_waste_type_unknown", waste_type=waste_type)
            continue
        total_c += tonnes * factors["FCC"] * factors["FFC"]
    return total_c * CO2_PER_C_RATIO * combustion_efficiency


def combustion_ch4_n2o_eq27(
    total_tonnes: float,
    ef_n2o_t_per_tonne: float = EF_N2O_INCINERATION_T_PER_TONNE,
    ef_ch4_t_per_tonne: float = EF_CH4_INCINERATION_T_PER_TONNE,
) -> float:
    """Combustion CH4+N2O in tCO2e/year (ACM0022 Eq.27 Option 2)."""
    return total_tonnes * (ef_n2o_t_per_tonne * GWP_N2O + ef_ch4_t_per_tonne * GWP_CH4)


def wastewater_ch4_eq28(
    volume_m3_per_year: float,
    cod_t_per_m3: float,
    bo_t_ch4_per_t_cod: float = B_O_DEFAULT_T_CH4_PER_T_COD,
    mcf: float = MCF_WASTEWATER_DEFAULT,
) -> float:
    """Run-off wastewater methane in tCO2e/year (ACM0022 Eq.28)."""
    if volume_m3_per_year <= 0 or cod_t_per_m3 <= 0:
        return 0.0
    return volume_m3_per_year * cod_t_per_m3 * bo_t_ch4_per_t_cod * mcf * GWP_CH4
