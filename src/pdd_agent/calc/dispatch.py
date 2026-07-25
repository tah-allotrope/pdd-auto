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
        if self.warnings:
            lines.append("")
            lines.append("### Calculation Warnings")
            for w in self.warnings:
                lines.append(f"- {w}")
        lines.append("")
        return "\n".join(lines)


def _map_acm0022(pi: ProjectInput) -> tuple[dict[str, Any], list[str]] | None:
    tech = pi.technology
    quant = pi.quantification
    warnings: list[str] = []

    waste_streams = []
    n_types = len(tech.waste_type)
    per_type_tonnes = tech.annual_waste_throughput / n_types if n_types else 0
    kept = []
    for wt in tech.waste_type:
        if wt in DOC_BY_WASTE_TYPE:
            kept.append(wt)
        else:
            warnings.append(f"waste_type '{wt}' not in DOC_BY_WASTE_TYPE; excluded from the calc")
    if not kept:
        logger.warning("calc_inputs_incomplete", missing=["technology.waste_type"])
        return None
    for wt in kept:
        waste_streams.append({"waste_type": wt, "annual_tonnes": per_type_tonnes})
    if n_types > 1:
        warnings.append("waste split evenly across N declared waste types")

    if tech.biomethanization_suitable_fraction is None:
        bio_frac = 0.0
        warnings.append(
            "biomethanization_suitable_fraction absent; assumed 0.0 "
            "(no anaerobic digestion pathway)"
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
        "grid_emission_factor_tco2_per_mwh": quant.grid_emission_factor,
        "grid_emission_factor_source": quant.grid_emission_factor_source,
        "crediting_period_years": pi.dates.crediting_period_years,
    }
    if tech.energy_generation_mwh_year is not None:
        mapped["electricity_exported_mwh_per_year"] = tech.energy_generation_mwh_year
    if quant.methane_capture_rate is not None:
        mapped["baseline_methane_captured_fraction"] = quant.methane_capture_rate

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
        return PddCalcResult(
            methodology_id="ACM0022",
            baseline_emissions_tco2e=raw.baseline_emissions_tco2e,
            project_emissions_tco2e=raw.project_emissions_tco2e,
            leakage_tco2e=raw.leakage_tco2e,
            net_emission_reductions_tco2e=raw.net_emission_reductions_tco2e,
            crediting_period_total_tco2e=raw.crediting_period_total_tco2e,
            crediting_period_years=raw.crediting_period_years,
            components=components,
            monitoring_params=[],
            warnings=warnings,
            raw_result=raw,
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
    )
