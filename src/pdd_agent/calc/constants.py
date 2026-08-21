"""Physical constants and methodology defaults for ACM0022 calculations.

Values sourced from:
- IPCC AR5 (GWP)
- CDM Tool 04 v08.0 (FOD model defaults)
- CDM Tool 03 v04.0 (fossil fuel factors)
- CDM Tool 05 v03.0 (electricity emissions)
- IPCC 2006 Guidelines Volume 5 Chapter 2 Table 2.4 (dry matter, total carbon)
  and Chapter 5 Tables 5.2/5.6 (fossil carbon fraction, N2O emission factor
  for continuous stoker-type MSW incineration) — incineration constants.
"""

from __future__ import annotations

GWP_CH4: float = 28.0  # AR5, tCO2e per tCH4

GWP_N2O: float = 265.0  # AR5, tCO2e per tN2O

# kg N2O per tonne of wet waste incinerated — IPCC 2006 V5 Ch.5 Table 5.6,
# continuous stoker-type MSW incineration.
EF_N2O_INCINERATION_KG_PER_TONNE: float = 0.05

# Fraction of incinerated carbon actually oxidised — IPCC default for modern
# MSW incineration (complete oxidation). Overridable engine input.
OXIDATION_FACTOR_INCINERATION: float = 1.0

CO2_PER_C_RATIO: float = 44.0 / 12.0  # molecular mass ratio CO2/C

# Per-waste-type incineration defaults (ASM-005):
#   dm  — dry matter content as a fraction of wet weight
#         (IPCC 2006 V5 Ch.2 Table 2.4)
#   CF  — total carbon content as a fraction of DRY matter
#         (IPCC 2006 V5 Ch.2 Table 2.4)
#   FCF — fraction of that carbon which is fossil in origin
#         (IPCC 2006 V5 Ch.5 Table 5.2)
INCINERATION_CARBON_BY_WASTE_TYPE: dict[str, dict[str, float]] = {
    "food_waste": {"dm": 0.40, "CF": 0.38, "FCF": 0.00},
    "garden_waste": {"dm": 0.40, "CF": 0.49, "FCF": 0.00},
    "paper_cardboard": {"dm": 0.90, "CF": 0.46, "FCF": 0.01},
    "wood": {"dm": 0.85, "CF": 0.50, "FCF": 0.00},
    "textiles": {"dm": 0.80, "CF": 0.50, "FCF": 0.20},
    "nappies": {"dm": 0.40, "CF": 0.70, "FCF": 0.10},
    "rubber_leather": {"dm": 0.84, "CF": 0.67, "FCF": 0.20},
    "plastics": {"dm": 1.00, "CF": 0.75, "FCF": 1.00},
    "inert": {"dm": 0.90, "CF": 0.03, "FCF": 1.00},
    "municipal_solid_waste": {"dm": 0.60, "CF": 0.40, "FCF": 0.30},
}

DENSITY_CH4: float = 0.0007168  # tonnes CH4 per Nm3 at STP (0°C, 1 atm)

FRACTION_CH4_BIOGAS_DEFAULT: float = 0.56  # m3 CH4 / m3 biogas

MCF_DEFAULT: float = 1.0  # managed, anaerobic SWDS (IPCC Table 3.1)
MCF_UNMANAGED_SHALLOW: float = 0.4
MCF_UNMANAGED_DEEP: float = 0.8

DOC_F_DEFAULT: float = 0.5  # fraction of DOC that decomposes

OX_DEFAULT: float = 0.0  # oxidation factor for unmanaged SWDS (conservative)
OX_MANAGED: float = 0.1

MODEL_CORRECTION_FACTOR_DEFAULT: float = 0.9  # φ_default per Tool 04

F_CH4_DEFAULT: float = 0.5  # fraction of CH4 in SWDS gas (volume)

CH4_TO_CO2_RATIO: float = 16.0 / 12.0  # molecular weight ratio

EF_CH4_DIGESTER_DEFAULT: float = 0.05  # 5% methane leakage from AD (Tool 14)

FLARE_EFFICIENCY_OPEN: float = 0.5  # 50% destruction for open flare (Tool 06)
FLARE_EFFICIENCY_ENCLOSED: float = 0.9  # 90% for enclosed flare

TDL_DEFAULT: float = 0.0  # transmission/distribution losses (conservative)

# DOC values by waste type (fraction, dry weight basis) - IPCC 2006 Table 2.4
DOC_BY_WASTE_TYPE: dict[str, float] = {
    "food_waste": 0.15,
    "garden_waste": 0.20,
    "paper_cardboard": 0.40,
    "wood": 0.43,
    "textiles": 0.24,
    "nappies": 0.24,
    "rubber_leather": 0.39,
    "municipal_solid_waste": 0.17,  # weighted average for mixed MSW
}

# Decay rates by waste type (1/year) - IPCC 2006 Table 3.3, wet tropical
DECAY_RATE_BY_WASTE_TYPE: dict[str, float] = {
    "food_waste": 0.185,
    "garden_waste": 0.100,
    "paper_cardboard": 0.060,
    "wood": 0.030,
    "textiles": 0.060,
    "nappies": 0.060,
    "rubber_leather": 0.060,
    "municipal_solid_waste": 0.09,  # conservative default for mixed MSW
}

# Fossil fuel emission factors (tCO2/GJ) - CDM Tool 03 defaults
FOSSIL_FUEL_EF: dict[str, float] = {
    "diesel": 0.0741,
    "gasoline": 0.0693,
    "natural_gas": 0.0561,
    "lpg": 0.0631,
    "fuel_oil": 0.0774,
    "coal": 0.0946,
}

# Net calorific values (GJ/tonne) - CDM Tool 03 defaults
FOSSIL_FUEL_NCV: dict[str, float] = {
    "diesel": 43.0,
    "gasoline": 44.3,
    "natural_gas": 48.0,  # GJ/1000 Nm3 -> per tonne needs conversion
    "lpg": 47.3,
    "fuel_oil": 40.4,
    "coal": 25.8,
}
