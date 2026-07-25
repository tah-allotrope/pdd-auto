"""ACM0022 emission reduction calculator for waste-to-energy projects.

Orchestrates CDM Tools 03-06 and 14 to calculate baseline, project,
and leakage emissions per ACM0022 v3.0 "Alternative waste treatment processes".

Key equations:
  BE_y = Σ(BE_CH4,t,y + BE_WW,t,y + BE_EN,t,y + BE_NG,t,y) × (1 - RATE_compliance,t)  [Eq.1]
  PE_y = PE_COMP,y + PE_AD,y + PE_GAS,y + PE_RDF_SB,y + PE_INC,y                       [Eq.17]
  LE_y = LE_COMP,y + LE_AD,y + LE_RDF_SB,y                                               [Eq.1 leakage]
  ER_y = BE_y - PE_y - LE_y                                                               [Eq.36]
"""

from __future__ import annotations

from typing import Any

from pdd_agent.calc import cdm_tool_03, cdm_tool_04, cdm_tool_05, cdm_tool_06, cdm_tool_14
from pdd_agent.calc.constants import DENSITY_CH4
from pdd_agent.calc.methodology import ComputationResult, ValidationResult
from pdd_agent.calc.models import ACM0022CalcInput, ACM0022CalcResult, EmissionComponent


class ACM0022Calculator:
    """Deterministic ACM0022 emission reduction calculator."""

    def __init__(self, inputs: ACM0022CalcInput) -> None:
        self._inp = inputs

    def calculate(self) -> ACM0022CalcResult:
        """Run the full ACM0022 calculation and return structured results."""
        components: list[EmissionComponent] = []

        # --- Intermediate: biogas and methane production ---
        total_waste = sum(ws.annual_tonnes for ws in self._inp.waste_streams)
        organic_to_ad = total_waste * self._inp.biomethanization_fraction
        annual_biogas_m3 = organic_to_ad * self._inp.biogas_yield_m3_per_tonne
        annual_methane_m3 = annual_biogas_m3 * self._inp.methane_fraction_biogas
        annual_methane_tonnes = annual_methane_m3 * DENSITY_CH4

        # Electricity from biogas (if not directly monitored)
        methane_lhv_kwh_per_m3 = 9.97
        if self._inp.electricity_exported_mwh_per_year is not None:
            electricity_generated_mwh = self._inp.electricity_exported_mwh_per_year
        else:
            gross_kwh = (
                annual_methane_m3 * methane_lhv_kwh_per_m3 * self._inp.engine_electrical_efficiency
            )
            electricity_generated_mwh = gross_kwh / 1000.0

        # ========== BASELINE EMISSIONS ==========

        # BE_CH4: methane from SWDS (FOD model, summed over waste streams).
        #
        # This is the methane the landfill would have emitted for waste the
        # project diverts, so it scales with swds_diversion_fraction — NOT with
        # biomethanization_fraction, which only governs how much of that waste is
        # routed to anaerobic digestion. A mass-burn plant biomethanizes nothing
        # and still avoids the entire landfill methane stream.
        be_ch4_total = 0.0
        for ws in self._inp.waste_streams:
            diverted_from_swds = ws.annual_tonnes * self._inp.swds_diversion_fraction
            be_ch4_ws = cdm_tool_04.methane_from_swds(
                waste_type=ws.waste_type,
                annual_waste_tonnes=diverted_from_swds,
                year=self._inp.calculation_year,
                doc_override=ws.doc_override,
                decay_rate_override=ws.decay_rate_override,
                model_correction_factor=self._inp.model_correction_factor,
                baseline_capture_fraction=self._inp.baseline_methane_captured_fraction,
                mcf=self._inp.mcf,
                oxidation_factor=self._inp.oxidation_factor,
                doc_f=self._inp.doc_f,
                f_ch4=self._inp.f_ch4,
            )
            be_ch4_total += be_ch4_ws

        components.append(
            EmissionComponent(
                name="BE_CH4 (methane from SWDS)",
                value_tco2e=be_ch4_total,
                formula_ref="ACM0022 Eq.1 + Tool 04 Eq.2",
                notes=(
                    f"FOD model, year {self._inp.calculation_year}, "
                    f"{self._inp.swds_diversion_fraction:.0%} of throughput diverted from SWDS"
                ),
            )
        )

        # BE_EC: baseline electricity displacement
        be_ec = cdm_tool_05.baseline_electricity_emissions(
            electricity_mwh=electricity_generated_mwh,
            grid_ef_tco2_per_mwh=self._inp.grid_emission_factor_tco2_per_mwh,
            tdl_factor=self._inp.tdl_factor,
        )
        components.append(
            EmissionComponent(
                name="BE_EC (displaced grid electricity)",
                value_tco2e=be_ec,
                formula_ref="ACM0022 Eq.13 + Tool 05 Eq.2",
                notes=f"EF={self._inp.grid_emission_factor_tco2_per_mwh} tCO2/MWh ({self._inp.grid_emission_factor_source})",
            )
        )

        baseline_total = (be_ch4_total + be_ec) * (1 - self._inp.rate_compliance)

        # ========== PROJECT EMISSIONS ==========

        # PE_EC: electricity consumed from grid
        pe_ec = cdm_tool_05.project_electricity_emissions(
            electricity_consumed_mwh=self._inp.electricity_consumed_from_grid_mwh_per_year,
            grid_ef_tco2_per_mwh=self._inp.grid_emission_factor_tco2_per_mwh,
            tdl_factor=self._inp.tdl_factor,
        )
        components.append(
            EmissionComponent(
                name="PE_EC (grid electricity consumed)",
                value_tco2e=pe_ec,
                formula_ref="Tool 05 Eq.1",
            )
        )

        # PE_FC: fossil fuel combustion
        pe_fc = 0.0
        for ff in self._inp.fossil_fuels:
            pe_fc += cdm_tool_03.fossil_fuel_emissions(
                fuel_type=ff.fuel_type,
                annual_consumption_tonnes=ff.annual_consumption_tonnes,
                ncv_override=ff.ncv_override,
                ef_override=ff.ef_override,
            )
        components.append(
            EmissionComponent(
                name="PE_FC (fossil fuel combustion)",
                value_tco2e=pe_fc,
                formula_ref="Tool 03 Eq.1",
            )
        )

        # PE_CH4: methane leakage from AD
        pe_ch4 = cdm_tool_14.digester_methane_leakage(
            methane_produced_tonnes=annual_methane_tonnes,
            leakage_fraction=self._inp.methane_leakage_fraction,
        )
        components.append(
            EmissionComponent(
                name="PE_CH4 (AD methane leakage)",
                value_tco2e=pe_ch4,
                formula_ref="Tool 14 Eq.4",
                notes=f"leakage fraction={self._inp.methane_leakage_fraction}",
            )
        )

        # PE_FLARE: incomplete flare destruction
        methane_to_flare_tonnes = annual_methane_tonnes * self._inp.fraction_biogas_to_flare
        pe_flare = cdm_tool_06.flaring_emissions(
            methane_to_flare_tonnes=methane_to_flare_tonnes,
            flare_type=self._inp.flare_type,
        )
        components.append(
            EmissionComponent(
                name="PE_FLARE (incomplete flaring)",
                value_tco2e=pe_flare,
                formula_ref="Tool 06 Eq.15",
            )
        )

        project_total = pe_ec + pe_fc + pe_ch4 + pe_flare

        # ========== LEAKAGE ==========

        # LE_ENDUSE_RDF_SB: RDF exported off-site
        le_rdf = 0.0
        if self._inp.rdf_exported_tonnes_per_year > 0 and not self._inp.rdf_end_use_documented:
            le_rdf = (
                self._inp.rdf_exported_tonnes_per_year
                * self._inp.rdf_ncv_gj_per_tonne
                * self._inp.rdf_fossil_carbon_ef_tco2_per_gj
            )
        components.append(
            EmissionComponent(
                name="LE_RDF (RDF end-use)",
                value_tco2e=le_rdf,
                formula_ref="ACM0022 Eq.34",
                notes="documented end-use" if self._inp.rdf_end_use_documented else "undocumented",
            )
        )

        # LE_AD: digestate storage
        le_digestate = cdm_tool_14.digestate_storage_leakage(
            digestate_stored_anaerobically=self._inp.digestate_stored_anaerobically,
        )
        components.append(
            EmissionComponent(
                name="LE_AD (digestate storage)",
                value_tco2e=le_digestate,
                formula_ref="Tool 14 Eq.5",
            )
        )

        leakage_total = le_rdf + le_digestate

        # ========== NET EMISSION REDUCTIONS ==========
        net = baseline_total - project_total - leakage_total
        crediting_total = net * self._inp.crediting_period_years

        return ACM0022CalcResult(
            baseline_emissions_tco2e=baseline_total,
            project_emissions_tco2e=project_total,
            leakage_tco2e=leakage_total,
            net_emission_reductions_tco2e=net,
            crediting_period_total_tco2e=crediting_total,
            baseline_methane_swds_tco2e=be_ch4_total,
            baseline_electricity_tco2e=be_ec,
            project_electricity_consumption_tco2e=pe_ec,
            project_fossil_fuel_tco2e=pe_fc,
            project_methane_leakage_tco2e=pe_ch4,
            project_flaring_tco2e=pe_flare,
            leakage_rdf_combustion_tco2e=le_rdf,
            leakage_digestate_tco2e=le_digestate,
            organic_waste_to_ad_tonnes=organic_to_ad,
            annual_biogas_m3=annual_biogas_m3,
            annual_methane_m3=annual_methane_m3,
            annual_methane_tonnes=annual_methane_tonnes,
            electricity_generated_mwh=electricity_generated_mwh,
            components=components,
            calculation_year=self._inp.calculation_year,
            crediting_period_years=self._inp.crediting_period_years,
        )

    # ------------------------------------------------------------------
    # MethodologyEngine protocol implementation
    # ------------------------------------------------------------------

    def methodology_id(self) -> str:
        return "ACM0022"

    def validate_inputs(self, inputs: dict[str, Any]) -> ValidationResult:
        try:
            ACM0022CalcInput(**inputs)
            return ValidationResult(ok=True, errors=[])
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(ok=False, errors=[str(exc)])

    def _parse_inputs(self, inputs: dict[str, Any]) -> ACM0022CalcInput:
        return ACM0022CalcInput(**inputs)

    def _run_calc(self, inputs: dict[str, Any]) -> ACM0022CalcResult:
        return ACM0022Calculator(self._parse_inputs(inputs)).calculate()

    def compute_baseline(self, inputs: dict[str, Any]) -> ComputationResult:
        result = self._run_calc(inputs)
        return ComputationResult(
            value=result.baseline_emissions_tco2e,
            unit="tCO2e/year",
            formula="BE_y = (BE_CH4 + BE_EC) * (1 - RATE_compliance)",
            provenance=[
                {"param": "waste_streams", "source": "user_input"},
                {"param": "biomethanization_fraction", "source": "user_input"},
                {"param": "grid_emission_factor_tco2_per_mwh", "source": "user_input"},
            ],
            notes="FOD methane + displaced grid electricity, discounted for compliance",
        )

    def compute_project(self, inputs: dict[str, Any]) -> ComputationResult:
        result = self._run_calc(inputs)
        return ComputationResult(
            value=result.project_emissions_tco2e,
            unit="tCO2e/year",
            formula="PE_y = PE_EC + PE_FC + PE_CH4 + PE_FLARE",
            provenance=[
                {"param": "electricity_consumed_from_grid_mwh_per_year", "source": "user_input"},
                {"param": "fossil_fuels", "source": "user_input"},
                {"param": "methane_leakage_fraction", "source": "user_input"},
                {"param": "fraction_biogas_to_flare", "source": "user_input"},
            ],
            notes="Grid consumption, fossil fuel combustion, AD leakage, and incomplete flaring",
        )

    def compute_leakage(self, inputs: dict[str, Any]) -> ComputationResult:
        result = self._run_calc(inputs)
        return ComputationResult(
            value=result.leakage_tco2e,
            unit="tCO2e/year",
            formula="LE_y = LE_RDF + LE_AD",
            provenance=[
                {"param": "rdf_exported_tonnes_per_year", "source": "user_input"},
                {"param": "digestate_stored_anaerobically", "source": "user_input"},
            ],
            notes="RDF end-use and digestate storage leakage",
        )

    def compute_net(self, inputs: dict[str, Any]) -> ComputationResult:
        result = self._run_calc(inputs)
        return ComputationResult(
            value=result.net_emission_reductions_tco2e,
            unit="tCO2e/year",
            formula="ER_y = BE_y - PE_y - LE_y",
            provenance=[
                {
                    "param": "baseline_emissions",
                    "source": "calc_engine",
                    "value": result.baseline_emissions_tco2e,
                },
                {
                    "param": "project_emissions",
                    "source": "calc_engine",
                    "value": result.project_emissions_tco2e,
                },
                {
                    "param": "leakage_emissions",
                    "source": "calc_engine",
                    "value": result.leakage_tco2e,
                },
            ],
            notes="Net annual emission reductions before crediting-period scaling",
        )

    def required_monitoring_params(self, inputs: dict[str, Any]) -> list[dict]:
        return [
            {
                "id": "ACM0022-PARAM-01",
                "name": "Annual waste throughput",
                "unit": "tonnes/year",
                "frequency": "Continuously",
                "source": "Project records / weighbridge",
                "section_ref": "5.2",
            },
            {
                "id": "ACM0022-PARAM-02",
                "name": "Biogas methane concentration",
                "unit": "% CH4",
                "frequency": "Monthly or per batch",
                "source": "Gas composition analysis",
                "section_ref": "5.2",
            },
            {
                "id": "ACM0022-PARAM-03",
                "name": "Recovered electricity",
                "unit": "MWh/year",
                "frequency": "Continuously",
                "source": "Electricity metering",
                "section_ref": "5.2",
            },
            {
                "id": "ACM0022-PARAM-04",
                "name": "Grid emission factor",
                "unit": "tCO2e/MWh",
                "frequency": "Annual update",
                "source": "ACM0022 default or national grid authority",
                "section_ref": "4.1",
            },
        ]
