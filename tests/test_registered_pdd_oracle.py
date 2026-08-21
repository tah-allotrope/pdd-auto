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

from pdd_agent.calc.dispatch import build_engine_inputs, compute_for
from schemas.project_input import ProjectInput

# Headline figures from the registered PDDs, in tCO2e.
SOC_SON_TOTAL_ERS = 3_808_082
INEGOL_TOTAL_ERS = 730_000
INEGOL_ANNUAL_ERS = 104_285

# Year-by-year schedule from the registered Soc Son PDD (S-5a): Table 9 gives
# baseline methane from the SWDS; Section 1.10 gives the estimated ERs.
SOC_SON_REGISTERED_BE_CH4_BY_YEAR = [
    277_866,
    466_829,
    596_016,
    684_963,
    746_778,
    790_258,
    821_308,
]
SOC_SON_REGISTERED_ER_BY_YEAR = [
    195_589,
    384_553,
    513_739,
    602_687,
    664_502,
    707_981,
    739_032,
]

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
    def test_crediting_period_total_within_tolerance(self):
        """Passed 2026-08-21 after PE_INC + corrected composition.

        Re-measured history: 3,413,977 (-10.3%) pre-PHASE-03; 5,312,566
        (+39.5%) after the FOD schedule; 5,397,730 (+41.7%) after the
        2026-08-20 composition fix; 4,010,142 (+5.3%) after adding PE_INC
        (187,895 tCO2e/yr) and correcting the composition to Table 8's exact
        1.000 (rubber_leather removed; plastics 3.0% + inert 40.8% split out
        of the 43.8% bucket). The xfail was flipped to a passing test because
        it genuinely passes — TOLERANCE untouched.
        """
        result = compute_for(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        assert result is not None
        error = _relative_error(result.crediting_period_total_tco2e, SOC_SON_TOTAL_ERS)
        assert error <= TOLERANCE, (
            f"engine computed {result.crediting_period_total_tco2e:,.0f} tCO2e against the "
            f"registered {SOC_SON_TOTAL_ERS:,} tCO2e ({error:.1%} error)"
        )

    def test_project_emissions_nonzero_for_incinerator(self):
        """A 52 MW incinerator burning 1.46 Mt/yr must report PE > 0 (S-5b)."""
        result = compute_for(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        assert result is not None
        assert result.project_emissions_tco2e > 0.0
        pe_inc = next(c for c in result.components if c.name.startswith("PE_INC"))
        assert pe_inc.value_tco2e > 0.0

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
        "Re-measured 2026-08-21 after PE_INC + capacity_ramp push (socson now "
        "4,010,142 tCO2e, +5.3% vs 3,808,082 — inside tolerance; inegol unchanged "
        "because its config declares no waste_composition, so it gains no "
        "incineration_streams and no ramp). The registered 104,285 tCO2e/yr is an "
        "AVERAGE over the 7-year crediting period, while PddCalcResult's scalars "
        "describe YEAR 1 of a first-order-decay baseline — the smallest year. "
        "Measured 2026-08-21: year 1 net = 50,690 (-51.4%), year 3 = 107,226 (+2.8% "
        "of the registered average), 7-year sum = 893,441 vs registered 730,000 "
        "(+22.4%). Closing the remaining gap needs site-specific project-emission "
        "and composition inputs the Inegol config lacks."
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


class TestSocSonAnnualSchedule:
    """Year-by-year measurement against the registered schedule (S-5a)."""

    def test_registered_constants_sum_to_published_totals(self):
        assert sum(SOC_SON_REGISTERED_BE_CH4_BY_YEAR) == 4_384_018
        assert sum(SOC_SON_REGISTERED_ER_BY_YEAR) == 3_808_083

    def test_registered_constant_charge_identity(self):
        """Registered ER_y = BE_CH4,y - 82,276.5 for every crediting year."""
        for be_ch4, er in zip(SOC_SON_REGISTERED_BE_CH4_BY_YEAR, SOC_SON_REGISTERED_ER_BY_YEAR):
            assert abs((be_ch4 - er) - 82_276.5) <= 0.5

    def _engine_year(self, engine_inputs: dict, year: int):
        from pdd_agent.calc.acm0022 import ACM0022Calculator
        from pdd_agent.calc.models import ACM0022CalcInput

        inputs = dict(engine_inputs, calculation_year=year)
        return ACM0022Calculator(ACM0022CalcInput(**inputs)).calculate()

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "D-1 (baseline methane too low), re-measured 2026-08-21 after PE_INC "
            "+ corrected composition: the engine's 7-year BE_CH4 sum is "
            "2,826,368 tCO2e vs the registered 4,384,018 tCO2e (-35.5%). The "
            "first-order-decay parameters (DOC, k, f_ch4, capture rate) "
            "understate methane growth relative to the registered PDD's own FOD "
            "run. Closing this needs an FOD parameter investigation, which is "
            "explicitly out of scope (RISK-05-03); TOLERANCE is not widened."
        ),
    )
    def test_engine_be_ch4_sum_within_tolerance_of_registered(self):
        mapped = build_engine_inputs(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        assert mapped is not None
        _mid, engine_inputs, _warnings = mapped
        be_ch4_sum = sum(
            self._engine_year(engine_inputs, y).baseline_methane_swds_tco2e for y in range(1, 8)
        )
        error = _relative_error(be_ch4_sum, sum(SOC_SON_REGISTERED_BE_CH4_BY_YEAR))
        assert error <= TOLERANCE, (
            f"engine 7-year BE_CH4 sum {be_ch4_sum:,.0f} tCO2e vs registered "
            f"{sum(SOC_SON_REGISTERED_BE_CH4_BY_YEAR):,} tCO2e ({error:.1%} error)"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "D-2 (everything but baseline methane has the wrong sign), "
            "re-measured 2026-08-21 after PE_INC: in the registered PDD, "
            "ER_y = BE_CH4,y - 82,276.5 every year, i.e. the net effect of "
            "(baseline electricity - project emissions - leakage) is a constant "
            "charge of -82,276.5 tCO2e/yr. The engine computes +169,110.6 tCO2e/yr "
            "for that same quantity (BE_EC 357,006.0 minus PE_INC-carrying PE "
            "187,895.4), a discrepancy of 251,387.1 tCO2e/yr. Closing it needs the "
            "registered PDD's actual grid-EF/displacement basis; TOLERANCE is not "
            "widened."
        ),
    )
    def test_non_methane_net_charge_matches_registered(self):
        mapped = build_engine_inputs(_load_pi("configs/projects/vietnam_socson_from_sheet.yaml"))
        assert mapped is not None
        _mid, engine_inputs, _warnings = mapped
        for y in range(1, 8):
            raw = self._engine_year(engine_inputs, y)
            charge = (
                raw.baseline_emissions_tco2e
                - raw.baseline_methane_swds_tco2e
                - raw.project_emissions_tco2e
                - raw.leakage_tco2e
            )
            assert abs(charge - (-82_276.5)) <= TOLERANCE * abs(-82_276.5), (
                f"year {y}: non-methane net charge {charge:,.1f} vs registered -82,276.5 tCO2e"
            )
