---
title: "Methodology-Parametrized Pipeline Under CI: Make Breadth Real for the LLM Path"
date: "2026-07-13"
status: "complete — all six phases delivered and reported (reports/2026-07-14-final-phase-01-02, -03-04, -05-06); only TASK-06-04 (cli.py package split) was explicitly deferred as a non-functional refactor."
request: "Multi-phase plan for CI, methodology-parametrized drafting prompt + judge rubric, parametrized test matrix, one-command provider scorecard, and architectural debt paydown (evidence registry flow, module splits, config-driven pricing, batch-approve fix)"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-13-pdd-post-reality-gap-next-level-brainstorm.md"
---

# Plan: Methodology-Parametrized Pipeline Under CI

## Objective
Make the drafting **intelligence layer** as methodology-broad as the calc/schema layer already is, protected by continuous integration, so that the imminent frontier-LLM proof validates all four methodology families (WTE/ACM0022, rice/VM0051, biochar/VM0044, cookstove/AMS-II.G) rather than only waste-to-energy. Today the calc engines and `ProjectInput` schema are multi-family, but the two artifacts the LLM actually reads — the section-drafting prompt and the judge rubric — are hardcoded to WTE/ACM0022, and there is no CI. This plan is entirely non-key-gated: every phase can be built and verified with the `demo`/`noop`/`ollama` providers and no API keys.

## Context Snapshot
- **Current state:** 606 tests pass (`python -m pytest -m "not corpus" -q`, ~90s). The reality-gap plan (`plans/2026-07-12-pdd-reality-gap-plan.md`) is complete: real `OllamaProvider`, thread-safe retrieval, provider opt-in behind cost ceilings, a real structured-JSON LLM judge, `pdd-agent scorecard`, and a rice VM0051 end-to-end pilot. But: (1) `prompts/section_draft_v2.md` and the inlined prompt text in `section_orchestrator.py` name "waste-to-energy" and "ACM0022" in load-bearing instructions; (2) `rules/verra/judge_rubric.yaml` is `bucket: "verra-wte-initial"` with `NO_FABRICATED_FACTS` hardcoding "ACM0022 calc engine" and `judge.py` hardcodes `_QUANTITATIVE_SECTIONS = {"1.10", "4.1", "4.2", "4.4"}` (WTE section map); (3) there is **no `.github/workflows/`**; (4) the test suite has **zero `pytest.mark.parametrize`** and every fixture is WTE-shaped — which is exactly why the rice pilot found 3 bugs the 601-test suite missed; (5) `_DEFAULT_PRICING` in `llm/budget.py` is hardcoded; (6) `EvidenceRegistry` exists on `ProjectInput` and is validated at the export gate and judge but is never *populated* at intake, injected into prompts, or auto-rendered as an appendix from one source of truth; (7) the section-review service has a logged, unfixed batch-approve-all defect.
- **Desired state:** A CI job runs the full non-corpus suite + lint on every push. Drafting prompts and the judge rubric are selected by the project's methodology, with a methodology-neutral core and per-family overlays. A parametrized test matrix exercises the draft→review→consistency→export path over all four families so WTE-shaped assumptions fail in CI, not in the next pilot. A single command (`pdd-agent prove`) runs a project through every available provider, judges each, and writes a head-to-head scorecard, skipping unkeyed providers gracefully. Model pricing lives in a YAML that `doctor` validates. The evidence registry flows intake → prompt → judge → DOCX appendix. The service supports atomic batch approval.
- **Key repo surfaces:** `.github/workflows/ci.yml` (new); `prompts/section_draft_v2.md` + `prompts/methodologies/*.md` (new); `src/pdd_agent/agent/section_orchestrator.py` (`_build_prompt`, `_QUANTITATIVE_SECTIONS` equivalent, prompt overlay selection); `rules/verra/judge_rubric.yaml` + `rules/verra/rubrics/*.yaml` (new); `src/pdd_agent/review/judge.py` (`_RUBRIC_PATH`, `_QUANTITATIVE_SECTIONS`, rubric selection); `src/pdd_agent/llm/budget.py` + `configs/model_pricing.yaml` (new); `src/pdd_agent/doctor.py`; `src/pdd_agent/phase05/provider_scorecard.py` + `src/pdd_agent/cli.py` (`prove` verb); `tests/test_methodology_matrix.py` (new); `src/pdd_agent/service/main.py` (batch approve); `src/pdd_agent/ingest/extract.py` + `src/pdd_agent/export/docx_export.py` (evidence flow); `schemas/project_input.py` (`EvidenceRegistry`, `technology.methodology_ids`, `technology.technology_type`).
- **Out of scope:** Any change requiring `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` or a running Ollama instance in tests; the frontier-LLM proof run itself; the per-family `ProjectInput` schema split (DEC-004 — deferred to a second real non-WTE project); the Monitoring-Report product; new methodology families beyond the existing four; splitting `service/main.py`, `section_orchestrator.py`, `docx_export.py` (only `cli.py` is split here); real Verra registry corpus download.

## Environment & Conventions
- **Stack:** Python 3.11+ (`requires-python = ">=3.11"`). Packaging via `hatchling` (wheel targets `src/pdd_agent` and `schemas`). Pydantic v2 for `schemas/project_input.py`. `structlog` event-style logging. `argparse` CLI. FastAPI + Jinja2 for the optional service. Dependency/lock management shows both `pip` and `uv` in use (`uv.lock` present); commands below use `pip`/`python -m` which work in the committed `.venv`.
- **Setup:** `pip install -e ".[dev,service,export,llm]"`
- **Build / Run:** No build step for library use. Service: `uvicorn pdd_agent.service.main:app --reload` then open `http://localhost:8000/dashboard`. CLI entry point: `pdd-agent <command>` (console script `pdd_agent.cli:main`).
- **Test:** Full suite (the CI target): `python -m pytest -m "not corpus" -q`. Single file: `python -m pytest tests/test_service.py -v`. Single test: `python -m pytest tests/test_service.py::TestDocxExport::test_docx_export_force_override -v`. Corpus-marked tests (`-m corpus`) require `data/corpus/normalized/` and are **excluded** from CI.
- **Lint/format:** `ruff` with `line-length = 100`, `target-version = "py311"`. Run: `ruff check .` and `ruff format --check .`.
- **Conventions & traps:** Tests must NEVER require API keys, network access, or a running Ollama instance — mock all HTTP. `demo`/`noop` providers are the safe default; real providers (`openai`, `anthropic`) are opt-in via `{PROVIDER}_API_KEY` and require `PDD_MAX_COST_USD`. `.env` in the invocation directory is auto-loaded via `python-dotenv`; never commit one. Dataclasses everywhere except `ProjectInput` (Pydantic v2). Optional external tools (`gws`, LibreOffice) must degrade gracefully. Currency is USD; token pricing is USD per 1M tokens in `_DEFAULT_PRICING` (values are dollars-per-million: `"gpt-4o": {"input": 2.50, "output": 10.00}`).
- **Repo map:**
  - `src/pdd_agent/agent/section_orchestrator.py` — per-section retrieval → prompt assembly → provider call → review gate. `_build_prompt()` assembles the prompt; some prompt discipline is inlined here, some in `prompts/section_draft_v2.md`.
  - `src/pdd_agent/review/judge.py` — `LLMJudge`, rubric loading (`_RUBRIC_PATH`), `_QUANTITATIVE_SECTIONS`, deterministic + `use_llm` scoring paths.
  - `src/pdd_agent/calc/methodology.py` — `MethodologyEngine` Protocol with `methodology_id`. Engines: `acm0022.py`, `rice_vm0051.py`, `biochar_vm0044.py`, `cookstove_amsiig.py`.
  - `schemas/project_input.py` — `ProjectInput`; `technology.methodology_ids: list[str]`, `technology.technology_type: Literal[...]`, `EvidenceRegistry`/`EvidenceItem`, `evidence_registry` field.
  - `src/pdd_agent/llm/budget.py` — `TokenBudget`, `_DEFAULT_PRICING`.
  - `src/pdd_agent/phase05/provider_scorecard.py` — `run_provider_scorecard()`; `src/pdd_agent/cli.py` — 17 argparse subcommands incl. existing `scorecard`.
  - `configs/projects/` — `demo_socson_like.yaml` (WTE), `rice_vm0051_pilot.yaml` (rice), plus `.assumptions.yaml` companions.
  - `tests/` — 48 test files, all WTE-shaped fixtures; no `parametrize`.

## Research Inputs
- From `research/2026-07-13-pdd-post-reality-gap-next-level-brainstorm.md`:
  - The sharpest new finding: **breadth is calc-real but prompt-blind.** `prompts/section_draft_v2.md` opens "specializing in Verra VCS carbon credit PDDs **for waste-to-energy projects**" and cites `[CALC:]` as "the **ACM0022** calculation engine"; `judge_rubric.yaml` is `bucket: "verra-wte-initial"` and hardcodes ACM0022 in `NO_FABRICATED_FACTS`. A real-LLM rice draft would be prompted and judged as WTE. This is a prerequisite for any real non-WTE proof.
  - The rice pilot "worked" only because it used the deterministic `demo` provider (a rice text template was bolted onto `DemoProvider`). Three real bugs surfaced because every existing test fixture is WTE-shaped; a methodology-parametrized test matrix is the systemic fix for that bug class.
  - `pytest.mark.parametrize` count in the suite is **zero**; adding a family dimension over `{wte, rice, biochar, cookstove}` fixtures makes WTE-shaped assumptions fail loudly in CI.
  - There is **no `.github/workflows`**; a single Actions job (`pytest -m "not corpus"` + `ruff`) is the highest value-per-hour item and should land first, protecting every other change.
  - `_DEFAULT_PRICING` is hardcoded and will drift as model IDs/prices churn; move to YAML and have `doctor` warn on missing pricing entries.
  - `EvidenceRegistry`/`EvidenceItem` exist and are validated at the export gate (`docx_export.py:_check_evidence_registry`) and judge, but nothing populates them at intake, injects `[E###]` IDs into the prompt, or renders the appendix from the registry object — it is ~60% built.
  - The rice pilot logged a batch approve-all defect in the section-review service ("did not fully apply — a batch/state-machine interaction not investigated further"); a human reviewing 36 sections will hit it.
  - Recommended sequencing: CI first (hours), then prompt+rubric+test-matrix parametrization (non-key-gated, determines whether the frontier proof validates breadth or only WTE), then one-command proof, then debt paydown.

## Assumptions and Constraints
- **DEC-001:** Methodology selection key is `ProjectInput.technology.methodology_ids` (a `list[str]`, e.g. `["ACM0022"]`, `["VM0051"]`) with `technology.technology_type` (e.g. `"rice_awd"`) as a secondary signal. This is already how `domain/methodology_rules.py` branches (`if "ACM0022" in tech.methodology_ids`).
- **DEC-002:** The four in-scope families and their canonical methodology IDs are: WTE=`ACM0022`, rice=`VM0051`, biochar=`VM0044`, cookstove=`AMS-II.G` (from the July-5 brainstorm DEC-010/Q-001 resolution and the existing calc engines).
- **DEC-003:** Backward compatibility is mandatory: any project whose methodology has no overlay/rubric falls back to the current WTE behavior unchanged, so all 606 existing tests keep passing.
- **CON-001:** Tests must not require API keys, network, or Ollama. All new tests use `demo`/`noop` providers or mock HTTP.
- **CON-002:** `ruff` line-length 100 and `ruff format` must pass on all new/modified files.
- **ASM-001:** The GitHub remote uses GitHub Actions (standard `.github/workflows/`). — **BINDING DEFAULT:** Write a GitHub Actions workflow at `.github/workflows/ci.yml`; if the project later moves to GitLab/other CI, the same two commands (`pip install -e ".[dev,service,export,llm]"`, `python -m pytest -m "not corpus" -q`, `ruff check .`) transfer directly.
- **ASM-002:** The CI runner should test a representative Python version. — **BINDING DEFAULT:** Run on `ubuntu-latest` with Python `3.11` and `3.12` in a matrix (min supported + one forward), using `pip`, since the suite is OS-independent (no Windows-only paths in `src/`).
- **ASM-003:** The methodology→section-quantification map differs per family (WTE quantification lives in `1.10`/`4.x`; rice in different subsections). — **BINDING DEFAULT:** Introduce a per-methodology `quantitative_sections` list in each rubric file; for methodologies without an explicit list, fall back to the current `{"1.10", "4.1", "4.2", "4.4"}`. Populate WTE with the current set and rice/biochar/cookstove with the same set initially (documented as provisional in the rubric file header) until a registered PDD refines them — this keeps behavior identical for WTE and safe for others.
- **ASM-004:** The batch-approve defect is a read-modify-write race in `ReviewStateStore` when a client loops the per-section approve endpoint. — **BINDING DEFAULT:** Fix by adding a single atomic `POST /api/runs/{run_id}/approve-all` endpoint that loads state once, approves all approvable sections in one in-memory pass, and saves once; do not attempt to make concurrent single-section writes lock-safe in this plan.
- **ASM-005:** Overlay prompt files are Markdown fragments concatenated into the assembled prompt, not full replacements. — **BINDING DEFAULT:** Each overlay contributes a methodology-scoped "Domain & Methodology Context" block; the methodology-neutral core carries all anti-hallucination/authority-order/marker rules.

## Specification
Methodology resolution logic (applied identically in the orchestrator and the judge):

1. Read `methodology_id` = first element of `project_input.technology.methodology_ids` if non-empty, else `None`.
2. Normalize: uppercase, strip whitespace (e.g. `"acm0022"` → `"ACM0022"`; `"AMS-II.G"` stays `"AMS-II.G"`).
3. Map `methodology_id` → family slug via this fixed table:
   - `ACM0022` → `wte`
   - `ACM0003` → `wte` (co-fire variant, same family)
   - `VM0051` → `rice`
   - `VM0044` → `biochar`
   - `AMS-II.G` → `cookstove`
   - anything else or `None` → `wte` (backward-compatible default per DEC-003)
4. The family slug selects: the prompt overlay file `prompts/methodologies/{family}.md` and the rubric file `rules/verra/rubrics/{family}.yaml`.
5. If the selected overlay or rubric file is absent, fall back to WTE (`prompts/methodologies/wte.md`, `rules/verra/rubrics/wte.yaml`), which must reproduce today's exact text/behavior.

Provider-availability logic for `pdd-agent prove` (reuse `provider_scorecard._is_provider_available`):
- `demo`, `noop`, `ollama` → always attempted.
- `openai`/`anthropic` → attempted only if `{PROVIDER}_API_KEY` is set AND `PDD_MAX_COST_USD` is a positive float; otherwise recorded as `skipped` with a reason, never an error.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | CI pipeline + config-driven model pricing | None | `.github/workflows/ci.yml`, `configs/model_pricing.yaml`, `doctor` pricing check |
| PHASE-02 | Methodology-parametrized drafting prompt | PHASE-01 | `prompts/methodologies/*.md`, family-aware `_build_prompt` |
| PHASE-03 | Methodology-parametrized judge rubric | PHASE-01 | `rules/verra/rubrics/*.yaml`, family-aware `LLMJudge` |
| PHASE-04 | Methodology-parametrized test matrix | PHASE-02, PHASE-03 | `tests/test_methodology_matrix.py`, per-family fixtures |
| PHASE-05 | One-command multi-provider proof | PHASE-03 | `pdd-agent prove`, per-provider judged scorecard |
| PHASE-06 | Architectural debt: evidence flow, batch-approve, cli split | PHASE-02, PHASE-03 | Evidence intake→prompt→appendix flow, `/api/runs/{id}/approve-all`, `src/pdd_agent/cli/` package |

## Detailed Phases

### PHASE-01 - CI Pipeline and Config-Driven Pricing
**Goal**
Establish continuous integration (the single highest value-per-hour item) and remove the hardcoded pricing table so no other phase can silently break the suite or mis-price a run. No behavior change to drafting.

**Tasks**
- [x] TASK-01-01: Add a GitHub Actions workflow running install + full non-corpus test suite + ruff on every push and PR.
- [x] TASK-01-02: Extract `_DEFAULT_PRICING` from `llm/budget.py` into `configs/model_pricing.yaml`; load it at module import with the current dict as an embedded fallback if the file is missing.
- [x] TASK-01-03: Add a pricing-coverage check to `pdd-agent doctor` that warns (not errors) when a configured judge/draft model has no pricing entry.

**File Changes**
- `.github/workflows/ci.yml` (create): GitHub Actions workflow. Triggers `on: [push, pull_request]`. One job `test` on `ubuntu-latest`, `strategy.matrix.python-version: ["3.11", "3.12"]`. Steps: checkout; `actions/setup-python` with the matrix version; `pip install -e ".[dev,service,export,llm]"`; `ruff check .`; `ruff format --check .`; `python -m pytest -m "not corpus" -q`. Do NOT run `-m corpus` (needs `data/corpus/normalized/`).
- `configs/model_pricing.yaml` (create): YAML mapping each model name to `{input: <usd_per_million>, output: <usd_per_million>}`, seeded from the current `_DEFAULT_PRICING` verbatim (`gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `claude-sonnet-5`, `claude-opus-4-8`, `claude-haiku-4-5-20251001`, `ollama-local`). Add a header comment: units are USD per 1,000,000 tokens.
- `src/pdd_agent/llm/budget.py` (modify): Replace the literal `_DEFAULT_PRICING` dict with a `_load_pricing()` function that reads `configs/model_pricing.yaml` (path resolved relative to repo root, same pattern as `judge.py`'s `_RUBRIC_PATH`) and falls back to the embedded dict (keep the current dict as `_FALLBACK_PRICING`) if the file is missing or unparseable. Leave `_estimate_cost`, `TokenBudget`, and all public APIs unchanged.
- `src/pdd_agent/doctor.py` (modify): Add a check that loads `configs/model_pricing.yaml` and the judge tier defaults (`_JUDGE_MODEL_TIER_DEFAULTS`) and prints a yellow/warning line for any model referenced by defaults or `PDD_JUDGE_MODEL`/`PDD_DRAFT_MODEL` env that has no pricing entry. Do not fail `doctor`'s exit code on a missing entry.

**Function Signatures**
- `_load_pricing() -> dict[str, dict[str, float]]` — returns the model→{input,output} USD-per-million pricing map from YAML, or `_FALLBACK_PRICING` if the file is absent/invalid.

**Test Specs**
- `tests/test_token_budget.py` (modify/add): `TokenBudget` cost estimation for `model="gpt-4o"`, 1,000,000 input + 1,000,000 output tokens → `estimated_cost_usd == 12.50` (unchanged from today, proving the YAML load is behavior-preserving).
- New test: monkeypatch `_load_pricing` source path to a nonexistent file → pricing falls back to `_FALLBACK_PRICING` and `gpt-4o` still prices at 2.50/10.00.
- New test: a model absent from the YAML (e.g. `"made-up-model"`) → `_estimate_cost` returns `0.0` for its own entry but still uses `fallback_key` behavior exactly as today (assert no exception).

**Dependencies**
- None (foundational).

**Exit Criteria**
- [ ] `.github/workflows/ci.yml` exists and its steps are copy-paste runnable locally: `ruff check . && ruff format --check . && python -m pytest -m "not corpus" -q` all pass.
- [ ] `python -m pytest -m "not corpus" -q` → `606 passed` (or more), `0 failed`.
- [ ] `configs/model_pricing.yaml` exists; deleting it does not break `python -m pytest tests/test_token_budget.py -q`.
- [ ] `pdd-agent doctor` runs and prints a pricing section without a non-zero exit.

**Phase Risks**
- **RISK-01-01:** CI fails on `ruff format --check` because existing files were never formatter-clean. Mitigation: run `ruff format .` once, commit the (whitespace-only) result in this phase, and confirm `python -m pytest -m "not corpus" -q` still passes before wiring the check into CI.

### PHASE-02 - Methodology-Parametrized Drafting Prompt
**Goal**
Split the WTE-hardcoded drafting instructions into a methodology-neutral core plus per-family overlays selected by the project's methodology, so a rice/biochar/cookstove draft is prompted with the correct domain framing and calc-engine name — while WTE output stays byte-for-byte identical.

**Tasks**
- [x] TASK-02-01: Create `prompts/methodologies/{wte,rice,biochar,cookstove}.md` overlay fragments; move the WTE-specific sentences out of `section_draft_v2.md` into `wte.md`, leaving `section_draft_v2.md` methodology-neutral.
- [x] TASK-02-02: Add a `_family_slug()` resolver and overlay-loading to `SectionOrchestrator`, and inject the selected overlay in `_build_prompt`.
- [x] TASK-02-03: Replace the inlined WTE-flavored `[CALC:]` phrasing in `_format_calc_injection`/`_build_prompt` with methodology-neutral phrasing that names the active methodology from `methodology_ids`.

**File Changes**
- `prompts/methodologies/wte.md` (create): The WTE-specific domain framing extracted from `section_draft_v2.md` — "waste-to-energy projects", ACM0022/ACM0003 references, WTE examples. Must reproduce the exact domain sentences currently in `section_draft_v2.md` so WTE prompts are unchanged.
- `prompts/methodologies/rice.md` (create): Rice/VM0051 AWD (alternate-wetting-and-drying) domain framing; methane-reduction-via-water-management; names the VM0051 calc engine for `[CALC:]`.
- `prompts/methodologies/biochar.md` (create): Biochar/VM0044 domain framing; carbon-removal-via-pyrolysis; names the VM0044 calc engine.
- `prompts/methodologies/cookstove.md` (create): Cookstove/AMS-II.G domain framing; fuel-efficiency/thermal-energy; names the AMS-II.G calc engine.
- `prompts/section_draft_v2.md` (modify): Remove the WTE-specific Role sentence and the "ACM0022 calculation engine" phrasing; keep all methodology-neutral content (Authority Order, Anti-Hallucination Protocol, marker table, content-class rules). Add a placeholder comment `<!-- Domain overlay injected at runtime from prompts/methodologies/{family}.md -->`.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): Add module-level `_METHODOLOGY_FAMILY = {"ACM0022": "wte", "ACM0003": "wte", "VM0051": "rice", "VM0044": "biochar", "AMS-II.G": "cookstove"}` and `_PROMPTS_METHODOLOGY_DIR = _PROMPTS_DIR / "methodologies"`. Add `_family_slug()` and `_load_overlay()` methods. In `_build_prompt`, after the authority/marker block, append the loaded overlay text. In `_format_calc_injection`, replace `"Methodology: {cr.methodology_version}"` hardcoding of ACM0022 phrasing with the resolved methodology id. Leave retrieval, fact-provenance, and project-summary assembly unchanged.

**Function Signatures**
- `SectionOrchestrator._family_slug(self) -> str` — returns the family slug (`"wte"|"rice"|"biochar"|"cookstove"`) from `self._project.technology.methodology_ids`, defaulting to `"wte"` when unknown/empty.
- `SectionOrchestrator._load_overlay(self) -> str` — returns the Markdown text of `prompts/methodologies/{family}.md`, falling back to `prompts/methodologies/wte.md` when the family file is missing.

**Test Specs**
- `tests/test_prompt_assembly.py` (modify/add): Build an orchestrator with a WTE project (`methodology_ids=["ACM0022"]`) → assembled prompt contains "waste-to-energy" (via overlay) and the assembled prompt for section `4.1` still contains the calc injection. Assert the WTE assembled prompt string is unchanged vs a saved golden (or contains the same key WTE phrases as before this phase).
- New: orchestrator with `methodology_ids=["VM0051"]`, `technology_type="rice_awd"` → `_family_slug() == "rice"`; assembled prompt contains rice/AWD framing and does NOT contain "waste-to-energy" or "landfill".
- New: orchestrator with `methodology_ids=["VM0044"]` → `_family_slug() == "biochar"`; with `["AMS-II.G"]` → `"cookstove"`.
- Edge: `methodology_ids=[]` or `["UNKNOWN"]` → `_family_slug() == "wte"` and `_load_overlay()` returns the WTE overlay (backward-compatible).
- Edge: delete `prompts/methodologies/rice.md` at test time → `_load_overlay()` for a rice project returns the WTE overlay without raising.

**Dependencies**
- PHASE-01 (CI must be green so the golden-equivalence assertion is enforced).

**Exit Criteria**
- [ ] `python -m pytest tests/test_prompt_assembly.py tests/test_section_orchestrator.py -q` → all pass.
- [ ] `python -m pytest -m "not corpus" -q` → still `606 passed` (WTE behavior unchanged) plus the new prompt tests.
- [ ] A rice project's assembled prompt (printed via a scratch script or test) contains no "waste-to-energy"/"landfill"/"biogas" strings.

**Phase Risks**
- **RISK-02-01:** Moving WTE sentences out of `section_draft_v2.md` accidentally changes the WTE prompt string, breaking a downstream snapshot. Mitigation: capture the current WTE assembled prompt as a golden fixture BEFORE editing, then assert equality after.

### PHASE-03 - Methodology-Parametrized Judge Rubric
**Goal**
Make the LLM judge select its rubric and its quantitative-section map by methodology family, so rice/biochar/cookstove drafts are scored against family-appropriate criteria instead of the WTE `NO_FABRICATED_FACTS` ACM0022 binding.

**Tasks**
- [x] TASK-03-01: Move `rules/verra/judge_rubric.yaml` content into `rules/verra/rubrics/wte.yaml` (verbatim) and create `rice.yaml`, `biochar.yaml`, `cookstove.yaml` from a shared skeleton with family-specific `NO_FABRICATED_FACTS` descriptions and a `quantitative_sections` list.
- [x] TASK-03-02: Add family resolution + rubric selection to `LLMJudge`; keep `rubric_path` override working; keep `rules/verra/judge_rubric.yaml` as a symlink-free copy or a thin pointer for backward compatibility.
- [x] TASK-03-03: Replace the module-level `_QUANTITATIVE_SECTIONS` constant with a per-rubric `quantitative_sections` value read from the selected rubric, defaulting to `{"1.10", "4.1", "4.2", "4.4"}`.

**File Changes**
- `rules/verra/rubrics/wte.yaml` (create): Exact copy of the current `judge_rubric.yaml`, plus a new top-level key `quantitative_sections: ["1.10", "4.1", "4.2", "4.4"]`.
- `rules/verra/rubrics/rice.yaml` (create): Same skeleton; `bucket: "verra-vm0051-rice"`; `NO_FABRICATED_FACTS.description` references the VM0051 calc engine; `quantitative_sections` per ASM-003 (provisional, documented in a header comment).
- `rules/verra/rubrics/biochar.yaml` (create): VM0044 analog.
- `rules/verra/rubrics/cookstove.yaml` (create): AMS-II.G analog.
- `rules/verra/judge_rubric.yaml` (modify): Keep it as the WTE default so any code path passing no family still works; add a header comment noting it is the WTE fallback and that family rubrics live in `rules/verra/rubrics/`.
- `src/pdd_agent/review/judge.py` (modify): Add `_RUBRICS_DIR = _RUBRIC_PATH.parent / "rubrics"` and the same `_METHODOLOGY_FAMILY` map (import from a shared location or duplicate as a small constant). Add a `methodology_ids: list[str] | None = None` parameter to `LLMJudge.__init__` (default `None`) that selects `rules/verra/rubrics/{family}.yaml`, falling back to `_RUBRIC_PATH` when the family file is absent or `methodology_ids` is `None`. Read `quantitative_sections` from the loaded rubric into `self._quantitative_sections` (a `set[str]`), defaulting to `{"1.10", "4.1", "4.2", "4.4"}`. Replace all uses of the module-level `_QUANTITATIVE_SECTIONS` with `self._quantitative_sections`. Leave `_resolve_model_name`, `_llm_judge_section`, and `_deterministic_judge_section` scoring logic otherwise intact.

**Function Signatures**
- `LLMJudge.__init__(self, provider_name: str = "demo", rubric_path: Path | None = None, pass_threshold: int | None = None, use_llm: bool = False, model_name: str | None = None, methodology_ids: list[str] | None = None) -> None` — constructs a judge; `methodology_ids` selects the family rubric when `rubric_path` is not explicitly given.
- `_family_slug_for(methodology_ids: list[str] | None) -> str` — module-level helper returning the family slug for a methodology list, defaulting to `"wte"`.

**Test Specs**
- `tests/test_judge.py` (or existing judge test file; modify/add): `LLMJudge()` with no args loads the WTE rubric and `self._quantitative_sections == {"1.10","4.1","4.2","4.4"}` (unchanged).
- New: `LLMJudge(methodology_ids=["VM0051"])` loads `rice.yaml` and `bucket == "verra-vm0051-rice"`.
- New: `LLMJudge(methodology_ids=["UNKNOWN"])` falls back to the WTE rubric without raising.
- New: `LLMJudge(rubric_path=<explicit path>, methodology_ids=["VM0051"])` honors the explicit `rubric_path` (explicit override beats family selection).
- Behavior-preservation: judging a WTE `DraftRun` fixture produces identical `JudgeResult.score`/`passed` values to before this phase (assert against the existing WTE judge test expectations).

**Dependencies**
- PHASE-01.

**Exit Criteria**
- [ ] `python -m pytest tests/ -k judge -q` → all pass.
- [ ] `python -m pytest -m "not corpus" -q` → no regressions.
- [ ] Grep confirms `judge.py` no longer references a module-level `_QUANTITATIVE_SECTIONS` for scoring (`grep -n "_QUANTITATIVE_SECTIONS" src/pdd_agent/review/judge.py` shows only the default fallback literal, not scoring-path usage).

**Phase Risks**
- **RISK-03-01:** The orchestrator or CLI constructs `LLMJudge` without passing `methodology_ids`, silently keeping WTE scoring for non-WTE runs. Mitigation: in this phase also thread `methodology_ids=self._project.technology.methodology_ids` at every `LLMJudge(...)` construction site (search `grep -rn "LLMJudge(" src/`), and add a test asserting a rice draft run is judged with the rice rubric end-to-end.

### PHASE-04 - Methodology-Parametrized Test Matrix
**Goal**
Add the missing family dimension to the test suite so the core draft→review→consistency→export path is exercised over all four families, converting the class of bug the rice pilot found by hand into a CI-enforced guarantee.

**Tasks**
- [x] TASK-04-01: Create minimal per-family `ProjectInput` fixtures (WTE, rice, biochar, cookstove) reusing existing configs where present.
- [x] TASK-04-02: Write a parametrized end-to-end test over the four families using the `demo` provider.
- [x] TASK-04-03: Add a parametrized assertion that each family selects the correct prompt overlay and judge rubric.

**File Changes**
- `tests/fixtures/methodology_projects.py` (create): Factory functions returning valid `ProjectInput` objects for each family. Reuse `configs/projects/demo_socson_like.yaml` (WTE) and `configs/projects/rice_vm0051_pilot.yaml` (rice) by loading them; construct minimal synthetic biochar (`methodology_ids=["VM0044"]`) and cookstove (`methodology_ids=["AMS-II.G"]`) inputs that satisfy `ProjectInput` validation (populate the three WTE-required fields — `waste_type`, `annual_waste_throughput`, `installed_capacity_mw` — with placeholders as the rice pilot did).
- `tests/test_methodology_matrix.py` (create): `@pytest.mark.parametrize("family", ["wte", "rice", "biochar", "cookstove"])` tests that: (a) draft all sections with the `demo` provider produces non-empty text for every section; (b) `review/consistency.py` net = baseline − project − leakage passes; (c) the export gate does not raise for an all-approved run; (d) `SectionOrchestrator._family_slug()` and `LLMJudge` select the matching overlay/rubric.

**Function Signatures**
- `make_project_input(family: str) -> ProjectInput` — returns a valid `ProjectInput` for the given family slug (`"wte"|"rice"|"biochar"|"cookstove"`).

**Test Specs**
- `make_project_input("biochar")` → a `ProjectInput` with `technology.methodology_ids == ["VM0044"]` that validates without error.
- Parametrized draft: for each family, `SectionOrchestrator(...).run()` with the `demo` provider → every canonical section has non-empty `text` and contains no other family's domain keywords (e.g. rice output contains no "landfill"; cookstove output contains no "rice paddy").
- Parametrized overlay/rubric: for `family="cookstove"`, `_family_slug() == "cookstove"` and `LLMJudge(methodology_ids=["AMS-II.G"])` loads `cookstove.yaml`.
- Edge: biochar/cookstove demo text — if `DemoProvider` has no template for a family, assert it falls back to generic (non-WTE-specific) text rather than emitting "municipal solid waste" (guards against the rice-pilot bug #1 recurring for the two untested families).

**Dependencies**
- PHASE-02 (overlays), PHASE-03 (rubrics).

**Exit Criteria**
- [ ] `python -m pytest tests/test_methodology_matrix.py -q` → all parametrized cases pass (≥ 4 families × cases).
- [ ] `grep -rc "parametrize" tests/test_methodology_matrix.py` → ≥ 1 (the suite now has real parametrization).
- [ ] `python -m pytest -m "not corpus" -q` → green including the new matrix.

**Phase Risks**
- **RISK-04-01:** `DemoProvider` lacks biochar/cookstove templates and emits WTE text, failing the keyword-absence assertion. Mitigation: if so, extend `DemoProvider`'s `technology_type`-keyed dispatch (same mechanism added for rice in the reality-gap push) with generic non-WTE fallbacks; this is expected work, not a blocker — it is precisely the WTE-shaped assumption the matrix is designed to surface.

### PHASE-05 - One-Command Multi-Provider Proof
**Goal**
Collapse the provider-scorecard checklist into a single command that runs a project through every available provider, judges each with the (now family-aware) LLM judge, and writes a head-to-head scorecard — skipping unkeyed providers gracefully so it runs today on `demo`+`ollama` and becomes the frontier proof by a model-string swap the moment a key lands.

**Tasks**
- [x] TASK-05-01: Add a `prove` subcommand that wraps `run_provider_scorecard` with provider auto-detection and per-provider judging.
- [x] TASK-05-02: Extend the scorecard rows with a judged pass-rate and per-provider estimated cost from `TokenBudget`.
- [x] TASK-05-03: Add convenience defaults so `pdd-agent prove --project inegol` resolves the Inegol config path.

**File Changes**
- `src/pdd_agent/phase05/provider_scorecard.py` (modify): Add an `auto` provider-selection mode that enumerates `["demo", "ollama", "openai", "anthropic"]`, keeps only those passing `_is_provider_available`, and records skipped ones with reasons in the rendered scorecard. In `_run_one_provider`, after drafting, construct `LLMJudge(provider_name=<judge_provider>, use_llm=<True only for keyed providers>, methodology_ids=<from project>)`, judge the run, and add `judged_pass_rate` and `estimated_cost_usd` to `ProviderScorecardRow`. Keep the deterministic judge for `demo`/`noop`.
- `src/pdd_agent/cli.py` (modify): Add a `prove` subparser: `--project`/`-p` (path or a known alias like `inegol`→`configs/demo/inegol_project_input.yaml`, `rice`→`configs/projects/rice_vm0051_pilot.yaml`, `socson`→`configs/projects/demo_socson_like.yaml`), `--providers` (default `auto`), `--output` (default `reports/provider-scorecard.md`). Wire to a `_run_prove(args, log)` handler mirroring the existing `_run_scorecard`.
- `src/pdd_agent/phase05/provider_scorecard.py` (modify `_render_scorecard`): Add columns for judged pass-rate (%) and estimated USD cost; add a "Skipped providers" section listing name + reason.

**Function Signatures**
- `run_provider_scorecard(input_path: Path, providers: list[str] | str, output_path: Path, judge: bool = True) -> Path` — runs the input through each available provider (or `"auto"`), optionally judges each, writes the scorecard markdown, returns its path.
- `_run_prove(args, log) -> None` — CLI handler resolving the project alias and invoking `run_provider_scorecard`.

**Test Specs**
- `tests/test_provider_scorecard.py` (or existing scorecard test; modify/add): `run_provider_scorecard(<rice yaml>, "auto", <tmp path>)` with only `demo` "available" (mock `_is_provider_available` to skip openai/anthropic/ollama) → scorecard file written; contains a `demo` row with a judged pass-rate; lists openai/anthropic as skipped with a reason.
- New: `pdd-agent prove --project rice --providers demo --output <tmp>` (invoked via the CLI main dispatcher with mocked args) → exit 0, scorecard exists.
- Edge: no providers available at all → scorecard still written, with all providers in the skipped section and a clear "no providers ran" note (never raises).

**Dependencies**
- PHASE-03 (family-aware judge so per-provider judging uses the right rubric).

**Exit Criteria**
- [ ] `pdd-agent prove --project rice --providers demo --output reports/prove-rice.md` → exit 0, file exists with a judged pass-rate column.
- [ ] Running `prove` with no API keys set does not error and marks `openai`/`anthropic` skipped.
- [ ] `python -m pytest -m "not corpus" -q` → green.

**Phase Risks**
- **RISK-05-01:** Auto mode attempts a real Ollama call in CI, violating the no-network constraint. Mitigation: `_is_provider_available("ollama")` must return False when no Ollama host responds; tests mock provider availability and never hit a live server. CI has no Ollama, so it is auto-skipped.

### PHASE-06 - Architectural Debt: Evidence Flow, Batch-Approve, CLI Split
**Goal**
Pay the three debts breadth is actively straining: make the evidence registry a living flow (intake → prompt → appendix), fix the logged batch-approve service defect atomically, and split the 814-line `cli.py` into a thin parser + per-command handlers.

**Tasks**
- [x] TASK-06-01: Populate `EvidenceRegistry` at intake and inject registered `[E###]` IDs into the drafting prompt.
- [x] TASK-06-02: Render the DOCX evidence appendix from the `EvidenceRegistry` object (single source of truth).
- [x] TASK-06-03: Add an atomic `POST /api/runs/{run_id}/approve-all` endpoint and a dashboard button; fix the read-modify-write batch defect.
- [ ] TASK-06-04: Split `src/pdd_agent/cli.py` into a `src/pdd_agent/cli/` package (thin `__main__`/parser + per-command handler modules), preserving the `pdd-agent` console-script entry point.

**File Changes**
- `src/pdd_agent/ingest/extract.py` (modify): When extracting a `ProjectInput`, register each extracted factual source as an `EvidenceItem` (sequential `E001`, `E002`, …) on `project_input.evidence_registry`, with `source_type` and `section_ref` set where known. Leave the extraction of scalar fields unchanged.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): In `_build_prompt`, add an "## Evidence Registry (cite these IDs)" block listing available `[E###]` IDs + descriptions from `project_input.evidence_registry`, so the LLM cites real IDs. Guard with `if project_input and project_input.evidence_registry`.
- `src/pdd_agent/export/docx_export.py` (modify): Render the evidence appendix from `project_input.evidence_registry` items (id, source_type, description, section_ref) instead of (or in addition to) any ad-hoc collection. Keep `_check_evidence_registry` export-gate validation intact.
- `src/pdd_agent/service/main.py` (modify): Add `@app.post("/api/runs/{run_id}/approve-all")` → `api_approve_all(run_id: str)` that loads the `ReviewStateStore` once, transitions every approvable section to `approved` in a single in-memory pass, saves once, and returns `{run_id, sections_approved, all_approved}`. Add a corresponding "Approve all" button to `templates/run_detail.html`. Leave the single-section `api_approve_section` endpoint unchanged.
- `src/pdd_agent/cli/__init__.py`, `src/pdd_agent/cli/parser.py`, `src/pdd_agent/cli/handlers/*.py` (create); `src/pdd_agent/cli.py` (delete or convert to a shim): Move each subcommand's handler (`_run_scorecard`, `_run_prove`, draft/review/judge/export/etc.) into `cli/handlers/`. Keep `main()` importable as `pdd_agent.cli:main` (either keep `cli.py` as a shim `from pdd_agent.cli.parser import main` or update `pyproject.toml` `[project.scripts]` to `pdd_agent.cli.parser:main`). If `pyproject.toml` is changed, note the console-script entry point moved.

**Function Signatures**
- `EvidenceRegistry.register(source_type: str, description: str, section_ref: str | None = None) -> str` — appends an `EvidenceItem` with the next sequential `E###` id and returns that id (use the existing `add`/constructor pattern in `schemas/project_input.py`).
- `api_approve_all(run_id: str) -> dict[str, Any]` — approves all approvable sections in one atomic load-modify-save and returns `{run_id, sections_approved, all_approved}`.

**Test Specs**
- `tests/test_extract.py` (modify): Extracting a `ProjectInput` from a fixture document populates `evidence_registry` with ≥ 1 `EvidenceItem` whose `evidence_id` matches `^E\d{3}$`.
- `tests/test_prompt_assembly.py` (add): With an `evidence_registry` containing `E001`, the assembled prompt for a HIGH-sensitivity section contains "E001".
- `tests/test_docx_export.py` (add): A run whose `project_input.evidence_registry` has two items exports a DOCX whose appendix lists both `evidence_id`s.
- `tests/test_service.py` (add): Create a demo run, `POST /api/runs/{id}/approve-all` → response `all_approved == True` and `sections_approved` equals the section count; a subsequent forced-free export succeeds (403 gate no longer triggers). This directly reproduces and guards the rice-pilot batch defect.
- `tests/test_cli.py` (add or modify): `pdd-agent --help` lists all existing subcommands plus `prove`; `python -c "from pdd_agent.cli import main"` (or the new entry path) imports without error.

**Dependencies**
- PHASE-02 (prompt assembly is where evidence IDs get injected), PHASE-03 (judge already validates `[E###]`).

**Exit Criteria**
- [ ] `POST /api/runs/{id}/approve-all` approves all 36 sections in one call in a test; the loop-race no longer reproduces.
- [ ] `python -c "import pdd_agent.cli"` and `pdd-agent --help` both succeed after the split; `pip install -e .` still exposes the `pdd-agent` console script.
- [ ] DOCX export appendix content is generated from `evidence_registry`.
- [ ] `python -m pytest -m "not corpus" -q` → green.

**Phase Risks**
- **RISK-06-01:** The `cli.py` split breaks the `pyproject.toml` console-script entry point or import paths used by tests/scripts. Mitigation: keep `pdd_agent/cli.py` as a one-line shim re-exporting `main`, so `pdd_agent.cli:main` keeps resolving and no `[project.scripts]` change is needed; verify with `pip install -e . && pdd-agent doctor`.
- **RISK-06-02:** Evidence appendix rendering double-counts items already rendered by the old ad-hoc path. Mitigation: make the registry the single source and delete the ad-hoc collection; assert exact appendix item count in the export test.

## Gotchas
- **Backward-compatibility is the acceptance bar for PHASE-02/03:** all 606 existing tests are WTE and must keep passing. Any change to WTE prompt text or WTE judge scoring is a regression, not an improvement. Capture WTE golden strings/scores before editing.
- **`methodology_ids` is a list, not a scalar.** Always resolve the family from the *first* element and uppercase-normalize; `AMS-II.G` contains a dot and a hyphen — do not strip them.
- **`_QUANTITATIVE_SECTIONS` is WTE-shaped** (`1.10`, `4.1`, `4.2`, `4.4`). Do not assume rice/biochar/cookstove quantification lives in the same subsections; ASM-003 keeps them identical-but-provisional until a registered PDD refines them — leave a header comment in each non-WTE rubric saying so.
- **Pricing units are USD per 1,000,000 tokens** (`"gpt-4o": {"input": 2.50}` = $2.50/M input tokens). Preserve exactly when moving to YAML or costs shift 1,000,000×.
- **Tests must never hit the network or require keys.** `prove`/scorecard auto-mode must mock provider availability in tests; CI has no Ollama and no keys, so real providers auto-skip — verify the skip path, don't assume it.
- **`ruff format --check` will be enforced by CI after PHASE-01.** Run `ruff format .` and commit before wiring the check, or the first CI run fails on pre-existing formatting.
- **The service persists per-run JSON via `ReviewStateStore`.** The batch-approve fix must load once and save once; do not call the single-section approve path in a server-side loop (that reintroduces the read-modify-write race).

## Verification Strategy
- **TEST-001:** `ruff check . && ruff format --check .` → exit 0, no findings.
- **TEST-002:** `python -m pytest -m "not corpus" -q` → `606 passed` or more, `0 failed`, `7 deselected`.
- **TEST-003:** `python -m pytest tests/test_methodology_matrix.py -q` → all family-parametrized cases pass.
- **TEST-004:** `python -m pytest tests/test_prompt_assembly.py -k "rice or overlay" -q` → rice assembled prompt contains no "waste-to-energy"/"landfill".
- **TEST-005:** `pdd-agent prove --project rice --providers demo --output reports/prove-rice.md && test -f reports/prove-rice.md` → exit 0, scorecard has a judged pass-rate column.
- **MANUAL-001:** Start the service (`uvicorn pdd_agent.service.main:app --reload`), create a demo run, click "Approve all" on the run-detail page → all sections show `approved` and the DOCX export button no longer returns 403.
- **MANUAL-002:** Run `pdd-agent doctor` → the pricing section lists all configured models; a deliberately-removed pricing entry produces a warning line but exit code stays 0.
- **OBS-001:** Confirm the GitHub Actions run (Actions tab) is green on both `3.11` and `3.12` for a PR containing these phases.

## Risks and Alternatives
- **RISK-001:** Parametrizing prompts/rubrics subtly shifts WTE output, invalidating the existing Inegol/Soc Son demo artifacts. Mitigation: golden-equivalence tests for WTE in PHASE-02/03; the WTE overlay and `wte.yaml` are verbatim extractions.
- **RISK-002:** The four-family matrix surfaces more WTE-shaped assumptions than budgeted (as the rice pilot did with 3 bugs). Mitigation: this is the intended outcome; each surfaced bug is a fix-in-place, and PHASE-04 explicitly expects `DemoProvider` template gaps for biochar/cookstove.
- **ALT-001:** Keep one wide WTE prompt and rely on the model to adapt per project. Rejected: the July-13 brainstorm shows the current prompt *instructs* the model it is drafting a WTE project — the model will follow the instruction, not infer around it; breadth stays unproven.
- **ALT-002:** Do the per-family `ProjectInput` schema split now (discriminated union). Rejected/deferred (DEC-004): the rice pilot re-confirmed the wide schema handles non-WTE families with placeholder values; premature abstraction across families not yet drafted for real is the bigger risk. Revisit on the second real non-WTE project.
- **ALT-003:** Defer CI until after the parametrization work. Rejected: CI is the cheapest insurance for exactly the backward-compat regressions PHASE-02/03 risk; it must land first.

## Suggested Next Step
Execute PHASE-01 (CI + config-driven pricing). Its exit criteria — a green `.github/workflows/ci.yml` running `ruff` + `python -m pytest -m "not corpus" -q`, and a deletable `configs/model_pricing.yaml` that does not break the budget tests — are verifiable before PHASE-02 begins, and CI then guards every subsequent phase's backward-compatibility bar.
