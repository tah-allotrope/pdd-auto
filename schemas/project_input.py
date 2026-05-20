"""Pydantic models for structured project facts — the input contract for PDD drafting.

All fields are required unless marked Optional.
A completed and validated instance of ProjectInput is the prerequisite for section drafting.
"""

from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator


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
    site_area_m2: float | None = Field(
        None, gt=0, description="Site area in square meters"
    )
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
    max_capacity_tph: float | None = Field(None, ge=0, description="Maximum RDF production capacity in tonnes per hour")
    planned_2024_tpd: float | None = Field(None, ge=0, description="Planned RDF production in 2024 in tonnes per day")
    planned_2035_tpd: float | None = Field(None, ge=0, description="Planned RDF production in 2035 in tonnes per day")


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
        "other",
    ] = Field(..., description="Primary waste treatment / energy recovery technology")
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
