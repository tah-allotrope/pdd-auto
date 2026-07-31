---
title: "Calc Spine, Cost Truth, and the First Real-Model Proof"
date: "2026-07-25"
status: "superseded — PHASE-01..05 landed in 47a4faf (final report reports/2026-07-25-calc-spine-cost-truth-final-report.md); the only remaining phase, PHASE-06 (build the production index + first real-model proof), is re-specified and extended by plans/2026-07-25-calc-correctness-and-audit-trail-plan.md, whose PHASE-01 already built data/index/corpus.fts.db and whose PHASE-06 covers the proof run."
request: "Implement Track A1-A4 (claude-code token/cost truth, provider preamble stripping, build the production index, run the first real-model proof) and Track B1-B4 (calc dispatch layer, generalized per-family calc injection, wire calc into the three orchestrator entry points, pdd-agent calc command), with Track F1-F4 documentation truth-sync and hygiene riding along."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-25-pdd-calc-spine-cost-truth-and-unrun-proof-brainstorm.md"
  - "research/2026-07-23-pdd-run-the-proof-and-close-the-loop-brainstorm.md"
---

# Plan: Calc Spine, Cost Truth, and the First Real-Model Proof

## Objective
Connect the repo's four already-built quantification engines (ACM0022, VM0051, VM0044, AMS-II.G — 1,796 lines with golden tests) to the drafting pipeline they have never been wired into, fix the `claude-code` provider's token and cost accounting (currently under-counting billed tokens by ~25× and reporting `$0.00` for runs that cost real money), strip assistant preamble that leaks into exported section bodies, and only then run the first full real-model proof (`pdd-agent prove`) so the resulting artifact shows computed-and-cited numbers, a truthful cost line, and clean section prose.

## Context Snapshot
- **Current state:**
  - `SectionOrchestrator.set_calc_result()` (`src/pdd_agent/agent/section_orchestrator.py:997`) has **zero callers** anywhere in `src/`, `scripts/`, or `tests/`. No CLI subcommand computes a calc result. `provider_scorecard._run_one_provider` and `service.main._execute_run` both build `SectionOrchestrator(...)` without one. Therefore `_should_inject_calc()` (line 219) has returned `False` on every run ever executed, and the `[CALC: ...]` citation block produced by `_format_calc_injection` (lines 234–280) has never appeared in any draft. `check_quantitative_consistency(..., calc_result=...)` (`src/pdd_agent/review/consistency.py:88`) is likewise always called with `calc_result` unset (`section_orchestrator.py:935`).
  - `_format_calc_injection` reads `ACM0022CalcResult`-only attributes (`baseline_methane_swds_tco2e`, `project_electricity_consumption_tco2e`, `organic_waste_to_ad_tonnes`, …). Passing a rice/biochar/cookstove result through it raises `AttributeError`.
  - `ClaudeCodeProvider._call_cli` (`src/pdd_agent/llm/claude_code_provider.py:132-140`) records only `usage.input_tokens + usage.output_tokens` and hardcodes `cost_usd=0.0`. Measured on 2026-07-25 with one real drafting call: `input_tokens 9, output_tokens 1053, cache_creation_input_tokens 25346, cache_read_input_tokens 0, total_cost_usd 0.167898` — i.e. the provider recorded 1,062 tokens and $0.00 for a call that billed ≈26,400 tokens and $0.168. The `TokenBudget(max_tokens=500_000)` ceiling set by `prove` is therefore effectively inert for this provider.
  - The same measured call returned text beginning `"I'll draft a conservative summary paragraph for section 1.1.1 …"` before the real content. All four real providers assign `text = response.text[:max_chars]` with no preamble stripping (`claude_code_provider.py:210`, `openai_provider.py:190`, `anthropic_provider.py:197`, `ollama_provider.py:181`), so that chatter reaches the exported DOCX.
  - `data/index/corpus.fts.db` does not exist in a fresh checkout; `get_retrieval_index()` (`src/pdd_agent/retrieval/index.py:280-291`) falls back to `data/index/demo.fts.db`, a 3-document bundled subset, while 17 normalized documents sit unused in `data/corpus/normalized/`.
  - `reports/` contains no `prove-*.md` or `provider-scorecard.md`: `pdd-agent prove` has never been run against a real provider.
  - Documentation drift: `README.md:5` claims "686 tests collected" (actual: 735 passed / 7 deselected); `README.md:311` calls `llm/ollama_provider.py` a stub that is "not yet a real HTTP client" (it is a working 230-line HTTP client); `README.md:328` claims the FastAPI service "forces the `demo` provider and disables corpus retrieval regardless of configuration" (it resolves `demo`/`noop`/`ollama`/`openai`/`anthropic` with documented fallbacks). `CLAUDE.md` names `plans/2026-07-12-pdd-reality-gap-plan.md` as the current push (two plans stale).
- **Desired state:**
  - A single `compute_for(project_input)` entry point returns a family-agnostic `PddCalcResult` for ACM0022 / VM0051 / VM0044 / AMS-II.G projects, or `None` with a logged reason when required inputs are absent.
  - Calc results are computed and injected for **real-provider runs only** at all three orchestrator construction sites, and flow into `check_quantitative_consistency`.
  - `pdd-agent calc --input <yaml>` prints and writes the full component breakdown with zero LLM calls.
  - `ClaudeCodeProvider` records all four token classes and the CLI's own `total_cost_usd`, so `PDD_MAX_COST_USD` and `TokenBudget` actually bind.
  - Real-provider output is normalized: no leading "I'll draft…" preamble, no trailing "Let me know if…" tail.
  - `reports/prove-inegol-claude-code.md` and `reports/prove-rice-claude-code.md` exist, produced by real runs, alongside `docs/2026-07-25-first-real-model-proof-findings.md`.
  - `README.md`, `CLAUDE.md`, and `activeContext.md` describe the repo as it actually is.
- **Key repo surfaces:** `src/pdd_agent/llm/claude_code_provider.py`, `src/pdd_agent/llm/budget.py`, `src/pdd_agent/llm/openai_provider.py`, `src/pdd_agent/llm/anthropic_provider.py`, `src/pdd_agent/llm/ollama_provider.py`, `src/pdd_agent/calc/` (`acm0022.py`, `rice_vm0051.py`, `biochar_vm0044.py`, `cookstove_amsiig.py`, `models.py`, `methodology.py`), `src/pdd_agent/agent/section_orchestrator.py`, `src/pdd_agent/phase05/provider_scorecard.py`, `src/pdd_agent/service/main.py`, `src/pdd_agent/cli.py`, `src/pdd_agent/review/consistency.py`, `schemas/project_input.py`, `configs/model_pricing.yaml`, `configs/projects/demo_socson_like.yaml`, `configs/projects/rice_vm0051_pilot.yaml`, `configs/demo/inegol_project_input.yaml`.
- **Out of scope:**
  - Packaging/distribution rework (moving `rules/`, `prompts/`, `configs/`, `templates/` into package data; replacing `REPO_ROOT = Path(__file__).resolve().parents[3]`; introducing `PDD_HOME`). Deliberately deferred to a follow-on plan.
  - Persisting calc results into `DraftRun` JSON and feeding them to `check_export_gate` in `src/pdd_agent/export/docx_export.py:192` (the export path loads runs by ID and has no calc result available). Not changed here.
  - Batching multiple sections per CLI invocation, or parallelizing section drafting. Both are follow-ups whose value is only measurable after PHASE-06 produces real per-section timings.
  - Making `claude-code` selectable in the FastAPI service (`_get_provider` in `src/pdd_agent/service/main.py:99`), run-store pagination/retention, and the Verra registry live-search capture (PHASE-04 of `plans/2026-07-23-run-real-model-proof-plan.md`). All independent; none blocks this plan.
  - Renaming `src/pdd_agent/phase05/` and `phase06/` to domain names.
  - Any change to the per-family `ProjectInput` schema shape.

## Environment & Conventions
- **Stack:** Python 3.11+ (`requires-python = ">=3.11"`), packaged with `hatchling`. Pydantic v2 for `schemas/project_input.py` and all `src/pdd_agent/calc/` models; plain dataclasses elsewhere. `structlog` event-style logging: `logger.warning("event_name", key=value)` — never f-string log messages. `argparse` CLI, console script `pdd-agent = pdd_agent.cli:main`. Dependency management: `uv` with a committed `uv.lock`; a `pip install -e` path also works and is what the primary CI job uses.
- **Setup:** `pip install -e ".[dev,service,export,llm]"` (pip path) **or** `uv sync --all-extras` (uv path).
- **Build / Run:** No build step. Run the CLI as `pdd-agent <command>` or `uv run --no-sync pdd-agent <command>`.
- **Test:** Full suite: `python -m pytest -m "not corpus" -q` (baseline before this plan: **735 passed, 7 deselected**, ~82s). Single file: `python -m pytest tests/test_claude_code_provider.py -v`. Single test: `python -m pytest tests/test_calc_dispatch.py::TestComputeFor::test_rice_project_returns_result -v` (that test is created in PHASE-03).
  - **Windows note:** a foreign `PYTHONPATH` can leak in from unrelated tooling and break collection with unrelated `ModuleNotFoundError`s. Clear it first: `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` (POSIX shell / Git Bash) or `$env:PYTHONPATH=''; uv run --no-sync python -m pytest -m "not corpus" -q` (PowerShell).
- **Conventions & traps:**
  - `ruff` with `line-length = 100`, `target-version = "py311"`. Run `ruff check .` and `ruff format .` before committing. CI runs `ruff check .`, `ruff format --check .`, the test suite on Python 3.11 and 3.12, plus a separate `lock-reproducibility` job running `uv lock --check` and `uv sync --locked --all-extras`.
  - **Tests must never require API keys, network access, a running Ollama instance, or an installed `claude`/`gws` CLI.** Mock all HTTP (`urllib.request.urlopen`), all `subprocess.run`, and all `shutil.which` calls. This is load-bearing for PHASE-01/02.
  - `demo` and `noop` providers are the safe default everywhere; real providers are opt-in via environment variables. Existing demo and benchmark artifacts under `reports/demo-packages/` are committed to git and must stay byte-identical — see CON-002.
  - **Units:** all emissions values are **tCO2e per year** unless the field name says otherwise; `crediting_period_total_tco2e` is an absolute total over the crediting period (annual net × years). Model pricing in `configs/model_pricing.yaml` is **USD per 1,000,000 tokens**. Grid emission factors are **tCO2/MWh**. Rice emission factors are **kg CH4 per hectare per day**. Cookstove fuel figures are **kg per day per stove**; NCV is **MJ/kg**; fuel emission factors are **kg CO2/MJ**.
  - `.env` in the invocation directory is auto-loaded via `python-dotenv`; never commit one.
- **Repo map:**
  - `src/pdd_agent/calc/` — four quantification engines plus seven CDM tool modules. `acm0022.py` exposes `ACM0022Calculator(ACM0022CalcInput).calculate() -> ACM0022CalcResult`. `rice_vm0051.py`, `biochar_vm0044.py`, `cookstove_amsiig.py` each expose an engine class implementing the `MethodologyEngine` protocol in `methodology.py` (`methodology_id()`, `validate_inputs(dict)`, `compute_baseline(dict)`, `compute_project(dict)`, `compute_leakage(dict)`, `compute_net(dict)`, `required_monitoring_params(dict)`), returning `ComputationResult(value, unit, formula, provenance, notes)`.
  - `src/pdd_agent/agent/section_orchestrator.py` — 999-line orchestrator: retrieval → prompt assembly → provider call → judge/redraft → review. Calc-relevant methods: `_should_inject_calc` (219), `_is_quantification_section` (231), `_format_calc_injection` (234), `set_calc_result` (997), `run_review` (878, calls `check_quantitative_consistency` at 935).
  - `src/pdd_agent/llm/` — provider implementations plus `budget.py` (`TokenBudget`, `CallRecord`), `env_config.py` (`configure_provider_from_env`), `judge_selection.py` (never-self-judge resolution shared by the orchestrator and the scorecard).
  - `src/pdd_agent/phase05/provider_scorecard.py` — the engine behind `pdd-agent prove`; `_run_one_provider` builds one orchestrator per provider.
  - `src/pdd_agent/service/main.py` — FastAPI service; `_execute_run` (329) builds the orchestrator for background runs.
  - `src/pdd_agent/cli.py` — 20 subcommands; `_run_draft` at line 475, `_run_prove` at line 678 (with its live `project_aliases` dict at line 684 mapping `socson`/`inegol`/`rice`).
  - `schemas/project_input.py` — top-level package **outside** `src/`, imported as `from schemas.project_input import ProjectInput`. Root model fields: `project`, `location`, `dates`, `technology`, `methodology_applicability`, `quantification`, `monitoring`, `safeguards`, `compliance_and_ownership`, `sustainable_development`, plus optional `generation_controls`, `review_flags`, `evidence_registry`, `suggested_methodologies`, `extraction_provenance`.

## Research Inputs
- From `research/2026-07-25-pdd-calc-spine-cost-truth-and-unrun-proof-brainstorm.md`:
  - `grep -rn "set_calc_result" --include=*.py .` returns exactly one hit: the method definition itself. The calc engines are an island — an entire receiving apparatus (`_should_inject_calc`, `[CALC:]` citation format, `docx_export(calc_result=…)`, `consistency._check_calc_vs_project_input`) with no sender. Read as unfinished wiring rather than intent.
  - Two bounded real `claude` CLI calls were measured on 2026-07-25. Trivial prompt: 3.0s, `total_cost_usd 0.0821625`, `cache_creation_input_tokens 12,614`, `cache_read_input_tokens 21,375`, `input_tokens 2`, `output_tokens 4`. Real drafting call (the repo's own `_build_prompt("1","1.1")` output for the Inegol project, 1,101 chars, plus the 247-char family system prompt): **36.1s**, `total_cost_usd 0.167898`, `input_tokens 9`, `output_tokens 1,053`, `cache_creation_input_tokens 25,346`, `cache_read_input_tokens 0`, 2,026 chars returned.
  - Cost is dominated by ~25k tokens of per-invocation CLI harness overhead, not by the ~300-token section prompt — so cost scales with **call count**, not prompt size. Extrapolation from the measured figures: 36 sections ≈ 22 minutes and ≈ $6 per project run; two projects ≈ $12; worst case with three redrafts per section ≈ $48.
  - The measured output began with `"I'll draft a conservative summary paragraph for section 1.1.1 using the project-specific facts provided. Since no corpus examples are available, I'll mark elements that typically require verification. --- # 1.1.1 Summary Description of the Project …"`. Neither `demo` nor `noop` ever produced chatter, so no existing test covers this.
  - `data/index/corpus.fts.db` is absent, so a "corpus-grounded" proof would silently run against the 3-document demo index; build the production index first and record which index was used.
  - Documentation drift list (README test count, Ollama "stub" description, service "forces demo" claim, stale `CLAUDE.md` plan pointer, dead `_PROJECT_ALIASES` at `cli.py:188`, leaked `data/index/__nonexistent_test.fts.db`).
- From `research/2026-07-23-pdd-run-the-proof-and-close-the-loop-brainstorm.md`:
  - The in-loop redraft judge's self-judging default was fixed in commits `4266be1` (shared `src/pdd_agent/llm/judge_selection.py`) and `aae79b3` (orchestrator wiring), so a real-provider run no longer lets a provider judge its own output. With no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` and no local Ollama, `resolve_judge_provider("claude-code")` falls through to `("demo", use_llm=False)` — the deterministic rule-based judge, which makes zero extra model calls. The first proof run's judge cost is therefore $0, and the LLM judge is not exercised unless `PDD_JUDGE_PROVIDER` is set explicitly.
  - `pdd-agent prove` accepts `--project` (path or alias `socson`/`inegol`/`rice`), `--providers` (comma-separated or `auto`), `--output`, and `--no-judge`. That surface is unchanged by this plan.

## Assumptions and Constraints
- **ASM-001:** The generic calc result type should reuse `ACM0022CalcResult`'s summary attribute names so existing consumers keep working unchanged — grounded in `src/pdd_agent/review/consistency.py:416-419` and `schemas/project_input.py:261` (`QuantificationInputs.from_calc_result`), which both read `baseline_emissions_tco2e`, `project_emissions_tco2e`, `leakage_tco2e`, `net_emission_reductions_tco2e`, `crediting_period_total_tco2e`. **BINDING DEFAULT:** define `PddCalcResult` with exactly those five float attributes plus `crediting_period_years: int`, and add `methodology_id: str`, `components: list[CalcComponent]`, `monitoring_params: list[dict]`, `warnings: list[str]`, and a `to_prompt_block() -> str` method. Do **not** rename anything on `ACM0022CalcResult`.
- **ASM-002:** Whether calc injection should apply to `demo`/`noop` runs is unresolved by the repo. **BINDING DEFAULT:** calc results are computed and passed to the orchestrator **only when the drafting provider name is not `demo` and not `noop`** — mirroring the existing pattern at `src/pdd_agent/phase05/provider_scorecard.py` (`drafting_enable_judge = enable_judge and provider_name not in ("demo", "noop")`). This keeps every committed demo/benchmark artifact byte-identical (CON-002) and puts calc exactly where the real proof runs.
- **ASM-003:** The mapping from `ProjectInput` to each engine's input dict cannot be inferred from a single source of truth. **BINDING DEFAULT:** implement exactly the mappings written out in `## Specification`, returning `None` (with a `structlog` warning naming the missing field paths) whenever a required engine field has no source value. Never invent a default for a value that carries physical meaning (grid emission factor, feedstock carbon fraction, fuel emission factor).
- **ASM-004:** `ACM0022CalcInput.biomethanization_fraction` is required but `ProjectTechnology.biomethanization_suitable_fraction` is optional and absent from `configs/projects/demo_socson_like.yaml`. **BINDING DEFAULT:** when it is `None`, use `0.0` and append the warning string `"biomethanization_suitable_fraction absent; assumed 0.0 (no anaerobic digestion pathway)"` to `PddCalcResult.warnings`. `0.0` is inside the field's `ge=0` bound and yields zero biogas, which is the honest reading for an incineration-only project.
- **ASM-005:** `configs/demo/inegol_project_input.yaml` has `quantification.grid_emission_factor: null`, so ACM0022 inputs are incomplete for the Inegol project. **BINDING DEFAULT:** do **not** invent a grid emission factor for Türkiye. `compute_for` returns `None`, the run logs `calc_inputs_incomplete`, and PHASE-06 records "calc skipped — missing `quantification.grid_emission_factor`" as a finding. The rice project (`configs/projects/rice_vm0051_pilot.yaml`) has complete inputs and is the run that demonstrates a live calc spine.
- **ASM-006:** The exact wording that qualifies as assistant "preamble" is a judgement call. **BINDING DEFAULT:** implement exactly the deterministic rules numbered in `## Specification` §2. When stripping would empty the text, return the original text unchanged.
- **ASM-007:** Whether the CLI's `total_cost_usd` represents money the operator pays depends on their plan. **BINDING DEFAULT:** record it verbatim as the authoritative cost for `claude-code` calls and treat it as spend for budget-ceiling purposes; keep the `claude-code: {input: 0.0, output: 0.0}` entry in `configs/model_pricing.yaml` as the fallback used only when the CLI omits the field.
- **ASM-008:** PHASE-06 is an operational phase — its tasks are commands to run and artifacts to inspect, not files to author from scratch. **BINDING DEFAULT:** whoever executes this plan runs PHASE-06's commands deliberately, having read the measured cost table in `## Specification` §4 first (budget ≈ $6 and ≈ 22 minutes per project, worst case ≈ $48 for both projects if redrafts fire on every section).
- **CON-001:** Tests must not require API keys, network access, a running Ollama instance, or an installed `claude`/`gws` CLI. Every provider test mocks `subprocess.run`; every Ollama-adjacent test mocks `urllib.request.urlopen`.
- **CON-002:** Committed artifacts under `reports/demo-packages/` and the outputs of `python scripts/run_demo.py`, `python scripts/run_inegol_demo.py`, and `pdd-agent run-vietnam-pdd` must remain byte-identical after this plan. All of those run with `demo` or `noop` providers, which ASM-002 excludes from calc injection.
- **CON-003:** `ruff check .` and `ruff format --check .` must pass (line length 100), and `uv lock --check` must still succeed — this plan adds no new third-party dependency, so `uv.lock` must not change.
- **CON-004:** The full non-corpus suite must end at **≥ 735 passed, 7 deselected** — no existing test may be deleted or weakened to make new code pass.
- **DEC-001:** Judge behavior is not modified by this plan. `pdd-agent prove` keeps its existing `--project`, `--providers`, `--output`, `--no-judge` surface, and the never-self-judge resolution in `src/pdd_agent/llm/judge_selection.py` stays exactly as committed.
- **DEC-002:** Calc results are **not** persisted into `DraftRun` JSON and are **not** passed to `check_export_gate`; the export path is untouched.
- **DEC-003:** Preamble normalization is applied to all four real providers (`claude-code`, `openai`, `anthropic`, `ollama`) at their single shared `text = response.text[:max_chars]` line, and to neither `demo` nor `noop`.

## Specification

### §1 — `ProjectInput` → engine input mappings (PHASE-03)

Engine selection uses the **first** entry of `project_input.technology.methodology_ids`, uppercased and stripped. Recognized values and their engines:

| `methodology_ids[0]` | Engine | Input model |
|---|---|---|
| `ACM0022` | `pdd_agent.calc.acm0022.ACM0022Calculator` | `ACM0022CalcInput` |
| `VM0051` | `pdd_agent.calc.rice_vm0051.RiceVm0051Engine` | `RiceInput` |
| `VM0044` | `pdd_agent.calc.biochar_vm0044.BiocharVm0044Engine` | `BiocharInput` |
| `AMS-II.G` | `pdd_agent.calc.cookstove_amsiig.CookstoveAmsiigEngine` | `CookstoveInput` |

Anything else (including an empty list) → return `None` and log `calc_engine_unsupported` with the observed methodology id.

**ACM0022 mapping** (source → target):
1. `technology.waste_type` (a `list[str]`) and `technology.annual_waste_throughput` (float, tonnes/year) → `waste_streams`: one `WasteStream` per entry in `waste_type`, each with `annual_tonnes = annual_waste_throughput / len(waste_type)` (equal split) and `waste_type` set to the entry verbatim **only if** it is a key of `pdd_agent.calc.constants.DOC_BY_WASTE_TYPE` (`food_waste`, `garden_waste`, `paper_cardboard`, `wood`, `textiles`, `nappies`, `rubber_leather`, `municipal_solid_waste`). Entries that are not keys are dropped and named in `warnings` as `"waste_type '<value>' not in DOC_BY_WASTE_TYPE; excluded from the calc"`. If no entry survives, return `None` (missing: `technology.waste_type`).
2. `technology.biomethanization_suitable_fraction` → `biomethanization_fraction`; when `None`, apply ASM-004.
3. `quantification.grid_emission_factor` → `grid_emission_factor_tco2_per_mwh`. Required (`gt=0`): when `None`, return `None` with missing field path `quantification.grid_emission_factor`.
4. `quantification.grid_emission_factor_source` → `grid_emission_factor_source`. Required: when `None` or empty, return `None` with missing field path `quantification.grid_emission_factor_source`.
5. `technology.energy_generation_mwh_year` → `electricity_exported_mwh_per_year` (pass `None` through; the engine estimates from biogas when absent).
6. `quantification.methane_capture_rate` → `baseline_methane_captured_fraction`; when `None`, omit so the model default `0.0` applies.
7. `dates.crediting_period_years` → `crediting_period_years`.
8. Every other `ACM0022CalcInput` field keeps its model default. Do not pass `fossil_fuels` or RDF fields — no `ProjectInput` field carries them.

**VM0051 (rice) mapping:** require `technology.rice_cultivation` to be non-`None`; otherwise return `None` with missing field path `technology.rice_cultivation`. Then map field-for-field: `area_ha`, `cultivation_days`, `baseline_water_regime`, `baseline_ef_kg_ch4_per_ha_per_day`, `project_practices` (a `list[dict]` that Pydantic coerces to `list[RiceProjectPractice]`), `gwp_ch4`, plus `crediting_period_years` from `dates.crediting_period_years`.

**VM0044 (biochar) mapping:** require `technology.biochar_production`; otherwise return `None` with that field path. Map `feedstock_type`, `dry_mass_tonnes`, `carbon_fraction`, `pyrolysis_temperature_c`, `stability_factor`, `permanence_factor`, plus `crediting_period_years` from `dates.crediting_period_years`.

**AMS-II.G (cookstove) mapping:** require `technology.cookstove_fleet` to be a non-empty list; otherwise return `None` with that field path. Map each `CookstoveFleetEntry` to one `StoveEntry` field-for-field (`fuel_type`, `stove_count`, `baseline_fuel_kg_per_day_per_stove`, `project_fuel_kg_per_day_per_stove`, `operating_days_per_year`, `ncv_mj_per_kg`, `ef_kg_co2_per_mj`, `fnrb`) into `CookstoveInput.stoves`, plus `crediting_period_years` from `dates.crediting_period_years`.

**Result assembly for the three protocol engines** (VM0051 / VM0044 / AMS-II.G), given `inputs: dict`:

```
baseline = engine.compute_baseline(inputs).value      # tCO2e/year
project  = engine.compute_project(inputs).value       # tCO2e/year
leakage  = engine.compute_leakage(inputs).value       # tCO2e/year
net      = engine.compute_net(inputs).value           # tCO2e/year
crediting_period_total = net * crediting_period_years # tCO2e (absolute)
```

- `components` gets one `CalcComponent(name, value_tco2e, unit, formula, notes)` per `compute_*` call, using that `ComputationResult`'s `formula`, `unit`, and `notes`, with `name` in `{"baseline", "project", "leakage", "net"}`.
- `monitoring_params = engine.required_monitoring_params(inputs)`.
- **Do not recompute `net` as `baseline - project - leakage`.** Each engine's `compute_net` is authoritative (VM0051's, for example, works in kg CH4 before applying GWP, and re-deriving it from rounded tCO2e values introduces drift).

**Result assembly for ACM0022:** call `ACM0022Calculator(ACM0022CalcInput(**mapped)).calculate()`, then copy `baseline_emissions_tco2e`, `project_emissions_tco2e`, `leakage_tco2e`, `net_emission_reductions_tco2e`, `crediting_period_total_tco2e`, `crediting_period_years` straight across, and convert each entry of the result's `components: list[EmissionComponent]` (fields `name`, `value_tco2e`, `formula_ref`, `notes`) into a `CalcComponent` with `unit="tCO2e/year"` and `formula=formula_ref`. Keep a reference to the original object on `PddCalcResult.raw_result` so the existing ACM0022-specific prompt formatting can still be used (see §3).

### §2 — Assistant-preamble normalization (PHASE-02)

`strip_assistant_preamble(text)` applies these steps in order:

1. If `text` is empty or contains no non-whitespace characters, return it unchanged.
2. Split into lines preserving order. Define a line as *preamble-shaped* when, after stripping leading whitespace and Markdown emphasis characters (`*`, `_`), it matches the case-insensitive regex `^(i'?ll |i will |i'?m going to |let me |here'?s |here is |sure[,.! ]|certainly[,.! ]|of course[,.! ]|i'?ve drafted |below is )`.
3. **Horizontal-rule form:** if, among the first 5 non-empty lines, there is a line whose stripped form is exactly `---`, `***`, or `___`, **and** at least one non-empty line before it is preamble-shaped, drop every line up to and including that rule line.
4. **Leading-lines form** (applied when step 3 did not fire): drop leading non-empty lines while they are preamble-shaped, stopping at the first non-empty line that is not preamble-shaped or that starts with `#`.
5. **Trailing form:** if a line's stripped form matches the case-insensitive regex `^(let me know|would you like|i hope this helps|feel free to|note: i'?ve |shall i )`, drop that line and everything after it.
6. Strip leading and trailing blank lines from the result.
7. If the result contains no non-whitespace characters, return the **original** `text` unchanged.

Worked example (the real measured output): input `"I'll draft a conservative summary paragraph for section 1.1.1 using the project-specific facts provided. Since no corpus examples are available, I'll mark elements that typically require verification.\n\n---\n\n# 1.1.1 Summary Description of the Project\n\nThe project is …"` → output starting exactly at `"# 1.1.1 Summary Description of the Project"`.

### §3 — Calc prompt injection dispatch (PHASE-03)

`SectionOrchestrator._format_calc_injection` becomes a two-branch dispatch and keeps its current behavior for ACM0022:

1. If `self._calc_result` is `None` → return `""` (unchanged).
2. If the object exposes a callable `to_prompt_block` **and** its `methodology_id` is not `"ACM0022"` → return `self._calc_result.to_prompt_block()`.
3. Otherwise (an `ACM0022CalcResult`, or a `PddCalcResult` whose `raw_result` is one) → run the existing ACM0022 formatting code against `self._calc_result.raw_result or self._calc_result`, unchanged, so WTE prompt text stays byte-identical.

`PddCalcResult.to_prompt_block()` emits, in this exact order and format:

```
\n## {methodology_id} Calculation Engine Results\n
The following values were computed by the {methodology_id} pure-Python calculation engine.
Use these as the authoritative quantification values. Cite with `[CALC: component_name]`.

- **Baseline emissions**: {baseline:,.2f} tCO2e/year [CALC: baseline_total]
- **Project emissions**: {project:,.2f} tCO2e/year [CALC: project_total]
- **Leakage**: {leakage:,.2f} tCO2e/year [CALC: leakage_total]
- **Net emission reductions**: {net:,.2f} tCO2e/year [CALC: net_ER]
- **Crediting period total**: {total:,.2f} tCO2e ({years} years) [CALC: crediting_total]

### Component Breakdown
- {name}: {value:,.2f} {unit} — {formula}      # one line per components[] entry

### Calculation Warnings
- {warning}                                     # section omitted entirely when warnings is empty
```

### §4 — Measured cost model for PHASE-06

All figures measured on 2026-07-25 against the local `claude` CLI with `--model sonnet`.

| Quantity | Measured / derived |
|---|---|
| Cost of one section-drafting call | **$0.167898** |
| Wall-clock of one section-drafting call | **36.1 s** |
| Billed tokens for that call | 9 input + 1,053 output + 25,346 cache-creation + 0 cache-read = **26,408** |
| Tokens the current code records for that call | 1,062 (≈4% of actual) |
| 36-section run, no redrafts | ≈ 22 min, ≈ **$6.05** |
| Two projects (Inegol + rice), no redrafts | ≈ 45 min, ≈ **$12.10** |
| Worst case, 3 redrafts on every section | ≈ 3 h, ≈ **$48** |

Set `PDD_MAX_COST_USD=15` for the PHASE-06 runs: above the two-project no-redraft estimate, well below the worst case, and — once PHASE-01 lands — an actually enforced ceiling that raises `BudgetExhaustedError` rather than running to completion silently.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Make `claude-code` token and cost accounting truthful so budget ceilings bind | None | `budget.py` cache-token + authoritative-cost support, `claude_code_provider.py` full usage parsing, new tests |
| PHASE-02 | Strip assistant preamble/tail from real-provider output | None | `src/pdd_agent/llm/output_normalize.py`, wiring in all four real providers, new tests |
| PHASE-03 | Family-agnostic calc result plus a methodology dispatch layer | None | `src/pdd_agent/calc/dispatch.py`, generalized `_format_calc_injection`, guarded consistency checks, new tests |
| PHASE-04 | Wire calc into the three drafting entry points and add `pdd-agent calc` | PHASE-03 | Calc wiring in `cli.py`, `provider_scorecard.py`, `service/main.py`, `run_review`; new `calc` subcommand; new tests |
| PHASE-05 | Bring `README.md`, `CLAUDE.md`, `activeContext.md` back in line with reality; hygiene | PHASE-01–04 | Truth-synced docs, dead alias removed, leaked index artifact removed |
| PHASE-06 | Build the production index and run the first real-model proof | PHASE-01, 02, 04 | `data/index/corpus.fts.db`, `reports/prove-inegol-claude-code.md`, `reports/prove-rice-claude-code.md`, findings doc |

## Detailed Phases

### PHASE-01 - Truthful Token and Cost Accounting for the Keyless Provider
**Goal**
`TokenBudget` counts every token class the Claude Code CLI bills for, and records the CLI's own `total_cost_usd` as authoritative, so `PDD_MAX_COST_USD` and `max_tokens` actually stop a runaway run and the scorecard's cost column is true.

**Tasks**
- [x] TASK-01-01: Add `cache_creation_tokens: int = 0` and `cache_read_tokens: int = 0` to `CallRecord` in `src/pdd_agent/llm/budget.py`.
- [x] TASK-01-02: Add a `total_cache_tokens` property to `TokenBudget` and include it in `total_tokens`. Because both new `CallRecord` fields default to `0`, every existing provider's accounting is unchanged.
- [x] TASK-01-03: Extend `TokenBudget.record()` with `cache_creation_tokens: int = 0`, `cache_read_tokens: int = 0`, and `cost_usd: float | None = None`. When `cost_usd` is not `None`, store it verbatim; otherwise fall back to `_estimate_cost(...)` exactly as today.
- [x] TASK-01-04: Add `total_cache_tokens` to the dict returned by `TokenBudget.summary()`, positioned immediately after `total_output_tokens`. Leave every existing key and its rounding unchanged.
- [x] TASK-01-05: In `ClaudeCodeProvider._call_cli`, parse `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` (default `0`) and top-level `total_cost_usd` (default `None`). Set `LLMResponse.tokens_used` to the sum of all four token classes and `LLMResponse.cost_usd` to `total_cost_usd or 0.0`; carry all five values in `LLMResponse.raw`.
- [x] TASK-01-06: In `ClaudeCodeProvider.draft_section`, pass the two cache-token counts and `cost_usd=response.raw.get("cost_usd")` through to `self._budget.record(...)`.
- [x] TASK-01-07: Update the comment block above the `claude-code` entry in `configs/model_pricing.yaml` to state that cost now comes from the CLI's reported `total_cost_usd` and that the `0.0` rates are the fallback used only when that field is absent. Do not change the numeric values.
- [x] TASK-01-08: Update the module docstring of `src/pdd_agent/llm/claude_code_provider.py` (lines 18–25), which currently says `total_cost_usd` is "not used here".

**File Changes**
- `src/pdd_agent/llm/budget.py` (modify): extend `CallRecord`, `TokenBudget.record()`, `total_tokens`, `summary()`; add `total_cache_tokens`. Leave `_load_pricing`, `_FALLBACK_PRICING`, `_estimate_cost`, `check_budget`, `utilization`, `remaining`, and `BudgetExhaustedError` untouched.
- `src/pdd_agent/llm/claude_code_provider.py` (modify): usage parsing in `_call_cli` and the `record(...)` call in `draft_section`; update the module docstring. Leave retry logic, timeout handling, `_assess_confidence`, `_extract_issues`, and the error-placeholder path unchanged.
- `configs/model_pricing.yaml` (modify): comment text only.
- `tests/test_token_budget.py` (modify): add cases for cache-token accounting and authoritative cost.
- `tests/test_claude_code_provider.py` (modify): add cases asserting the full-usage parse, using `unittest.mock.patch("pdd_agent.llm.claude_code_provider.subprocess.run")` in the style already used in that file.

**Function Signatures**
- `TokenBudget.record(self, section_id: str, input_tokens: int, output_tokens: int, model: str = "", provider: str = "", cache_creation_tokens: int = 0, cache_read_tokens: int = 0, cost_usd: float | None = None) -> CallRecord` — appends and returns the call record, using `cost_usd` verbatim when provided.
- `TokenBudget.total_cache_tokens (property) -> int` — sum of `cache_creation_tokens + cache_read_tokens` across all recorded calls.

**Test Specs**
- `TokenBudget().record(section_id="1.1", input_tokens=9, output_tokens=1053, cache_creation_tokens=25346, cache_read_tokens=0, cost_usd=0.167898, provider="claude-code", model="sonnet")` → `budget.total_tokens == 26408`, `budget.total_cache_tokens == 25346`, `budget.estimated_cost_usd == 0.167898`.
- `TokenBudget().record(section_id="1.1", input_tokens=1000, output_tokens=500, model="gpt-4o")` (no cache args, no `cost_usd`) → `total_tokens == 1500`, `total_cache_tokens == 0`, `estimated_cost_usd == pytest.approx(0.0075)` (1000/1e6×2.50 + 500/1e6×10.00) — proves the pre-existing estimation path is untouched.
- `TokenBudget(max_tokens=30_000, max_cost_usd=0.10)` then the first record above, then `check_budget()` → raises `BudgetExhaustedError` whose message contains `Cost budget exhausted`.
- `ClaudeCodeProvider.draft_section` with `subprocess.run` mocked to return `{"result": "Section text.", "is_error": false, "total_cost_usd": 0.167898, "usage": {"input_tokens": 9, "output_tokens": 1053, "cache_creation_input_tokens": 25346, "cache_read_input_tokens": 0}}` → the attached budget shows `total_tokens == 26408` and `estimated_cost_usd == 0.167898`.
- Same call with a payload whose `usage` omits both cache keys and which has no `total_cost_usd` → `total_tokens == 1062`, `estimated_cost_usd == 0.0` (defensive parsing, no `KeyError`).
- `TokenBudget().summary()` → the returned dict contains the key `total_cache_tokens` and still contains every key it returns today (`max_tokens`, `max_cost_usd`, `total_input_tokens`, `total_output_tokens`, `total_tokens`, `utilization`, `remaining`, `estimated_cost_usd`, `num_calls`, `exhausted`, `cost_ceiling_hit`).

**Dependencies**
- None.

**Exit Criteria**
- [ ] `python -m pytest tests/test_token_budget.py tests/test_claude_code_provider.py -q` passes with the new cases present.
- [ ] `python -m pytest -m "not corpus" -q` reports at least 735 passed, 7 deselected.
- [ ] `grep -n "cache_creation_input_tokens" src/pdd_agent/llm/claude_code_provider.py` returns at least one line.

**Phase Risks**
- **RISK-01-01:** Widening `total_tokens` could trip budget ceilings in other providers' tests. Mitigated by defaulting both new fields to `0` — only callers that pass cache tokens (i.e. `ClaudeCodeProvider`) see any change.
- **RISK-01-02:** A future CLI version could rename `total_cost_usd`. Mitigated by defaulting to `None` and falling back to the existing pricing-table estimate, never raising.

### PHASE-02 - Assistant-Preamble Normalization for Real Providers
**Goal**
Section bodies produced by real providers start at the content, not at "I'll draft…", and do not end with "Let me know if…".

**Tasks**
- [x] TASK-02-01: Create `src/pdd_agent/llm/output_normalize.py` implementing `strip_assistant_preamble` exactly per `## Specification` §2, with the two module-level compiled regexes (`_PREAMBLE_RE`, `_TRAILER_RE`) and the horizontal-rule set `{"---", "***", "___"}`.
- [x] TASK-02-02: In `src/pdd_agent/llm/claude_code_provider.py:210`, change `text = response.text[:max_chars]` to `text = strip_assistant_preamble(response.text)[:max_chars]`.
- [x] TASK-02-03: Apply the identical change at `src/pdd_agent/llm/openai_provider.py:190`, `src/pdd_agent/llm/anthropic_provider.py:197`, and `src/pdd_agent/llm/ollama_provider.py:181`.
- [x] TASK-02-04: Create `tests/test_output_normalize.py` covering the specs below.
- [ ] TASK-02-05: Add one case to `tests/test_claude_code_provider.py` proving the normalizer is wired into `draft_section` (mocked subprocess, preamble-bearing payload).

**File Changes**
- `src/pdd_agent/llm/output_normalize.py` (create): one public function plus module-private regexes and helpers. No imports beyond `re` and `from __future__ import annotations`.
- `src/pdd_agent/llm/claude_code_provider.py` (modify): import and apply the normalizer at the single text-assignment line. Leave the error-placeholder text path alone — placeholders like `[CLAUDE-CODE ERROR — …]` must never be normalized.
- `src/pdd_agent/llm/openai_provider.py`, `src/pdd_agent/llm/anthropic_provider.py`, `src/pdd_agent/llm/ollama_provider.py` (modify): same one-line change each.
- `tests/test_output_normalize.py` (create).
- `tests/test_claude_code_provider.py` (modify): one added case.

**Function Signatures**
- `strip_assistant_preamble(text: str) -> str` — returns the text with a leading conversational preamble and a trailing conversational tail removed; returns the input unchanged when stripping would leave nothing.

**Test Specs**
- `strip_assistant_preamble("I'll draft a conservative summary paragraph for section 1.1.1 using the project-specific facts provided.\n\n---\n\n# 1.1.1 Summary Description of the Project\n\nThe project is a facility.")` → `"# 1.1.1 Summary Description of the Project\n\nThe project is a facility."`
- `strip_assistant_preamble("Here's the section:\n\nThe project boundary includes the site.")` → `"The project boundary includes the site."`
- `strip_assistant_preamble("The project boundary includes the site.")` → unchanged (no preamble present).
- `strip_assistant_preamble("# 1.1 Heading\n\nBody text.")` → unchanged (a heading is never preamble).
- `strip_assistant_preamble("Body text.\n\nLet me know if you'd like more detail.")` → `"Body text."`
- `strip_assistant_preamble("I'll draft this now.")` → unchanged (stripping would empty the text, so the original is returned).
- `strip_assistant_preamble("Baseline emissions are 1,000 tCO2e/year.\n\n---\n\nProject emissions are 200 tCO2e/year.")` → unchanged (a horizontal rule with no preceding preamble line must not trigger truncation).
- `strip_assistant_preamble("")` → `""`.
- `ClaudeCodeProvider.draft_section` with mocked `subprocess.run` returning `{"result": "Sure, here's the section.\n\n# 3.3 Project Boundary\n\nThe boundary is defined.", "is_error": false, "usage": {}}` → `draft.text` starts with `"# 3.3 Project Boundary"`.

**Dependencies**
- None (independent of PHASE-01; both touch `claude_code_provider.py` but at different lines).

**Exit Criteria**
- [ ] `python -m pytest tests/test_output_normalize.py -q` passes.
- [ ] `grep -rn "strip_assistant_preamble" src/pdd_agent/llm/` shows exactly five hits: the definition plus four provider call sites.
- [ ] `python -m pytest -m "not corpus" -q` reports at least 735 passed, 7 deselected.

**Phase Risks**
- **RISK-02-01:** Over-eager stripping could delete real content whose first line legitimately begins with "Here is". Mitigated by rule 7 (never return empty), by stopping at the first non-preamble line, and by the explicit "horizontal rule with no preceding preamble" test case.

### PHASE-03 - Family-Agnostic Calc Result and Methodology Dispatch
**Goal**
One function turns a `ProjectInput` into a computed, family-agnostic quantification result — or into a clear `None` with the missing field paths logged — and the orchestrator can format any family's result without WTE-specific attribute access.

**Tasks**
- [x] TASK-03-01: Create `src/pdd_agent/calc/dispatch.py` with `CalcComponent`, `PddCalcResult`, `ENGINE_BY_METHODOLOGY`, `build_engine_inputs`, and `compute_for`, implementing `## Specification` §1 exactly.
- [x] TASK-03-02: Implement `PddCalcResult.to_prompt_block()` per `## Specification` §3.
- [x] TASK-03-03: Generalize `SectionOrchestrator._format_calc_injection` into the three-branch dispatch of `## Specification` §3, keeping the existing ACM0022 body verbatim as branch 3 and reading it from `raw_result` when present.
- [x] TASK-03-04: Guard `_check_calc_result_internal` in `src/pdd_agent/review/consistency.py` (line 411) so its ACM0022-specific decomposition check (`baseline_methane_swds_tco2e + baseline_electricity_tco2e`, line 440) runs only when **both** attributes exist: `if hasattr(calc_result, "baseline_methane_swds_tco2e") and hasattr(calc_result, "baseline_electricity_tco2e"):`. The generic baseline/project/leakage/net arithmetic check above it stays unconditional.
- [ ] TASK-03-05: Update the `calc_result` type annotations and docstrings in `src/pdd_agent/review/consistency.py` (lines 92, 100, 415) from `ACM0022CalcResult` to `ACM0022CalcResult | PddCalcResult`, using a `TYPE_CHECKING`-guarded import so no runtime import cycle is introduced.
- [x] TASK-03-06: Create `tests/test_calc_dispatch.py` covering the specs below.

**File Changes**
- `src/pdd_agent/calc/dispatch.py` (create): the whole dispatch layer. Imports only from `pdd_agent.calc.*` and `schemas.project_input`, plus `structlog`. Must not import `pdd_agent.agent.*` (that direction would be circular).
- `src/pdd_agent/agent/section_orchestrator.py` (modify): `_format_calc_injection` only. Do not touch `_should_inject_calc`, `_is_quantification_section`, or `_build_prompt`.
- `src/pdd_agent/review/consistency.py` (modify): the `hasattr` guard plus annotation/docstring updates. Leave every threshold, tolerance, and flag severity unchanged.
- `tests/test_calc_dispatch.py` (create).

**Function Signatures**
- `CalcComponent` (dataclass) — fields `name: str`, `value_tco2e: float`, `unit: str = "tCO2e/year"`, `formula: str = ""`, `notes: str = ""`.
- `PddCalcResult` (dataclass) — fields `methodology_id: str`, `baseline_emissions_tco2e: float`, `project_emissions_tco2e: float`, `leakage_tco2e: float`, `net_emission_reductions_tco2e: float`, `crediting_period_total_tco2e: float`, `crediting_period_years: int`, `components: list[CalcComponent] = field(default_factory=list)`, `monitoring_params: list[dict] = field(default_factory=list)`, `warnings: list[str] = field(default_factory=list)`, `raw_result: Any | None = None`.
- `PddCalcResult.to_prompt_block(self) -> str` — the Markdown block defined in §3, ready to concatenate into a section prompt.
- `build_engine_inputs(project_input: ProjectInput) -> tuple[str, dict[str, Any], list[str]] | None` — returns `(methodology_id, engine_input_dict, warnings)` or `None` when the methodology is unsupported or a required source field is missing.
- `compute_for(project_input: ProjectInput) -> PddCalcResult | None` — returns the computed result, or `None` (logging `calc_inputs_incomplete` with `missing=[...]`, or `calc_engine_unsupported` with the observed methodology id).

**Test Specs**
- `compute_for(<rice pilot ProjectInput loaded from configs/projects/rice_vm0051_pilot.yaml>)` → a `PddCalcResult` with `methodology_id == "VM0051"`, `baseline_emissions_tco2e == pytest.approx(1.30 * 5000.0 * 220 * 28.0 / 1000.0)` (= 40,040.0 tCO2e/year), `leakage_tco2e == 0.0`, `net_emission_reductions_tco2e > 0`, `crediting_period_total_tco2e == pytest.approx(net * crediting_period_years)`, and `len(components) == 4`.
- `compute_for(<Inegol ProjectInput loaded from configs/demo/inegol_project_input.yaml>)` → `None` (that file has `quantification.grid_emission_factor: null`).
- `compute_for(<Soc Son demo ProjectInput loaded from configs/projects/demo_socson_like.yaml>)` → a `PddCalcResult` with `methodology_id == "ACM0022"`, `raw_result` an `ACM0022CalcResult`, `warnings` containing the substring `"biomethanization_suitable_fraction absent"`, and `crediting_period_years == 10`.
- A `ProjectInput` whose `technology.methodology_ids == ["VM0033"]` → `None`.
- A `ProjectInput` whose `methodology_ids == ["VM0051"]` but whose `technology.rice_cultivation is None` → `None`.
- `PddCalcResult(methodology_id="VM0051", baseline_emissions_tco2e=40040.0, project_emissions_tco2e=28028.0, leakage_tco2e=0.0, net_emission_reductions_tco2e=12012.0, crediting_period_total_tco2e=84084.0, crediting_period_years=7).to_prompt_block()` → a string containing `"## VM0051 Calculation Engine Results"`, `"[CALC: net_ER]"`, `"40,040.00 tCO2e/year"`, and **not** containing `"BE_CH4"` or `"organic waste"`.
- `PddCalcResult(...)` with `warnings=[]` → `to_prompt_block()` does not contain `"### Calculation Warnings"`.
- `SectionOrchestrator(project_input=<socson>, calc_result=<ACM0022CalcResult fixture>)._format_calc_injection()` → still contains `"[CALC: BE_CH4]"` (proves the WTE path is byte-compatible).
- `check_quantitative_consistency(draft_sections=[], project_input=None, run_id="t", calc_result=<PddCalcResult with baseline=100.0, project=30.0, leakage=0.0, net=70.0>)` → returns a report with no `AttributeError` raised and no flag mentioning `baseline_methane_swds_tco2e`.

**Dependencies**
- None (uses only existing engines and schema fields).

**Exit Criteria**
- [ ] `python -m pytest tests/test_calc_dispatch.py -q` passes.
- [ ] `python -m pytest tests/test_acm0022_calc.py tests/test_calc_integration.py tests/test_rice_vm0051.py tests/test_biochar_vm0044.py tests/test_cookstove_amsiig.py -q` passes unchanged.
- [ ] `python -m pytest -m "not corpus" -q` reports at least 735 passed, 7 deselected.

**Phase Risks**
- **RISK-03-01:** The equal-split waste-stream mapping is an approximation for multi-entry `waste_type` lists. Mitigated by recording it as a `PddCalcResult.warnings` entry (`"waste split evenly across N declared waste types"`) whenever `len(waste_type) > 1`, so it is visible in the prompt block and in `pdd-agent calc` output.
- **RISK-03-02:** Deriving `net` from the engine rather than from `baseline − project − leakage` can produce a small arithmetic mismatch that `_check_calc_result_internal` flags. That is correct behavior (the engines are authoritative and the check has a tolerance); do not "fix" it by recomputing `net`.

### PHASE-04 - Wire Calc Into the Drafting Entry Points and Add `pdd-agent calc`
**Goal**
Real-provider runs compute their quantification with the engine, inject it into Section 4 prompts, and cross-check draft numbers against it — while every `demo`/`noop` artifact stays byte-identical. A standalone `pdd-agent calc` command exposes the breakdown with zero LLM calls.

**Tasks**
- [x] TASK-04-01: In `src/pdd_agent/cli.py:_run_draft`, after `project_input` is resolved and before the orchestrator is constructed, compute `calc_result = compute_for(project_input) if args.provider not in ("demo", "noop") else None`, pass it as `SectionOrchestrator(calc_result=calc_result, ...)`, and log `calc_engine_ready` with `methodology_id` and `net_tco2e` (or `calc_engine_skipped` with `reason`).
- [x] TASK-04-02: Apply the same rule in `src/pdd_agent/phase05/provider_scorecard.py:_run_one_provider`, reusing the existing `provider_name not in ("demo", "noop")` idiom already present there for the judge.
- [x] TASK-04-03: Apply the same rule in `src/pdd_agent/service/main.py:_execute_run`, gating on the resolved provider name.
- [x] TASK-04-04: In `SectionOrchestrator.run_review` (line 935), pass `calc_result=self._calc_result` to `check_quantitative_consistency(...)`. Change nothing else in that method.
- [x] TASK-04-05: Add a `calc` subcommand to `build_parser` in `src/pdd_agent/cli.py` with `--input` (required, path to a ProjectInput YAML) and `--output` (optional path; when given, write the result as JSON). Register it by adding `"calc": lambda: _run_calc(args, log),` to the `commands` dict inside `main()` (the dict starting at `src/pdd_agent/cli.py:407`, dispatched at line 434 via `commands[args.command]()`).
- [x] TASK-04-06: Implement `_run_calc(args, log)` printing the methodology id, the five summary values, the component breakdown, the monitoring-parameter count, and any warnings; exit with a clear message when `compute_for` returns `None`.
- [x] TASK-04-07: Add a `| pdd-agent calc | Compute methodology quantification for a ProjectInput without any LLM call |` row to the CLI table in `README.md`.
- [ ] TASK-04-08: Create `tests/test_calc_wiring.py` covering the specs below.

**File Changes**
- `src/pdd_agent/cli.py` (modify): calc computation in `_run_draft`; new `calc` subparser, dispatch entry, and `_run_calc`. Do not alter any other subcommand's flags or defaults.
- `src/pdd_agent/phase05/provider_scorecard.py` (modify): compute and pass `calc_result` in `_run_one_provider`. Leave `ProviderScorecardRow`, the skip logic, and the markdown writer unchanged.
- `src/pdd_agent/service/main.py` (modify): compute and pass `calc_result` in `_execute_run`. Leave every route and the status-file protocol unchanged.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): one added keyword argument at the `check_quantitative_consistency` call in `run_review`.
- `README.md` (modify): one added CLI-table row.
- `tests/test_calc_wiring.py` (create).

**Function Signatures**
- `_run_calc(args, log) -> None` — loads the ProjectInput YAML at `args.input`, calls `compute_for`, prints the breakdown, and writes JSON to `args.output` when provided.

**Test Specs**
- `pdd-agent draft --input configs/projects/rice_vm0051_pilot.yaml --provider noop` (invoked in-process with the orchestrator patched to capture its kwargs) → the orchestrator receives `calc_result=None`.
- The same invocation with `--provider ollama` and `compute_for` patched to return a `PddCalcResult` → the orchestrator receives that exact object.
- `SectionOrchestrator(project_input=<rice>, calc_result=<PddCalcResult>, provider=NoopProvider()).run_review()` → completes without raising and returns a dict containing the `consistency` key.
- `python -m pdd_agent.cli calc --input configs/projects/rice_vm0051_pilot.yaml` (invoked via `subprocess` or the parser directly) → exit code `0` and stdout containing `VM0051` and `40,040.00`.
- `python -m pdd_agent.cli calc --input configs/demo/inegol_project_input.yaml` → exit code `0` and stdout containing the substring `grid_emission_factor` (the named missing input), with no traceback.
- `_run_calc` with `--output <tmp>/calc.json` → the file exists and parses as JSON with the keys `methodology_id`, `baseline_emissions_tco2e`, `project_emissions_tco2e`, `leakage_tco2e`, `net_emission_reductions_tco2e`, `crediting_period_total_tco2e`, `components`, `warnings`.
- Regression: `python scripts/run_demo.py` then `git status --porcelain reports/demo-packages/` → **no** modified tracked files (CON-002).

**Dependencies**
- PHASE-03 (`compute_for`, `PddCalcResult`).

**Exit Criteria**
- [ ] `python -m pytest tests/test_calc_wiring.py tests/test_cli_prove.py tests/test_service.py tests/test_phase05_demo.py -q` passes.
- [ ] `pdd-agent calc --input configs/projects/rice_vm0051_pilot.yaml` prints a VM0051 breakdown and exits `0`.
- [ ] `python scripts/run_demo.py && git status --porcelain reports/demo-packages/` prints nothing.
- [ ] `python -m pytest -m "not corpus" -q` reports at least 735 passed, 7 deselected.

**Phase Risks**
- **RISK-04-01:** Injecting calc numbers that disagree with a ProjectInput's hand-entered quantification will raise new consistency flags on real-provider runs. That is the intended signal, not a regression — record any such flags in PHASE-06's findings doc rather than suppressing them.
- **RISK-04-02:** The service's provider resolution can fall back to `demo` (`_get_provider` returns the effective provider, not the requested one). Gate on the **effective** name so a fallback run does not get calc injected.

### PHASE-05 - Documentation Truth-Sync and Hygiene
**Goal**
Every status claim in the repo's front-door documents matches what the code does, so the next reader's first hour is not spent discovering that the known-gaps list is stale.

**Tasks**
- [x] TASK-05-01: In `README.md:5`, replace the test-count sentence with the count produced by running the suite at this phase (`python -m pytest -m "not corpus" -q | tail -1`). Quote the exact numbers reported.
- [x] TASK-05-02: In `README.md:311`, correct the `llm/ollama_provider.py` description — it is a working HTTP client against `{OLLAMA_BASE_URL}/api/chat`, not a stub.
- [x] TASK-05-03: In `README.md` "Known Gaps" (around line 328), delete the claim that the FastAPI service "forces the `demo` provider and disables corpus retrieval regardless of configuration" and replace it with the two gaps that are actually true today: (a) `_get_provider` does not recognize `claude-code`, so that provider silently falls back to `demo` with `reason="unknown_provider"`; (b) `/dashboard` and `/api/runs` scan and `stat()` every `run-*.json` in the runs directory on each request, with no pagination or retention policy.
- [ ] TASK-05-04: Add a "Quantification engines" subsection to `README.md` under Architecture describing `pdd-agent calc`, `compute_for`, the four supported methodology ids, and the demo/noop exclusion rule (ASM-002).
- [x] TASK-05-05: In `CLAUDE.md`, update the "Where to look" pointer from `plans/2026-07-12-pdd-reality-gap-plan.md` to this plan's path.
- [x] TASK-05-06: Rewrite `activeContext.md` to describe this plan: its six phases as checkable items, the current test count, and the remaining external blockers (no `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`; Ollama not installed; Verra registry live search still uncaptured).
- [x] TASK-05-07: Delete the unused `_PROJECT_ALIASES` dict at `src/pdd_agent/cli.py:188`. Verify first that the live dict at `_run_prove` (line 684) is the one actually consulted: `grep -n "_PROJECT_ALIASES\|project_aliases" src/pdd_agent/cli.py`.
- [x] TASK-05-08: Delete the leaked test artifact `data/index/__nonexistent_test.fts.db` and confirm it is not tracked (`git ls-files data/index/`). If a test creates it, make that test use `tmp_path`.

**File Changes**
- `README.md` (modify): status line, Ollama description, Known Gaps, new quantification-engines subsection, plus the `calc` CLI row from PHASE-04 if not already added.
- `CLAUDE.md` (modify): the "Current push" plan pointer only.
- `activeContext.md` (modify): full rewrite for this plan.
- `src/pdd_agent/cli.py` (modify): delete the dead dict at line 188 only.
- `data/index/__nonexistent_test.fts.db` (delete).
- `tests/` (modify, only if TASK-05-08 finds the test that creates that file).

**Function Signatures**
- None — no code interfaces change in this phase.

**Test Specs**
- `python -m pytest -m "not corpus" -q` → the printed count equals the number written into `README.md:5`.
- `grep -c "_PROJECT_ALIASES" src/pdd_agent/cli.py` → `0`.
- `ls data/index/` → lists only `.gitkeep` and `demo.fts.db` (plus `corpus.fts.db` once PHASE-06 has run).
- `grep -n "forces the .demo. provider" README.md` → no matches.

**Dependencies**
- PHASE-01 through PHASE-04 (the documented behavior must already be true).

**Exit Criteria**
- [ ] `ruff check . && ruff format --check .` passes.
- [ ] Every claim in `README.md`'s status line and Known Gaps list is verifiable by a command in `## Verification Strategy`.
- [ ] `python -m pytest -m "not corpus" -q` still reports at least 735 passed, 7 deselected.

**Phase Risks**
- **RISK-05-01:** Deleting `data/index/__nonexistent_test.fts.db` while a test depends on its presence would break the suite. Mitigated by running the full suite immediately after deletion and, if it fails, redirecting the offending test to `tmp_path` rather than restoring the file.

### PHASE-06 - Build the Production Index and Run the First Real-Model Proof
**Goal**
Produce the repo's first real-model artifacts: two completed `pdd-agent prove` runs against the `claude-code` provider, grounded in the full 17-document corpus, with truthful cost lines and a written findings document.

**Tasks**
- [ ] TASK-06-01: Confirm the environment: `python --version` (expect 3.11+), `which claude` (or `where claude` on Windows) must resolve, and `pdd-agent doctor` must report the `claude` CLI as found.
- [x] TASK-06-02: Build the production retrieval index: `pdd-agent build-index --corpus-dir data/corpus/normalized --index-db data/index/corpus.fts.db`. Confirm `data/index/corpus.fts.db` exists and is larger than `data/index/demo.fts.db`.
- [ ] TASK-06-03: Record a pre-flight note listing which index file `get_retrieval_index()` will select (`corpus.fts.db` when present, else `demo.fts.db`) and the document count indexed.
- [ ] TASK-06-04: Run the Inegol proof with a bound cost ceiling: `PDD_MAX_COST_USD=15 pdd-agent prove --project inegol --providers claude-code --output reports/prove-inegol-claude-code.md` (PowerShell: `$env:PDD_MAX_COST_USD='15'; pdd-agent prove --project inegol --providers claude-code --output reports/prove-inegol-claude-code.md`). Expect ≈22 minutes and ≈$6.
- [ ] TASK-06-05: Run the rice proof: same command with `--project rice --output reports/prove-rice-claude-code.md`. This is the run where the calc spine fires (ASM-005).
- [ ] TASK-06-06: Inspect both scorecards for `Sections failed`, `redraft_count`, `total_tokens`, `estimated_cost_usd`, and `judge_provider`. Record the observed wall-clock and cost per section.
- [ ] TASK-06-07: Open the drafted sections of the rice run (`data/runs/run-*.json`, newest) and verify: no section body begins with an assistant preamble; Section 4.x bodies contain at least one `[CALC:` citation.
- [ ] TASK-06-08: Write `docs/2026-07-25-first-real-model-proof-findings.md` covering: commands run; index used and document count; per-project wall-clock, token count, and cost; sections failed and why; whether the calc block appeared in Section 4 for rice; the Inegol `calc_inputs_incomplete` skip and its missing field; any new consistency flags raised by calc-vs-ProjectInput comparison; observed prose-quality issues; and a recommended default drafting model.
- [ ] TASK-06-09: Append a short "First real-model proof" subsection to `README.md` linking both scorecards and the findings doc, replacing any remaining claim that every artifact to date is demo/noop output.

**File Changes**
- `data/index/corpus.fts.db` (create): build output; ignored by git via the existing `data/index/*` rule in `.gitignore` — do not force-add it.
- `reports/prove-inegol-claude-code.md` (create): generated by the `prove` command.
- `reports/prove-rice-claude-code.md` (create): generated by the `prove` command.
- `docs/2026-07-25-first-real-model-proof-findings.md` (create): hand-written findings.
- `README.md` (modify): one added subsection.

**Function Signatures**
- None — no code interfaces change in this phase.

**Test Specs**
- None — no testable behavior changes in this phase. Verification is the operational checks in `## Verification Strategy` (MANUAL-001 through MANUAL-004).

**Dependencies**
- PHASE-01 (so the cost ceiling binds and the scorecard's cost column is true), PHASE-02 (so section bodies are clean), PHASE-04 (so calc is injected for real providers).
- An authenticated local `claude` CLI on `PATH`.

**Exit Criteria**
- [ ] `ls reports/prove-inegol-claude-code.md reports/prove-rice-claude-code.md` lists both files.
- [ ] Each scorecard's `claude-code` row shows `sections_drafted == 36` and a non-zero `estimated_cost_usd`.
- [ ] `docs/2026-07-25-first-real-model-proof-findings.md` exists and states the per-project cost and wall-clock actually observed.
- [ ] `grep -c "\[CALC:" <newest rice run JSON>` returns a non-zero count.

**Phase Risks**
- **RISK-06-01:** A section call exceeds `_DEFAULT_TIMEOUT_SECONDS = 300` and produces a `[CLAUDE-CODE ERROR …]` placeholder, inflating `sections_failed`. Mitigation: the measured per-call latency is 36s, leaving ample headroom; if timeouts appear, raise the limit for the run via `CLAUDE_CODE_TIMEOUT_SECONDS=600` (already environment-configurable, no code change) and note it in the findings doc.
- **RISK-06-02:** The cost ceiling trips mid-run and raises `BudgetExhaustedError`, leaving a partial scorecard. That is the ceiling working as designed — record the partial result, raise `PDD_MAX_COST_USD` deliberately, and re-run rather than removing the ceiling.
- **RISK-06-03:** The `claude` CLI could prompt for authentication or a permission decision and block. Mitigation: TASK-06-01 verifies a working headless call first; if the CLI ever blocks, stop the run rather than leaving it hanging.

## Gotchas
- `schemas/` is a **top-level package outside `src/`** — import it as `from schemas.project_input import ProjectInput`, never `from pdd_agent.schemas...`. It is listed separately in `[tool.hatch.build.targets.wheel] packages`.
- `src/pdd_agent/calc/dispatch.py` must not import from `pdd_agent.agent.*`: `provider_scorecard.py` already imports `SectionOrchestrator`, and the orchestrator will import the dispatch module — importing back would create a cycle.
- **Never recompute `net` as `baseline − project − leakage`.** VM0051 computes emission reductions in kg CH4 and applies GWP once at the end; re-deriving from tCO2e values introduces rounding drift that the consistency checker will then flag as a real inconsistency.
- Units are easy to confuse here: `crediting_period_total_tco2e` is an **absolute total over the whole crediting period**, while every other emissions field is **per year**. `ACM0022CalcResult.crediting_period_years` defaults to `7`, but `ProjectInput.dates.crediting_period_years` is authoritative — always pass it explicitly.
- `configs/projects/demo_socson_like.yaml` uses `crediting_period_years: 10`; `configs/projects/rice_vm0051_pilot.yaml` and `configs/demo/inegol_project_input.yaml` use `7`. Do not hardcode either.
- The rice pilot config carries WTE-shaped fields (`waste_type: [rice_straw_residue]`, `annual_waste_throughput: 25000.0`, `installed_capacity_mw: 0.0`) because those `ProjectInput` fields are required. They are **not** calc inputs for VM0051 — ignore them entirely in the rice mapping.
- `rice_straw_residue` is deliberately **not** a key of `DOC_BY_WASTE_TYPE`; the ACM0022 mapping's key check must not crash on it (it can never be reached for a VM0051 project, but the guard belongs in the code regardless).
- `TokenBudget.check_budget()` raises **before** a call is made (it is invoked at the top of the provider retry loop and at the top of `draft_section`), so a ceiling hit aborts the remaining sections rather than truncating the current one.
- The `claude` CLI charges roughly $0.08–$0.17 **per invocation** regardless of prompt size, because ~25k tokens of harness context are created per call. Never "just re-run it to check" during development — use the mocked tests.
- `structlog` calls take an event name plus keyword pairs: `logger.warning("calc_inputs_incomplete", missing=missing_paths)`. Never `logger.warning(f"missing {paths}")`.
- Any file written under `data/runs/`, `data/index/`, or `data/corpus/raw|normalized` is gitignored. Do not `git add -f` build outputs; `reports/prove-*.md` **is** tracked and should be committed.
- CI enforces `uv lock --check`. This plan adds no dependency; if `uv.lock` changes, something went wrong.

## Verification Strategy
- **TEST-001:** `python -m pytest -m "not corpus" -q` → `735 passed, 7 deselected` or more passed, zero failed.
- **TEST-002:** `python -m pytest tests/test_token_budget.py tests/test_claude_code_provider.py -q` → all pass, including the case asserting `total_tokens == 26408` and `estimated_cost_usd == 0.167898`.
- **TEST-003:** `python -m pytest tests/test_output_normalize.py -q` → all pass, including the "horizontal rule with no preceding preamble is preserved" case.
- **TEST-004:** `python -m pytest tests/test_calc_dispatch.py tests/test_calc_wiring.py -q` → all pass.
- **TEST-005:** `ruff check . && ruff format --check .` → `All checks passed!` and no reformatting required.
- **TEST-006:** `uv lock --check` → succeeds with no lockfile change.
- **TEST-007:** `pdd-agent calc --input configs/projects/rice_vm0051_pilot.yaml` → exit `0`, stdout contains `VM0051` and `40,040.00`.
- **TEST-008:** `pdd-agent calc --input configs/demo/inegol_project_input.yaml` → exit `0`, stdout names `quantification.grid_emission_factor` as the missing input, no traceback.
- **TEST-009:** `python scripts/run_demo.py && git status --porcelain reports/demo-packages/` → prints nothing (committed demo artifacts unchanged, CON-002).
- **TEST-010:** `grep -c "_PROJECT_ALIASES" src/pdd_agent/cli.py` → `0`.
- **MANUAL-001:** After TASK-06-02, `ls -la data/index/` shows `corpus.fts.db` present and larger than `demo.fts.db`.
- **MANUAL-002:** After TASK-06-04 and TASK-06-05, open both `reports/prove-*.md` files and confirm the `claude-code` row shows `sections_drafted = 36`, `sections_failed = 0` (or a documented explanation), and a non-zero `estimated_cost_usd`.
- **MANUAL-003:** Open the newest rice run JSON under `data/runs/` and confirm (a) no section text begins with `I'll`, `Here's`, `Sure`, or `Let me`, and (b) at least one Section 4.x body contains `[CALC:`.
- **MANUAL-004:** Confirm `docs/2026-07-25-first-real-model-proof-findings.md` records the observed per-project wall-clock and USD cost, and compares them against the ≈22 min / ≈$6 estimate in `## Specification` §4.
- **OBS-001:** During the PHASE-06 runs, watch for the structlog events `calc_engine_ready`, `calc_engine_skipped`, `token_budget_warning`, and `claude_code_timeout`. A `token_budget_warning` at 80% utilization is the first sign the ceiling is about to bind.

## Risks and Alternatives
- **RISK-001:** Wiring calc into real-provider runs surfaces disagreements between engine output and hand-entered ProjectInput numbers, which raise new consistency flags and could hard-block DOCX export via `check_export_gate`. Mitigation: ASM-002 confines calc to real-provider runs, so no committed demo artifact is affected; treat any new flags on the rice proof as findings to document, not defects to suppress.
- **RISK-002:** PHASE-06 costs real money against a subscription with an imperfectly understood billing model. Mitigation: PHASE-01 lands first so `PDD_MAX_COST_USD=15` actually binds; the measured cost table sets expectations before the first command runs.
- **RISK-003:** Preamble stripping changes text that downstream review checks key on (for example `_assess_confidence` looking for `[REVIEW REQUIRED`, or `TBDTracker` scanning for markers). Mitigation: the normalizer only removes leading/trailing conversational lines and never touches bracketed markers; the full suite (which exercises those checks) must stay green.
- **RISK-004:** `compute_for` returning `None` for the Inegol project could read as a failure during the proof. Mitigation: it is the correct, honest behavior (ASM-005) and is explicitly written up in the findings doc as a data gap, not a code gap.
- **ALT-001:** Give each `*CalcResult` type its own `to_prompt_block()` and drop the dispatch layer. Rejected: `ACM0022CalcResult` is a Pydantic model shared with `QuantificationInputs.from_calc_result` and the existing consistency checks, and adding presentation logic to it spreads formatting across four modules instead of one.
- **ALT-002:** Change `_format_calc_injection` to a purely generic implementation for all families, including ACM0022. Rejected: it would change WTE prompt text that every existing WTE expectation is built around, for no benefit; the three-branch dispatch keeps the WTE path byte-identical.
- **ALT-003:** Do the batching optimization (multiple sections per CLI invocation) before PHASE-06 to cut the ≈$12 proof cost. Rejected: batching changes prompt structure and would make the first real-model artifact a test of the batching design rather than of the pipeline. Run the proof first, then optimize against measured numbers.
- **ALT-004:** Skip PHASE-01 and simply pass `--no-judge` plus a short run to keep costs down. Rejected: the run would still report `$0.00` in its own scorecard, which is precisely the kind of untrue artifact this plan exists to stop producing.

## Suggested Next Step
Execute PHASE-01. It is self-contained, touches two files plus two test files, requires no network or API key, and its exit criteria are verifiable with `python -m pytest tests/test_token_budget.py tests/test_claude_code_provider.py -q`. PHASE-02 and PHASE-03 can proceed in parallel with it if more than one person is executing; PHASE-04 needs PHASE-03, and PHASE-06 must not start until PHASE-01, PHASE-02, and PHASE-04 have all passed their exit criteria.
