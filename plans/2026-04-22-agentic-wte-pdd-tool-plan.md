---
+title: "Agentic Low-Cost WTE PDD Tool"
+date: "2026-04-22"
+status: "draft"
+request: "Draft a detailed multi-phase plan for an agentic/AI tool that creates waste-to-energy carbon credit PDDs at zero/minimal cost using local research, a fresh research brief, and Google Workspace CLI (gws) against the provided Drive folder."
+plan_type: "multi-phase"
+research_inputs:
+  - "research/Waste to Energy Carbon Credits.md"
+  - "research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt"
+  - "research/2026-04-22_wte-pdd-ingestion.md"
+---
+
+# Plan: Agentic Low-Cost WTE PDD Tool
+
+## Objective
+Build a local-first, agentic assistant that ingests a narrow Verra-style waste-to-energy corpus, normalizes and sections it, and produces section-by-section PDD drafts with provenance and review flags rather than an unverifiable full-document hallucination. Keep recurring infrastructure cost near zero by relying on local files, `gws` for Drive access, open/low-cost retrieval, and optional paid model calls only where rule-based or local methods are insufficient.
+
+## Context Snapshot
+- **Current state:** Workspace contains WTE methodology notes, an internal VCM document generation memo, and a sample `template/VCS_Soc Son_Project-Description.pdf`; `gws` is installed and can read the provided Drive folder metadata, which currently exposes 13 PDF project documents; no implementation code exists yet.
+- **Desired state:** A reproducible CLI pipeline can inventory the Drive corpus, normalize a first homogeneous WTE bucket, draft each PDD section with citations and confidence flags, run compliance checks, and export a reviewable draft package back to local files and/or Drive.
+- **Key repo surfaces:** Existing inputs in `research/` and `template/`; intended code surfaces `pyproject.toml`, `src/pdd_agent/`, `configs/`, `schemas/`, `data/`, `prompts/`, `rules/`, `scripts/`, and `tests/`.
+- **Out of scope:** Production SaaS UI, multi-standard support beyond the first Verra-style bucket, automatic registry submission, legal/audit sign-off without human review, and broad all-methodology support in the first build.
+
+## Research Inputs
+- `research/Waste to Energy Carbon Credits.md` - Constrains the first corpus to a methodology-homogeneous WTE bucket and highlights double-counting boundaries between landfill diversion, biogas utilization, RDF production, and cement fuel substitution.
+- `research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt` - Supplies the low-cost POC framing, corpus-bucketing logic, and target success criteria, but its solar-first assumptions should be replaced with WTE-specific bucketing and review gates.
+- `research/2026-04-22_wte-pdd-ingestion.md` - Confirms that `gws` works against the provided Drive folder in this environment, that the sample Soc Son PDF is machine-readable, and that planning should favor section-level RAG with provenance over monolithic generation.
+
+## Assumptions and Constraints
+- **ASM-001:** The first useful bucket is a narrow Verra-style municipal solid waste / waste-to-power corpus pulled from the provided Drive folder and then split by methodology, template generation, project structure, and geography before drafting begins.
+- **ASM-002:** The sample `template/VCS_Soc Son_Project-Description.pdf` is representative enough to seed the initial heading tree and parser tests, but the official Verra template and methodology references still need to be ingested into the project as source-of-truth reference material.
+- **CON-001:** The tool must stay near-zero on recurring infrastructure cost, so phase 1-4 should use local filesystem storage, SQLite/FTS or equivalent local retrieval, and `gws` rather than hosted vector databases or a custom Drive OAuth app.
+- **CON-002:** PDF-first ingestion is the default path because the accessible Drive folder currently contains PDFs; OCR or premium extraction should remain a fallback triggered only by parseability metrics.
+- **DEC-001:** `gws drive files list` and `gws drive files get` are the approved ingestion surfaces for folder inventory and metadata capture because they are already working in this environment.
+- **DEC-002:** Human review is mandatory for methodology eligibility, additionality, baseline logic, safeguards, and final quantitative sections; the tool optimizes for a high-quality assisted first draft, not unsupervised final issuance documents.
+
+## Phase Summary
+| Phase | Goal | Dependencies | Primary outputs |
+|---|---|---|---|
+| PHASE-01 | Bootstrap the repo, inventory the Drive corpus, and lock the first homogeneous WTE bucket | None | Python CLI skeleton, Drive manifest, raw corpus cache, normalization report |
+| PHASE-02 | Convert Verra/WTE structure into a reusable section schema and project input contract | PHASE-01 | Canonical section schema, parser tests, project input schema, methodology rule map |
+| PHASE-03 | Build the agentic section-drafting pipeline with provenance and cost controls | PHASE-02 | Retrieval index, section orchestrator, provider abstraction, draft JSON/Markdown outputs |
+| PHASE-04 | Add compliance checks and reviewer handoff surfaces | PHASE-03 | WTE/Verra rule checks, review report, DOCX/Markdown export, Drive upload flow |
+| PHASE-05 | Benchmark the POC on a real WTE example and decide next expansion | PHASE-04 | Demo configuration, scorecard, section comparison report, go/no-go recommendation |
+
+## Detailed Phases
+
+### PHASE-01 - Foundation, Drive Inventory, and Corpus Bucketing
+**Goal**
+Stand up the minimal code structure and produce a trustworthy manifest of the Drive-based WTE corpus so every later phase works from a narrow, reproducible, and parseable document set.
+
+**Tasks**
+- [ ] TASK-01-01: Initialize a lean Python CLI workspace with `pyproject.toml`, `src/pdd_agent/`, `tests/`, and a single entrypoint for ingestion and drafting commands.
+- [ ] TASK-01-02: Wrap `gws drive files list` and `gws drive files get` in a thin ingestion layer that records file IDs, names, MIME types, modified timestamps, parent folders, and local cache paths in `data/corpus/manifest.jsonl`.
+- [ ] TASK-01-03: Download or export the first corpus candidate set from the provided Drive folder into `data/corpus/raw/verra/` and store official reference material in `data/reference/verra/` and `data/reference/methodologies/`.
+- [ ] TASK-01-04: Normalize each candidate document into plain text plus lightweight metadata in `data/corpus/normalized/`, preserving page numbers, heading lines, and parseability flags.
+- [ ] TASK-01-05: Define `configs/corpus_buckets/verra-wte-initial.yaml` so the first drafting bucket is selected by methodology family, template generation, project structure, geography, and document quality rather than by filename only.
+- [ ] TASK-01-06: Generate a corpus readiness report that marks which files are in-bucket, out-of-bucket, or blocked by poor extraction/OCR needs.
+
+**Files / Surfaces**
+- `pyproject.toml` - Minimal runtime and test dependencies for a local-first CLI tool.
+- `src/pdd_agent/cli.py` - Single command surface for inventory, normalize, parse, draft, review, and export workflows.
+- `src/pdd_agent/ingest/drive.py` - Thin wrapper around `gws` commands and manifest writing.
+- `configs/corpus_buckets/verra-wte-initial.yaml` - Explicit inclusion rules for the first homogeneous WTE corpus bucket.
+- `data/corpus/manifest.jsonl` - Source-of-truth inventory keyed by Drive file ID and local cache path.
+- `data/corpus/raw/verra/` - Immutable cache of downloaded/exported source files.
+- `data/corpus/normalized/` - Parseable text derivatives and extraction metadata.
+- `tests/test_drive_inventory.py` - Regression coverage for manifest generation and MIME branching.
+- `template/VCS_Soc Son_Project-Description.pdf` - Seed sample used to verify that PDF-first parsing is feasible.
+
+**Dependencies**
+- Local `gws` authentication and continued access to Drive folder `1pp23yRZ8qtopw1BPXrzVewXsmmWplCse`.
+- Python PDF/text extraction libraries that can handle the current PDF corpus without paid OCR.
+- Availability of at least one official Verra template/methodology reference to store in `data/reference/`.
+
+**Exit Criteria**
+- [ ] `data/corpus/manifest.jsonl` covers every file currently exposed in the provided Drive folder with stable IDs and MIME types.
+- [ ] At least 5-10 in-bucket WTE documents are normalized into machine-readable text with heading preservation and explicit parseability status.
+- [ ] `configs/corpus_buckets/verra-wte-initial.yaml` exists and explains why each included file belongs in the initial drafting bucket.
+- [ ] The project has a runnable CLI entrypoint and ingestion tests for manifest generation and cache behavior.
+
+**Phase Risks**
+- **RISK-01-01:** The accessible folder may mix multiple WTE subtypes or methodology families; mitigate by making bucket selection a first-class config file instead of an ad hoc filter.
+- **RISK-01-02:** Some PDFs may parse poorly or contain scanned pages; mitigate by recording extraction quality now and deferring OCR until a measured blocker appears.
+
+### PHASE-02 - Section Schema and Input Contract
+**Goal**
+Translate the Verra/WTE document structure into machine-usable schemas so the drafting system knows what each section needs, what can be reused, and what must come from project-specific evidence.
+
+**Tasks**
+- [ ] TASK-02-01: Extract a canonical heading tree from `template/VCS_Soc Son_Project-Description.pdf` and 2-3 additional in-bucket documents, then reconcile heading drift into one normalized section map.
+- [ ] TASK-02-02: Create `schemas/pdd_section_schema.yaml` with one record per section, including section type, expected evidence class, allowed boilerplate level, and review sensitivity.
+- [ ] TASK-02-03: Build `schemas/project_input.schema.json` (or a Pydantic model) for structured project facts, numeric inputs, document references, and unresolved placeholders.
+- [ ] TASK-02-04: Encode WTE-specific methodology hazards in a rules file, especially landfill-diversion vs fuel-substitution ownership, additionality, safeguards, and monitoring-plan requirements.
+- [ ] TASK-02-05: Implement and test a section parser that maps normalized corpus text into the canonical section schema and records section coverage per document.
+- [ ] TASK-02-06: Write a provenance policy that defines which generated statements may originate from user inputs, retrieved corpus examples, official references, or unresolved placeholders.
+
+**Files / Surfaces**
+- `schemas/pdd_section_schema.yaml` - Canonical section taxonomy and drafting rules.
+- `schemas/project_input.schema.json` - Structured contract for project-specific inputs and supporting evidence.
+- `src/pdd_agent/parse/section_parser.py` - Parser that aligns normalized text to the canonical section map.
+- `src/pdd_agent/domain/methodology_rules.py` - WTE/Verra-specific logic and rule loading.
+- `rules/verra/wte_bucket_rules.yaml` - Human-readable rules for additionality, double counting, safeguards, and monitoring.
+- `docs/provenance-policy.md` - Allowed source classes and unsupported-claim behavior.
+- `tests/test_section_parser.py` - Regression tests for heading alignment and section coverage.
+- `tests/test_input_schema.py` - Validation tests for required project facts and placeholder handling.
+
+**Dependencies**
+- PHASE-01 normalized corpus, manifest, and in-bucket selection.
+- Access to the official Verra template and target methodology references captured in `data/reference/`.
+
+**Exit Criteria**
+- [ ] `schemas/pdd_section_schema.yaml` covers all sections required for the first WTE bucket and labels each section by content type and review sensitivity.
+- [ ] The parser aligns sections for the initial bucket with documented drift or achieves a coverage threshold high enough to support retrieval-based drafting.
+- [ ] `schemas/project_input.schema.json` validates a full demo project config and rejects incomplete mandatory numeric or evidentiary fields.
+- [ ] WTE-specific methodology hazards are encoded in a reusable rule file rather than left implicit in prompts.
+
+**Phase Risks**
+- **RISK-02-01:** Heading and appendix drift may reduce parser reliability; mitigate by storing aliases and section-level confidence rather than requiring one exact heading string per section.
+- **RISK-02-02:** Over-generalizing the schema too early will make prompts vague; mitigate by optimizing first for one narrow WTE bucket and expanding only after a successful demo.
+
+### PHASE-03 - Agentic Drafting and Retrieval Orchestration
+**Goal**
+Build a low-cost section-by-section drafting engine that retrieves the right examples and references, writes only supported content, and leaves explicit review flags when evidence is missing.
+
+**Tasks**
+- [ ] TASK-03-01: Implement a local retrieval layer using SQLite FTS/BM25 first, with optional local embeddings or reranking only if measured retrieval quality is insufficient.
+- [ ] TASK-03-02: Create a section orchestrator that assembles, per section, the template requirements, methodology rule excerpts, top-matching corpus snippets, and project-specific inputs.
+- [ ] TASK-03-03: Add a provider abstraction so the tool can run with a local model or low-cost API-backed model without changing orchestration logic.
+- [ ] TASK-03-04: Emit structured outputs for each section that include drafted text, source snippets, source IDs, confidence, and unresolved issues.
+- [ ] TASK-03-05: Enforce a hard rule that unsupported statements become placeholders or reviewer TODOs instead of free-form generated claims.
+- [ ] TASK-03-06: Define CLI commands such as `inventory`, `normalize`, `parse`, `build-index`, `draft-section`, and `draft-pdd` so the workflow stays scriptable and inexpensive to rerun.
+
+**Files / Surfaces**
+- `src/pdd_agent/retrieval/index.py` - Local indexing pipeline for normalized corpus sections and reference docs.
+- `src/pdd_agent/retrieval/search.py` - Query-time retrieval and scoring.
+- `src/pdd_agent/agent/section_orchestrator.py` - Per-section planner/executor that coordinates retrieval and drafting.
+- `src/pdd_agent/llm/provider.py` - Model abstraction for local-first and API-optional execution.
+- `prompts/section_draft.md` - Stable instructions for supported drafting behavior and citation requirements.
+- `data/index/` - Local retrieval artifacts; prefer SQLite or filesystem-backed formats to avoid infrastructure cost.
+- `data/runs/` - Per-run JSON outputs, citations, and confidence data.
+- `tests/test_section_orchestrator.py` - Deterministic tests using a small canned corpus and fixed project inputs.
+
+**Dependencies**
+- PHASE-02 section schema, project input contract, and methodology rules.
+- A small validated in-bucket corpus that can support example retrieval without cross-methodology contamination.
+
+**Exit Criteria**
+- [ ] Given a demo project config, the tool can draft every section in the canonical schema into structured JSON or Markdown.
+- [ ] Every non-empty section output includes provenance data pointing to inputs, reference material, or retrieved corpus examples.
+- [ ] Unsupported or low-confidence sections are converted into explicit TODOs/review flags instead of uncited narrative.
+- [ ] End-to-end drafting can run locally without any hosted database or managed vector service.
+
+**Phase Risks**
+- **RISK-03-01:** A monolithic prompt will produce plausible but weakly grounded text; mitigate by keeping orchestration section-scoped and provenance-first.
+- **RISK-03-02:** Even low-cost model calls can grow expensive if retrieval is noisy; mitigate by caching retrieval, drafting only changed sections, and reserving paid models for the hardest sections.
+
+### PHASE-04 - Compliance, Review, and Reviewer Handoff
+**Goal**
+Turn draft sections into a reviewable PDD package with explicit compliance checks, issue lists, and easy handoff back into the existing Drive-based workflow.
+
+**Tasks**
+- [ ] TASK-04-01: Implement rule-based checks for required sections, missing evidence, double-counting flags, methodology eligibility, and unresolved quantitative inputs.
+- [ ] TASK-04-02: Build a consistency checker that compares project inputs, generated sections, and reported numbers for obvious contradictions or missing units.
+- [ ] TASK-04-03: Generate reviewer-friendly artifacts: section pack in Markdown/JSON, a consolidated issue report, and a DOCX export aligned to the target project-description format.
+- [ ] TASK-04-04: Upload the draft package and review report back to Drive via `gws drive files create` so the workflow fits the same document-sharing surface already used by the team.
+- [ ] TASK-04-05: Add a simple approval state model such as `drafted`, `needs-input`, `needs-domain-review`, and `ready-for-human-edit` so handoff is visible without building a web app.
+
+**Files / Surfaces**
+- `src/pdd_agent/review/checks.py` - Rule execution for section completeness and methodology risk flags.
+- `src/pdd_agent/review/consistency.py` - Cross-section numeric and evidence consistency checks.
+- `rules/verra/wte_review_rules.yaml` - Review checklist maintained outside code where possible.
+- `src/pdd_agent/export/docx_export.py` - Template-aware export into a reviewable document.
+- `src/pdd_agent/export/drive_upload.py` - Thin wrapper around `gws drive files create` for artifact upload.
+- `reports/` - Human-readable issue lists, provenance tables, and run summaries.
+- `tests/test_review_checks.py` - Coverage for missing-evidence flags, double-counting prompts, and status transitions.
+
+**Dependencies**
+- PHASE-03 structured draft outputs and provenance records.
+- Stable target format for the first project-description export.
+
+**Exit Criteria**
+- [ ] A single command produces the drafted section pack, a review issue list, and an exportable document artifact.
+- [ ] Rule checks catch missing or contradictory evidence before human review starts.
+- [ ] At least one generated artifact can be uploaded back to Drive using the already-available `gws` surface.
+- [ ] Review states are persisted so reruns do not erase human feedback.
+
+**Phase Risks**
+- **RISK-04-01:** Review logic may drift into fuzzy prompt-only judgment; mitigate by expressing as many checks as possible as explicit rules and structured assertions.
+- **RISK-04-02:** DOCX formatting can consume disproportionate effort; mitigate by treating Markdown + structured JSON as the primary truth and DOCX as a final export layer.
+
+### PHASE-05 - Benchmark, Demo, and Expansion Decision
+**Goal**
+Run a credible POC benchmark on a real WTE-like example, measure value vs cost, and decide whether to deepen the first bucket or expand into adjacent methodologies.
+
+**Tasks**
+- [ ] TASK-05-01: Create a demo project configuration that approximates a Soc Son-like waste-to-power case using only facts that can be entered and reviewed cleanly.
+- [ ] TASK-05-02: Run the full pipeline end-to-end and capture runtime, manual interventions, section coverage, unsupported-claim count, and any model/API spend.
+- [ ] TASK-05-03: Compare generated sections against one real reference PDD and score them for factual grounding, structural correctness, and reviewer usefulness.
+- [ ] TASK-05-04: Document what remained manual, which sections were strongest/weakest, and whether the near-zero-cost architecture is good enough for continued investment.
+- [ ] TASK-05-05: Produce a short decision memo recommending one of three follow-ups: harden the same bucket, add a second WTE bucket, or pause and revisit architecture.
+
+**Files / Surfaces**
+- `configs/projects/demo_socson_like.yaml` - Reproducible input set for the first benchmark run.
+- `scripts/run_demo.py` - One-command runner for inventory, parse, draft, review, and export.
+- `reports/demo-scorecard.md` - Measured cost, quality, and review-burden summary.
+- `reports/section-diff.md` - Side-by-side notes comparing generated vs reference sections.
+- `README.md` - Minimal operator guidance once the POC reaches repeatable demo quality.
+
+**Dependencies**
+- PHASE-04 reviewable draft package and export flow.
+- At least one reference PDD and one demo input configuration suitable for comparison.
+
+**Exit Criteria**
+- [ ] The demo run completes end-to-end on one real WTE-like case without ad hoc manual file wrangling between phases.
+- [ ] The scorecard shows whether the tool achieves a materially useful first draft for a meaningful subset of sections.
+- [ ] Per-run infrastructure cost remains effectively zero and any paid model cost is transparent, bounded, and easy to disable.
+- [ ] A written go/no-go recommendation exists for the next engineering step.
+
+**Phase Risks**
+- **RISK-05-01:** A single demo may overfit to one project shape; mitigate by treating the first benchmark as proof of workflow and requiring a second project before any broader claims.
+- **RISK-05-02:** Quality may look good structurally but still be weak on domain nuance; mitigate by scoring reviewer usefulness and provenance quality, not just template resemblance.
+
+## Verification Strategy
+- **TEST-001:** Add unit and fixture-based tests for Drive inventory, MIME-aware download/export handling, section parsing, input-schema validation, retrieval selection, and compliance checks.
+- **TEST-002:** Create a regression fixture from `template/VCS_Soc Son_Project-Description.pdf` (or its extracted text) so heading-tree extraction and section alignment stay stable across refactors.
+- **TEST-003:** Add an end-to-end smoke test that runs the pipeline on a tiny local fixture corpus with no network dependency.
+- **MANUAL-001:** Compare a generated draft pack against one real WTE PDD and verify that every paragraph can be traced to project inputs, reference docs, or retrieved examples.
+- **MANUAL-002:** Manually inspect the highest-risk sections - methodology applicability, baseline scenario, additionality, safeguards, and monitoring - before judging the POC successful.
+- **OBS-001:** Log per-run document counts, section coverage, unsupported-claim count, parseability rate, and upload/export success.
+- **OBS-002:** Track runtime and model/API spend per run so "near-zero cost" remains a measurable constraint, not a slogan.
+
+## Risks and Alternatives
+- **RISK-001:** The first corpus may be too heterogeneous for reliable few-shot retrieval, which would make every prompt noisier and more expensive; mitigate by enforcing bucket discipline before building generation.
+- **RISK-002:** PDF extraction quality may create hidden data loss in tables, formulas, or appendices; mitigate by logging extraction confidence and isolating OCR as an explicit later decision.
+- **RISK-003:** Human reviewers may distrust AI-authored content even when it is grounded; mitigate by making provenance, unresolved TODOs, and review states visible by default.
+- **ALT-001:** Build a full end-to-end document generator that outputs a near-final PDD in one shot; not chosen because it hides provenance, magnifies hallucination risk, and is harder to validate section by section.
+- **ALT-002:** Use a hosted vector DB and web app from day one; not chosen because it conflicts with the zero/minimal-cost goal and is unnecessary before retrieval quality is proven locally.
+- **ALT-003:** Skip `gws` and write a custom Drive API client; not chosen because `gws` already works in this environment and removes OAuth/UI plumbing from the critical path.
+
+## Grill Me
+No open clarification questions.
+
+## Suggested Next Step
+Begin PHASE-01 by locking the first WTE corpus bucket from the provided Drive folder and building the `gws`-backed manifest/normalization flow before any generation logic is written.
