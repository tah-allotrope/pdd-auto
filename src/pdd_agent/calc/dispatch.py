"""Family-agnostic calc dispatch: ProjectInput -> PddCalcResult.

Maps a ProjectInput to the appropriate quantification engine (ACM0022,
VM0051, VM0044, AMS-II.G), computes the result, and wraps it in a
uniform PddCalcResult for prompt injection and consistency checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from pdd_agent.calc.acm0022 import ACM0022Calculator
from pdd_agent.calc.biochar_vm0044 import BiocharVm0044Engine
from pdd_agent.calc.constants import DOC_BY_WASTE_TYPE
from pdd_agent.calc.cookstove_amsiig import CookstoveAmsiigEngine
from pdd_agent.calc.models import ACM0022CalcInput
from pdd_agent.calc.rice_vm0051 import RiceVm0051Engine
from schemas.project_input import ProjectInput

logger = structlog.get_logger()

ENGINE_BY_METHODOLOGY: dict[str, str] = {
    "ACM0022": "acm0022",
    "VM0051": "vm0051",
    "VM0044": "vm0044",
    "AMS-II.G": "amsiig",
}


@dataclass
class CalcComponent:
    name: str
    value_tco2e: float
    unit: str = "tCO2e/year"
    formula: str = ""
    notes: str = ""


@dataclass
class AnnualErEntry:
    year: int
    baseline_tco2e: float
    project_tco2e: float
    leakage_tco2e: float
    net_tco2e: float


@dataclass
class PddCalcResult:
    methodology_id: str
    baseline_emissions_tco2e: float
    project_emissions_tco2e: float
    leakage_tco2e: float
    net_emission_reductions_tco2e: float
    crediting_period_total_tco2e: float
    crediting_period_years: int
    components: list[CalcComponent] = field(default_factory=list)
    monitoring_params: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_result: Any = None
    annual_schedule: list[AnnualErEntry] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        lines = [
            f"\n## {self.methodology_id} Calculation Engine Results\n",
            f"The following values were computed by the {self.methodology_id} "
            "pure-Python calculation engine.\n"
            "Use these as the authoritative quantification values. "
            "Cite with `[CALC: component_name]`.\n",
            f"- **Baseline emissions**: {self.baseline_emissions_tco2e:,.2f} "
            "tCO2e/year [CALC: baseline_total]",
            f"- **Project emissions**: {self.project_emissions_tco2e:,.2f} "
            "tCO2e/year [CALC: project_total]",
            f"- **Leakage**: {self.leakage_tco2e:,.2f} tCO2e/year [CALC: leakage_total]",
            f"- **Net emission reductions**: {self.net_emission_reductions_tco2e:,.2f} "
            "tCO2e/year [CALC: net_ER]",
            f"- **Crediting period total**: {self.crediting_period_total_tco2e:,.2f} "
            f"tCO2e ({self.crediting_period_years} years) [CALC: crediting_total]",
            "",
            "### Component Breakdown",
        ]
        for comp in self.components:
            lines.append(f"- {comp.name}: {comp.value_tco2e:,.2f} {comp.unit} — {comp.formula}")
        if self.annual_schedule:
            lines.append("")
            lines.append("### Year-by-Year Emission Reductions")
            for entry in self.annual_schedule[:30]:
                lines.append(f"- Year {entry.year}: {entry.net_tco2e:,.2f} tCO2e")
        if self.warnings:
            lines.append("")
            lines.append("### Calculation Warnings")
            for w in self.warnings:
                lines.append(f"- {w}")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe mapping of this result, excluding `raw_result`.

        `raw_result` holds a Pydantic ACM0022CalcResult for ACM0022 (and None for
        the other families) and is not JSON-serializable via a plain dict/list
        walk; downstream consumers (DraftRun persistence, export) never need it.
        """
        return {
            "methodology_id": self.methodology_id,
            "baseline_emissions_tco2e": self.baseline_emissions_tco2e,
            "project_emissions_tco2e": self.project_emissions_tco2e,
            "leakage_tco2e": self.leakage_tco2e,
            "net_emission_reductions_tco2e": self.net_emission_reductions_tco2e,
            "crediting_period_total_tco2e": self.crediting_period_total_tco2e,
            "crediting_period_years": self.crediting_period_years,
            "components": [
                {
                    "name": c.name,
                    "value_tco2e": c.value_tco2e,
                    "unit": c.unit,
                    "formula": c.formula,
                    "notes": c.notes,
                }
                for c in self.components
            ],
            "monitoring_params": self.monitoring_params,
            "warnings": self.warnings,
            "annual_schedule": [
                {
                    "year": e.year,
                    "baseline_tco2e": e.baseline_tco2e,
                    "project_tco2e": e.project_tco2e,
                    "leakage_tco2e": e.leakage_tco2e,
                    "net_tco2e": e.net_tco2e,
                }
                for e in self.annual_schedule
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PddCalcResult":
        """Reconstruct a PddCalcResult from `to_dict` output.

        Tolerates missing keys by falling back to the dataclass defaults, so a
        run JSON written before a field existed still loads cleanly.
        """
        return cls(
            methodology_id=data.get("methodology_id", ""),
            baseline_emissions_tco2e=data.get("baseline_emissions_tco2e", 0.0),
            project_emissions_tco2e=data.get("project_emissions_tco2e", 0.0),
            leakage_tco2e=data.get("leakage_tco2e", 0.0),
            net_emission_reductions_tco2e=data.get("net_emission_reductions_tco2e", 0.0),
            crediting_period_total_tco2e=data.get("crediting_period_total_tco2e", 0.0),
            crediting_period_years=data.get("crediting_period_years", 0),
            components=[CalcComponent(**c) for c in data.get("components", [])],
            monitoring_params=data.get("monitoring_params", []),
            warnings=data.get("warnings", []),
            raw_result=None,
            annual_schedule=[AnnualErEntry(**e) for e in data.get("annual_schedule", [])],
        )


def _map_acm0022(pi: ProjectInput) -> tuple[dict[str, Any], list[str]] | None:
    tech = pi.technology
    quant = pi.quantification
    warnings: list[str] = []

    waste_streams: list[dict[str, Any]] = []
    incineration_streams: list[dict[str, Any]] = []
    is_incineration = tech.technology_type == "incineration_with_energy_recovery"
    if tech.waste_composition:
        excluded_fraction = 0.0
        for entry in tech.waste_composition:
            warnings.append(
                f"waste_composition: {entry.waste_type} {entry.mass_fraction:.1%} — {entry.source}"
            )
            annual_tonnes = tech.annual_waste_throughput * entry.mass_fraction
            if entry.waste_type in DOC_BY_WASTE_TYPE:
                waste_streams.append(
                    {"waste_type": entry.waste_type, "annual_tonnes": annual_tonnes}
                )
            else:
                excluded_fraction += entry.mass_fraction
                if not is_incineration:
                    warnings.append(
                        f"waste_composition: unmapped type {entry.waste_type} contributes no BE_CH4"
                    )
                else:
                    warnings.append(
                        f"waste_composition: unmapped type {entry.waste_type} contributes PE_INC (incineration) but no BE_CH4 (landfill methane)"
                    )
            if is_incineration:
                incineration_streams.append(
                    {"waste_type": entry.waste_type, "annual_tonnes": annual_tonnes}
                )
        if excluded_fraction > 0 and not is_incineration:
            warnings.append(
                f"waste_composition: {excluded_fraction:.1%} of mass is non-degradable or unmapped and contributes no BE_CH4"
            )
        if not waste_streams:
            logger.warning("calc_inputs_incomplete", missing=["technology.waste_type"])
            return None
    else:
        kept = [wt for wt in tech.waste_type if wt in DOC_BY_WASTE_TYPE]
        excluded = [wt for wt in tech.waste_type if wt not in DOC_BY_WASTE_TYPE]
        if not kept:
            logger.warning("calc_inputs_incomplete", missing=["technology.waste_type"])
            return None
        per_type_tonnes = tech.annual_waste_throughput / len(kept)
        for wt in kept:
            waste_streams.append({"waste_type": wt, "annual_tonnes": per_type_tonnes})
        if excluded:
            warnings.append(
                f"waste types {excluded} are not in DOC_BY_WASTE_TYPE; their mass was redistributed across {kept}"
            )
        if len(kept) > 1:
            warnings.append("waste split evenly across N declared waste types")

    if tech.biomethanization_suitable_fraction is None:
        bio_frac = 0.0
        warnings.append(
            "biomethanization_suitable_fraction absent; assumed 0.0 "
            "(no anaerobic digestion pathway; does not affect BE_CH4)"
        )
    else:
        bio_frac = tech.biomethanization_suitable_fraction

    if quant.grid_emission_factor is None:
        logger.warning("calc_inputs_incomplete", missing=["quantification.grid_emission_factor"])
        return None
    if not quant.grid_emission_factor_source:
        logger.warning(
            "calc_inputs_incomplete", missing=["quantification.grid_emission_factor_source"]
        )
        return None

    mapped: dict[str, Any] = {
        "waste_streams": waste_streams,
        "biomethanization_fraction": bio_frac,
        "swds_diversion_fraction": 1.0,
        "grid_emission_factor_tco2_per_mwh": quant.grid_emission_factor,
        "grid_emission_factor_source": quant.grid_emission_factor_source,
        "crediting_period_years": pi.dates.crediting_period_years,
    }
    # Climate zone resolution (S-1d): declared wins else derived from latitude
    try:
        from pdd_agent.calc.constants import climate_zone_for

        zone = climate_zone_for(pi.location.latitude, pi.location.climate_zone)
        mapped["climate_zone"] = zone
        derived = pi.location.climate_zone is None
        warnings.append(f"calc_climate_zone_resolved: zone={zone} derived={derived}")
    except Exception as exc:
        warnings.append(f"climate_zone resolution failed: {exc}")
    if incineration_streams:
        mapped["incineration_streams"] = incineration_streams
    elif is_incineration and waste_streams:
        # When composition was not declared, incineration streams mirror waste_streams for Eq.22
        pass
    if tech.energy_generation_mwh_year is not None:
        mapped["electricity_exported_mwh_per_year"] = tech.energy_generation_mwh_year
    if quant.methane_capture_rate is not None:
        mapped["baseline_methane_captured_fraction"] = quant.methane_capture_rate
    if quant.grid_tdl_factor is not None:
        mapped["tdl_factor"] = quant.grid_tdl_factor
    # Auxiliary fossil fuel
    if getattr(tech, "auxiliary_fossil_fuel", None):
        mapped["fossil_fuels"] = [
            {
                "fuel_type": f.fuel_type,
                "annual_consumption_tonnes": f.annual_tonnes,
                "ncv_override": f.ncv_gj_per_tonne,
                "ef_override": f.ef_tco2_per_gj,
            }
            for f in tech.auxiliary_fossil_fuel
        ]
    # Wastewater
    rw = getattr(tech, "runoff_wastewater", None)
    if rw is not None:
        mapped["runoff_wastewater_m3_per_year"] = rw.annual_volume_m3
        mapped["runoff_wastewater_cod_t_per_m3"] = rw.cod_t_per_m3
        mapped["wastewater_bo_t_ch4_per_t_cod"] = rw.bo_t_ch4_per_t_cod
        mapped["wastewater_mcf"] = rw.mcf
    elif is_incineration:
        warnings.append("runoff_wastewater absent; PE_WW assumed zero")

    return mapped, warnings


def _map_vm0051(pi: ProjectInput) -> tuple[dict[str, Any], list[str]] | None:
    rc = pi.technology.rice_cultivation
    if rc is None:
        logger.warning("calc_inputs_incomplete", missing=["technology.rice_cultivation"])
        return None
    mapped = {
        "area_ha": rc.area_ha,
        "cultivation_days": rc.cultivation_days,
        "baseline_water_regime": rc.baseline_water_regime,
        "baseline_ef_kg_ch4_per_ha_per_day": rc.baseline_ef_kg_ch4_per_ha_per_day,
        "project_practices": rc.project_practices,
        "gwp_ch4": rc.gwp_ch4,
        "crediting_period_years": pi.dates.crediting_period_years,
    }
    return mapped, []


def _map_vm0044(pi: ProjectInput) -> tuple[dict[str, Any], list[str]] | None:
    bp = pi.technology.biochar_production
    if bp is None:
        logger.warning("calc_inputs_incomplete", missing=["technology.biochar_production"])
        return None
    mapped = {
        "feedstock_type": bp.feedstock_type,
        "dry_mass_tonnes": bp.dry_mass_tonnes,
        "carbon_fraction": bp.carbon_fraction,
        "pyrolysis_temperature_c": bp.pyrolysis_temperature_c,
        "stability_factor": bp.stability_factor,
        "permanence_factor": bp.permanence_factor,
        "crediting_period_years": pi.dates.crediting_period_years,
    }
    return mapped, []


def _map_amsiig(pi: ProjectInput) -> tuple[dict[str, Any], list[str]] | None:
    fleet = pi.technology.cookstove_fleet
    if not fleet:
        logger.warning("calc_inputs_incomplete", missing=["technology.cookstove_fleet"])
        return None
    stoves = []
    for entry in fleet:
        stoves.append(
            {
                "fuel_type": entry.fuel_type,
                "stove_count": entry.stove_count,
                "baseline_fuel_kg_per_day_per_stove": entry.baseline_fuel_kg_per_day_per_stove,
                "project_fuel_kg_per_day_per_stove": entry.project_fuel_kg_per_day_per_stove,
                "operating_days_per_year": entry.operating_days_per_year,
                "ncv_mj_per_kg": entry.ncv_mj_per_kg,
                "ef_kg_co2_per_mj": entry.ef_kg_co2_per_mj,
                "fnrb": entry.fnrb,
            }
        )
    mapped = {
        "stoves": stoves,
        "crediting_period_years": pi.dates.crediting_period_years,
    }
    return mapped, []


def build_engine_inputs(
    project_input: ProjectInput,
) -> tuple[str, dict[str, Any], list[str]] | None:
    mids = project_input.technology.methodology_ids
    if not mids:
        logger.warning("calc_engine_unsupported", methodology_id="")
        return None
    mid = mids[0].strip().upper()
    if mid not in ENGINE_BY_METHODOLOGY:
        logger.warning("calc_engine_unsupported", methodology_id=mid)
        return None

    if mid == "ACM0022":
        result = _map_acm0022(project_input)
    elif mid == "VM0051":
        result = _map_vm0051(project_input)
    elif mid == "VM0044":
        result = _map_vm0044(project_input)
    elif mid == "AMS-II.G":
        result = _map_amsiig(project_input)
    else:
        return None

    if result is None:
        return None
    engine_inputs, warnings = result
    return mid, engine_inputs, warnings


def _ramp_factor(capacity_ramp: list[float] | None, year: int) -> float:
    """Return the year's utilisation factor per S-5c; 1.0 when no ramp."""
    if not capacity_ramp:
        return 1.0
    if 1 <= year <= len(capacity_ramp):
        return capacity_ramp[year - 1]
    return capacity_ramp[-1]


def compute_for(project_input: ProjectInput) -> PddCalcResult | None:
    mapped = build_engine_inputs(project_input)
    if mapped is None:
        return None

    mid, engine_inputs, warnings = mapped
    cpy = project_input.dates.crediting_period_years

    if mid == "ACM0022":
        calc_input = ACM0022CalcInput(**engine_inputs)
        raw = ACM0022Calculator(calc_input).calculate()
        components = [
            CalcComponent(
                name=c.name,
                value_tco2e=c.value_tco2e,
                unit="tCO2e/year",
                formula=c.formula_ref,
                notes=c.notes,
            )
            for c in raw.components
        ]

        # Year-by-year schedule: BE_CH4 (and therefore BE_y) varies with the
        # crediting-period year under the FOD model; PE_y and LE_y do not, since
        # none of their inputs are time-varying in ProjectInput. A declared
        # capacity_ramp scales every year's waste masses and electricity export
        # (S-5c); the year-1 nameplate scalars on PddCalcResult stay unramped.
        ramp = project_input.technology.capacity_ramp
        schedule: list[AnnualErEntry] = []
        for y in range(1, cpy + 1):
            year_inputs = dict(engine_inputs)
            year_inputs["calculation_year"] = y
            factor = _ramp_factor(ramp, y)
            if factor != 1.0:
                year_inputs["waste_streams"] = [
                    {**ws, "annual_tonnes": ws["annual_tonnes"] * factor}
                    for ws in year_inputs.get("waste_streams", [])
                ]
                if "incineration_streams" in year_inputs:
                    year_inputs["incineration_streams"] = [
                        {**s, "annual_tonnes": s["annual_tonnes"] * factor}
                        for s in year_inputs["incineration_streams"]
                    ]
                if year_inputs.get("electricity_exported_mwh_per_year") is not None:
                    year_inputs["electricity_exported_mwh_per_year"] = (
                        year_inputs["electricity_exported_mwh_per_year"] * factor
                    )
            year_raw = ACM0022Calculator(ACM0022CalcInput(**year_inputs)).calculate()
            schedule.append(
                AnnualErEntry(
                    year=y,
                    baseline_tco2e=year_raw.baseline_emissions_tco2e,
                    project_tco2e=year_raw.project_emissions_tco2e,
                    leakage_tco2e=year_raw.leakage_tco2e,
                    net_tco2e=year_raw.net_emission_reductions_tco2e,
                )
            )
        crediting_period_total = sum(e.net_tco2e for e in schedule)

        return PddCalcResult(
            methodology_id="ACM0022",
            baseline_emissions_tco2e=raw.baseline_emissions_tco2e,
            project_emissions_tco2e=raw.project_emissions_tco2e,
            leakage_tco2e=raw.leakage_tco2e,
            net_emission_reductions_tco2e=raw.net_emission_reductions_tco2e,
            crediting_period_total_tco2e=crediting_period_total,
            crediting_period_years=raw.crediting_period_years,
            components=components,
            monitoring_params=ACM0022Calculator(calc_input).required_monitoring_params(
                engine_inputs
            ),
            warnings=warnings,
            raw_result=raw,
            annual_schedule=schedule,
        )

    if mid == "VM0051":
        engine = RiceVm0051Engine()
    elif mid == "VM0044":
        engine = BiocharVm0044Engine()
    elif mid == "AMS-II.G":
        engine = CookstoveAmsiigEngine()
    else:
        return None

    baseline_r = engine.compute_baseline(engine_inputs)
    project_r = engine.compute_project(engine_inputs)
    leakage_r = engine.compute_leakage(engine_inputs)
    net_r = engine.compute_net(engine_inputs)
    crediting_total = net_r.value * cpy

    components = [
        CalcComponent(
            name="baseline",
            value_tco2e=baseline_r.value,
            unit=baseline_r.unit,
            formula=baseline_r.formula,
            notes=baseline_r.notes,
        ),
        CalcComponent(
            name="project",
            value_tco2e=project_r.value,
            unit=project_r.unit,
            formula=project_r.formula,
            notes=project_r.notes,
        ),
        CalcComponent(
            name="leakage",
            value_tco2e=leakage_r.value,
            unit=leakage_r.unit,
            formula=leakage_r.formula,
            notes=leakage_r.notes,
        ),
        CalcComponent(
            name="net",
            value_tco2e=net_r.value,
            unit=net_r.unit,
            formula=net_r.formula,
            notes=net_r.notes,
        ),
    ]
    mon_params = engine.required_monitoring_params(engine_inputs)

    # No time dynamic for these families: every year is identical, so the
    # schedule is flat and its sum reduces to the existing net * cpy product.
    schedule = [
        AnnualErEntry(
            year=y,
            baseline_tco2e=baseline_r.value,
            project_tco2e=project_r.value,
            leakage_tco2e=leakage_r.value,
            net_tco2e=net_r.value,
        )
        for y in range(1, cpy + 1)
    ]

    return PddCalcResult(
        methodology_id=mid,
        baseline_emissions_tco2e=baseline_r.value,
        project_emissions_tco2e=project_r.value,
        leakage_tco2e=leakage_r.value,
        net_emission_reductions_tco2e=net_r.value,
        crediting_period_total_tco2e=crediting_total,
        crediting_period_years=cpy,
        components=components,
        monitoring_params=mon_params,
        warnings=warnings,
        annual_schedule=schedule,
    )
