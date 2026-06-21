"""CDM Tool 06: Project emissions from flaring.

Calculates project emissions from incomplete destruction of methane
during flaring of residual biogas.

Reference: CDM Tool 06 v02.0 — "Project emissions from flaring"
"""

from __future__ import annotations

from pdd_agent.calc.constants import FLARE_EFFICIENCY_ENCLOSED, FLARE_EFFICIENCY_OPEN, GWP_CH4


def flaring_emissions(
    methane_to_flare_tonnes: float,
    flare_type: str = "open",
    flare_efficiency_override: float | None = None,
) -> float:
    """Calculate project emissions from flaring of biogas (tCO2e/year).

    PE_flare,y = GWP_CH4 × F_CH4,RG × (1 - η_flare)  (Equation 15, Tool 06)

    Args:
        methane_to_flare_tonnes: Mass of methane sent to flare (tonnes CH4/year).
        flare_type: "open" (50% efficiency) or "enclosed" (90% efficiency).
        flare_efficiency_override: Override flare efficiency (fraction).

    Returns:
        Flaring emissions in tCO2e/year.
    """
    if flare_efficiency_override is not None:
        eta = flare_efficiency_override
    elif flare_type == "enclosed":
        eta = FLARE_EFFICIENCY_ENCLOSED
    else:
        eta = FLARE_EFFICIENCY_OPEN

    return GWP_CH4 * methane_to_flare_tonnes * (1 - eta)
