"""Validate the calc engines against figures published in registered VCS PDDs.

Every other calc test in this suite asserts that the engine reproduces its own
arithmetic. These tests assert that it reproduces a *validated* document — the
only evidence that the quantification is defensible in front of a VVB.

The oracle values below were read out of the registered project descriptions in
`data/corpus/normalized/`. They are hard-coded rather than re-parsed at test
time so these tests run without the (gitignored) corpus present, and therefore
carry no `corpus` marker: they read committed config YAML only.

Sources:
  VCS_Soc_Son_Project-Description.norm.json  -> "Total estimated ERs  3,808,082"
  VCS_Inegol_Project-Description.norm.json   -> "Total estimated ERs 730,000"
                                             -> "average annual emission reduction
                                                 ... is around 104,285"
"""

from pathlib import Path

import pytest
import yaml

from pdd_agent.calc.dispatch import compute_for
from schemas.project_input import ProjectInput

# Headline figures from the registered PDDs, in tCO2e.
SOC_SON_TOTAL_ERS = 3_808_082
INEGOL_TOTAL_ERS = 730_000
INEGOL_ANNUAL_ERS = 104_285

# The repo configs do not carry waste-composition splits or site-specific
# project-emission inputs, so an exact match is not achievable. 20% is loose
# enough to absorb that and tight enough that a structurally missing baseline
# term cannot hide inside it.
TOLERANCE = 0.20


def _load_pi(path: str) -> ProjectInput:
    root = Path(__file__).parent.parent
    with open(root / path, encoding="utf-8") as f:
        return ProjectInput.model_validate(yaml.safe_load(f))


def _relative_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / expected


class TestSocSonOracle:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Re-measured 2026-08-20 after PHASE-05 waste-composition fix: engine "
            "computed 5,397,730 tCO2e crediting-period total vs registered "
            "3,808,082 tCO2e (+41.7%). Before PHASE-03 the same test passed at "
            "3,413,977 tCO2e (year-1 net x 7, -10.3%); PHASE-03's FOD schedule "
            "raised it to 5,312,566 tCO2e (+39.5%). With the Soc Son composition "
            "now declared (food_waste 51.9%, paper 2.7%, textiles 1.6%, rubber 1.3%, "
            "wood/garden 0.0%; 42.5% inert correctly excluded, so 839,500 t/yr "
            "degradable of 1,460,000 t/yr total reaches the engine) the gap moves "
            "to +41.7% — higher because the degradable mix is more methane-rich than "
            "the previous even split. The remaining gap is still the same phenomenon "
            "documented in TestInegolOracle: the repo config carries no capacity "
            "ramp or site-specific project-emission inputs to offset FOD growth the "
            "way the registered PDD does. Closing it needs those inputs, not a "
            "wider tolerance."
        ),
    )
    def test_crediting_period_total_within_tolerance(self):
        result = compute_for(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        assert result is not None
        error = _relative_error(result.crediting_period_total_tco2e, SOC_SON_TOTAL_ERS)
        assert error <= TOLERANCE, (
            f"engine computed {result.crediting_period_total_tco2e:,.0f} tCO2e against the "
            f"registered {SOC_SON_TOTAL_ERS:,} tCO2e ({error:.1%} error)"
        )

    def test_baseline_methane_is_material(self):
        """Avoided landfill methane is the economic case for a WTE project.

        It must not be zero for a project whose whole premise is landfill
        diversion.
        """
        result = compute_for(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        assert result is not None
        be_ch4 = next(c for c in result.components if c.name.startswith("BE_CH4"))
        assert be_ch4.value_tco2e > 0.0


_YEAR_ONE_XFAIL = pytest.mark.xfail(
    strict=True,
    reason=(
        "Re-measured 2026-08-20 after PHASE-05 (socson now 5,397,730 tCO2e, +41.7% vs "
        "3,808,082; inegol unchanged). The registered 104,285 tCO2e/yr is an AVERAGE "
        "over the 7-year crediting period, while PddCalcResult's scalars describe "
        "YEAR 1 of a first-order-decay baseline — the smallest year. Measured after "
        "the BE_CH4 fix: year 1 net = 50,690 (-51.4%), year 3 = 107,226 (+2.8% of the "
        "registered average), 7-year sum = 893,441 vs registered 730,000 (+22.4%). "
        "Summing the schedule instead of multiplying year 1 by 7 moves this from "
        "-51% to +22%; closing the remaining gap needs the project-emission inputs "
        "the config lacks."
    ),
)


class TestInegolOracle:
    @_YEAR_ONE_XFAIL
    def test_annual_net_within_tolerance(self):
        result = compute_for(_load_pi("configs/demo/inegol_project_input.yaml"))
        assert result is not None
        error = _relative_error(result.net_emission_reductions_tco2e, INEGOL_ANNUAL_ERS)
        assert error <= TOLERANCE, (
            f"engine computed {result.net_emission_reductions_tco2e:,.0f} tCO2e/yr against the "
            f"registered {INEGOL_ANNUAL_ERS:,} tCO2e/yr ({error:.1%} error)"
        )

    @_YEAR_ONE_XFAIL
    def test_crediting_period_total_within_tolerance(self):
        result = compute_for(_load_pi("configs/demo/inegol_project_input.yaml"))
        assert result is not None
        error = _relative_error(result.crediting_period_total_tco2e, INEGOL_TOTAL_ERS)
        assert error <= TOLERANCE, (
            f"engine computed {result.crediting_period_total_tco2e:,.0f} tCO2e against the "
            f"registered {INEGOL_TOTAL_ERS:,} tCO2e ({error:.1%} error)"
        )

    def test_baseline_methane_accumulates_across_crediting_period(self):
        """The FOD baseline must grow year over year as waste piles up.

        This is the property that makes the year-1 scalar an understatement, and
        it is what the year-by-year schedule will expose.
        """
        from pdd_agent.calc.acm0022 import ACM0022Calculator
        from pdd_agent.calc.dispatch import build_engine_inputs
        from pdd_agent.calc.models import ACM0022CalcInput

        mapped = build_engine_inputs(_load_pi("configs/demo/inegol_project_input.yaml"))
        assert mapped is not None
        _mid, engine_inputs, _warnings = mapped

        def _be_ch4(year: int) -> float:
            inputs = dict(engine_inputs, calculation_year=year)
            return (
                ACM0022Calculator(ACM0022CalcInput(**inputs))
                .calculate()
                .baseline_methane_swds_tco2e
            )

        assert _be_ch4(1) < _be_ch4(4) < _be_ch4(7)

    def test_displaced_grid_electricity_matches_registered_factor(self):
        """BE_EC is the one term we can check exactly: MWh x combined-margin EF."""
        result = compute_for(_load_pi("configs/demo/inegol_project_input.yaml"))
        assert result is not None
        be_ec = next(c for c in result.components if c.name.startswith("BE_EC"))
        assert be_ec.value_tco2e == pytest.approx(49_935.315 * 0.5410, rel=1e-6)
