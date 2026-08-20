"""Pydantic models for structured project facts — the input contract for PDD drafting.

All fields are required unless marked Optional.
A completed and validated instance of ProjectInput is the prerequisite for section drafting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from pdd_agent.calc.models import ACM0022CalcResult


class AuditHistoryEntry(BaseModel):
    audit_type: str = Field(..., description="e.g. validation, verification")
    period: str = Field(..., description="Audit period string")
    program: str = Field(..., description="e.g. VCS")
    vvb_name: str = Field(..., description="Validation/Verification Body name")
    number_of_years: int = Field(..., ge=1, description="Number of years covered")


class ProjectIdentity(BaseModel):
    project_name: str = Field(
        ..., min_length=1, description="Official project name as registered or intended"
    )
    project_id_vcs: str | None = Field(
        None, description="VCS project ID once registered (e.g. VCS-XXXX)"
    )
    proponent_name: str = Field(
        ..., min_length=1, description="Legal entity name of project proponent"
    )
    proponent_contact_email: str = Field(..., description="Primary contact email for the proponent")
    other_entities: list[str] = Field(
        default_factory=list, description="Names of other entities involved in the project"
    )
    ownership: str = Field(..., description="Ownership structure description")
    vcs_standard_version: str | None = Field(
        None, description="VCS Standard version (e.g. v4.4, v4.7)"
    )
    prepared_by: str | None = Field(
        None, description="Entity that prepared the project description"
    )
    audit_history: list[AuditHistoryEntry] = Field(
        default_factory=list, description="List of audit/verification history entries"
    )


class Coordinate(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class ProjectLocation(BaseModel):
    country: str = Field(..., min_length=1, description="ISO 3166-1 country name or alpha-2 code")
    region: str = Field(..., min_length=1, description="Province, state, or region")
    city: str = Field(..., min_length=1, description="City or municipal area")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Decimal degrees, WGS84")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Decimal degrees, WGS84")
    landfill_latitude: float | None = Field(
        None,
        ge=-90.0,
        le=90.0,
        description="Baseline landfill GPS latitude if landfill diversion is part of the claim",
    )
    landfill_longitude: float | None = Field(
        None, ge=-180.0, le=180.0, description="Baseline landfill GPS longitude if applicable"
    )
    site_area_m2: float | None = Field(None, gt=0, description="Site area in square meters")
    grid_connection_point: str | None = Field(
        None, description="Grid connection substation or point"
    )
    boundary_coordinates: list[Coordinate] = Field(
        default_factory=list, description="List of GPS coordinates defining project boundary"
    )


class ProjectDates(BaseModel):
    start_date: str = Field(..., description="Project start date ISO 8601 (YYYY-MM-DD)")
    crediting_period_start: str = Field(..., description="Crediting period start date ISO 8601")
    crediting_period_years: int = Field(
        ..., ge=1, le=30, description="Crediting period duration in years (typically 10 for WTE)"
    )
    project_scale_small: bool = Field(
        False,
        description="True if project qualifies as small-scale under the applicable methodology",
    )


class EngineEntry(BaseModel):
    model: str = Field(..., description="Engine model identifier")
    commissioning_date: str | None = Field(None, description="Commissioning date ISO 8601")


class RDFCapacity(BaseModel):
    max_capacity_tph: float | None = Field(
        None, ge=0, description="Maximum RDF production capacity in tonnes per hour"
    )
    planned_2024_tpd: float | None = Field(
        None, ge=0, description="Planned RDF production in 2024 in tonnes per day"
    )
    planned_2035_tpd: float | None = Field(
        None, ge=0, description="Planned RDF production in 2035 in tonnes per day"
    )


class CookstoveFleetEntry(BaseModel):
    """A single improved-cookstove cohort for AMS-II.G quantification."""

    fuel_type: str = Field(..., description="Baseline fuel type (e.g. wood, charcoal)")
    stove_count: int = Field(..., gt=0, description="Number of stoves / households")
    baseline_fuel_kg_per_day_per_stove: float = Field(
        ..., gt=0, description="Baseline fuel consumption per stove per day (kg/day)"
    )
    project_fuel_kg_per_day_per_stove: float = Field(
        ..., gt=0, description="Improved-stove fuel consumption per stove per day (kg/day)"
    )
    operating_days_per_year: int = Field(365, ge=1, le=366)
    ncv_mj_per_kg: float = Field(..., gt=0, description="Net calorific value (MJ/kg)")
    ef_kg_co2_per_mj: float = Field(..., gt=0, description="Fuel CO2 emission factor (kg CO2/MJ)")
    fnrb: float = Field(..., ge=0.0, le=1.0, description="Non-renewable biomass fraction")


class RiceCultivationParams(BaseModel):
    """Rice-cultivation inputs for VM0051 quantification."""

    area_ha: float = Field(..., gt=0, description="Cultivated rice area (ha)")
    cultivation_days: int = Field(..., ge=1, le=366, description="Flooded/cultivated days per year")
    baseline_water_regime: str = Field("continuously_flooded", description="Baseline water regime")
    baseline_ef_kg_ch4_per_ha_per_day: float = Field(
        1.30, gt=0, description="Baseline CH4 emission factor (kg CH4/ha/day)"
    )
    project_practices: list[dict] = Field(
        default_factory=list,
        description="Project practices with keys: practice, scaling_factor (optional)",
    )
    gwp_ch4: float = Field(28.0, gt=0, description="Methane GWP")


class BiocharProductionParams(BaseModel):
    """Biochar production inputs for VM0044 quantification."""

    feedstock_type: str = Field(..., description="Feedstock type (e.g. wood_chip, rice_husk)")
    dry_mass_tonnes: float = Field(..., gt=0, description="Dry feedstock mass per year (tonnes)")
    carbon_fraction: float = Field(..., gt=0, le=1, description="Carbon fraction of dry feedstock")
    pyrolysis_temperature_c: float = Field(..., gt=0, description="Pyrolysis peak temperature (°C)")
    stability_factor: float | None = Field(
        None, gt=0, le=1, description="Optional measured stability fraction"
    )
    permanence_factor: float = Field(
        1.0, ge=0, le=1, description="Discount for uncertainty / reversibility risk"
    )


class WasteFraction(BaseModel):
    waste_type: str = Field(..., min_length=1, description="Key into DOC_BY_WASTE_TYPE")
    mass_fraction: float = Field(
        ..., ge=0.0, le=1.0, description="Share of annual_waste_throughput, dimensionless 0-1"
    )
    source: str = Field(..., min_length=1, description="Where this fraction was published")


class ProjectTechnology(BaseModel):
    methodology_ids: list[str] = Field(
        ..., min_length=1, description="VCS methodology IDs (e.g. [ACM0022, ACM0003])"
    )
    technology_type: Literal[
        "anaerobic_digestion",
        "incineration_with_energy_recovery",
        "landfill_gas_capture",
        "refuse_derived_fuel",
        "mechanical_biological_treatment",
        "combined_wte_ad",
        "improved_cookstoves",
        "rice_awd",
        "biochar_production",
        "other",
    ] = Field(..., description="Primary project technology")
    waste_type: list[str] = Field(
        ...,
        min_length=1,
        description="Types of waste processed (e.g. [municipal_solid_waste, kitchen_waste])",
    )
    annual_waste_throughput: float = Field(
        ..., gt=0, description="Annual waste throughput in tonnes per year"
    )
    installed_capacity_mw: float = Field(
        ..., ge=0, description="Installed electricity generation capacity in MW"
    )
    energy_generation_mwh_year: float | None = Field(
        None, gt=0, description="Annual net electricity generation in MWh/year (if known)"
    )
    tip_fee_usd_per_tonne: float | None = Field(
        None, ge=0, description="Tipping fee in USD/tonne of waste (if applicable)"
    )
    landfill_diversion_claim: bool = Field(
        False, description="True if the project claims credits for landfill diversion"
    )
    fuel_substitution_claim: bool = Field(
        False,
        description="True if the project claims credits for fossil fuel displacement (cement / industrial fuel substitution)",
    )
    gas_engine_commissioning: list[EngineEntry] = Field(
        default_factory=list, description="List of gas engines with commissioning dates"
    )
    rdf_capacity: RDFCapacity | None = Field(
        None, description="RDF production capacity and planned production"
    )
    biomethanization_suitable_fraction: float | None = Field(
        None, ge=0, le=1, description="Fraction of waste suitable for biomethanization (0-1)"
    )
    waste_composition: list[WasteFraction] = Field(
        default_factory=list,
        description=(
            "Published waste-composition split. When non-empty it replaces the "
            "even split across waste_type. Fractions may sum to less than 1.0 — "
            "inert mass generates no landfill methane and is legitimately omitted."
        ),
    )
    capacity_ramp: list[float] | None = Field(
        None,
        description=(
            "Optional per-crediting-period-year capacity utilisation, dimensionless "
            "0-1, index 0 = year 1. Reserved for a future ramp-aware baseline; "
            "validated but not yet consumed by the calc engine."
        ),
    )
    cookstove_fleet: list[CookstoveFleetEntry] | None = Field(
        None, description="Cookstove cohorts for AMS-II.G projects"
    )
    rice_cultivation: RiceCultivationParams | None = Field(
        None, description="Rice cultivation params for VM0051 projects"
    )
    biochar_production: BiocharProductionParams | None = Field(
        None, description="Biochar production params for VM0044 projects"
    )

    @model_validator(mode="after")
    def validate_waste_composition(self) -> "ProjectTechnology":
        if self.waste_composition:
            total = sum(entry.mass_fraction for entry in self.waste_composition)
            if total > 1.0 + 1e-9:
                raise ValueError(
                    f"waste_composition mass fractions sum to {total:.4f}, which exceeds 1.0"
                )
        if self.capacity_ramp is not None:
            for idx, value in enumerate(self.capacity_ramp):
                if not 0.0 <= value <= 1.0:
                    raise ValueError(f"capacity_ramp[{idx}] value {value} is outside [0.0, 1.0]")
        return self


class MethodologyApplicability(BaseModel):
    eligibility_checklist: dict[str, bool] = Field(
        ...,
        description="Mapping of methodology applicability condition name to True (met) / False (not met). "
        "Keys must match conditions in the methodology document exactly.",
    )
    deviation_from_methodology: str | None = Field(
        None,
        description="Describe any deviations from the methodology, or None if no deviations.",
    )


class QuantificationInputs(BaseModel):
    baseline_emissions_tco2e_per_year: float | None = Field(
        None, ge=0, description="Estimated annual baseline emissions in tCO2e/year"
    )
    project_emissions_tco2e_per_year: float | None = Field(
        None, ge=0, description="Estimated annual project emissions in tCO2e/year"
    )
    leakage_tco2e_per_year: float | None = Field(
        0.0, ge=0, description="Estimated annual leakage in tCO2e/year"
    )
    net_emissions_tco2e_per_year: float | None = Field(
        None, description="Net annual emission reductions = Baseline - Project - Leakage"
    )
    grid_emission_factor: float | None = Field(
        None, gt=0, description="Grid emission factor in tCO2e/MWh (from official source)"
    )
    grid_emission_factor_source: str | None = Field(
        None,
        description="Source of grid emission factor (e.g. ACM0022 default, national grid authority, regional grid operator)",
    )
    methane_capture_rate: float | None = Field(
        None, ge=0, le=1, description="Methane capture rate at baseline landfill (fraction, 0-1)"
    )
    methane_generation_factor: float | None = Field(
        None,
        gt=0,
        description="Methano-genesis factor for landfill baseline (tonnes CH4/tonne waste)",
    )
    crediting_period_total_tco2e: float | None = Field(
        None, description="Total estimated credits over the crediting period (net × years)"
    )

    @classmethod
    def from_calc_result(cls, result: "ACM0022CalcResult") -> "QuantificationInputs":
        """Populate from an ACM0022CalcResult, preserving provenance."""
        return cls(
            baseline_emissions_tco2e_per_year=result.baseline_emissions_tco2e,
            project_emissions_tco2e_per_year=result.project_emissions_tco2e,
            leakage_tco2e_per_year=result.leakage_tco2e,
            net_emissions_tco2e_per_year=result.net_emission_reductions_tco2e,
            grid_emission_factor=None,
            grid_emission_factor_source=None,
            crediting_period_total_tco2e=result.crediting_period_total_tco2e,
        )


class MonitoringPlan(BaseModel):
    parameters_monitored: list[dict] = Field(
        ...,
        description="List of monitoring plan parameter dicts with keys: name, unit, frequency, method, data_source",
    )
    monitoring_equipment: list[str] = Field(
        default_factory=list,
        description="List of monitoring equipment or metering systems installed",
    )
    data_management: str = Field(
        ...,
        description="Description of how monitoring data is recorded, stored, and quality-controlled",
    )


class SafeguardsEvidence(BaseModel):
    no_net_harm_statement: str = Field(
        ..., description="Statement confirming no net harm analysis completed"
    )
    stakeholder_consultation_completed: bool = Field(
        False, description="True if stakeholder consultation was performed"
    )
    stakeholder_consultation_date: str | None = Field(
        None, description="Date of stakeholder consultation ISO 8601"
    )
    environmental_impact_assessment: bool = Field(
        False, description="True if EIA has been completed"
    )
    eia_reference: str | None = Field(None, description="EIA document reference or permit number")


class ComplianceAndOwnership(BaseModel):
    no_participation_other_programs: bool = Field(
        True, description="Confirm no participation in other GHG programs"
    )
    no_other_forms_of_credit: bool = Field(
        True, description="Confirm no other carbon credits claimed for the same emissions"
    )
    other_ghg_programs: list[str] = Field(
        default_factory=list, description="List of other GHG programs if applicable"
    )
    credit_ownership_statement: str = Field(
        ..., description="Statement of who owns the credits produced by this project"
    )
    double_counting_risk: bool = Field(
        False,
        description="True if the project combines landfill diversion and fuel substitution — requires explicit credit ownership delineation",
    )


class SustainableDevelopment(BaseModel):
    sd_contributions: list[str] = Field(
        default_factory=list,
        description="List of sustainable development contributions (e.g. SDG goals)",
    )
    sd_comments: str | None = Field(
        None, description="Additional comments on sustainable development"
    )


class EvidenceItem(BaseModel):
    """A single evidence reference for the evidence registry."""

    evidence_id: str = Field(..., description="Unique evidence ID (e.g. E001, E002)")
    source_type: Literal[
        "corpus",
        "methodology",
        "user_input",
        "calc_engine",
        "registry",
        "synthetic",
        "expert_judgment",
    ] = Field(..., description="Type of evidence source")
    description: str = Field(..., description="What this evidence supports")
    document_ref: str | None = Field(None, description="Document name or path")
    section_ref: str | None = Field(None, description="Section ID where evidence applies")
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field("MEDIUM", description="Confidence level")


class EvidenceRegistry(BaseModel):
    """Registry of all evidence items cited in the PDD draft."""

    items: list[EvidenceItem] = Field(default_factory=list)

    def next_id(self) -> str:
        return f"E{len(self.items) + 1:03d}"

    def add(self, source_type: str, description: str, **kwargs) -> str:
        eid = self.next_id()
        self.items.append(
            EvidenceItem(
                evidence_id=eid, source_type=source_type, description=description, **kwargs
            )
        )
        return eid

    def by_section(self, section_id: str) -> list[EvidenceItem]:
        return [item for item in self.items if item.section_ref == section_id]


class GenerationControls(BaseModel):
    """Controls for LLM-based section generation."""

    provider_name: str = Field(
        "noop", description="LLM provider to use (noop, demo, openai, ollama)"
    )
    model_name: str = Field("gpt-4o", description="Model name for the provider")
    max_tokens_per_section: int = Field(
        4000, ge=100, le=16000, description="Max tokens per section draft"
    )
    temperature: float = Field(0.1, ge=0.0, le=1.0, description="LLM temperature")
    token_budget: int = Field(500_000, ge=1000, description="Total token budget for the run")
    token_warning_threshold: float = Field(
        0.8, ge=0.0, le=1.0, description="Budget warning threshold"
    )
    use_v2_prompt: bool = Field(
        True, description="Use v2 prompt template with anti-hallucination markers"
    )
    inject_calc_results: bool = Field(
        True, description="Inject ACM0022 calc results into Section 4 prompts"
    )
    inject_corpus_retrieval: bool = Field(
        True, description="Inject FTS5/BM25 corpus retrieval into prompts"
    )
    max_corpus_examples: int = Field(5, ge=0, le=20, description="Max corpus examples per section")
    max_corpus_chars: int = Field(1500, ge=0, le=5000, description="Max chars per corpus example")


class ReviewFlags(BaseModel):
    """Flags controlling review gates and quality thresholds."""

    require_evidence_for_high: bool = Field(
        True, description="HIGH sensitivity sections require at least one evidence citation"
    )
    require_expert_for_critical: bool = Field(
        True, description="CRITICAL sections require domain expert sign-off"
    )
    block_on_missing_markers: bool = Field(
        True, description="Block finalization if [MISSING] markers remain"
    )
    max_inference_ratio: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Max fraction of content that can be [INFERENCE]-tagged before review gate triggers",
    )
    auto_flag_synthetic: bool = Field(
        True, description="Automatically flag sections using synthetic assumptions"
    )


class SuggestedMethodology(BaseModel):
    """A methodology suggestion from the screening module."""

    methodology_id: str = Field(..., description="Methodology ID (e.g. ACM0022, AM0025)")
    name: str = Field(..., description="Full methodology name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    rationale: str = Field(..., description="Why this methodology was suggested")
    active_status_source: str = Field(
        "verra_registry", description="Source confirming methodology is active"
    )
    version: str | None = Field(None, description="Latest methodology version (e.g. v3.0)")


class ExtractionProvenance(BaseModel):
    """Tracks which fields came from extraction vs defaults vs [MISSING]."""

    extracted_fields: list[str] = Field(
        default_factory=list, description="Fields successfully extracted from document"
    )
    defaulted_fields: list[str] = Field(default_factory=list, description="Fields set to defaults")
    missing_fields: list[str] = Field(default_factory=list, description="Fields marked [MISSING]")
    source_document: str | None = Field(None, description="Path or name of source document")
    extraction_model: str | None = Field(None, description="LLM model used for extraction")


class ProjectInput(BaseModel):
    """Root model — a fully populated instance represents one complete project input set."""

    project: ProjectIdentity
    location: ProjectLocation
    dates: ProjectDates
    technology: ProjectTechnology
    methodology_applicability: MethodologyApplicability
    quantification: QuantificationInputs
    monitoring: MonitoringPlan
    safeguards: SafeguardsEvidence
    compliance_and_ownership: ComplianceAndOwnership
    sustainable_development: SustainableDevelopment
    generation_controls: GenerationControls | None = Field(
        None, description="LLM generation controls (optional)"
    )
    review_flags: ReviewFlags | None = Field(None, description="Review gate flags (optional)")
    evidence_registry: EvidenceRegistry | None = Field(
        None, description="Evidence registry for citation tracking (optional)"
    )
    suggested_methodologies: list[SuggestedMethodology] | None = Field(
        None, description="Methodology suggestions from screening (optional)"
    )
    extraction_provenance: ExtractionProvenance | None = Field(
        None, description="Provenance tracking for document extraction (optional)"
    )

    @field_validator("technology", mode="before")
    @classmethod
    def validate_technology_combinations(cls, v):
        if isinstance(v, dict):
            fuel = v.get("fuel_substitution_claim", False)
            diversion = v.get("landfill_diversion_claim", False)
            if fuel and diversion:
                raise ValueError(
                    "CRITICAL: Project claims BOTH landfill diversion and fuel substitution. "
                    "This creates a double-counting risk. You must clearly delineate which credits "
                    "belong to which activity, referencing separate methodology IDs (ACM0022 for "
                    "diversion, ACM0003 for fuel substitution)."
                )
        return v

    @field_validator("quantification")
    @classmethod
    def validate_net_emissions(cls, v):
        net = v.net_emissions_tco2e_per_year
        baseline = v.baseline_emissions_tco2e_per_year
        project = v.project_emissions_tco2e_per_year
        leakage = v.leakage_tco2e_per_year
        # Skip validation if any key value is None (TBD / incomplete input)
        if net is None or baseline is None or project is None or leakage is None:
            return v
        if net < 0:
            raise ValueError(f"Net emissions cannot be negative: got {net}")
        expected_net = baseline - project - leakage
        if abs(net - expected_net) > 0.01:
            raise ValueError(
                f"Net emissions ({net}) does not match "
                f"baseline ({baseline}) - project ({project}) - leakage ({leakage}) = {expected_net}. "
                f"Check calculation."
            )
        return v

    def summary(self) -> str:
        net = self.quantification.net_emissions_tco2e_per_year
        net_str = f"{net:,.0f}" if net is not None else "TBD"
        return (
            f"Project: {self.project.project_name}\n"
            f"  Country: {self.location.country}\n"
            f"  Methodology: {', '.join(self.technology.methodology_ids)}\n"
            f"  Technology: {self.technology.technology_type}\n"
            f"  Capacity: {self.technology.installed_capacity_mw} MW\n"
            f"  Annual waste: {self.technology.annual_waste_throughput:,.0f} tonnes\n"
            f"  Net tCO2e/year: {net_str}\n"
            f"  Crediting period: {self.dates.crediting_period_years} years\n"
        )
