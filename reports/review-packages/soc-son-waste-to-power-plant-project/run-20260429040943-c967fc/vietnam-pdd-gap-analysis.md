# Vietnam PDD Gap Analysis

- Run ID: `run-20260429040943-c967fc`
- Project: `Soc Son waste to power plant project`
- Blocking review states: `36`
- Low/unsupported sections: `36`

## Missing Data That Most Reduced Confidence

- `quantification.project_emissions_tco2e_per_year` blocked=`True` hits=`8` sections=`1.10, 1.13, 3.4, 3.5, 4.1, 4.2, 4.4, 5.2` sources=`synthetic_assumption=8`
  Rationale: Workbook does not provide project emissions breakdown
  Fastest evidence add: Detailed GHG calculation workbook plus cited Vietnam grid-emission-factor source
- `quantification.baseline_emissions_tco2e_per_year` blocked=`True` hits=`7` sections=`1.10, 1.13, 3.4, 3.5, 4.1, 4.4, 5.2` sources=`synthetic_assumption=7`
  Rationale: Workbook only provides net annual emission reductions, so baseline split is unresolved
  Fastest evidence add: Detailed GHG calculation workbook plus cited Vietnam grid-emission-factor source
- `quantification.grid_emission_factor_source` blocked=`True` hits=`7` sections=`1.10, 1.13, 3.4, 3.5, 4.1, 4.4, 5.2` sources=`synthetic_assumption=7`
  Rationale: Official grid factor citation is not in workbook
  Fastest evidence add: Detailed GHG calculation workbook plus cited Vietnam grid-emission-factor source
- `location.latitude` blocked=`True` hits=`6` sections=`1.11, 1.12, 1.13, 1.18, 3.3, 3.4` sources=`synthetic_assumption=6`
  Rationale: Workbook does not contain coordinates
  Fastest evidence add: Site coordinates, landfill map, and project permit drawings
- `location.longitude` blocked=`True` hits=`6` sections=`1.11, 1.12, 1.13, 1.18, 3.3, 3.4` sources=`synthetic_assumption=6`
  Rationale: Workbook does not contain coordinates
  Fastest evidence add: Site coordinates, landfill map, and project permit drawings
- `monitoring.parameters_monitored` blocked=`True` hits=`3` sections=`5.1, 5.2, 5.3` sources=`synthetic_assumption=3`
  Rationale: Workbook does not include monitoring plan details
  Fastest evidence add: Monitoring plan, metering SOPs, and equipment calibration records
- `safeguards.no_net_harm_statement` blocked=`True` hits=`2` sections=`2.1, 2.5` sources=`synthetic_assumption=2`
  Rationale: Workbook does not include safeguards documentation
  Fastest evidence add: EIA package, stakeholder consultation records, and safeguards evidence
- `technology.installed_capacity_mw` blocked=`False` hits=`14` sections=`1.1, 1.10, 1.11, 1.13, 1.15, 1.18, 1.3, 1.4, 3.2, 3.4, 3.5, 4.3, 5.1, 5.2` sources=`synthetic_assumption=14`
  Rationale: Installed MW is not present, estimated from annual generation using 85% capacity factor
  Fastest evidence add: Technical datasheet, EPC summary, and plant operating design documents
- `technology.tip_fee_usd_per_tonne` blocked=`False` hits=`12` sections=`1.10, 1.11, 1.13, 1.18, 1.3, 1.4, 3.2, 3.4, 3.5, 4.3, 5.1, 5.2` sources=`demo_default=12`
  Rationale: Reused conservative demo placeholder until commercial inputs are confirmed
  Fastest evidence add: Technical datasheet, EPC summary, and plant operating design documents
- `location.landfill_latitude` blocked=`False` hits=`8` sections=`1.11, 1.12, 1.13, 1.18, 3.3, 3.4, 4.1, 4.3` sources=`synthetic_assumption=8`
  Rationale: Baseline landfill coordinates are missing from the workbook
  Fastest evidence add: Site coordinates, landfill map, and project permit drawings
- `location.landfill_longitude` blocked=`False` hits=`8` sections=`1.11, 1.12, 1.13, 1.18, 3.3, 3.4, 4.1, 4.3` sources=`synthetic_assumption=8`
  Rationale: Baseline landfill coordinates are missing from the workbook
  Fastest evidence add: Site coordinates, landfill map, and project permit drawings
- `quantification.grid_emission_factor` blocked=`False` hits=`8` sections=`1.10, 1.13, 3.4, 3.5, 4.1, 4.4, 5.1, 5.2` sources=`demo_default=8`
  Rationale: Conservative placeholder reused from existing Vietnam demo config
  Fastest evidence add: Detailed GHG calculation workbook plus cited Vietnam grid-emission-factor source
- `compliance_and_ownership.credit_ownership_statement` blocked=`False` hits=`7` sections=`1.13, 1.14, 1.15, 1.16, 1.7, 3.4, 3.5` sources=`synthetic_assumption=7`
  Rationale: Workbook does not contain executed ownership language
  Fastest evidence add: Executed ownership, sponsor, and carbon-rights documentation
- `location.city` blocked=`False` hits=`7` sections=`1.1, 1.11, 1.12, 1.13, 1.18, 3.3, 3.4` sources=`demo_default=7`
  Rationale: Soc Son alignment with existing demo and local template naming
  Fastest evidence add: Site coordinates, landfill map, and project permit drawings
- `location.region` blocked=`False` hits=`7` sections=`1.1, 1.11, 1.12, 1.13, 1.18, 3.3, 3.4` sources=`demo_default=7`
  Rationale: Soc Son is located in Hanoi in the existing repo demo path
  Fastest evidence add: Site coordinates, landfill map, and project permit drawings
- `project.other_entities` blocked=`False` hits=`4` sections=`1.11, 1.18, 1.6, 3.5` sources=`synthetic_assumption=4`
  Rationale: Workbook omits partner entities
  Fastest evidence add: Executed ownership, sponsor, and carbon-rights documentation
- `project.ownership` blocked=`False` hits=`4` sections=`1.11, 1.18, 1.7, 3.5` sources=`synthetic_assumption=4`
  Rationale: Workbook omits ownership wording
  Fastest evidence add: Executed ownership, sponsor, and carbon-rights documentation
- `project.proponent_contact_email` blocked=`False` hits=`4` sections=`1.11, 1.18, 1.5, 3.5` sources=`synthetic_assumption=4`
  Rationale: Workbook does not include contact details
  Fastest evidence add: Executed ownership, sponsor, and carbon-rights documentation
- `project.proponent_name` blocked=`False` hits=`4` sections=`1.11, 1.18, 1.5, 3.5` sources=`synthetic_assumption=4`
  Rationale: Workbook does not identify legal proponent name
  Fastest evidence add: Executed ownership, sponsor, and carbon-rights documentation
- `monitoring.data_management` blocked=`False` hits=`3` sections=`5.1, 5.2, 5.3` sources=`synthetic_assumption=3`
  Rationale: Workbook does not include data-management details
  Fastest evidence add: Monitoring plan, metering SOPs, and equipment calibration records
- `safeguards.environmental_impact_assessment` blocked=`False` hits=`2` sections=`2.3, 2.5` sources=`synthetic_assumption=2`
  Rationale: Workbook does not evidence an EIA
  Fastest evidence add: EIA package, stakeholder consultation records, and safeguards evidence

## Highest-Leverage External Documents

- `Site coordinates, landfill map, and project permit drawings` impact=`42`
- `Detailed GHG calculation workbook plus cited Vietnam grid-emission-factor source` impact=`30`
- `Technical datasheet, EPC summary, and plant operating design documents` impact=`26`
- `Executed ownership, sponsor, and carbon-rights documentation` impact=`23`
- `Monitoring plan, metering SOPs, and equipment calibration records` impact=`6`
- `EIA package, stakeholder consultation records, and safeguards evidence` impact=`4`

## Current Blocking Review States

- 1.1: Needs Domain Review
- 1.2: Needs Domain Review
- 1.3: Needs Domain Review
- 1.4: Needs Domain Review
- 1.5: Needs Domain Review
- 1.6: Needs Domain Review
- 1.7: Needs Domain Review
- 1.8: Needs Domain Review
- 1.9: Needs Domain Review
- 1.10: Needs Domain Review
- 1.11: Needs Domain Review
- 1.12: Needs Domain Review
- 1.13: Needs Domain Review
- 1.14: Needs Domain Review
- 1.15: Needs Domain Review
- 1.16: Needs Domain Review
- 1.17: Needs Domain Review
- 1.18: Needs Domain Review
- 2.1: Needs Domain Review
- 2.2: Needs Domain Review
- 2.3: Needs Domain Review
- 2.4: Needs Domain Review
- 2.5: Needs Domain Review
- 3.1: Needs Domain Review
- 3.2: Needs Domain Review
- 3.3: Needs Domain Review
- 3.4: Needs Domain Review
- 3.5: Needs Domain Review
- 3.6: Needs Domain Review
- 4.1: Needs Domain Review
- 4.2: Needs Domain Review
- 4.3: Needs Domain Review
- 4.4: Needs Domain Review
- 5.1: Needs Domain Review
- 5.2: Needs Domain Review
- 5.3: Needs Domain Review
