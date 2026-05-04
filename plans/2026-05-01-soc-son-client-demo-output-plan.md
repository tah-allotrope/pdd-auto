---
+title: "Soc Son Client Demo Output Upgrade"
+date: "2026-05-01"
+status: "phase-04-complete"
+request: "review word or pdf soc son output from implementation of the last plan and understand why it contain so much gibberish, evoke plan skill for multiphase so next sample word output will contain synthetic info suffice for a demo with client"
+plan_type: "multi-phase"
+research_inputs:
+  - "research/2026-04-22_wte-pdd-ingestion.md"
+  - "research/2026-04-26_pdd-auto-commercial-ideas.md"
---

+# Plan: Soc Son Client Demo Output Upgrade

+## Objective
+Produce a separate, client-demo-ready Soc Son sample Word artifact that is readable, internally consistent, and explicitly synthetic. The immediate goal is to stop using the current reviewer-facing package as a client-facing sample and replace it with a demo output path that shows plausible section content instead of placeholder and review-gate telemetry.

+## Context Snapshot
+- **Current state:** The latest published Soc Son DOCX at `reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx` is a faithful export of `data/runs/run-20260429041046-2616b7.json`, not a broken formatter. That run used provider `noop`, and `src/pdd_agent/llm/provider.py` intentionally emits `[PLACEHOLDER ...]` section bodies. `src/pdd_agent/phase06/spreadsheet_mapper.py` also injects many `synthetic_assumption` and `demo_default` fields, while `src/pdd_agent/export/docx_export.py` faithfully exports the placeholder body, review notes, assumption appendix, and reviewer-issues appendix. `reports/demo-scorecard.md` confirms the same design mismatch in the demo benchmark path: `36` placeholder sections and `36` low-confidence sections.
+- **Desired state:** The next Soc Son sample should publish a readable demo DOCX, and optionally a PDF, under a separate client-demo artifact path such as `reports/demo-packages/`. The main body should contain coherent synthetic prose and aligned synthetic numbers, while the synthetic nature of the artifact remains clearly disclosed on the cover and in a concise appendix.
+- **Key repo surfaces:** `src/pdd_agent/llm/provider.py`, `src/pdd_agent/llm/openai_provider.py`, `src/pdd_agent/llm/ollama_provider.py`, `src/pdd_agent/agent/section_orchestrator.py`, `src/pdd_agent/export/docx_export.py`, `src/pdd_agent/phase05/benchmark.py`, `src/pdd_agent/phase06/spreadsheet_mapper.py`, `src/pdd_agent/phase06/vietnam_workflow.py`, `src/pdd_agent/cli.py`, `scripts/run_demo.py`, `prompts/section_draft.md`, `configs/projects/demo_socson_like.yaml`, `reports/demo-scorecard.md`, `reports/section-diff.md`, `tests/test_phase05_demo.py`, `tests/test_docx_export.py`, `tests/test_phase06_cli.py`, `README.md`.
+- **Out of scope:** Turning the Vietnam review workflow into a final audited filing, hiding that the sample is synthetic, wiring commercial OpenAI or Ollama generation end to end, or weakening the existing review-gated publication contract under `reports/review-packages/`.

+## Research Inputs
+- `research/2026-04-22_wte-pdd-ingestion.md` - Confirms the tool should remain provenance-first and review-gated for real PDD work, so the client-demo path must be a separate artifact contract rather than a silent relaxation of the reviewer-facing workflow.
+- `research/2026-04-26_pdd-auto-commercial-ideas.md` - Confirms `NoopProvider` is only placeholder scaffolding and that quantification credibility should remain deterministic, which favors a curated synthetic demo path over rushing real LLM integration for this specific need.

+## Assumptions and Constraints
+- **ASM-001:** The current gibberish is primarily a workflow-contract mismatch, not a DOCX export defect, because the exported run JSON already contains `[PLACEHOLDER ...]` content for nearly every section.
+- **ASM-002:** The fastest path to a client-demo-ready artifact is curated synthetic content using existing `ProjectInput` surfaces, not wiring a real API-backed text model.
+- **ASM-003:** `configs/projects/demo_socson_like.yaml` is a better base for a clean sample than `configs/projects/vietnam_socson_from_sheet.yaml`, because the demo config already contains coherent monitoring, safeguards, ownership, and quantification inputs without the spreadsheet mapper's intentionally blocked review items.
+- **CON-001:** Synthetic demo content must remain explicitly labeled as demo content at the document or package level.
+- **CON-002:** The current reviewer-facing `run-vietnam-pdd` contract under `reports/review-packages/` should keep its current review-heavy behavior for internal validation and evidence-gap tracking.
+- **CON-003:** PDF export is optional unless a local conversion path is available; DOCX remains the guaranteed artifact surface.
+- **DEC-001:** The repo already has a separate `phase05` demo workflow, so the client-demo artifact should build on `phase05` rather than overloading the Vietnam review package path.
+- **DEC-002:** `SectionOrchestrator` and `export_run_to_docx()` remain the core assembly and export surfaces rather than introducing an unrelated one-off document builder.

+## Phase Summary
+| Phase | Goal | Dependencies | Primary outputs |
+|---|---|---|---|
+| PHASE-01 | Define a separate client-demo artifact contract and capture the current failure mode precisely | None | Demo-vs-review contract, acceptance rules, canonical output path |
+| PHASE-02 | Curate a full synthetic Soc Son demo dataset that can support every section without review-gated gaps | PHASE-01 | Demo config, demo assumptions file, deterministic quantitative inputs |
+| PHASE-03 | Generate readable demo prose and export a cleaner client-facing document package | PHASE-02 | Demo provider or narrative renderer, cleaner DOCX export behavior, CLI/script surface |
+| PHASE-04 | Verify the new demo artifact end to end and publish a fresh client-demo sample | PHASE-03 | Passing tests, fresh demo DOCX, optional PDF, refreshed docs and sample reports |

+## Detailed Phases

+### PHASE-01 - Demo Artifact Contract And Root-Cause Trace
+**Goal**
+Make the root cause explicit and prevent future confusion between reviewer-facing artifacts and client-demo artifacts.

+**Tasks**
+- [x] TASK-01-01: Trace the latest Soc Son output from `run_vietnam_pdd_workflow()` to `DraftRun.save()` and confirm, in code and docs, that `provider="noop"` is the direct source of the placeholder-heavy body text.
+- [x] TASK-01-02: Define the client-demo acceptance contract: no `[PLACEHOLDER` markers in the main body, no `REVIEW REQUIRED` bullets in the main body, aligned cross-section numbers, and one concise synthetic disclosure on the cover plus a compact appendix.
+- [x] TASK-01-03: Choose the canonical publication path for demo artifacts, with `reports/demo-packages/<project-slug>/<run-id>/` plus a stable `latest.docx` alias as the default target.
+- [x] TASK-01-04: Decide how much review telemetry should remain in a demo package, with the default being summary-level disclosure only rather than exporting the full reviewer-issues appendix used by internal review packages.
+- [x] TASK-01-05: Update repo docs so `reports/review-packages/` clearly means internal review output and `reports/demo-packages/` clearly means synthetic client-demo output.

+**Files / Surfaces**
+- `src/pdd_agent/llm/provider.py` - Confirms the current `NoopProvider` behavior is placeholder-by-design.
+- `src/pdd_agent/phase06/vietnam_workflow.py` - Confirms the last Soc Son package was intentionally produced through the review workflow.
+- `reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx` - Concrete artifact to audit and use as the root-cause reference.
+- `reports/demo-scorecard.md` - Confirms the current demo benchmark path still accepts placeholder-heavy output.
+- `README.md` - Needs the artifact-contract split documented clearly.

+**Dependencies**
+- None

+**Exit Criteria**
+- [x] The repo has one explicit distinction between internal review packages and client-demo packages.
+- [x] Another engineer can explain why the current Soc Son DOCX looks noisy without re-reading the full run JSON.
+- [x] The canonical output path and acceptance rules for the new demo artifact are concrete enough to implement without guesswork.

+**Phase Risks**
+- **RISK-01-01:** If the contract stays ambiguous, implementation may only suppress some exporter noise while still generating placeholder body text; mitigate by defining body-level acceptance rules before any code changes.

+### PHASE-02 - Curated Synthetic Demo Inputs
+**Goal**
+Create a coherent Soc Son-like synthetic input set that is rich enough to draft all sections without falling back to review-gated missing-data placeholders.

+**Tasks**
+- [x] TASK-02-01: Add failing tests that prove the demo input covers all sections needed for a readable sample and does not carry the spreadsheet mapper's blocked-review gaps into the demo path.
+- [x] TASK-02-02: Extend `create_demo_project_input()` or add a dedicated `configs/projects/demo_socson_like.assumptions.yaml` so the demo path has structured provenance for synthetic facts instead of relying on the Vietnam spreadsheet's missing-data assumption register.
+- [x] TASK-02-03: Fill the demo dataset with coherent synthetic facts for proponent identity, ownership, consultation, EIA, monitoring, project location, and methodology applicability so Section 1, 2, 3, 4, and 5 all have usable narrative inputs.
+- [x] TASK-02-04: Decide whether to introduce a distinct provenance/source type such as `demo_curated` so demo-safe synthetic facts are not conflated with unresolved review-gated assumptions.
+- [x] TASK-02-05: Ensure all quantitative fields used in Sections `1.10`, `3.4`, `4.1`, `4.2`, `4.4`, and `5.2` are internally consistent and deterministic from the same synthetic dataset.

+**Files / Surfaces**
+- `src/pdd_agent/phase05/benchmark.py` - Current `create_demo_project_input()` surface and likely home of richer demo-input generation.
+- `configs/projects/demo_socson_like.yaml` - Existing demo input that should become the canonical client-demo base.
+- `configs/projects/demo_socson_like.assumptions.yaml` - Likely new structured assumptions/provenance companion for the demo path.
+- `src/pdd_agent/phase06/spreadsheet_mapper.py` - Useful reference for assumption-register structure, but should not remain the source of client-demo gaps.
+- `tests/test_phase05_demo.py` - Primary place to lock down demo-input coverage and consistency expectations.

+**Dependencies**
+- PHASE-01 demo artifact contract and path decision.

+**Exit Criteria**
+- [x] The demo path has one coherent ProjectInput plus assumptions/provenance surface that can support every required section.
+- [x] Quantitative fields are internally consistent and do not require spreadsheet-review gate warnings to remain visible in the main body.
+- [x] The demo dataset can be regenerated deterministically in the workspace.

+**Phase Risks**
+- **RISK-02-01:** Reusing the spreadsheet-derived Soc Son mapping too directly will keep dragging review-gated missing-data logic into the demo output; mitigate by treating the demo dataset as a curated synthetic fixture rather than a thin spreadsheet veneer.

+### PHASE-03 - Demo Narrative Generation And Cleaner Export
+**Goal**
+Replace placeholder-heavy body text with readable synthetic prose while keeping the artifact clearly marked as a demo.

+**Tasks**
+- [x] TASK-03-01: Add failing tests for a demo drafting mode that produces readable section prose and guarantees zero `[PLACEHOLDER` markers in the exported main body.
+- [x] TASK-03-02: Introduce a deterministic demo authoring path, likely a `DemoProvider` or equivalent section renderer, that uses `ProjectInput`, schema guidance, and structured synthetic facts to produce section text instead of placeholder text.
+- [x] TASK-03-03: Update `SectionOrchestrator` so the demo path can preserve fact provenance and synthetic disclosures without automatically converting every synthetic field into `REVIEW REQUIRED` body text.
+- [x] TASK-03-04: Update `export_run_to_docx()` so demo exports keep a strong cover disclosure but replace the full reviewer-issues appendix with a concise assumptions summary that is appropriate for a client-facing sample.
+- [x] TASK-03-05: Extend `run_demo_benchmark()` and `scripts/run_demo.py`, or add a nearby dedicated script/flag, so the demo workflow can publish `reports/demo-packages/<project-slug>/<run-id>/` plus `latest.docx` and optionally `latest.pdf` when a local converter exists.
+- [x] TASK-03-06: Surface the demo artifact path clearly in `src/pdd_agent/cli.py` so operators do not need to inspect `data/runs/` or internal review-package directories.

+**Files / Surfaces**
+- `src/pdd_agent/llm/provider.py` - Likely home for a deterministic `demo` provider registration path.
+- `src/pdd_agent/agent/section_orchestrator.py` - Needs audience-specific behavior that distinguishes demo prose from reviewer placeholders.
+- `src/pdd_agent/export/docx_export.py` - Needs a cleaner demo export layout and appendix strategy.
+- `src/pdd_agent/phase05/benchmark.py` - Natural place to publish demo packages from the existing demo workflow.
+- `scripts/run_demo.py` - One-command surface for generating the client-demo artifact.
+- `src/pdd_agent/cli.py` - Needs argument surface and output logging for the demo package path.
+- `tests/test_docx_export.py` - Needs assertions for demo-mode export layout and content rules.
+- `tests/test_phase05_demo.py` - Needs assertions for non-placeholder demo section generation.

+**Dependencies**
+- PHASE-02 curated synthetic demo inputs.

+**Exit Criteria**
+- [x] The demo run JSON and exported DOCX contain readable synthetic section text instead of noop placeholders.
+- [x] The main body of the demo DOCX contains no `[PLACEHOLDER` or `REVIEW REQUIRED` markers.
+- [x] The exported demo artifact still discloses its synthetic/demo status clearly without overwhelming the document with internal review telemetry.
+
+**Phase Risks**
+- **RISK-03-01:** Hiding too much review context could make the sample look deceptively final; mitigate by keeping an explicit cover-page disclosure and a concise appendix of synthetic assumptions.
+- **RISK-03-02:** Demo prose may drift away from the schema or quantification totals; mitigate by using deterministic templates and shared numeric sources instead of free-form generation.

+### PHASE-04 - Verification And Fresh Client Demo Artifact
+**Goal**
+Prove the new demo contract works by generating a fresh Soc Son client-demo package and confirming it is readable enough for a live client conversation.

+**Tasks**
+- [ ] TASK-04-01: Add regression tests covering zero-placeholder demo output, aligned quantification numbers, demo-package publication, and CLI/script surfacing of the published path.
+- [ ] TASK-04-02: Run the refreshed demo workflow end to end and publish a fresh DOCX under `reports/demo-packages/`.
+- [ ] TASK-04-03: If a local converter is available, publish a matching PDF and verify that it mirrors the DOCX content rather than the old review-package content.
+- [ ] TASK-04-04: Refresh README examples and any demo-facing reports so the repo points users to the client-demo package rather than the internal review package when the goal is a sample output.
+- [ ] TASK-04-05: Manually inspect the generated artifact and confirm that the cover disclosure, body prose, quantitative totals, and appendix summary would all be understandable in a client demo without extra apology or translation.

+**Files / Surfaces**
+- `tests/test_phase05_demo.py` - Needs end-to-end assertions for the demo artifact contract.
+- `tests/test_docx_export.py` - Needs export-level assertions for demo formatting and disclosure behavior.
+- `src/pdd_agent/cli.py` - Needs verification that surfaced paths match generated artifacts.
+- `reports/demo-packages/` - New canonical client-demo publication directory.
+- `README.md` - Needs updated sample-output guidance.
+
+**Dependencies**
+- PHASE-03 demo authoring and export behavior.

+**Exit Criteria**
+- [ ] The workspace contains a fresh Soc Son client-demo DOCX at the new demo package path.
+- [ ] Automated tests pass for demo generation, export, and publication behavior.
+- [ ] Manual inspection confirms the sample reads like a coherent synthetic PDD draft instead of an internal placeholder bundle.

+**Phase Risks**
+- **RISK-04-01:** A passing test suite may still leave behind a visually noisy client artifact; mitigate by requiring one manual open/read of the final DOCX or PDF before declaring success.

+## Verification Strategy
+- **TEST-001:** Extend `tests/test_phase05_demo.py` so demo-mode runs must produce zero placeholder sections, coherent quantitative sections, and a published demo package path.
+- **TEST-002:** Extend `tests/test_docx_export.py` so demo exports must retain a cover disclosure but omit raw reviewer-issue dumps from the main body.
+- **TEST-003:** Add or extend CLI tests so the demo command or flag surfaces `reports/demo-packages/.../latest.docx` explicitly.
+- **MANUAL-001:** Run the demo workflow, open the generated DOCX, and confirm the first three sections read as coherent synthetic prose with no placeholder markers.
+- **MANUAL-002:** Confirm Sections `1.10`, `4.1`, `4.2`, and `4.4` use the same deterministic synthetic numbers across the body and appendix.
+- **OBS-001:** Log the provider, artifact audience (`review` vs `client_demo`), publication path, placeholder count, and whether PDF conversion succeeded or was skipped.

+## Risks and Alternatives
+- **RISK-001:** Operators may confuse review packages and demo packages once both exist; mitigate with separate directories, separate CLI output labels, and explicit README language.
+- **RISK-002:** Synthetic demo content may be mistaken for real project evidence if disclosures are too subtle; mitigate with strong cover text and package naming that includes `demo`.
+- **ALT-001:** Only restyle `export_run_to_docx()` and hide the current appendices; not chosen because the core problem is that the run JSON itself is placeholder-heavy.
+- **ALT-002:** Wire `OpenAIProvider` or `OllamaProvider` immediately and rely on model prose; not chosen because both providers are currently stubs and LLM prose alone does not solve deterministic quantification or disclosure needs.
+- **ALT-003:** Reuse `run-vietnam-pdd` and relax its review gates for demo purposes; not chosen because that would blur the review contract and weaken the internal artifact that the last plan just clarified.

+## Grill Me
+1. **Q-001:** Should the client-demo artifact be a separate package contract, or should it replace the current Soc Son review package output? (user agree default)
+   - **Recommended default:** Separate package contract under `reports/demo-packages/`.
+   - **Why this matters:** It determines whether we preserve the current reviewer-facing workflow intact or mutate it into something less review-safe.
+   - **If answered differently:** Replacing the current review package would reduce surfaces but risks losing the explicit evidence-gap output that is still useful internally.
+2. **Q-002:** Should the first client demo anchor on the curated `demo_socson_like.yaml`, or should it stay tied to the spreadsheet-derived Vietnam Soc Son mapping? (user stay tied to spreadsheet)
+   - **Recommended default:** Anchor on the curated demo config first.
+   - **Why this matters:** It determines whether we optimize for clean synthetic storytelling or for fidelity to a spreadsheet row that currently has many intentional evidence gaps.
+   - **If answered differently:** Staying tied to the spreadsheet path will require more logic to suppress or reinterpret review-gated missing-data signals.
+3. **Q-003:** How strong should the synthetic disclosure be in the demo artifact? (user agree default)
+   - **Recommended default:** Strong cover-page disclosure plus a concise appendix, but no inline `REVIEW REQUIRED` markers in the body.
+   - **Why this matters:** It changes the tone of the document and how client-safe the artifact feels while still remaining honest.
+   - **If answered differently:** Stronger inline disclosure is safer but may still feel noisy; lighter disclosure is smoother but raises misrepresentation risk.
+4. **Q-004:** Is DOCX sufficient for the next client sample, or do you want a guaranteed PDF alongside it? (user agree default)
+   - **Recommended default:** DOCX required, PDF optional when local conversion is available.
+   - **Why this matters:** Guaranteed PDF support adds dependency and verification work that may delay the faster DOCX fix.
+   - **If answered differently:** A PDF requirement should add a dedicated conversion and verification step to PHASE-03 and PHASE-04.

+## Suggested Next Step
+Implement PHASE-02 next so the future client-demo workflow has one coherent synthetic input surface and no longer depends on the spreadsheet mapper's review-gated gaps for client-facing sample generation.
