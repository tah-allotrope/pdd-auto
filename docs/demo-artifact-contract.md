# Demo Artifact Contract

## Purpose

Define the Phase 01 contract for a future client-demo Soc Son package without changing the existing internal review workflow.

## Root Cause Trace

1. `src/pdd_agent/phase06/vietnam_workflow.py` runs `run_vietnam_pdd_workflow()` with provider `noop` by default.
2. `SectionOrchestrator.run()` saves the drafted sections through `DraftRun.save()` into `data/runs/<run-id>.json`.
3. `src/pdd_agent/llm/provider.py` implements `NoopProvider.draft_section()` as structured placeholder output, not readable narrative prose.
4. `src/pdd_agent/export/docx_export.py` then faithfully exports that same placeholder-heavy run into the reviewer-facing DOCX package.

The current Soc Son DOCX looks noisy because the workflow is doing exactly what the internal review contract asks it to do: publish a disclosure-first, review-gated draft, not a client-demo sample.

## Current Review Contract

- `reports/review-packages/` is the canonical home for internal review output.
- Review packages may include placeholder section bodies, `REVIEW REQUIRED` issues, assumption appendices, and reviewer-issue appendices.
- The latest Soc Son package under `reports/review-packages/soc-son-waste-to-power-plant-project/latest.docx` should continue to preserve that internal-review behavior.
- `run-vietnam-pdd` remains a reviewer-facing workflow and must not silently become a client-demo workflow.

## Client-Demo Contract

Future demo packages must be separate synthetic artifacts with this acceptance contract:

- No `[PLACEHOLDER` markers in the main body.
- No `REVIEW REQUIRED` bullets in the main body.
- Cross-section quantitative values stay aligned across narrative, tables, and appendices.
- The cover clearly states that the document is a synthetic client-demo sample.
- The appendix stays concise and summarizes synthetic assumptions instead of dumping the full reviewer-issues appendix.

## Canonical Demo Publication Path

The default client-demo package target is:

- Run-scoped artifact: `reports/demo-packages/<project-slug>/<run-id>/`
- Stable alias: `reports/demo-packages/<project-slug>/latest.docx`
- Optional alias when local conversion exists: `reports/demo-packages/<project-slug>/latest.pdf`

This keeps the client-demo package separate from the existing review-package history and makes the audience of each artifact obvious from the path alone.

## Telemetry Policy For Demo Packages

- Keep summary-level synthetic disclosure.
- Keep a compact assumptions appendix.
- Do not export the full reviewer-issues appendix used by `reports/review-packages/`.
- Do not surface raw review-gate language inside the main body.

## Evidence For The Current Mismatch

- `src/pdd_agent/llm/provider.py` documents `NoopProvider` as a zero-cost placeholder provider for human-in-the-loop review mode.
- `reports/demo-scorecard.md` records `36` placeholder sections and `36` low-confidence sections for the current benchmark workflow, confirming the same audience mismatch exists there too.
- The latest published Soc Son DOCX under `reports/review-packages/` is therefore behaving as designed for review, but not as needed for a client demo.

## Phase 01 Outcome

Phase 01 does not change generation or export behavior yet. It makes the artifact contract explicit so later phases can build a true client-demo package without weakening the internal review workflow.
