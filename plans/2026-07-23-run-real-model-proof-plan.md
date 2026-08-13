---
title: "Fix Self-Judging Redraft Loop, Run the First Real-Model Proof, Capture the Verra Registry API"
date: "2026-07-23"
status: "abandoned — closed by explicit user request on 2026-08-05 to clear the backlog and start fresh. PHASE-01/02 (judge-selection extraction, in-loop self-judging fix) were genuinely done (4266be1/aae79b3); PHASE-03's proof run was carried forward by plans/2026-07-25-calc-correctness-and-audit-trail-plan.md PHASE-06; PHASE-04 (live Verra registry search-API capture via browser devtools) was never built. If the registry capture is wanted later, re-plan it fresh rather than resuming this file."
request: "Scope the plan to Track A1 (fix in-loop redraft self-judging in section_orchestrator.py) + A2 (run pdd-agent prove --project inegol --providers claude-code) + A3 (run --project rice) as the primary sequence, with Track B1 (Verra registry search-API capture via browser devtools) as an independent parallel phase."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-23-pdd-run-the-proof-and-close-the-loop-brainstorm.md"
---

# Plan: Fix Self-Judging Redraft Loop, Run the First Real-Model Proof, Capture the Verra Registry API

## Objective
Fix the one known defect standing between "ready to run" and "safe to run" — the in-loop redraft
judge in `SectionOrchestrator` still defaults to a provider judging its own output — then execute the
project's long-deferred milestone: the first full-scale, real-model, multi-family drafting proof using
the keyless `claude-code` provider, for both the WTE family (Inegol) and a non-WTE family (rice). In
parallel, capture the live Verra public-registry search API shape via browser devtools so
`registry_download.py` can move from manual-download mode to a real live downloader for the three
newer methodology families (rice/biochar/cookstove), unblocking real (non-synthetic) corpus population.

## Context Snapshot
- **Current state:** `src/pdd_agent/phase05/provider_scorecard.py` already cross-judges correctly in
  `prove`'s post-hoc scoring pass (never lets a provider judge itself — see `_select_judge_provider`,
  `_JUDGE_PREFERENCE_ORDER = ["anthropic", "openai", "claude-code", "ollama"]`). But
  `src/pdd_agent/agent/section_orchestrator.py`'s `_run_judge_redraft_loop` method (used by the
  *in-loop* judge/redraft cycle that fires during drafting itself, when `enable_judge=True`) still
  resolves the judge provider with `judge_provider_name = os.environ.get("PDD_JUDGE_PROVIDER",
  drafting_provider_name)` — i.e. it defaults to self-judging whenever `PDD_JUDGE_PROVIDER` is unset.
  For a real provider (e.g. `claude-code`), self-judging means the same model judges its own output and
  can trigger real redraft calls (up to `max_redraft_attempts`, default 3) with no cross-check. `prove`
  (via `_run_one_provider` in `provider_scorecard.py`) enables this in-loop judge for every real
  provider whenever `--no-judge` is not passed (`drafting_enable_judge = enable_judge and
  provider_name not in ("demo", "noop")`) — so `pdd-agent prove --project inegol --providers
  claude-code` today would hit exactly this bug. No `reports/prove-*.md` artifact has ever been
  produced by a full run of `pdd-agent prove` against a real provider; the full-scale proof has never
  been executed. `src/pdd_agent/ingest/registry_download.py`'s `_search_projects()` makes a "best-effort
  real search attempt" against `https://registry.verra.org/uiapi/asset/asset/search` using a payload
  shape the module's own docstring says "could not be fully reconstructed from the minified bundle
  alone without browser devtools network inspection of a real search interaction" — it has never been
  verified against a live capture, so it silently falls back to manual-download mode on every call
  today (confirmed: `data/corpus/registry/` does not exist; no rice/biochar/cookstove corpus has ever
  been fetched live).
- **Desired state:** The in-loop redraft judge resolves its judge provider using the same
  never-self-judge cross-judging logic already proven correct in `provider_scorecard.py`, sourced from
  one shared module so the logic can never diverge between the two call sites again. `pdd-agent prove
  --project inegol --providers claude-code` and `pdd-agent prove --project rice --providers claude-code`
  have both been run to completion, each producing a scorecard artifact under `reports/` with `Sections
  failed = 0` (or a documented, resolved explanation if not), plus a findings write-up. Independently,
  `registry_download.py`'s search payload and response parsing match the real, devtools-verified Verra
  registry API shape, and `pdd-agent fetch-registry` has been run live for VM0051 (rice), VM0044
  (biochar), and AMS-II.G (cookstove), producing non-empty, non-manual-mode manifests.
- **Key repo surfaces:** `src/pdd_agent/agent/section_orchestrator.py` (`_run_judge_redraft_loop`),
  `src/pdd_agent/phase05/provider_scorecard.py` (`_is_provider_available`, `_select_judge_provider`,
  `_JUDGE_PREFERENCE_ORDER`), `src/pdd_agent/review/judge.py` (`LLMJudge`),
  `src/pdd_agent/llm/claude_code_provider.py`, `src/pdd_agent/cli.py` (`prove` subcommand,
  `_run_prove`), `src/pdd_agent/ingest/registry_download.py`, `tests/test_provider_scorecard.py`,
  `tests/test_section_orchestrator.py`, `tests/test_registry_download.py`, `configs/demo/
  inegol_project_input.yaml`, `configs/projects/rice_vm0051_pilot.yaml`, `docs/corpus-readiness.md`.
- **Out of scope:** Building an entirely new judge-selection UI or CLI flag surface (the existing
  `PDD_JUDGE_PROVIDER` env override and `--no-judge` flag are sufficient and stay unchanged); the Ollama
  small-model dress rehearsal (`docs/ollama-dress-rehearsal.md`, genuinely blocked — Ollama is not
  installed on the reference dev machine, unrelated to this plan's phases); the Monitoring-Report
  product bet and Tinh onboarding (correctly sequenced after this plan's proof, per the source
  brainstorm); parallelizing section drafting for wall-clock speed (only worth doing if PHASE-03's run
  turns out to take uncomfortably long — not pre-built speculatively); any change to the per-family
  `ProjectInput` schema (deferred decision, unaffected by this plan); removing the dead, unused
  `_PROJECT_ALIASES` dict at `src/pdd_agent/cli.py:188` (duplicate of the working `project_aliases`
  dict inside `_run_prove` at line 681 — noted as a Gotcha below, not fixed here to avoid scope creep).

## Environment & Conventions
- **Stack:** Python 3.11+ (`requires-python = ">=3.11"` in `pyproject.toml`), packaged with
  `hatchling`. Pydantic v2 for `schemas/project_input.py`; dataclasses elsewhere. `structlog`
  event-style logging (`logger.warning("event_name", key=value)`). `argparse` CLI (console script
  `pdd-agent = pdd_agent.cli:main`). Dependency management: `uv` with a committed `uv.lock` (a
  `pip install -e` path also works and is what CI's primary `test` job uses).
- **Setup:** `pip install -e ".[dev,service,export,llm]"` (pip path) or `uv sync --all-extras` (uv
  path).
- **Build / Run:** No build step. CLI: `pdd-agent <command>` (or `uv run --no-sync pdd-agent
  <command>`).
- **Test:** Full suite: `python -m pytest -m "not corpus" -q` (currently: 729 passed, 7 deselected).
  Single file: `python -m pytest tests/test_section_orchestrator.py -v`. Single test:
  `python -m pytest tests/test_judge_selection.py::TestSelectJudgeProvider::test_prefers_anthropic_over_drafting_provider -v`
  (this exact test is created in PHASE-01 below). On Windows dev machines, a foreign `PYTHONPATH` may
  leak in from other tooling — if the full suite errors on collection with unrelated `ModuleNotFoundError`s,
  clear it first: `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` (POSIX shell) or
  `$env:PYTHONPATH=''; uv run --no-sync python -m pytest -m "not corpus" -q` (PowerShell).
- **Conventions & traps:** `ruff` with `line-length = 100`, `target-version = "py311"`; run
  `ruff check .` and `ruff format .` before committing (CI's `test` job runs `ruff check .` and
  `ruff format --check .`, and a separate `lock-reproducibility` job enforces `uv lock --check`).
  **Tests must NEVER require API keys, network access, a running Ollama instance, or an installed
  `claude`/`gws` CLI — mock all HTTP, subprocess, and `shutil.which` calls.** This constraint is
  load-bearing for PHASE-02 specifically: see `## Gotchas`. `demo`/`noop` providers are the safe
  default; real providers are opt-in via env vars. Model pricing units in
  `configs/model_pricing.yaml` are USD per 1,000,000 tokens. `.env` in the invocation directory is
  auto-loaded via `python-dotenv`; never commit one.
- **Repo map:**
  - `src/pdd_agent/agent/section_orchestrator.py` — per-section retrieval → prompt assembly →
    provider call → judge/redraft loop. `_run_judge_redraft_loop` (currently ~line 669) owns the
    in-loop judge-provider resolution this plan fixes.
  - `src/pdd_agent/phase05/provider_scorecard.py` — `run_provider_scorecard()`, the CLI-facing `prove`
    engine; already has correct never-self-judge logic (`_select_judge_provider`,
    `_is_provider_available`, `_JUDGE_PREFERENCE_ORDER`) that PHASE-01 extracts to a shared module.
  - `src/pdd_agent/llm/claude_code_provider.py` — the keyless frontier provider (263 lines, already
    implemented and tested); shells out to `claude -p --output-format json --model {model}
    --append-system-prompt "{text}"`.
  - `src/pdd_agent/review/judge.py` — `LLMJudge(provider_name, rubric_path, pass_threshold, use_llm,
    model_name, methodology_ids, token_budget)`; `token_budget` (when passed) attaches to the judge's
    provider via `set_budget` so judge-call tokens land in the same budget as drafting tokens.
  - `src/pdd_agent/ingest/registry_download.py` — `_search_projects()`, `download_registered_pdds()`,
    `refresh_manifest()`; PHASE-04 replaces the guessed OData payload shape with a devtools-verified one.
  - `src/pdd_agent/cli.py` — `prove` subcommand (`_run_prove`, ~line 678); project aliases:
    `socson` → `configs/projects/demo_socson_like.yaml`, `inegol` →
    `configs/demo/inegol_project_input.yaml`, `rice` → `configs/projects/rice_vm0051_pilot.yaml`.
  - `configs/corpus_buckets/verra-{rice-vm0051,biochar-vm0044,cookstove-amsiig}.yaml` — bucket configs
    for the three families PHASE-04 populates real corpus for.
  - `docs/corpus-readiness.md` — has a "New Family Corpora — Registry Fetch Status" table currently
    showing "Manual-download mode / 0 documents" for all three families; PHASE-04 updates it.

## Research Inputs
- From `research/2026-07-23-pdd-run-the-proof-and-close-the-loop-brainstorm.md`:
  - Verified directly against the repo and environment (2026-07-23): 729 tests passed / 7 deselected;
    CI green with branch protection active; the `claude` CLI is present and on `PATH` on the reference
    dev machine; `reports/` contains zero `prove-*.md` artifacts — the full-scale proof has never run.
  - The prior push's own final report (`reports/2026-07-17-final-phase-03-04-05-06-*.html`) explicitly
    ran only a *bounded, small* manual verification call instead of the full 36-section
    `pdd-agent prove --project inegol --providers claude-code`, specifically because the in-loop
    redraft judge still self-judges by default — and flagged both "fix the self-judging redraft loop"
    and "run the full proof" as immediate next steps, unexecuted as of this plan.
  - `A1` (fix self-judging): mirror `provider_scorecard.py`'s PHASE-04 cross-judge preference-order
    logic (`["anthropic", "openai", "claude-code", "ollama"]`, first available non-drafting provider,
    `demo` fallback) into the orchestrator's redraft path, with an explicit regression test asserting
    the judge provider differs from the drafting provider when alternatives exist.
  - `A2`/`A3` (run the proof): no new code required beyond the A1 fix — the `claude` CLI is on `PATH`
    in the reference environment, no procurement or external dependency blocks this. Budget real
    wall-clock cost: up to 36 sequential `claude -p` subprocess calls per project, plus judge/redraft
    calls.
  - `B1` (registry capture): the registry blocker has been open since 2026-07-12 (three prior pushes),
    always described as "needs browser-devtools inspection of the search API shape" — a one-time
    interactive capture with any standard browser's devtools Network tab resolves it, independent of
    A1–A3.

## Assumptions and Constraints
- **ASM-001:** The shared judge-selection logic should live in a new module,
  `src/pdd_agent/llm/judge_selection.py`, rather than having `section_orchestrator.py` import from
  `phase05/provider_scorecard.py` directly — grounded in the repo: `provider_scorecard.py` already
  imports `SectionOrchestrator` from `section_orchestrator.py`, so the reverse import would be
  circular. A new leaf module under `src/pdd_agent/llm/` (sibling to `budget.py`, `provider.py`) has no
  such conflict.
- **ASM-002:** `select_judge_provider`'s pure form (given a precomputed `available_providers: list[str]`)
  is kept for `provider_scorecard.py` (which already computes availability once for the whole
  scorecard run and must not re-probe per provider), while `section_orchestrator.py` gets a new
  convenience wrapper, `resolve_judge_provider(drafting_provider: str) -> tuple[str, bool]`, that
  probes `JUDGE_PREFERENCE_ORDER` itself and delegates to `select_judge_provider` — because the
  orchestrator has no precomputed availability list of its own (it judges one provider per run, not a
  fleet). **BINDING DEFAULT:** implement exactly this two-function split; do not force a single
  signature onto both call sites.
- **ASM-003:** The orchestrator must resolve the judge provider **once per orchestrator instance** (not
  once per section) — **BINDING DEFAULT:** cache the `(judge_provider_name, use_llm)` tuple on the
  `SectionOrchestrator` instance after the first resolution, because `is_provider_available("ollama")`
  performs a live 2-second-timeout HTTP probe, and a 36-section run would otherwise repeat that probe
  up to 36 times.
- **ASM-004:** Tests exercising `enable_judge=True` must not depend on which real-provider CLIs/keys
  happen to be present on the machine running `pytest` — grounded in the repo's own stated constraint
  ("tests must never require API keys, network access, a running Ollama instance... mock all HTTP") and
  the concrete fact that the reference dev machine has `claude` on `PATH`, which would otherwise make
  `resolve_judge_provider` pick `claude-code` as judge during test runs and shell out for real.
  **BINDING DEFAULT:** every test that triggers the in-loop judge/redraft path must explicitly force
  every real provider unavailable (`monkeypatch.delenv` the API-key env vars, `monkeypatch.setattr` the
  `shutil.which` used by the availability check to return `None`, and mock `urllib.request.urlopen` to
  raise for the Ollama probe) so the judge deterministically falls back to `demo`, OR must explicitly
  monkeypatch `resolve_judge_provider`/`LLMJudge` itself when testing the wiring in isolation. See
  `## Gotchas` for the exact patch targets.
- **ASM-005:** PHASE-03 (running the real proof) is an operational phase, not a code-only phase — its
  tasks describe real commands to run and real artifacts to inspect, not files to edit. **BINDING
  DEFAULT:** whoever executes this plan runs PHASE-03's commands themselves as a deliberate action
  (they involve real, though subscription-billed rather than pay-per-token, `claude` CLI usage and
  meaningful wall-clock time — plan for 15–60+ minutes per project run, not seconds).
- **ASM-006:** PHASE-04's exact Verra registry search request/response shape cannot be known without a
  live capture (the current payload in `registry_download.py` is explicitly documented as an unverified
  guess). **BINDING DEFAULT:** the executor performs one live, interactive search on
  `https://registry.verra.org/app/search/VCS` with browser devtools' Network tab open, filtered to
  methodology `VM0051`, and uses the *actually observed* request URL, method, headers, and body shape
  — not the currently-guessed OData shape — to rewrite `_search_projects()`. If the observed shape
  differs from OData (`$filter`/`$top`/`$skip`), follow the observed shape exactly; do not preserve the
  guessed shape "just in case."
- **ASM-007:** No PII or non-public data is involved in the registry capture — the Verra registry
  search endpoint returns only public project-registration metadata, the same data a human researcher
  sees in the browser. **BINDING DEFAULT:** captured fixtures may be committed to the repo under
  `tests/fixtures/registry_capture/`.
- **CON-001:** Tests must not require API keys, network access, a running Ollama instance, or an
  installed `claude`/`gws` CLI (existing repo-wide constraint, restated here because PHASE-02
  specifically risks violating it if not handled per ASM-004).
- **CON-002:** `ruff check .` and `ruff format --check .` must pass on all new/modified files (line
  length 100).
- **CON-003:** Backward compatibility bar for PHASE-01/02: for any drafting provider when
  `PDD_JUDGE_PROVIDER` is explicitly set, behavior must be unchanged from today (explicit env override
  always wins, exactly as it does in `provider_scorecard.py` today).
- **DEC-001:** Judge preference order is `["anthropic", "openai", "claude-code", "ollama"]`, unchanged
  from the existing `_JUDGE_PREFERENCE_ORDER` in `provider_scorecard.py` — PHASE-01 relocates this
  constant, it does not redesign it.
- **DEC-002:** `prove`'s CLI surface (`--project`, `--providers`, `--output`, `--no-judge`) is unchanged
  by this plan. PHASE-03 uses the existing flags exactly as documented in `README.md`.

## Specification
Judge-provider resolution logic (PHASE-01/02), the single source of truth both call sites use:

1. If the `PDD_JUDGE_PROVIDER` environment variable is set, use it as the judge provider. Its
   `use_llm` flag is `True` unless its value is `"demo"` or `"noop"`.
2. Otherwise, iterate `JUDGE_PREFERENCE_ORDER = ["anthropic", "openai", "claude-code", "ollama"]` in
   order. For each candidate, skip it if it equals the drafting provider's name (a provider must never
   judge itself). Otherwise check availability:
   - `"anthropic"` / `"openai"`: available iff the `{PROVIDER}_API_KEY` environment variable
     (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) is set (cost-ceiling gating for these two stays in
     `provider_scorecard.py`'s own `_is_provider_available`, unchanged — the shared
     `is_provider_available` used by both call sites checks only the key, matching what
     `judge_selection.is_provider_available` needs for judge-selection purposes; drafting availability
     gating is a separate, already-correct concern in `provider_scorecard.py` and is not touched by
     this plan).
   - `"claude-code"`: available iff `shutil.which(os.environ.get("CLAUDE_CODE_CLI", "claude"))` is not
     `None`.
   - `"ollama"`: available iff a GET to `{OLLAMA_BASE_URL or "http://localhost:11434"}/api/tags`
     succeeds within 2 seconds.
   - The first available, non-self candidate is selected with `use_llm=True`.
3. If no candidate qualifies, fall back to `("demo", use_llm=False)` — the deterministic rule-based
   judge, which makes zero real provider calls.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Extract never-self-judge selection logic into a shared module | None | `src/pdd_agent/llm/judge_selection.py`, `tests/test_judge_selection.py`, `provider_scorecard.py` refactored to import (not redefine) |
| PHASE-02 | Fix the in-loop redraft judge to use the shared logic (the actual A1 bug fix) | PHASE-01 | `section_orchestrator.py` wired to `resolve_judge_provider`, judge-budget threading, regression tests |
| PHASE-03 | Run the first real-model multi-family proof (Inegol + rice) | PHASE-02 | `reports/prove-inegol-claude-code.md`, `reports/prove-rice-claude-code.md`, findings doc |
| PHASE-04 | Capture the live Verra registry search API and populate real corpora | None (independent of PHASE-01–03) | `_search_projects()` rewritten against a verified payload shape, `tests/fixtures/registry_capture/`, populated `data/corpus/registry/{vm0051,vm0044,amsiig}/` |

## Detailed Phases

### PHASE-01 - Extract Shared Judge-Selection Logic
**Goal**
Move the already-correct never-self-judge selection logic out of `provider_scorecard.py` and into a
new shared module so `section_orchestrator.py` can use the identical logic in PHASE-02, without a
circular import and without duplicating the availability-probing code a second time.

**Tasks**
- [x] TASK-01-01: Create `src/pdd_agent/llm/judge_selection.py` containing the relocated
      `JUDGE_PREFERENCE_ORDER` constant, `probe_ollama_available()`, `is_provider_available()`, and
      `select_judge_provider()` — moved verbatim (same behavior) from `provider_scorecard.py`, plus a
      new `resolve_judge_provider()` convenience function for single-call-site use (see Function
      Signatures below).
- [x] TASK-01-02: Modify `src/pdd_agent/phase05/provider_scorecard.py` to delete its local
      `_JUDGE_PREFERENCE_ORDER`, `_probe_ollama_available`, `_is_provider_available`,
      `_select_judge_provider` definitions and instead import the relocated functions from
      `judge_selection.py`, binding them to the same private names (`_is_provider_available =
      is_provider_available`, `_select_judge_provider = select_judge_provider`) so every other line in
      the file (which calls these by their old private names) needs no further change. Remove the
      now-unused `import shutil`, `import urllib.error`, `import urllib.request` lines (verify via
      `ruff check src/pdd_agent/phase05/provider_scorecard.py` that nothing else in the file still
      references them before removing).
- [x] TASK-01-03: Create `tests/test_judge_selection.py`. Move the existing `TestIsProviderAvailable`
      and `TestSelectJudgeProvider` test classes from `tests/test_provider_scorecard.py` into this new
      file, updating imports to `from pdd_agent.llm.judge_selection import (is_provider_available,
      select_judge_provider)` and updating every `monkeypatch.setattr("pdd_agent.phase05.
      provider_scorecard.shutil.which", ...)` call to target
      `"pdd_agent.llm.judge_selection.shutil.which"` instead (see `## Gotchas` for why this exact
      string must change). Add new test coverage for `resolve_judge_provider()` (see Test Specs).
- [x] TASK-01-04: Modify `tests/test_provider_scorecard.py`: delete the `TestIsProviderAvailable` and
      `TestSelectJudgeProvider` classes (now live in `test_judge_selection.py`). Leave the module-level
      import of `_is_provider_available` and `_select_judge_provider` from
      `pdd_agent.phase05.provider_scorecard` unchanged — they are still used directly by
      `TestRunProviderScorecard` and `TestAutoModeScorecard` in the same file (e.g. the
      `monkeypatch.setattr("pdd_agent.phase05.provider_scorecard._is_provider_available", ...)` calls
      around what is currently line 161 and line 245) and remain valid because TASK-01-02 keeps those
      names bound in `provider_scorecard`'s module namespace via import-alias.

**File Changes**
- `src/pdd_agent/llm/judge_selection.py` (create): module docstring explaining this is the shared
  never-self-judge selection logic used by both `prove`'s post-hoc scorecard and the in-loop redraft
  judge. Contents: `import os`, `import shutil`, `import urllib.error`, `import urllib.request`;
  `JUDGE_PREFERENCE_ORDER = ["anthropic", "openai", "claude-code", "ollama"]`;
  `probe_ollama_available()`, `is_provider_available()`, `select_judge_provider()` (bodies identical to
  today's `_probe_ollama_available`, `_is_provider_available`, `_select_judge_provider` in
  `provider_scorecard.py`, only renamed to drop the leading underscore since they are now a shared,
  cross-module API); new `resolve_judge_provider()` (see Function Signatures).
- `src/pdd_agent/phase05/provider_scorecard.py` (modify): delete four specific definitions —
  `_JUDGE_PREFERENCE_ORDER` (currently line 38), `_probe_ollama_available` (currently lines 69–84),
  `_is_provider_available` (currently lines 86–104), `_select_judge_provider` (currently lines
  107–126). These are **not contiguous**: `@dataclass class ProviderScorecardRow` (currently lines
  41–56) and `_parse_positive_float` (currently lines 59–66) sit between `_JUDGE_PREFERENCE_ORDER` and
  `_probe_ollama_available` and must be preserved untouched — delete only the four named
  definitions, not the lines between them. Add near the top, after the existing
  `from pdd_agent.llm.provider import get_provider_registry` import:
  `from pdd_agent.llm.judge_selection import (JUDGE_PREFERENCE_ORDER as _JUDGE_PREFERENCE_ORDER,
  is_provider_available as _is_provider_available, select_judge_provider as
  _select_judge_provider)`. Remove `import shutil`, `import urllib.error`, `import urllib.request`
  from the top-level import block. Leave every other function in the file (`_run_one_provider`,
  `_render_row`, `_render_scorecard`, `run_provider_scorecard`, `_resolve_providers`,
  `_count_failed_sections`, `ProviderScorecardRow`) completely unchanged — they reference
  `_is_provider_available` / `_select_judge_provider` / `_JUDGE_PREFERENCE_ORDER` by name only and do
  not care whether those names are `def`s or import-aliases.
- `tests/test_judge_selection.py` (create): the moved `TestIsProviderAvailable` and
  `TestSelectJudgeProvider` classes (11 existing test methods total, see current
  `tests/test_provider_scorecard.py` lines 21–89 for the exact bodies to move), plus new
  `TestResolveJudgeProvider` coverage (see Test Specs).
- `tests/test_provider_scorecard.py` (modify): delete the `TestIsProviderAvailable` and
  `TestSelectJudgeProvider` classes (currently lines 21–89). No other change to this file.

**Function Signatures**
- `probe_ollama_available() -> tuple[bool, str | None]` — `(True, None)` if a GET to
  `{OLLAMA_BASE_URL env var or "http://localhost:11434"}/api/tags` succeeds within 2 seconds, else
  `(False, "ollama_unreachable")`.
- `is_provider_available(provider_name: str) -> tuple[bool, str | None]` — `(True, None)` for
  `"demo"`/`"noop"` always; delegates to `probe_ollama_available()` for `"ollama"`; checks
  `shutil.which(os.environ.get("CLAUDE_CODE_CLI", "claude"))` for `"claude-code"`; checks
  `{PROVIDER}_API_KEY` env var presence and a positive `PDD_MAX_COST_USD` for `"openai"`/`"anthropic"`;
  `(False, "unknown_provider")` for anything else.
- `select_judge_provider(drafting_provider: str, available_providers: list[str]) -> tuple[str, bool]`
  — resolves which provider judges `drafting_provider`'s output given a precomputed list of already-
  available provider names. Returns `(name, use_llm)`. Honors `PDD_JUDGE_PROVIDER` env override first;
  otherwise the first `JUDGE_PREFERENCE_ORDER` entry present in `available_providers` that isn't
  `drafting_provider`; else `("demo", False)`.
- `resolve_judge_provider(drafting_provider: str) -> tuple[str, bool]` — convenience wrapper for
  single-call-site use (no precomputed availability list available): builds
  `available = [p for p in JUDGE_PREFERENCE_ORDER if is_provider_available(p)[0]]` then returns
  `select_judge_provider(drafting_provider, available)`. This is what `section_orchestrator.py` calls
  in PHASE-02.

**Test Specs**
- `is_provider_available("claude-code")` with `shutil.which` patched to return `None` →
  `(False, "claude_cli_not_found")` (moved verbatim from existing
  `test_claude_code_unavailable_without_cli`).
- `select_judge_provider("ollama", ["demo", "ollama", "anthropic"])` →
  `("anthropic", True)` (moved verbatim from existing `test_prefers_anthropic_over_drafting_provider`).
- New: `resolve_judge_provider("claude-code")` with `is_provider_available` patched via
  `monkeypatch.setattr("pdd_agent.llm.judge_selection.is_provider_available", lambda name: (True,
  None) if name == "anthropic" else (False, "unavailable"))` and `PDD_JUDGE_PROVIDER` unset →
  `("anthropic", True)` (drafting provider `claude-code` is correctly skipped even though it would
  otherwise be a "real" candidate later in the preference order).
- New: `resolve_judge_provider("ollama")` with `is_provider_available` patched to always return
  `(False, "unavailable")` → `("demo", False)` (full fallback, no candidate available).
- New: `resolve_judge_provider("anthropic")` with `PDD_JUDGE_PROVIDER="ollama"` env var set →
  `("ollama", True)` (explicit env override always wins, even naming a normally-available-but-lower-
  preference candidate).

**Dependencies**
- None.

**Exit Criteria**
- [ ] `python -m pytest tests/test_judge_selection.py -v` — all tests pass.
- [ ] `python -m pytest tests/test_provider_scorecard.py -v` — all remaining tests pass (same pass
      count as before this phase, minus the 11 moved tests).
- [ ] `ruff check src/pdd_agent/llm/judge_selection.py src/pdd_agent/phase05/provider_scorecard.py` —
      no findings (confirms the unused-import removals were correct).
- [ ] `python -m pytest -m "not corpus" -q` — full suite passes with the same total test count as
      before this phase (tests moved, not lost or duplicated).

**Phase Risks**
- **RISK-01-01:** Deleting `import shutil`/`urllib.error`/`urllib.request` from
  `provider_scorecard.py` before confirming nothing else in the file uses them would break the module
  at import time. Mitigation: run `ruff check` (which flags unused imports as F401, so their *absence*
  after removal proves nothing else needed them) and the file's own test suite before considering
  TASK-01-02 done.

### PHASE-02 - Fix the In-Loop Redraft Judge (the A1 Bug Fix)
**Goal**
Replace `section_orchestrator.py`'s self-judging default (`os.environ.get("PDD_JUDGE_PROVIDER",
drafting_provider_name)`) with a call to the shared `resolve_judge_provider()` from PHASE-01, cached
once per orchestrator run, and thread the run's `TokenBudget` into the in-loop judge so its token cost
is counted (matching what `provider_scorecard.py`'s post-hoc judging pass already does correctly).

**Tasks**
- [x] TASK-02-01: Add `from pdd_agent.llm.judge_selection import resolve_judge_provider` to the imports
      in `src/pdd_agent/agent/section_orchestrator.py`.
- [x] TASK-02-02: Add a `self._judge_provider_cache: tuple[str, bool] | None = None` instance
      attribute in `SectionOrchestrator.__init__` (alongside the existing `self.redraft_count: int = 0`
      line), and a new private method `_resolve_judge_provider(self, drafting_provider_name: str) ->
      tuple[str, bool]` that lazily computes and caches the result of `resolve_judge_provider(...)`.
- [x] TASK-02-03: In `_run_judge_redraft_loop`, replace the two lines
      ```python
      drafting_provider_name = getattr(self._provider, "name", "demo")
      judge_provider_name = os.environ.get("PDD_JUDGE_PROVIDER", drafting_provider_name)
      ```
      with
      ```python
      drafting_provider_name = getattr(self._provider, "name", "demo")
      judge_provider_name, judge_use_llm = self._resolve_judge_provider(drafting_provider_name)
      ```
      and update the `LLMJudge(...)` construction immediately below to use `use_llm=judge_use_llm`
      (instead of the old inline `judge_provider_name not in ("demo", "noop")` expression) and add
      `token_budget=self._budget` as a new keyword argument (this is the ASM-008-equivalent fix noted
      in the source brainstorm's Track C3: judge-call tokens were previously excluded from the
      in-loop judge's cost accounting).
- [x] TASK-02-04: Remove the now-dead local `import os` statement inside `_run_judge_redraft_loop`
      (it was only used for the line replaced in TASK-02-03; confirm via `ruff check` that no other
      `os.` reference remains in that function before deleting the import).
- [x] TASK-02-05: Update `tests/test_section_orchestrator.py`'s existing
      `test_judge_redraft_loop_parks_failed_section` test to explicitly force deterministic judge
      fallback (see `## Gotchas` for why this is required — the reference dev machine has `claude` on
      `PATH`, which would otherwise make this test actually shell out): add a `monkeypatch` parameter
      and the four explicit unavailability patches listed in ASM-004 before constructing the
      orchestrator.
- [x] TASK-02-06: Add new regression tests to `tests/test_section_orchestrator.py` proving the fix
      (see Test Specs below): the judge provider must never equal the drafting provider when an
      alternative is available, and must fall back to `demo` (never silently defaulting back to the
      drafting provider) when nothing else is available.

**File Changes**
- `src/pdd_agent/agent/section_orchestrator.py` (modify): add the import (near the existing
  `from pdd_agent.review.judge import LLMJudge` line); add `_judge_provider_cache` init and
  `_resolve_judge_provider` method; rewrite the judge-provider-resolution lines inside
  `_run_judge_redraft_loop` per TASK-02-03; delete the function-local `import os` per TASK-02-04.
  Leave every other method (`draft_section`, `_enrich_draft`, `_build_redraft_prompt`,
  `_park_section_for_domain_review`, `draft_all_sections`, `run`, `run_review`, etc.) unchanged.
- `tests/test_section_orchestrator.py` (modify): update
  `test_judge_redraft_loop_parks_failed_section` per TASK-02-05; add a new `TestRedraftJudgeSelection`
  class per TASK-02-06.

**Function Signatures**
- `SectionOrchestrator._resolve_judge_provider(self, drafting_provider_name: str) -> tuple[str, bool]`
  — returns the cached `(judge_provider_name, use_llm)` tuple, computing it via
  `resolve_judge_provider(drafting_provider_name)` on first call within this orchestrator instance's
  lifetime and reusing it for every subsequent section in the same run.

**Test Specs**
- `test_judge_redraft_loop_parks_failed_section` (updated): with `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`
  unset, `pdd_agent.llm.judge_selection.shutil.which` patched to return `None`, and
  `pdd_agent.llm.judge_selection.urllib.request.urlopen` patched to raise `urllib.error.URLError`, the
  test's existing assertions (`draft.confidence == "UNSUPPORTED"`, `"JUDGE REDRAFT FAILED"` in issues)
  must still pass — this proves the fix doesn't change deterministic-fallback behavior, only removes
  the self-judging default.
- New `TestRedraftJudgeSelection.test_never_self_judges_when_alternative_available`: construct a fake
  provider with `.name = "ollama"` (reuse the existing `_CitationFailingProvider` pattern, or a
  minimal new fake), monkeypatch `pdd_agent.agent.section_orchestrator.resolve_judge_provider` to
  return `("anthropic", True)` unconditionally, monkeypatch
  `pdd_agent.agent.section_orchestrator.LLMJudge` with a `MagicMock` whose `judge_section` returns a
  passing `JudgeResult`, construct `SectionOrchestrator(provider=<fake ollama provider>,
  enable_judge=True)`, call `draft_section("1", "1.1")`, then assert the mocked `LLMJudge` was
  constructed with `provider_name="anthropic"` (never `"ollama"`, the drafting provider's own name).
- New `TestRedraftJudgeSelection.test_falls_back_to_demo_when_no_alternative`: same setup, but
  monkeypatch `resolve_judge_provider` to return `("demo", False)`, and assert `LLMJudge` was
  constructed with `provider_name="demo", use_llm=False`.
- New `TestRedraftJudgeSelection.test_caches_judge_provider_across_sections`: monkeypatch
  `resolve_judge_provider` with a `MagicMock(return_value=("anthropic", True))`, construct an
  orchestrator with `enable_judge=True`, call `draft_section` for two different sections (e.g. `("1",
  "1.1")` and `("1", "1.2")`), then assert the `resolve_judge_provider` mock was called exactly once
  (proving the per-instance cache from TASK-02-02 works, not re-resolving — and not re-probing
  Ollama/keys — on every section).

**Dependencies**
- PHASE-01 (needs `judge_selection.resolve_judge_provider` to exist).

**Exit Criteria**
- [ ] `python -m pytest tests/test_section_orchestrator.py -v` — all tests pass, including the three
      new `TestRedraftJudgeSelection` tests and the updated
      `test_judge_redraft_loop_parks_failed_section`.
- [ ] `python -m pytest -m "not corpus" -q` — full suite passes.
- [ ] `ruff check src/pdd_agent/agent/section_orchestrator.py` — no findings (confirms the dead
      `import os` was actually removed and nothing else broke).
- [ ] Manual check: `grep -n "PDD_JUDGE_PROVIDER, drafting_provider_name" src/pdd_agent/agent/section_orchestrator.py`
      returns no results (the literal self-judging default line is gone).

**Phase Risks**
- **RISK-02-01:** If TASK-02-05 is skipped, `test_judge_redraft_loop_parks_failed_section` becomes
  environment-dependent: on any machine with `claude` on `PATH` (including the reference dev machine
  this plan was authored on), the fix from PHASE-02 would make this test's in-loop judge actually
  select `claude-code` and shell out to the real CLI during a `pytest` run, violating the repo's own
  "tests must never require... an installed `claude`... CLI" constraint and potentially incurring real
  (if subscription-billed) usage from a test run. Mitigation: TASK-02-05 is not optional — verify by
  temporarily running the test suite on a machine with `claude` on `PATH` and confirming no subprocess
  to `claude` occurs (e.g. via `strace`/`Process Monitor`, or simpler: temporarily add a print/log
  inside `ClaudeCodeProvider._call_cli` and confirm it's never hit during `pytest tests/
  test_section_orchestrator.py -v`).

### PHASE-03 - Run the First Real-Model Multi-Family Proof
**Goal**
Execute `pdd-agent prove` against the `claude-code` provider for both the WTE family (Inegol) and a
non-WTE family (rice), now that PHASE-02 has made the in-loop judge safe to run by default, producing
the project's first real-model drafting artifacts and a findings write-up.

**Tasks**
- [ ] TASK-03-01: Confirm the environment is ready: run `claude --version` (expect a version string,
      not a "command not found" error) and `pdd-agent doctor` (expect the `claude CLI` line to report
      `[OK]`, not `[WARN]`).
- [ ] TASK-03-02: Run `pdd-agent prove --project inegol --providers claude-code --output
      reports/prove-inegol-claude-code.md`. This uses the existing `inegol` alias
      (`configs/demo/inegol_project_input.yaml`) and drafts all 36 sections via the `claude-code`
      provider with the in-loop judge enabled by default (no `--no-judge` flag needed — PHASE-02 made
      the default safe: with no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/Ollama available on the reference
      machine, `resolve_judge_provider("claude-code")` falls back to the deterministic `demo` judge,
      which makes zero additional real-provider calls for judging itself, only for any redraft
      attempts the deterministic judge's findings trigger).
- [ ] TASK-03-03: Inspect `reports/prove-inegol-claude-code.md`. Record: `Sections drafted` (expect
      36), `Sections failed` (expect 0 — investigate and resolve before proceeding if nonzero;
      `[CLAUDE-CODE ERROR` prefixed section text indicates a CLI-invocation failure, see
      `claude_code_provider.py`'s error path), `Judge` column value (expect `demo` given the reference
      machine's environment, unless the operator has since set real provider keys), `Redraft count`,
      `Total tokens`, `Est. cost (USD)` (expect `$0.0` — subscription-billed, not per-token), `Wall
      clock (s)`.
- [ ] TASK-03-04: Run `pdd-agent prove --project rice --providers claude-code --output
      reports/prove-rice-claude-code.md`, using the existing `rice` alias
      (`configs/projects/rice_vm0051_pilot.yaml`). Repeat the same inspection as TASK-03-03.
- [ ] TASK-03-05: Create `docs/<run-date>-real-model-proof-findings.md` (substitute the actual date the
      runs completed) summarizing both runs in the same runbook style as the existing
      `docs/ollama-dress-rehearsal.md`: sections drafted/failed per project, redraft counts, judge
      provider actually used, wall-clock time, any marker-parsing anomalies observed in the drafted
      text (`[MISSING]`, `[INFERENCE]`, `[REVIEW REQUIRED]` frequency), and an explicit go/no-go
      statement on whether the resulting Inegol DOCX is ready for domain-expert sign-off.
- [ ] TASK-03-06: Update `README.md`'s "Known Gaps" section: remove or amend the bullet stating "Real
      LLM providers (OpenAI, Anthropic) are implemented but have never executed a live drafting run" —
      it is now inaccurate (the `claude-code` provider, itself a real frontier Anthropic model, has
      run live). Update `activeContext.md` to record this plan's completion, the two report paths, and
      the findings doc path.

**File Changes**
- `reports/prove-inegol-claude-code.md` (create): output of TASK-03-02, generated by
  `run_provider_scorecard` — do not hand-author this file.
- `reports/prove-rice-claude-code.md` (create): output of TASK-03-04, generated the same way.
- `docs/<run-date>-real-model-proof-findings.md` (create): hand-authored findings write-up per
  TASK-03-05.
- `README.md` (modify): the "Known Gaps" bullet per TASK-03-06. Leave every other line unchanged.
- `activeContext.md` (modify): record this plan's phase progress and completion per this project's
  existing convention (see the file's current structure — a "Phase progress" checklist, "Test results"
  section, and "Suggested next steps" list).

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
None — no testable behavior changes in this phase (the artifacts produced are operational evidence,
verified by the Exit Criteria below via direct inspection, not by automated tests).

**Dependencies**
- PHASE-02 (the in-loop judge must be fixed before running this at scale, per PHASE-02's own
  RISK-02-01 and the source brainstorm's explicit warning against running the full proof before A1
  lands).

**Exit Criteria**
- [ ] `reports/prove-inegol-claude-code.md` exists and shows `Sections drafted = 36`,
      `Sections failed = 0`.
- [ ] `reports/prove-rice-claude-code.md` exists and shows `Sections drafted = 36`,
      `Sections failed = 0`.
- [ ] `docs/<run-date>-real-model-proof-findings.md` exists with an explicit go/no-go statement.
- [ ] `grep -c "REVIEW REQUIRED\|MISSING\|CLAUDE-CODE ERROR" reports/prove-inegol-claude-code.md` and
      the rice equivalent have been reviewed and their counts recorded in the findings doc (a nonzero
      count is not itself a failure — it is exactly the anti-hallucination marker system working as
      designed — but it must be recorded, not ignored).

**Phase Risks**
- **RISK-03-01:** A 36-section run against a real CLI has meaningfully longer wall-clock time and less
  predictable failure modes than the `demo`/`noop` providers this project has run almost exclusively
  until now (subprocess timeouts, CLI authentication expiring mid-run, rate limiting). Mitigation: the
  `claude-code` provider already has a `_MAX_RETRIES = 2` retry loop with backoff and a
  `_DEFAULT_TIMEOUT_SECONDS = 300` per-call timeout (both already implemented, not new code this
  plan adds); if TASK-03-02/04 shows a nonzero `Sections failed`, treat that as a real finding for the
  findings doc (TASK-03-05), not a plan failure to silently retry away.
- **RISK-03-02:** This phase involves real (though subscription-metered, not pay-per-token) API usage
  and non-trivial wall-clock time under the operator's own Claude subscription — per ASM-005, this
  must be a deliberate, knowing action by whoever executes this phase, not an unattended side effect.

### PHASE-04 - Capture the Live Verra Registry Search API
**Goal**
Replace `registry_download.py`'s unverified, best-effort OData search payload with one confirmed
against a real, devtools-observed request/response from the public Verra registry search UI, then use
it to populate real (non-synthetic) corpus documents for the rice, biochar, and cookstove methodology
families for the first time.

**Tasks**
- [ ] TASK-04-01: Using a web browser with developer tools open to the Network tab, navigate to
      `https://registry.verra.org/app/search/VCS`. Filter the search by methodology `VM0051` (or the
      closest available filter the UI exposes — e.g. a free-text search for "VM0051" if there is no
      dedicated methodology-code filter field) and execute the search. In the Network tab, find the
      XHR/fetch request the search triggers (do not assume it is a POST to
      `/uiapi/asset/asset/search` — confirm the actual method and URL from what fires; the current
      code's guess may be wrong per ASM-006). Record: the exact request URL, HTTP method, all request
      headers the browser sent (excluding cookies/auth tokens, which are session-specific and must not
      be captured or committed), and the full request body (if any).
- [ ] TASK-04-02: From the same captured request, copy the response body (a representative sample is
      fine — 3–5 project records is enough to confirm field names; the full response may be very
      large). Save the request body as `tests/fixtures/registry_capture/vm0051_search_request.json`
      and the trimmed response body as
      `tests/fixtures/registry_capture/vm0051_search_response.json`.
- [ ] TASK-04-03: Rewrite `_search_projects()` in `src/pdd_agent/ingest/registry_download.py` so its
      request-construction (`_SEARCH_URL`, the JSON payload shape, headers) matches the captured
      request exactly, and its response parsing (currently
      `data.get("value", data.get("results", []))` plus the per-project field lookups in
      `download_registered_pdds()`: `project.get("project_id") or project.get("id")`,
      `project.get("title") or project.get("name")`, `project.get("pdd_url") or
      project.get("document_url") or project.get("url")`) matches the real field names observed in the
      captured response — keep the existing multi-fallback `.get(...) or .get(...)` pattern for
      robustness against minor schema variance across different record types, but ensure the *first*
      alternative in each fallback chain is the field name actually observed live.
- [ ] TASK-04-04: Update the module docstring at the top of `registry_download.py` (currently
      describing the payload shape as unverified, "could not be fully reconstructed... without browser
      devtools") to state the shape is now devtools-verified, with the capture date.
- [ ] TASK-04-05: Add a test to `tests/test_registry_download.py` that loads
      `tests/fixtures/registry_capture/vm0051_search_response.json` as a mocked `urlopen` response
      body and asserts `_search_projects("VM0051", limit=5)` correctly parses it into the expected
      number of project records with correct `project_id`/`title`/pdf-url fields — this is a
      regression test against the *real* observed shape, replacing reliance on the existing test's
      hand-constructed guessed-shape fixture (`test_successful_search_and_download`, which may keep
      testing the older guessed shape unchanged as an additional case, or be updated to the real shape
      — either is acceptable as long as both the guessed-shape-compatible parsing and the real shape
      are covered).
- [ ] TASK-04-06: Run `pdd-agent fetch-registry --methodology VM0051 --limit 5 --output-dir
      data/corpus/registry/vm0051` for real. Confirm `data/corpus/registry/vm0051/manifest.json` has
      non-empty `records` and no `"note"` key referencing manual-download mode. Repeat for
      `--methodology VM0044 --output-dir data/corpus/registry/vm0044` (biochar) and
      `--methodology "AMS-II.G" --output-dir data/corpus/registry/amsiig` (cookstove).
- [ ] TASK-04-07: Update `docs/corpus-readiness.md`'s "New Family Corpora — Registry Fetch Status"
      table: change the "Result" column from "Manual-download mode" to "Live" and the "Documents
      downloaded" column from `0` to the actual count, for all three rows.

**File Changes**
- `src/pdd_agent/ingest/registry_download.py` (modify): rewrite `_search_projects()`'s payload
  construction and `download_registered_pdds()`'s field-extraction fallback chains per TASK-04-03;
  update the module docstring per TASK-04-04. Leave `_throttle()`, `_sanitize_filename()`,
  `_download_pdf()`, `_write_manifest()`, `refresh_manifest()` unchanged.
- `tests/fixtures/registry_capture/vm0051_search_request.json` (create): captured request body per
  TASK-04-02.
- `tests/fixtures/registry_capture/vm0051_search_response.json` (create): trimmed captured response
  body per TASK-04-02.
- `tests/test_registry_download.py` (modify): add the new real-shape parsing test per TASK-04-05.
- `docs/corpus-readiness.md` (modify): the "New Family Corpora" table per TASK-04-07. Leave the rest
  of the file (the original April 2026 WTE bucket readiness report) unchanged.
- `data/corpus/registry/vm0051/`, `data/corpus/registry/vm0044/`, `data/corpus/registry/amsiig/`
  (create): populated by TASK-04-06's live `fetch-registry` runs — PDF files plus `manifest.json` each.

**Function Signatures**
- `_search_projects(methodology_id: str, limit: int) -> list[dict[str, Any]]` — signature unchanged
  from today; only its internal payload/parsing logic changes per TASK-04-03.

**Test Specs**
- `_search_projects("VM0051", limit=5)` with `urllib.request.urlopen` mocked to return the captured
  `vm0051_search_response.json` fixture body → returns a list of dicts whose length matches the
  fixture's record count, and whose `project_id`/`title`/pdf-url values match the fixture's real field
  values (not the previously-guessed `project_id`/`title`/`pdd_url` names, unless the capture confirms
  those guesses happened to be correct).
- `download_registered_pdds("VM0051", tmp_path, limit=5)` with the same mocked response and a mocked
  successful PDF download → `manifest.json` in `tmp_path` has no `"note"` key and `len(records) > 0`.

**Dependencies**
- None (independent of PHASE-01–03; may be executed in parallel by a different session/operator).

**Exit Criteria**
- [ ] `python -m pytest tests/test_registry_download.py -v` — all tests pass, including the new
      real-shape test.
- [ ] `data/corpus/registry/vm0051/manifest.json`, `.../vm0044/manifest.json`,
      `.../amsiig/manifest.json` each exist with non-empty `records` and no manual-mode `"note"`.
- [ ] `ruff check src/pdd_agent/ingest/registry_download.py` — no findings.
- [ ] `python -m pytest -m "not corpus" -q` — full suite passes.

**Phase Risks**
- **RISK-04-01:** The Verra registry may rate-limit or block scripted access once real traffic
  patterns are used at scale (beyond the one interactive capture). Mitigation: the existing
  `_throttle()` (2-second minimum interval) and `_MAX_RETRIES = 3` with exponential backoff are already
  implemented and unchanged by this phase; TASK-04-06 uses a small `--limit 5` per family rather than a
  bulk pull, consistent with the "one search, throttled downloads" framing in the source brainstorm's
  ASM-03.
- **RISK-04-02:** If the live registry's actual response shape is fundamentally different from the
  guessed OData shape (e.g. GraphQL instead of REST/OData, or a shape requiring session cookies this
  plan explicitly avoids capturing per ASM-007/TASK-04-01), TASK-04-03 may require a larger rewrite
  than a simple field-name correction. Mitigation: if the captured request requires session-specific
  auth (cookies, CSRF tokens) that a stateless script cannot easily replicate, fall back to documenting
  the exact manual steps in `registry_download.py`'s docstring and treat the live-fetch upgrade
  (TASK-04-03 onward) as not achievable this phase — the manual-download mode (already implemented and
  functioning) remains the safe fallback, and this phase's capture work still has value for a future
  session even if full automation isn't reachable today.

## Gotchas
- **The reference dev machine has `claude` on `PATH`.** Any test that enables the in-loop judge
  (`enable_judge=True`) without explicitly forcing all real providers unavailable will, after PHASE-02,
  pick `claude-code` as judge on this machine and shell out to the real CLI during `pytest` — silently
  violating the repo's "tests never require external tools" rule and potentially costing real
  (subscription) usage on every test run. This is why PHASE-02 (ASM-004, TASK-02-05, RISK-02-01) is not
  optional busywork — skipping it turns the test suite flaky-by-machine.
- **`monkeypatch.setattr("some.module.path.shutil.which", ...)` requires `some.module.path` to
  literally execute `import shutil`** (not `from shutil import which`) — pytest's dotted-string
  `setattr` resolves each segment via `getattr`, so `getattr(module, "shutil")` must succeed. Because
  `shutil` is a real singleton module object, patching `.which` through any one import reference
  patches it for every other reference in the process too — but the *path string itself* must still
  name a module that has that `import shutil` line. This is why TASK-01-03 must retarget the
  monkeypatch strings to `pdd_agent.llm.judge_selection.shutil.which` after the functions move — the
  old string `pdd_agent.phase05.provider_scorecard.shutil.which` will raise `AttributeError` once
  `provider_scorecard.py` no longer imports `shutil` directly.
- **`is_provider_available("ollama")` performs a real 2-second-timeout HTTP probe.** Calling
  `resolve_judge_provider()` fresh on every section (instead of caching per orchestrator instance, per
  ASM-003/TASK-02-02) would add up to 36 such probes to a single run when Ollama is unreachable — not
  fatal, but a real and avoidable latency cost once real providers are actually being used in PHASE-03.
- **`src/pdd_agent/cli.py` has a dead, unused `_PROJECT_ALIASES` dict at line 188**, duplicating the
  working `project_aliases` dict inside `_run_prove()` at line 681. Not touched by this plan (out of
  scope, see Context Snapshot) — noted here so the executor doesn't mistake it for something this plan
  should have wired up.
- **`prove`'s `--providers claude-code` still respects `--no-judge`** if an operator wants a faster,
  cheaper first pass before PHASE-03's full judged run — this flag is unchanged by this plan and
  remains available as an escape hatch if PHASE-03's default (judged) run turns out to take
  uncomfortably long.

## Verification Strategy
- **TEST-001:** `python -m pytest -m "not corpus" -q` → all tests pass (729 baseline plus new tests
  added across PHASE-01/02/04, no regressions).
- **TEST-002:** `python -m pytest tests/test_judge_selection.py tests/test_provider_scorecard.py tests/test_section_orchestrator.py tests/test_registry_download.py -v` → all pass; spot-check output for the specific new test names listed in each phase's Test Specs.
- **TEST-003:** `ruff check . && ruff format --check .` → no findings (matches CI's `test` job).
- **TEST-004:** `grep -n "PDD_JUDGE_PROVIDER, drafting_provider_name" src/pdd_agent/agent/section_orchestrator.py` → no output (confirms the literal self-judging line is gone; see PHASE-02 Exit Criteria).
- **MANUAL-001:** After PHASE-02, run `pdd-agent doctor` and confirm the `claude CLI` line still
  reports `[OK]` (PHASE-02 changes judge selection, not CLI detection — this is a smoke check that
  nothing broke provider registration).
- **MANUAL-002:** After PHASE-03, open `reports/prove-inegol-claude-code.md` in a text editor and read
  at least 3 full section bodies (not just the summary table) to sanity-check the drafted prose reads
  as real, coherent PDD content — not a repeated error placeholder or garbled CLI JSON leaking through.
- **OBS-001:** After PHASE-03, `grep -c "^\[CLAUDE-CODE ERROR" reports/prove-inegol-claude-code.md`
  and the rice equivalent should be `0`; if nonzero, that count directly measures section-level
  provider failures and must be investigated before treating the proof as complete (see PHASE-03
  RISK-03-01).
- **OBS-002:** After PHASE-04, `cat data/corpus/registry/vm0051/manifest.json | python -c "import
  json,sys; d=json.load(sys.stdin); print(len(d['records']), d.get('note', 'no note — live mode'))"`
  → expect a positive record count and `"live mode"` (not a manual-download note).

## Risks and Alternatives
- **RISK-001:** PHASE-01's refactor touches a file (`provider_scorecard.py`) that is exercised by
  CI on every push; a mistake in the import-aliasing could silently change `prove`'s behavior in a way
  the existing test suite doesn't catch. Mitigation: PHASE-01's exit criteria explicitly require the
  full suite to pass with the *same total test count* as before (tests moved, not lost), and TASK-01-02
  is scoped to be a pure mechanical extraction (no logic changes) — the moved function bodies must be
  byte-for-byte behaviorally identical, only their module location changes.
- **RISK-002:** PHASE-03 and PHASE-04 both involve live, non-repo-internal systems (the `claude` CLI's
  subscription-billed usage; the public Verra registry) whose exact behavior cannot be fully verified
  by reading code alone. Both phases' task lists are written to fail safely and document findings
  rather than assume success — this is intentional, not a gap in the plan.
- **ALT-001:** An alternative to PHASE-01's shared-module extraction would be duplicating the
  never-self-judge logic directly inside `section_orchestrator.py` instead of factoring it out. Rejected
  because the source brainstorm explicitly diagnosed the current bug as arising *from* duplicated,
  divergent logic (the scorecard's post-hoc pass got fixed in a prior push; the in-loop pass didn't) —
  a second duplication would recreate the exact failure mode this plan exists to close out.
- **ALT-002:** An alternative to PHASE-03's default judged run would be to always pass `--no-judge` for
  the first real-model proof, deferring judge-quality signal entirely. Rejected because PHASE-02
  already makes the default judged path safe (falls back to the free deterministic `demo` judge on
  this machine's environment, never self-judges, never silently multiplies real calls) — running
  judged by default produces strictly more useful signal (redraft counts, pass rates) at no extra real
  cost in this environment, so there is no reason to throw that away.

## Suggested Next Step
Execute PHASE-01, verify its exit criteria, then proceed to PHASE-02 (which depends on it). PHASE-04
has no dependency on PHASE-01–03 and may be executed at any point, including in parallel by a separate
session, once browser-devtools access is available.
