"""Pydantic input/output models for ACM0022 emission calculations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WasteStream(BaseModel):
    """A single waste stream entering the project."""

    waste_type: str = Field(..., description="Waste type key matching constants.DOC_BY_WASTE_TYPE")
    annual_tonnes: float = Field(..., gt=0, description="Annual waste input (tonnes/year)")
    doc_override: float | None = Field(None, ge=0, le=1, description="Override DOC fraction")
    decay_rate_override: float | None = Field(
        None, gt=0, description="Override decay rate k (1/year)"
    )


class FossilFuelInput(BaseModel):
    """Fossil fuel consumption by the project."""

    fuel_type: str = Field(..., description="Fuel type key matching constants.FOSSIL_FUEL_EF")
    annual_consumption_tonnes: float = Field(
        ..., ge=0, description="Annual consumption (tonnes/year)"
    )
    ncv_override: float | None = Field(None, gt=0, description="Override NCV (GJ/tonne)")
    ef_override: float | None = Field(None, gt=0, description="Override emission factor (tCO2/GJ)")


class ACM0022CalcInput(BaseModel):
    """All inputs needed for an ACM0022 emission reduction calculation."""

    # Waste inputs
    waste_streams: list[WasteStream] = Field(
        ..., min_length=1, description="Waste streams entering the project"
    )
    biomethanization_fraction: float = Field(
        ...,
        ge=0,
        le=1,
        description="Fraction of incoming waste suitable for biomethanization",
    )
    swds_diversion_fraction: float = Field(
        1.0,
        ge=0,
        le=1,
        description=(
            "Fraction of incoming waste diverted from a solid waste disposal site. "
            "Drives BE_CH4 (avoided landfill methane). Distinct from "
            "biomethanization_fraction, which drives only the anaerobic digestion "
            "pathway (biogas, PE_CH4, LE_AD)."
        ),
    )

    # Biogas / energy parameters
    biogas_yield_m3_per_tonne: float = Field(
        130.0,
        gt=0,
        description="Biogas yield (Nm3 biogas per tonne organic waste fed to AD)",
    )
    methane_fraction_biogas: float = Field(
        0.56, gt=0, le=1, description="Volume fraction of CH4 in biogas"
    )
    engine_electrical_efficiency: float = Field(
        0.41, gt=0, le=1, description="Gas engine electrical efficiency"
    )
    electricity_exported_mwh_per_year: float | None = Field(
        None,
        ge=0,
        description="Monitored net electricity export (MWh/year); if None, estimated from biogas",
    )
    electricity_consumed_from_grid_mwh_per_year: float = Field(
        0.0, ge=0, description="Grid electricity consumed by the project (MWh/year)"
    )

    # Grid emission factor
    grid_emission_factor_tco2_per_mwh: float = Field(
        ..., gt=0, description="Grid emission factor (tCO2/MWh)"
    )
    grid_emission_factor_source: str = Field(..., description="Source of grid emission factor")
    tdl_factor: float = Field(
        0.0,
        ge=0,
        le=0.3,
        description="Transmission and distribution loss factor (fraction)",
    )

    # Baseline SWDS parameters
    baseline_methane_captured_fraction: float = Field(
        0.0,
        ge=0,
        le=1,
        description="Fraction of methane captured at baseline SWDS (f_y)",
    )
    mcf: float = Field(1.0, gt=0, le=1, description="Methane correction factor")
    oxidation_factor: float = Field(0.0, ge=0, le=0.2, description="Oxidation factor (OX)")
    model_correction_factor: float = Field(
        0.9, gt=0, le=1, description="Model correction factor (φ)"
    )
    doc_f: float = Field(0.5, gt=0, le=1, description="Fraction of DOC that decomposes")
    f_ch4: float = Field(0.5, gt=0, le=1, description="Fraction of CH4 in SWDS gas (volume)")
    rate_compliance: float = Field(
        0.0,
        ge=0,
        le=1,
        description="Regulatory compliance discount factor",
    )

    # Project emission parameters
    fossil_fuels: list[FossilFuelInput] = Field(
        default_factory=list, description="Fossil fuels consumed by the project"
    )
    methane_leakage_fraction: float = Field(
        0.05,
        ge=0,
        le=1,
        description="Fraction of methane produced that leaks from AD (EF_CH4,default)",
    )
    flare_type: str = Field("open", description="Flare type: 'open' (50%) or 'enclosed' (90%)")
    fraction_biogas_to_flare: float = Field(
        0.0,
        ge=0,
        le=1,
        description="Fraction of total biogas sent to flare (vs engines)",
    )

    # Leakage
    rdf_exported_tonnes_per_year: float = Field(
        0.0, ge=0, description="RDF exported off-site (tonnes/year)"
    )
    rdf_ncv_gj_per_tonne: float = Field(
        10.5, gt=0, description="Net calorific value of RDF (GJ/tonne)"
    )
    rdf_fossil_carbon_ef_tco2_per_gj: float = Field(
        0.0, ge=0, description="CO2 emission factor for fossil carbon in RDF (tCO2/GJ)"
    )
    rdf_end_use_documented: bool = Field(
        False, description="True if documented evidence of RDF end-use (CDM project/combustion)"
    )
    digestate_stored_anaerobically: bool = Field(
        False, description="True if digestate is stored under anaerobic conditions"
    )

    # Crediting period
    crediting_period_years: int = Field(..., ge=1, le=30, description="Crediting period in years")
    calculation_year: int = Field(
        1,
        ge=1,
        le=30,
        description="Which year of the crediting period to calculate for (affects FOD model)",
    )


class EmissionComponent(BaseModel):
    """A single emission source with its value and provenance."""

    name: str
    value_tco2e: float
    formula_ref: str = Field("", description="ACM0022/Tool equation reference")
    notes: str = ""


class ACM0022CalcResult(BaseModel):
    """Structured output from an ACM0022 emission reduction calculation."""

    # Summary values
    baseline_emissions_tco2e: float = Field(
        ..., description="Total baseline emissions (tCO2e/year)"
    )
    project_emissions_tco2e: float = Field(..., description="Total project emissions (tCO2e/year)")
    leakage_tco2e: float = Field(..., description="Total leakage (tCO2e/year)")
    net_emission_reductions_tco2e: float = Field(
        ..., description="Net = baseline - project - leakage (tCO2e/year)"
    )
    crediting_period_total_tco2e: float = Field(..., description="Net × crediting years (tCO2e)")

    # Decomposed baseline
    baseline_methane_swds_tco2e: float = Field(
        ..., description="BE_CH4: methane from SWDS (FOD model)"
    )
    baseline_electricity_tco2e: float = Field(
        ..., description="BE_EN/BE_EC: displaced grid electricity"
    )

    # Decomposed project emissions
    project_electricity_consumption_tco2e: float = Field(
        ..., description="PE_EC: grid electricity consumed"
    )
    project_fossil_fuel_tco2e: float = Field(..., description="PE_FC: fossil fuel combustion")
    project_methane_leakage_tco2e: float = Field(..., description="PE_CH4: methane leakage from AD")
    project_flaring_tco2e: float = Field(..., description="PE_FLARE: incomplete flare destruction")

    # Decomposed leakage
    leakage_rdf_combustion_tco2e: float = Field(
        ..., description="LE_ENDUSE_RDF: RDF end-use leakage"
    )
    leakage_digestate_tco2e: float = Field(..., description="LE_AD: digestate storage leakage")

    # Intermediate values for audit
    organic_waste_to_ad_tonnes: float = Field(
        ..., description="Annual organic waste fed to AD (tonnes/year)"
    )
    annual_biogas_m3: float = Field(..., description="Annual biogas production (Nm3/year)")
    annual_methane_m3: float = Field(..., description="Annual methane production (Nm3/year)")
    annual_methane_tonnes: float = Field(..., description="Annual methane production (tonnes/year)")
    electricity_generated_mwh: float = Field(
        ..., description="Gross electricity from biogas (MWh/year)"
    )

    # Component breakdown for full audit trail
    components: list[EmissionComponent] = Field(default_factory=list)

    # Metadata
    methodology_version: str = "ACM0022 v3.0"
    calculation_year: int = 1
    crediting_period_years: int = 7
