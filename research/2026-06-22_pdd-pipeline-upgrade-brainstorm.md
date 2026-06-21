---
title: "PDD Pipeline Upgrade to Audit-Ready Completeness"
date: "2026-06-22"
type: "brainstorm"
depth: "standard"
source_request: "Based on the research brief, brainstorm concrete upgrades to this pdd-auto repo that would close the identified gaps and capture the market opportunity"
slug: "pdd-pipeline-upgrade"
---

# Brainstorm: PDD Pipeline Upgrade to Audit-Ready Completeness

## Problem & Why Now
<!-- seeds /plan ## Objective -->

The pdd-auto pipeline is the most structurally mature PDD automation tool that exists (218 tests, corpus RAG, structured review, provenance tracking, DOCX export on the Verra v4.4 template) — but it cannot produce a real PDD because three critical capabilities are missing:

1. **Emission calculations are empty.** ACM0022 baseline/project/leakage numbers are hardcoded demo values or null. Hang Tran's Jun 11 review of Tinh's Seraphin draft flagged this as the #1 blocker: "calculations currently show no results for baseline or project emissions." This gap affects both tracks (pipeline and Codex).

2. **No real LLM provider is wired.** Only `NoopProvider` (placeholders) and `DemoProvider` (deterministic synthetic prose) exist. The `OpenAIProvider` is a stub returning `[OPENAI STUB]`. Section prose is shallow and unusable for VVB review.

3. **Document intake is spreadsheet-bound.** Only the Vietnam WtE Excel workbook can feed `ProjectInput`. No path exists to extract structured project data from arbitrary Word/PDF/text documents — yet Tinh's extraction prompt already solves this.

**Why now:** The research brief (277 sources, 2026-06-22) found that this is a **wide-open market opportunity**: zero open-source PDD generators exist, the only known competitor (Verst Carbon) is closed-source and opaque, VVB capacity delays cost developers **$2.6B by 2030** and block **4.8 GtCO₂** of credits, and registry API infrastructure (Verra + S&P Global, Gold Standard Digital MRV) is arriving in 2026. The internal team (Hang, Tinh) is actively producing PDDs for real projects (Seraphin) — the pipeline should be their tool, not a demo.

## Current vs Desired State
<!-- seeds /plan ## Context Snapshot -->

- **Current state:** A production-quality Python pipeline with corpus RAG (FTS5/BM25), Pydantic schema (60+ fields), rule-based methodology checks (ACM0022/ACM0003 only), 5-state review workflow, DOCX export on Verra v4.4 template, two demos (Soc Son, Inegol), and 218 passing tests. But: no real emission calculations, no real LLM drafting, spreadsheet-only intake, hardcoded methodology rules, no registry API integration.

- **Desired state:** The pipeline generates an **audit-ready PDD** for a WTE project like Seraphin: real ACM0022 emission numbers, LLM-drafted prose with evidence citations and anti-hallucination discipline, all VCS v4.4 sections populated, monitoring plan, methodology screening. Output is DOCX + PDF + web preview. Hang opens it and says "this is ready for VVB desk review."

- **Key repo surfaces:**
  - `schemas/project_input.py` — QuantificationInputs (lines 161-192), ProjectTechnology (lines 101-147)
  - `src/pdd_agent/llm/provider.py` — BaseProvider, ProviderRegistry, ModelConfig (abstract provider system)
  - `src/pdd_agent/llm/openai_provider.py` — OpenAIProvider stub
  - `src/pdd_agent/phase06/spreadsheet_mapper.py` — build_project_input_payload (lines 205-312, synthetic emission splits)
  - `src/pdd_agent/domain/methodology_rules.py` — MethodologyRules class (hardcoded ACM0022/ACM0003)
  - `rules/verra/wte_methodology_rules.yaml` — all methodology logic
  - `src/pdd_agent/agent/section_orchestrator.py` — provider injection, review checks
  - `src/pdd_agent/retrieval/search.py` — FTS5/BM25 corpus search (already works)
  - `prompts/section_draft.md` — current drafting prompt (to be replaced by Tinh's prompt discipline)
  - `src/pdd_agent/export/docx_export.py` — 11 structured table renderers, template-based export
  - `src/pdd_agent/review/consistency.py` — quantitative cross-checks
  - `src/pdd_agent/review/tbd_tracker.py` — TBD/placeholder detection

## Resolved Decisions
<!-- the grilled Q&A; each one keeps /plan's Grill Me empty -->

- **DEC-001:** Primary user is the internal Allotrope team (Tung, Hang, Tinh) — generating draft-quality PDDs for real WTE projects ready for expert review and VVB submission.
- **DEC-002:** Success bar is audit-ready completeness — real emissions numbers, LLM-drafted prose, methodology screening, monitoring plan, all VCS v4.4 sections populated. Ready for VVB desk review.
- **DEC-003:** ACM0022 quantification as a pure Python engine with Pydantic input/output models — deterministic, testable, version-tracked, auditable. The only approach VVBs will accept.
- **DEC-004:** First real LLM provider is OpenAI GPT-4, building on the existing `OpenAIProvider` stub. Provider abstraction supports future Claude/Ollama additions.
- **DEC-005:** Adopt Tinh's extraction prompt (`Create_YAML_From_Project_Summary_Prompt.txt`) for document→ProjectInput intake, mapping its output onto our Pydantic schema. Merges both tracks.
- **DEC-006:** Methodology screening via Verra active methodology list + LLM matching with confidence scores. Start with WTE methods, expand. Aligns with Tinh's `suggested_methodologies` approach.
- **DEC-007:** Inject top-k corpus chunks per section into the LLM prompt. The FTS5/BM25 retrieval infrastructure already exists; wire it through `draft_section()` into the prompt template.
- **DEC-008:** Adopt Tinh's prompt discipline wholesale — authority order (input YAML → evidence registry → template → VCS rules → comparable projects → general logic), `[MISSING]/[INFERENCE]/[REVIEW REQUIRED]` markers, evidence-ID citations `[E001]`, per-section review notes. Replaces `prompts/section_draft.md`.
- **DEC-009:** Sequential phasing — Phase 1: quantification engine (~2 wk), Phase 2: LLM+prompt (~2 wk), Phase 3: document intake + methodology screening (~1-2 wk), Phase 4: registry API integration (deferred to when Verra API lands).
- **DEC-010:** Validate calc engine with Inegol (already in repo) as primary, Seraphin when data arrives, plus synthetic edge cases for robustness.
- **DEC-011:** Output format evolves to DOCX + PDF + web preview for internal sharing and colleague review.
- **DEC-012:** ProjectInput stays canonical schema. Absorb Tinh's `generation_controls`, `review_flags`, `evidence_registry`, and `suggested_methodologies` as new optional nested Pydantic models.
- **DEC-013:** Per-run token budget with configurable limit (e.g., 500K tokens), 80% warning, 100% hard-stop, and per-run cost logging.
- **DEC-014:** Seraphin WTE project is the acceptance test. If Hang approves the pipeline-generated PDD, the upgrade is validated.
- **DEC-015:** Target timeline is 4-6 weeks — Phase 1 ~2 weeks, Phase 2 ~2 weeks, Phase 3 ~1-2 weeks. Registry API deferred.

## Assumptions & Constraints
<!-- seeds /plan ## Assumptions and Constraints -->

- **ASM-001:** ACM0022 methodology text and CDM tools (Tool 03, 04, 05, 07, 12) are publicly available from UNFCCC CDM website and can be implemented in Python without licensing issues.
- **ASM-002:** Tinh's prompt artifacts (`Create_YAML_From_Project_Summary_Prompt.txt`, `PDD creation prompt.txt`, `Schema_ver1.yaml`) are available to the team from the shared Drive folder.
- **ASM-003:** Seraphin project data (from Hang's Jun 9 inputs) will be available for acceptance testing within the timeline.
- **ASM-004:** OpenAI API access with GPT-4 is available and budgeted for internal development/testing.
- **ASM-005:** The existing 218 tests must continue to pass throughout all phases (no regressions).
- **CON-001:** VVBs require deterministic, reproducible calculations — LLM-generated numbers are not acceptable for quantification sections.
- **CON-002:** Independent third-party validation, stakeholder consultation/FPIC, and legal ownership checks cannot be automated and remain manual.
- **CON-003:** The Verra VCS v4.4 template DOCX is the required output format for registry submission.
- **CON-004:** PDF conversion depends on local converter availability (LibreOffice or similar); may need to be optional.
- **CON-005:** Registry API integration is blocked until Verra's next-gen registry API is publicly available (Phase 1 expected early 2026).

## Approaches Considered
<!-- seeds /plan ## Risks and Alternatives -->

- **Chosen: Pure Python ACM0022 engine** — implements methodology formulas as testable, versioned Python code with Pydantic I/O models. Matches repo patterns, auditable by VVBs, cross-validated against reference projects.
  - **Why:** VVBs require deterministic calculations. The existing Python test infrastructure can validate formulas. Per-parameter provenance tracking fits the assumption register pattern.

- **ALT-001: Spreadsheet-backed calculation** — inject values into Hang's WtE Excel model via openpyxl, read results.
  - **Why not:** Creates opaque dependency on a specific Excel file. Not version-controllable. Calculation logic hidden in cell formulas. Harder to test and audit.

- **ALT-002: LLM-assisted calculation** — feed ACM0022 methodology text + project data to LLM.
  - **Why not:** Non-deterministic. VVBs will not accept LLM-generated emission numbers. Cannot reproduce the exact same result across runs.

- **ALT-003: Build custom extraction pipeline** instead of adopting Tinh's prompt.
  - **Why not:** Duplicates proven work. Tinh's extraction prompt already handles Word/PDF/text/OCR → structured YAML with methodology screening and evidence registry. Better to merge than rebuild.

- **ALT-004: All-at-once sprint** for all upgrades simultaneously.
  - **Why not:** Too much parallel risk. Sequential phasing allows each phase to build on validated foundations. Quantification is the prerequisite for everything else.

## Out of Scope

- **Registry API integration** — deferred to Phase 4, after Verra's next-gen API is publicly available (early 2026).
- **Non-WTE methodologies** — initial calc engine covers ACM0022 only; methodology screening suggests others but doesn't calculate for them.
- **Automated stakeholder consultation** — regulatory hard stop; cannot be automated.
- **FPIC documentation generation** — requires actual community engagement evidence.
- **Multi-language support** — PDDs are in English per VCS standard.
- **Mobile/web UI** — pipeline remains CLI-driven for internal team use.
- **Article 6 / CORSIA compliance** — future scope after core PDD generation works.

## Open Questions
<!-- the few that survived; seed /plan ## Grill Me -->

1. **Q-001:** What specific Seraphin project data is available from Hang's Jun 9 inputs — and is there a calculation spreadsheet or emission reduction estimate we can validate against?
   - **Recommended default:** Start with Inegol as the primary validation target; add Seraphin data as it becomes available. Don't block Phase 1 on Seraphin data.
   - **Why this matters:** The calc engine needs at least one real-world reference project with known-correct emission numbers to validate against.

2. **Q-002:** Does Tinh's `PDD creation prompt.txt` and `Create_YAML_From_Project_Summary_Prompt.txt` need any adaptation before we adopt them, or can we use them as-is?
   - **Recommended default:** Use as-is for the initial integration, then iterate based on output quality. The prompts are well-designed; the gap is in mapping their output to our schema, not in the prompts themselves.
   - **Why this matters:** If significant prompt rework is needed, Phase 2 and Phase 3 timelines shift.

3. **Q-003:** Is there a preferred PDF conversion tool available on the team's machines (LibreOffice, wkhtmltopdf, or similar)?
   - **Recommended default:** Use LibreOffice CLI (`soffice --convert-to pdf`) if available; make PDF generation optional with a clear skip message if not.
   - **Why this matters:** DEC-011 calls for DOCX + PDF + web preview. PDF conversion needs a local tool.

## Suggested Next Step

Run `/plan pdd-pipeline-upgrade` to turn this into a multi-phase implementation plan.
