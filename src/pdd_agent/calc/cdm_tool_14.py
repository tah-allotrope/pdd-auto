"""CDM Tool 14: Project and leakage emissions from anaerobic digesters.

Calculates methane leakage from anaerobic digestion and emissions from
digestate management.

Reference: CDM Tool 14 v02.0 — "Project and leakage emissions from
anaerobic digesters"
"""

from __future__ import annotations

from pdd_agent.calc.constants import EF_CH4_DIGESTER_DEFAULT, GWP_CH4


def digester_methane_leakage(
    methane_produced_tonnes: float,
    leakage_fraction: float = EF_CH4_DIGESTER_DEFAULT,
) -> float:
    """Project emissions from methane leakage at the anaerobic digester (tCO2e/year).

    PE_CH4,y = Q_CH4,y × EF_CH4,default × GWP_CH4  (Equation 4, Tool 14)

    Args:
        methane_produced_tonnes: Total methane produced by digester (tonnes CH4/year).
        leakage_fraction: Fraction of CH4 that leaks (default 5%).

    Returns:
        Methane leakage emissions in tCO2e/year.
    """
    return methane_produced_tonnes * leakage_fraction * GWP_CH4


def digestate_storage_leakage(
    digestate_stored_anaerobically: bool,
    solid_digestate_tonnes: float = 0.0,
    volatile_solids_fraction: float = 0.0,
    methane_conversion_factor: float = 0.1,
) -> float:
    """Leakage emissions from anaerobic storage of digestate (tCO2e/year).

    Returns 0 if digestate is managed aerobically (the common case for
    well-operated facilities like Inegol).

    Args:
        digestate_stored_anaerobically: True if stored in anaerobic conditions.
        solid_digestate_tonnes: Mass of solid digestate (tonnes/year).
        volatile_solids_fraction: Fraction of volatile solids remaining.
        methane_conversion_factor: MCF for digestate storage conditions.

    Returns:
        Digestate leakage emissions in tCO2e/year.
    """
    if not digestate_stored_anaerobically:
        return 0.0

    # Simplified estimate per Tool 14 Option 2
    return solid_digestate_tonnes * volatile_solids_fraction * methane_conversion_factor * GWP_CH4
