---
title: "PDD Pipeline Upgrade to Audit-Ready Completeness"
date: "2026-06-22"
status: "superseded — PHASE-01..03 fully implemented (29/29 tasks); the explicitly deferred PHASE-04 registry-API work now lives in plans/2026-07-12-pdd-reality-gap-plan.md (PHASE-05 downloader, delivered) and plans/2026-07-23-run-real-model-proof-plan.md (PHASE-04 live search-API capture)."
request: "Based on research and brainstorm reports, create a multi-phase implementation plan to upgrade pdd-auto from demo-quality to audit-ready PDD generation"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-06-22_carbon-pdd-barriers-automation.md"
  - "research/2026-06-22_pdd-pipeline-upgrade-brainstorm.md"
  - "docs/2026-06-15-tinh-track-vs-repo-comparison.md"
---

# Plan: PDD Pipeline Upgrade to Audit-Ready Completeness

## Objective

Transform pdd-auto from a demo-quality pipeline (NoopProvider placeholders, no emission calculations, spreadsheet-only intake) into the first open-source tool that generates audit-ready Verra VCS Project Design Documents. The target: Hang opens the pipeline-generated Seraphin PDD and says "this is ready for VVB desk review." This matters now because the $2.6B VVB bottleneck and 4.8 GtCO2 issuance gap represent a wide-open market opportunity with zero open-source competitors (research brief, 277 sources).

## Context Snapshot

- **Current state:** Production-quality Python pipeline with corpus RAG (FTS5/BM25), Pydantic schema (60+ fields), rule-based methodology checks (ACM0022/ACM0003), 5-state review workflow, DOCX export on Verra v4.4 template, two demos (Soc Son, Inegol), and 218 passing tests. But: no real emission calculations, no real LLM drafting, spreadsheet-only intake, hardcoded methodology rules, no registry API integration.
- **Desired state:** Pipeline generates an audit-ready PDD for WTE projects: real ACM0022 emission numbers, LLM-drafted prose with evidence citations and anti-hallucination discipline, all VCS v4.4 sections populated, monitoring plan, methodology screening. Output is DOCX + PDF + web preview. Ready for VVB desk review.
- **Key repo surfaces:**
  - `schemas/project_input.py` — QuantificationInputs (lines 161-192), ProjectTechnology (lines 101-147)
  - `src/pdd_agent/llm/provider.py` — BaseProvider, ProviderRegistry, ModelConfig, NoopProvider, DemoProvider
  - `src/pdd_agent/llm/openai_provider.py` — 52-line stub returning `[OPENAI STUB]`
  - `src/pdd_agent/agent/section_orchestrator.py` — provider injection, retrieval, prompt assembly, review gates
  - `src/pdd_agent/domain/methodology_rules.py` — MethodologyRules class (YAML loader)
  - `rules/verra/wte_methodology_rules.yaml` — ACM0022/ACM0003 rules (4 params each)
  - `src/pdd_agent/retrieval/search.py` — FTS5/BM25 corpus search (DEFAULT_K=5, MAX_K=50)
  - `prompts/section_draft.md` — current 117-line drafting prompt
  - `src/pdd_agent/export/docx_export.py` — 11 structured table renderers, template-based export
  - `src/pdd_agent/review/consistency.py` — quantitative cross-checks, ACM0022 required params
  - `src/pdd_agent/phase06/spreadsheet_mapper.py` — current Vietnam WtE Excel intake
  - `src/pdd_agent/ingest/normalize.py` — corpus normalization pipeline
- **Out of scope:**
  - Non-WTE methodologies beyond ACM0022 (methodology screening suggests them but does not calculate)
  - Automated stakeholder consultation / FPIC documentation (regulatory hard stop)
  - Multi-language support (VCS standard is English)
  - Mobile/web UI (CLI-driven for internal team)
  - Article 6 / CORSIA compliance (future scope)
  - Registry API integration (deferred until Verra next-gen API lands)

## Research Inputs

- **research/2026-06-22_carbon-pdd-barriers-automation.md** — Establishes the market context: $100K-$400K per PDD, 6-36 month timelines, VVB $2.6B delay costs by 2030, 4.8 GtCO2 issuance gap, zero open-source PDD generators, Verst Carbon as sole competitor (closed-source). Confirms quantification as #1 technical blocker. Identifies regulatory constraints on what can/cannot be automated (CON-001, CON-002). Validates the 40-70% cost reduction potential of Digital MRV.
- **research/2026-06-22_pdd-pipeline-upgrade-brainstorm.md** — 15 resolved design decisions (DEC-001 through DEC-015) covering primary user (internal team), success bar (audit-ready), calc engine (pure Python), LLM provider (OpenAI GPT-4), document intake (Tinh's extraction prompt), methodology screening (Verra active list + LLM), RAG strategy (top-k corpus injection), prompt style (Tinh's authority order), phasing (quantification first), test data (both projects + synthetic), output format (DOCX + PDF + web preview), schema merge (ProjectInput canonical), cost guardrails (per-run token budget), validation target (Seraphin), and timeline (4-6 weeks).
- **docs/2026-06-15-tinh-track-vs-repo-comparison.md** — Maps the complementary capabilities of Tinh's Codex track vs the pipeline. Identifies three capabilities to absorb: document-to-YAML intake, methodology screening, and production-grade LLM drafting prompt. Confirms the shared gap: no emission calculation engine on either track.

## Assumptions and Constraints

- **ASM-001:** ACM0022 methodology text and CDM tools (Tool 03, 04, 05, 07, 12) are publicly available from the UNFCCC CDM website and can be implemented in Python without licensing issues.
- **ASM-002:** Tinh's prompt artifacts (`Create_YAML_From_Project_Summary_Prompt.txt`, `PDD creation prompt.txt`, `Schema_ver1.yaml`) are available from the shared Drive folder `Registered WTE PDD`.
- **ASM-003:** Seraphin project data (from Hang's Jun 9 inputs) will be available for acceptance testing. Inegol (already in repo) is the primary validation target until then.
- **ASM-004:** OpenAI API access with GPT-4 is available and budgeted for internal development/testing.
- **ASM-005:** The existing 218 tests must continue to pass throughout all phases (zero regressions).
- **CON-001:** VVBs require deterministic, reproducible calculations. LLM-generated emission numbers are unacceptable for quantification sections. The calc engine must be pure Python with Pydantic I/O.
- **CON-002:** Independent third-party validation, stakeholder consultation/FPIC, and legal ownership checks cannot be automated and remain manual processes.
- **CON-003:** The Verra VCS v4.4 template DOCX is the required output format for registry submission.
- **CON-004:** PDF conversion depends on local converter availability (LibreOffice CLI); make it optional with a clear skip message.
- **DEC-001:** Primary user is the internal Allotrope team (Tung, Hang, Tinh).
- **DEC-002:** Success bar is audit-ready completeness — ready for VVB desk review.
- **DEC-003:** ACM0022 quantification as a pure Python engine with Pydantic I/O models.
- **DEC-004:** First real LLM provider is OpenAI GPT-4 via existing OpenAIProvider stub.
- **DEC-014:** Seraphin WTE project is the acceptance test. Pipeline-generated PDD approved by Hang = validated.

## Phase Summary

| Phase | Goal | Dependencies | Duration | Primary outputs |
|---|---|---|---|---|
| PHASE-01 | ACM0022 pure Python calc engine | None | ~2 weeks | `src/pdd_agent/calc/acm0022.py`, Pydantic calc models, 40+ unit tests, Inegol validation |
| PHASE-02 | Wire OpenAI GPT-4 + Tinh's prompt discipline + RAG injection | PHASE-01 | ~2 weeks | Real `OpenAIProvider`, new prompt template, corpus-grounded drafting, token budget |
| PHASE-03 | Document intake + methodology screening | PHASE-02 | ~1-2 weeks | LLM extraction pipeline, methodology matching, schema extensions |
| PHASE-04 | Registry API integration | PHASE-03 + Verra API availability | Deferred | Verra API client, automated project registration status checks |

## Detailed Phases

---

### PHASE-01 — ACM0022 Pure Python Calculation Engine

**Goal**
Build a deterministic, auditable ACM0022 emission calculation engine that derives baseline, project, and leakage emissions from activity data. This is the #1 blocker identified by Hang's Jun 11 review ("calculations currently show no results for baseline or project emissions") and affects both the pipeline and Codex tracks.

**Tasks**

- [x] TASK-01-01: Define Pydantic input model `ACM0022CalcInput` with all required activity data fields
  - Waste throughput (tonnes/year)
  - Biogas methane concentration (fraction, 0-1)
  - Recovered electricity (MWh/year)
  - Grid emission factor (tCO2e/MWh) + source
  - Methane generation potential / waste composition parameters
  - Methane capture efficiency
  - Plant capacity factor and operating hours
  - CDM Tool 03 parameters (default values for common waste compositions)
  - CDM Tool 04 parameters (grid emission factor decomposition: OM + BM)
  - CDM Tool 05 parameters (baseline scenario identification inputs)

- [x] TASK-01-02: Define Pydantic output model `ACM0022CalcResult` with structured results
  - Baseline emissions (tCO2e/year) — decomposed by source (methane avoidance, displaced grid electricity)
  - Project emissions (tCO2e/year) — decomposed by source (combustion, auxiliary power, transport)
  - Leakage emissions (tCO2e/year) — with per-source breakdown
  - Net emission reductions (tCO2e/year) = baseline - project - leakage
  - Crediting period total (tCO2e) — net * crediting years
  - Per-parameter provenance (source, assumption flag, uncertainty)
  - Calculation metadata (methodology version, tool versions used, timestamp)

- [x] TASK-01-03: Implement the core calculation engine `ACM0022Calculator`
  - `calculate_baseline()` — methane avoidance from waste diversion + displaced grid electricity
  - `calculate_project()` — direct combustion emissions + auxiliary energy + transport
  - `calculate_leakage()` — upstream/downstream effects per ACM0022 boundary
  - `calculate_net_reductions()` — orchestrator calling all three + net
  - Each function returns intermediate values for audit trail
  - All formulas referenced to ACM0022 v03.0 paragraph numbers

- [x] TASK-01-04: Implement CDM Tool integrations as helper modules
  - `cdm_tool_03.py` — default emission factors for waste types (Table 1, Table 2)
  - `cdm_tool_04.py` — grid emission factor calculation (combined margin = OM * w_OM + BM * w_BM)
  - `cdm_tool_07.py` — emission factor for fossil fuel displacement
  - `cdm_tool_12.py` — baseline identification for WTE projects
  - Verified implementation inventory also retains Tools 05, 06, and 14 used by the ACM0022 calculator.

- [x] TASK-01-05: Wire calc results into `QuantificationInputs` in `schemas/project_input.py`
  - Add a `from_calc_result(result: ACM0022CalcResult) -> QuantificationInputs` class method
  - Populate `baseline_emissions_tco2e_per_year`, `project_emissions_tco2e_per_year`, `leakage_tco2e_per_year`, `net_emissions_tco2e_per_year`, `crediting_period_total_tco2e`
  - Preserve provenance metadata for each populated field

- [x] TASK-01-06: Update `rules/verra/wte_methodology_rules.yaml` with calculation-level rules
  - Add formula references (ACM0022 equations by number)
  - Add parameter validity ranges per CDM tools
  - Add cross-check rules (e.g., net reductions must be positive, baseline > project)

- [x] TASK-01-07: Update `src/pdd_agent/review/consistency.py` to cross-check calc results
  - Validate that Section 4 (quantification) numbers match calc engine output
  - Flag if any emission component is zero when the methodology expects non-zero
  - Compare grid emission factor against known country-level ranges

- [x] TASK-01-08: Write unit tests for the calculation engine (~95 tests)
  - Test each formula function independently with known inputs/outputs
  - Test CDM tool helper functions
  - Test edge cases: zero waste throughput, 100% methane capture, extreme grid factors
  - Test that `ACM0022CalcResult` round-trips through Pydantic serialization

- [x] TASK-01-09: Validate against Inegol reference project (VCS-3908, already in repo)
  - Extract Inegol's known emission parameters from `data/corpus/normalized/`
  - Run the calc engine with Inegol inputs
  - Compare output against published VCS-3908 emission reductions
  - Document any discrepancies and their sources

- [x] TASK-01-10: Add synthetic edge-case test fixtures
  - Small-scale project (< 10,000 tCO2e/year)
  - Large-scale project (> 500,000 tCO2e/year)
  - High leakage scenario (leakage > 10% of baseline)
  - Zero grid emission factor edge case
  - Multiple waste stream compositions

**Files / Surfaces**

- `src/pdd_agent/calc/` (new directory) — all calculation modules
- `src/pdd_agent/calc/__init__.py` — package init
- `src/pdd_agent/calc/acm0022.py` — core ACM0022 calculator
- `src/pdd_agent/calc/models.py` — `ACM0022CalcInput`, `ACM0022CalcResult` Pydantic models
- `src/pdd_agent/calc/cdm_tool_03.py` — waste type default emission factors
- `src/pdd_agent/calc/cdm_tool_04.py` — grid emission factor calculation
- `src/pdd_agent/calc/cdm_tool_07.py` — fossil fuel displacement factors
- `src/pdd_agent/calc/cdm_tool_12.py` — baseline identification
- `schemas/project_input.py` — add `from_calc_result()` to QuantificationInputs (line ~192)
- `rules/verra/wte_methodology_rules.yaml` — extend with formula references
- `src/pdd_agent/review/consistency.py` — extend cross-checks for calc results
- `tests/test_acm0022_calc.py` — unit tests for the calculator
- `tests/test_cdm_tools.py` — unit tests for CDM tool helpers
- `tests/test_calc_integration.py` — Inegol validation + edge cases

**Dependencies**
- None (this phase is the foundation)

**Exit Criteria**
- [x] `ACM0022Calculator.calculate()` produces non-zero emission reductions for Inegol inputs
- [x] Inegol calc results are in plausible range (positive net, baseline > project, leakage = 0 for aerobic digestate)
- [x] All 95 new tests pass (exceeded 40+ target)
- [x] All 218 existing tests still pass (313 total, zero regressions)
- [x] `ACM0022CalcResult` includes per-component provenance via `EmissionComponent.formula_ref`
- [x] Each formula is traceable to a specific ACM0022 v03.0 / CDM Tool equation number

**Phase Risks**
- **RISK-01-01:** ACM0022 methodology text may be ambiguous on certain formula parameters (e.g., methane correction factor by waste type). *Mitigation:* Cross-reference CDM Tool 03 default values; document assumptions explicitly; validate against Inegol as ground truth.
- **RISK-01-02:** Inegol published data may not include enough intermediate values for full validation. *Mitigation:* Use synthetic edge cases plus Seraphin data (when available) for additional validation coverage.
- **RISK-01-03:** CDM Tool 04 grid emission factor calculation requires country-specific data that may not be readily available. *Mitigation:* Implement with configurable data sources; provide IGES default factors as fallback; accept user-provided values.

---

### PHASE-02 — Wire OpenAI GPT-4 + Prompt Discipline + RAG Injection

**Goal**
Replace the stub `OpenAIProvider` with a real implementation, adopt Tinh's prompt discipline (authority order, evidence citations, anti-hallucination markers), and wire the existing FTS5/BM25 retrieval system into the drafting prompt. This turns shallow placeholder prose into audit-grade section drafts grounded in corpus evidence and real emission numbers from Phase 1.

**Tasks**

- [x] TASK-02-01: Implement real `OpenAIProvider` in `src/pdd_agent/llm/openai_provider.py`
  - Replace the 52-line stub with actual OpenAI API calls
  - Use `openai` Python SDK (async-compatible)
  - Implement `draft_section()` with proper request/response handling
  - Support `ModelConfig` parameters: model_name, api_key, base_url, max_tokens, temperature
  - Return `DraftSection` with populated confidence, provenance, issues, and provider fields
  - Handle API errors gracefully (rate limits, token limits, network errors)
  - Add retry logic with exponential backoff (max 3 retries)

- [x] TASK-02-02: Implement per-run token budget and cost tracking (DEC-013)
  - Create `src/pdd_agent/llm/budget.py` with `TokenBudget` class
  - Configurable limit (default 500K tokens per run)
  - Track input/output tokens per call
  - 80% warning threshold (log warning, continue)
  - 100% hard-stop (raise `BudgetExhaustedError`, no more LLM calls)
  - Per-run cost logging (input/output token counts, estimated cost at current pricing)
  - Budget summary in the run's metadata output

- [x] TASK-02-03: Adopt Tinh's prompt discipline — replace `prompts/section_draft.md`
  - Create new `prompts/section_draft_v2.md` based on Tinh's `PDD creation prompt.txt`
  - Authority order: (1) input YAML/ProjectInput, (2) evidence registry / corpus chunks, (3) VCS v4.4 template rules, (4) official methodology/tools, (5) comparable project examples, (6) general domain logic
  - Anti-hallucination markers: `[MISSING]` for data not provided, `[INFERENCE]` for derived claims, `[REVIEW REQUIRED]` for expert-check items
  - Evidence-ID citations: `[E001]`, `[E002]` referencing corpus chunks by retrieval ID
  - Per-section review notes as structured sidecar output
  - Content class annotations from existing prompt (BOILERPLATE, FACTUAL, EVIDENCE_BASED, METHODOLOGY_DEPENDENT, QUANTITATIVE, NARRATIVE, OPTIONAL)
  - Keep existing citation formats (CORPUS, METHODOLOGY, VERRA REGISTRY, USER INPUT, SYNTHETIC ASSUMPTION) and add Tinh's `[E001]` format as primary

- [x] TASK-02-04: Wire FTS5/BM25 retrieval into `draft_section()` call path (DEC-007)
  - Modify `SectionOrchestrator._assemble_prompt()` to inject top-k corpus chunks
  - For each section being drafted, query `search.py` with section-specific terms
  - Use configurable k (default 5, from `DEFAULT_K` in `search.py`)
  - Format retrieved chunks with source attribution (document name, section, BM25 score)
  - Include retrieval metadata in `DraftSection.provenance`

- [x] TASK-02-05: Wire Phase-1 calc results into quantification section prompts
  - When drafting Section 4 (Quantification), inject `ACM0022CalcResult` into the prompt context
  - The LLM drafts the narrative around the numbers (it does not generate the numbers)
  - Prompt instructs the LLM to use exact calc values, never approximate or round
  - Include formula references from the calc engine's provenance metadata

- [x] TASK-02-06: Update `SectionOrchestrator` to use new prompt and provider
  - Modify `section_orchestrator.py` to load `section_draft_v2.md` as the prompt template
  - Pass corpus chunks and calc results as template variables
  - Parse structured output (section text + review notes + evidence register)
  - Feed review notes into the existing 5-state review workflow

- [x] TASK-02-07: Extend `schemas/project_input.py` with Tinh's schema additions (DEC-012)
  - Add `GenerationControls` Pydantic model (inferable/non-inferable field lists, missing-info policy, citation policy)
  - Add `ReviewFlags` Pydantic model (per-field review status)
  - Add `EvidenceRegistry` Pydantic model (evidence items with IDs, sources, confidence)
  - Add these as optional nested fields on `ProjectInput`
  - Preserve backward compatibility — all new fields are `Optional` with `None` default

- [x] TASK-02-08: Add PDF export capability (DEC-011)
  - Create `src/pdd_agent/export/pdf_export.py`
  - Use LibreOffice CLI (`soffice --convert-to pdf`) if available
  - Make PDF generation optional with clear skip message if LibreOffice not found
  - Add `--pdf` flag to CLI

- [x] TASK-02-09: Write integration tests for LLM drafting pipeline
  - Test `OpenAIProvider.draft_section()` with mocked API responses
  - Test prompt assembly with corpus injection
  - Test token budget enforcement (warning at 80%, stop at 100%)
  - Test that quantification sections use calc results, not LLM-generated numbers
  - Test fallback behavior when corpus has no relevant chunks

- [x] TASK-02-10: End-to-end test: generate a complete PDD draft for Inegol
  - Run the full pipeline: calc engine + LLM drafting + review + DOCX export
  - Verify all 30+ subsections are populated (no `[PLACEHOLDER]` text)
  - Verify emission numbers in Section 4 match Phase-1 calc output exactly
  - Verify evidence citations reference actual corpus documents
  - Verify DOCX output renders correctly on the v4.4 template

**Files / Surfaces**

- `src/pdd_agent/llm/openai_provider.py` — replace stub with real implementation
- `src/pdd_agent/llm/budget.py` (new) — token budget tracking
- `prompts/section_draft_v2.md` (new) — Tinh's prompt discipline adapted
- `prompts/section_draft.md` — kept as fallback reference (not deleted)
- `src/pdd_agent/agent/section_orchestrator.py` — wire corpus + calc + new prompt
- `schemas/project_input.py` — add GenerationControls, ReviewFlags, EvidenceRegistry
- `src/pdd_agent/export/pdf_export.py` (new) — optional PDF conversion
- `tests/test_openai_provider.py` (new) — provider tests with mocked API
- `tests/test_token_budget.py` (new) — budget enforcement tests
- `tests/test_prompt_assembly.py` (new) — prompt template + corpus injection tests
- `tests/test_e2e_inegol_draft.py` (new) — end-to-end Inegol PDD generation

**Dependencies**
- PHASE-01 complete (calc results needed for quantification section prompts)
- OpenAI API key available in environment (`OPENAI_API_KEY`)
- `openai` Python package added to project dependencies

**Exit Criteria**
- [ ] `OpenAIProvider.draft_section()` returns real prose (not stubs) for all VCS v4.4 sections
- [ ] Each drafted section includes evidence citations (`[E001]`, `[E002]`) referencing corpus chunks
- [ ] Quantification section (Section 4) contains exact values from `ACM0022CalcResult`, not LLM approximations
- [ ] Anti-hallucination markers (`[MISSING]`, `[INFERENCE]`, `[REVIEW REQUIRED]`) appear where appropriate
- [ ] Token budget enforcement works: warning at 80%, hard-stop at 100%
- [ ] Per-run cost log shows input/output token counts
- [ ] DOCX export produces a complete document with all sections populated
- [ ] PDF export works when LibreOffice is available; graceful skip when not
- [ ] All new tests pass; all 218 + Phase-1 tests still pass

**Phase Risks**
- **RISK-02-01:** GPT-4 output quality may not meet audit-ready standard without extensive prompt iteration. *Mitigation:* Start with Tinh's proven prompt (already tested on Seraphin draft); iterate based on Hang's review feedback; the prompt template is a separate file that can be tuned without code changes.
- **RISK-02-02:** Token budget may be too tight for full 30-section PDD generation. *Mitigation:* Default 500K is generous (~250 pages of output); make it configurable; log actual usage to calibrate.
- **RISK-02-03:** OpenAI API rate limits may slow down end-to-end generation. *Mitigation:* Sequential section drafting (not parallel) avoids rate limits; add configurable delay between calls; retry with backoff.

---

### PHASE-03 — Document Intake + Methodology Screening

**Goal**
Add two capabilities the pipeline currently lacks: (1) extract structured `ProjectInput` from arbitrary documents (Word/PDF/text) using Tinh's extraction prompt, and (2) screen project descriptions against Verra's active methodology list to suggest applicable methodologies with confidence scores. These unlock fast onboarding of new projects beyond the Vietnam spreadsheet workflow.

**Tasks**

- [x] TASK-03-01: Implement LLM-based document extraction pipeline
  - Create `src/pdd_agent/ingest/extract.py`
  - Accept input: file path (DOCX, PDF, plain text) or raw text string
  - Extract text from DOCX (python-docx) and PDF (existing ingest capabilities)
  - Send extracted text to OpenAI GPT-4 with Tinh's `Create_YAML_From_Project_Summary_Prompt.txt` adapted as the extraction prompt
  - Parse LLM output (structured YAML) into `ProjectInput` Pydantic model
  - Handle encoding issues (mojibake, Turkish characters) per Tinh's prompt rules
  - Return `ProjectInput` with provenance metadata (which fields came from extraction vs defaults)

- [x] TASK-03-02: Create the extraction prompt template
  - Create `prompts/extract_project_input.md` based on Tinh's `Create_YAML_From_Project_Summary_Prompt.txt`
  - Map output schema to `ProjectInput` Pydantic model fields (not Tinh's `Schema_ver1.yaml`)
  - Include Tinh's non-invention rules and `[MISSING]` handling
  - Include methodology screening output fields (`suggested_methodologies` with confidence)
  - Include evidence registry output fields

- [x] TASK-03-03: Implement methodology screening module
  - Create `src/pdd_agent/domain/methodology_screen.py`
  - Load Verra active VCS methodology list (initially hardcoded from VCS website, with clear path to API-based refresh)
  - Load CDM methodology list (ACM series relevant to WTE/waste/energy)
  - Accept project description text and extracted `ProjectInput`
  - Use LLM to match project activity against methodology applicability conditions
  - Return ranked `SuggestedMethodology` list: methodology_id, name, confidence (0-1), rationale, active_status_source
  - Flag when the user's selected methodology doesn't match the top suggestion

- [x] TASK-03-04: Create methodology data files
  - `data/methodologies/verra_vcs_active.json` — VCS methodologies with IDs, names, applicability conditions, status
  - `data/methodologies/cdm_active.json` — CDM methodologies relevant to WTE (ACM0022, ACM0003, ACM0006, AM0025, etc.)
  - Include methodology version numbers and last-updated dates
  - Document the refresh process for when new methodologies are added

- [x] TASK-03-05: Add `SuggestedMethodology` Pydantic model to schema
  - Add to `schemas/project_input.py` as a new model
  - Add `suggested_methodologies: list[SuggestedMethodology] | None` to `ProjectInput`
  - Include fields: methodology_id, name, confidence, rationale, active_status_source, version

- [x] TASK-03-06: Create CLI commands for new intake paths
  - Add `pdd-agent extract <file>` command — runs extraction and prints `ProjectInput` summary
  - Add `pdd-agent screen <file-or-input>` command — runs methodology screening
  - Add `pdd-agent draft --from-doc <file>` command — full pipeline from document to DOCX

- [x] TASK-03-07: Write tests for document extraction
  - Test extraction from DOCX, PDF, and plain text inputs
  - Test that extracted `ProjectInput` has expected fields populated for a known document
  - Test `[MISSING]` handling for documents with incomplete information
  - Test encoding fix rules (mojibake, special characters)
  - Use mocked LLM responses for unit tests; one real API call for integration test

- [x] TASK-03-08: Write tests for methodology screening
  - Test screening against known WTE project descriptions → should rank ACM0022 highest
  - Test screening against non-WTE descriptions → should not suggest ACM0022
  - Test confidence scores are in valid range (0-1)
  - Test handling of unknown/novel project types

- [x] TASK-03-09: Integration test: document → PDD draft end-to-end
  - Start from a raw project description document (use Inegol's original PDD text)
  - Extract → screen → calculate → draft → review → export DOCX
  - Verify the output PDD is comparable to the demo-generated Inegol PDD

**Files / Surfaces**

- `src/pdd_agent/ingest/extract.py` (new) — LLM-based document extraction
- `prompts/extract_project_input.md` (new) — extraction prompt template
- `src/pdd_agent/domain/methodology_screen.py` (new) — methodology screening
- `data/methodologies/verra_vcs_active.json` (new) — VCS methodology list
- `data/methodologies/cdm_active.json` (new) — CDM methodology list
- `schemas/project_input.py` — add SuggestedMethodology model
- `src/pdd_agent/cli.py` or equivalent — add extract/screen/draft-from-doc commands
- `tests/test_extract.py` (new) — extraction pipeline tests
- `tests/test_methodology_screen.py` (new) — screening tests
- `tests/test_e2e_doc_to_pdd.py` (new) — end-to-end document intake test

**Dependencies**
- PHASE-02 complete (extraction and screening use OpenAI GPT-4 provider)
- Tinh's prompt artifacts available from shared Drive folder (ASM-002)
- `python-docx` already in project dependencies

**Exit Criteria**
- [ ] `extract.py` produces a valid `ProjectInput` from a sample project description document
- [ ] Methodology screening correctly ranks ACM0022 as top suggestion for WTE projects
- [ ] `pdd-agent draft --from-doc <file>` produces a complete DOCX PDD from a raw document
- [ ] Extraction provenance shows which fields were extracted vs defaulted vs marked `[MISSING]`
- [ ] All new tests pass; all existing + Phase-1 + Phase-2 tests still pass

**Phase Risks**
- **RISK-03-01:** LLM extraction quality depends heavily on input document format and completeness. *Mitigation:* Include robust `[MISSING]` handling; the extraction prompt explicitly marks what it couldn't find; human review of extracted `ProjectInput` before proceeding to draft.
- **RISK-03-02:** Verra methodology list may be incomplete or stale by the time this phase ships. *Mitigation:* Document the refresh process; make methodology data files easily updatable; the screening module logs its data version.
- **RISK-03-03:** Tinh's extraction prompt may need adaptation to map onto `ProjectInput` rather than `Schema_ver1.yaml`. *Mitigation:* Start with minimal adaptation (per Q-002 recommended default); iterate based on output quality.

---

### PHASE-04 — Registry API Integration (Deferred)

**Goal**
Integrate with Verra's next-gen registry API (and potentially Gold Standard Digital MRV) to automate project registration status checks, methodology list refreshes, and project data retrieval. This phase is deferred until the Verra + S&P Global next-gen registry API is publicly available (Phase 1 expected early 2026, per research brief).

**Tasks**

- [ ] [DEFERRED] TASK-04-01: Monitor Verra API availability and documentation
  - Track Verra + S&P Global registry modernization announcements
  - Track Gold Standard Digital MRV Pilot progress (through Oct 2026)
  - Document API endpoints, authentication, and rate limits when available

- [ ] [DEFERRED] TASK-04-02: Implement Verra API client
  - Create `src/pdd_agent/registry/verra_client.py`
  - Project registration status lookup
  - Active methodology list retrieval (replaces hardcoded JSON files from Phase 3)
  - Project data retrieval for validation
  - Authentication and rate limit handling

- [ ] [DEFERRED] TASK-04-03: Implement automated methodology list refresh
  - Replace `data/methodologies/verra_vcs_active.json` with API-backed refresh
  - Cache locally with TTL
  - Log version changes

- [ ] [DEFERRED] TASK-04-04: Add project registration status to PDD workflow
  - Check if project is already registered/listed on Verra
  - Pull existing project data for pre-population
  - Validate against registry constraints

**Files / Surfaces**

- `src/pdd_agent/registry/` (new directory) — registry API clients
- `src/pdd_agent/registry/verra_client.py` — Verra API integration
- `data/methodologies/` — transition from static to API-backed with cache

**Dependencies**
- PHASE-03 complete
- Verra next-gen registry API publicly available with documentation
- API credentials provisioned

**Exit Criteria**
- [ ] Methodology list auto-refreshes from Verra API
- [ ] Project registration status is checked before PDD generation
- [ ] API client handles rate limits and authentication gracefully

**Phase Risks**
- **RISK-04-01:** Verra API may not provide the endpoints needed for full integration. *Mitigation:* This phase is deferred precisely because the API is not yet available; scope will be refined when documentation is published.
- **RISK-04-02:** API rate limits may be restrictive. *Mitigation:* Local caching with TTL; batch requests where possible.

---

## Verification Strategy

**Automated Tests**
- **TEST-001:** `pytest tests/test_acm0022_calc.py` — all ACM0022 formula unit tests pass
- **TEST-002:** `pytest tests/test_cdm_tools.py` — all CDM tool helper tests pass
- **TEST-003:** `pytest tests/test_calc_integration.py` — Inegol validation within 10% of published values
- **TEST-004:** `pytest tests/test_openai_provider.py` — OpenAI provider returns real drafts (mocked API)
- **TEST-005:** `pytest tests/test_token_budget.py` — budget enforcement at 80%/100% thresholds
- **TEST-006:** `pytest tests/test_prompt_assembly.py` — corpus chunks injected into prompt
- **TEST-007:** `pytest tests/test_extract.py` — document extraction produces valid ProjectInput
- **TEST-008:** `pytest tests/test_methodology_screen.py` — ACM0022 ranked top for WTE
- **TEST-009:** `pytest` (full suite) — all existing 218 tests still pass at every phase boundary

**Manual Validation**
- **MANUAL-001:** After Phase 1 — review Inegol calc results against published VCS-3908 data with Hang
- **MANUAL-002:** After Phase 2 — generate a complete Inegol PDD DOCX and have Hang review prose quality, citation accuracy, and section completeness
- **MANUAL-003:** After Phase 2 — generate Seraphin PDD (when data available) and submit for Hang's desk-review assessment
- **MANUAL-004:** After Phase 3 — test document intake with a raw project description not in the corpus

**Observability**
- **OBS-001:** Per-run token usage and cost logs — review after each Phase 2/3 test run to calibrate budget
- **OBS-002:** Calc engine provenance logs — every calculation step traceable to formula + input values

## Risks and Alternatives

- **RISK-001:** Seraphin project data may not arrive during the 4-6 week timeline. *Mitigation:* Inegol is the primary validation target; Seraphin is the acceptance test. If Seraphin data is delayed, validate against Inegol + synthetic cases and add Seraphin as a follow-up.
- **RISK-002:** OpenAI API costs may exceed budget during development/testing. *Mitigation:* Token budget with per-run caps (DEC-013); use DemoProvider for unit tests; reserve real API calls for integration tests and manual reviews.
- **RISK-003:** The pipeline may produce PDDs that look complete but contain subtle methodology errors only a VVB would catch. *Mitigation:* Hang's expert review is the gate; the calc engine is deterministic and auditable; anti-hallucination markers flag uncertain content explicitly.
- **ALT-001:** Spreadsheet-backed calculation (Hang's WtE Excel model via openpyxl). *Not chosen:* Creates opaque dependency on a specific Excel file, not version-controllable, calculation logic hidden in cell formulas, harder to test and audit (DEC-003).
- **ALT-002:** LLM-assisted calculation. *Not chosen:* Non-deterministic, VVBs will not accept LLM-generated emission numbers, cannot reproduce exact results across runs (CON-001).
- **ALT-003:** Build custom extraction pipeline instead of adopting Tinh's prompt. *Not chosen:* Duplicates proven work; Tinh's prompt already handles Word/PDF/text/OCR with methodology screening and evidence registry (DEC-005).
- **ALT-004:** All-at-once sprint for all upgrades simultaneously. *Not chosen:* Too much parallel risk; sequential phasing allows each phase to build on validated foundations; quantification is prerequisite for everything else (DEC-009).

## Grill Me

1. **Q-001:** What specific Seraphin project data is available from Hang's Jun 9 inputs — and is there a calculation spreadsheet or emission reduction estimate we can validate against?
   - **Recommended default:** Start with Inegol as the primary validation target; add Seraphin data as it becomes available. Don't block Phase 1 on Seraphin data.
   - **Why this matters:** The calc engine needs at least one real-world reference project with known-correct emission numbers to validate against.
   - **If answered differently:** If Seraphin data is available now, it becomes the Phase 1 validation target alongside Inegol, which strengthens confidence but may slow down Phase 1 if data is incomplete.

2. **Q-002:** Does Tinh's extraction prompt need adaptation before adoption, or can we use it as-is with only schema-mapping changes?
   - **Recommended default:** Use as-is for initial integration, then iterate based on output quality. The prompts are well-designed; the gap is in mapping their output to our `ProjectInput` schema.
   - **Why this matters:** If significant prompt rework is needed, Phase 3 timeline shifts by 1-2 weeks.
   - **If answered differently:** If major rework is needed, Phase 3 expands to ~3 weeks and may need its own prompt iteration sub-phase.

3. **Q-003:** Is LibreOffice available on team machines for PDF conversion, or should we use a different converter?
   - **Recommended default:** Use LibreOffice CLI (`soffice --convert-to pdf`) if available; make PDF generation optional with clear skip message if not.
   - **Why this matters:** DEC-011 calls for DOCX + PDF + web preview. PDF conversion needs a local tool.
   - **If answered differently:** If wkhtmltopdf or another tool is preferred, adjust `pdf_export.py` accordingly; the interface stays the same.

## Suggested Next Step

Answer the Grill Me questions (or accept the recommended defaults), then begin Phase 1 implementation: define the `ACM0022CalcInput` and `ACM0022CalcResult` Pydantic models, implement the core calculator, and validate against Inegol.
