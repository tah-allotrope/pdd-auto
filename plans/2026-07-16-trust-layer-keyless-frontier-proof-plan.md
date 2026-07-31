---
title: "Trust-Layer Hardening, Honest Proof Harness, and the Keyless Frontier Provider"
date: "2026-07-16"
status: "complete — bulk-corrected 2026-07-31 per directive: plan predates 2026-07-20 and is presumed fully implemented (NOT individually verified against git/code evidence)"
request: "Multi-phase plan for Tracks A2–A5 (CI trust hardening), B1–B5 (proof-harness hardening), C1 (ClaudeCodeProvider keyless frontier path), C4 (small-model Ollama dress rehearsal) from the 2026-07-16 brainstorm"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-16-pdd-trust-layer-and-unblock-brainstorm.md"
---

# Plan: Trust-Layer Hardening, Honest Proof Harness, and the Keyless Frontier Provider

## Objective
Make the project's trust infrastructure (CI, lockfile, environment diagnostics, recorded claims) impossible to silently break again; fix the known defects in the `pdd-agent prove` proof harness so its scorecard cannot lie; and add a `claude-code` drafting provider that shells out to the locally installed Claude Code CLI — giving the pipeline a frontier Anthropic model **today, with zero API key**, so the long-blocked real-model multi-family proof can finally run. Ends with a completed small-model Ollama dress rehearsal that shakes out nondeterministic-output bugs on free tokens before any real run.

## Context Snapshot
- **Current state:** 686 tests collected (679 run, 7 corpus-marked deselected), all passing locally and on GitHub Actions as of commit `577c634` — the *first* green CI in the project's history (CI was red from its creation on 2026-07-13 until 2026-07-16 due to an undeclared `python-multipart` dependency, and nobody noticed: no badge, no branch protection, no notification habit). The lockfile `uv.lock` was stale until 2026-07-16 and is never exercised by CI. All three real providers (`openai`, `anthropic`, `ollama`) still carry a hardcoded system prompt naming "waste-to-energy projects", contradicting the methodology-parametrized user prompt for non-WTE projects. `pdd-agent prove` treats Ollama as always-available (a machine without Ollama gets a scorecard row of 36 judged error-placeholder sections presented as a real run), its `Redraft count` column is always 0, judge token costs are excluded from `estimated_cost_usd`, it self-judges by default, and only `BudgetExhaustedError` is caught per provider (any other provider exception kills the whole scorecard). The CLI's `inegol` project alias wrongly points at the Soc Son config. No `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` exists in the environment; the machine has a working Claude Code CLI installation (`claude` on PATH) with an active subscription.
- **Desired state:** CI failures are surfaced by a README badge and branch protection; a second CI job enforces `uv.lock`; `pdd-agent doctor` diagnoses fresh-install gaps, PYTHONPATH pollution, and lockfile staleness; system prompts are family-aware with WTE byte-identical to today; `prove` probes real provider availability, reports failed sections explicitly, cross-judges, counts redrafts, includes judge cost, and survives any single provider's failure; a registered `claude-code` provider drafts via the local CLI (mocked in tests); a completed 36-section Ollama run on a small model is documented.
- **Key repo surfaces:** `.github/workflows/ci.yml`, `README.md`, `uv.lock`, `pyproject.toml`, `src/pdd_agent/doctor.py`, `src/pdd_agent/agent/section_orchestrator.py`, `src/pdd_agent/llm/{provider,env_config,openai_provider,anthropic_provider,ollama_provider,budget}.py`, `src/pdd_agent/review/judge.py`, `src/pdd_agent/phase05/provider_scorecard.py`, `src/pdd_agent/cli.py`, `configs/model_pricing.yaml`, `tests/{test_doctor,test_provider_scorecard,test_methodology_matrix,test_prompt_assembly}.py`.
- **Out of scope:** Running the frontier proof itself and getting domain-expert sign-off (a run, not a code change — it follows this plan); the Verra registry live-download upgrade (needs a browser network capture, separate effort); the Monitoring-Report product; any change to review/consistency/export logic; per-family `ProjectInput` schema split (deferred decision DEC-004 from prior plans, unchanged); paid API keys.

## Environment & Conventions
- **Stack:** Python 3.11+ (`requires-python = ">=3.11"`), packaged with `hatchling` (wheel targets `src/pdd_agent` and `schemas`). Pydantic v2 for `schemas/project_input.py`; dataclasses everywhere else. `structlog` event-style logging (`logger.warning("event_name", key=value)`). `argparse` CLI (console script `pdd-agent = pdd_agent.cli:main`). FastAPI + Jinja2 optional service. Dependency management: `uv` with a committed `uv.lock` (a `pip install -e` path is also documented and used by the existing CI job — both must keep working).
- **Setup:** `uv sync --all-extras` (uv path) or `pip install -e ".[dev,service,export,llm]"` (pip path).
- **Build / Run:** No build step. CLI: `pdd-agent <command>` (or `uv run --no-sync pdd-agent <command>`). Service: `uvicorn pdd_agent.service.main:app --reload`.
- **Test:** Full suite: `python -m pytest -m "not corpus" -q` (expect `679 passed, 7 deselected` before this plan; more after). Single file: `python -m pytest tests/test_provider_scorecard.py -v`. Single test: `python -m pytest tests/test_doctor.py::test_check_model_pricing -v` (adjust node id). On the primary dev machine (Windows), a foreign `PYTHONPATH` may be injected by other tooling — always prefix: `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` (POSIX shell) or clear `$env:PYTHONPATH` in PowerShell.
- **Conventions & traps:** `ruff` with `line-length = 100`, `target-version = "py311"`; run `ruff check .` AND `ruff format .` before committing (CI enforces `ruff format --check .`). Tests must NEVER require API keys, network access, a running Ollama instance, or an installed `claude`/`gws` CLI — mock all HTTP and subprocess calls. `demo`/`noop` providers are the safe default; real providers are opt-in via env vars. Model pricing units are **USD per 1,000,000 tokens** in `configs/model_pricing.yaml`. `.env` in the invocation directory is auto-loaded (`python-dotenv`); never commit one. Optional external tools must degrade gracefully (WARN, never crash).
- **Repo map:**
  - `src/pdd_agent/agent/section_orchestrator.py` — per-section retrieval → prompt assembly → provider call → judge/redraft loop. Owns `family_slug_for()` (methodology → family slug) and `_load_overlay()` (family prompt overlay).
  - `src/pdd_agent/llm/provider.py` — `BaseProvider` ABC, `NoopProvider`, `DemoProvider`, `ModelConfig`, `ProviderRegistry` (`get_provider_registry()`), `configure_provider(config)`, `DraftRun`/`DraftSection` dataclasses.
  - `src/pdd_agent/llm/env_config.py` — `configure_provider_from_env(provider_name)`; env-var naming pattern `{PROVIDER}_MODEL`, `{PROVIDER}_BASE_URL`, etc.
  - `src/pdd_agent/llm/{openai,anthropic,ollama}_provider.py` — real providers; each hardcodes the WTE system prompt today; each has `set_budget()` and a retry loop.
  - `src/pdd_agent/llm/budget.py` — `TokenBudget` (`record()`, `check_budget()`, `total_tokens`, `estimated_cost_usd`), `BudgetExhaustedError`.
  - `src/pdd_agent/review/judge.py` — `LLMJudge(provider_name, rubric_path, pass_threshold, use_llm, model_name, methodology_ids)`; deterministic + `use_llm` scoring; gets its provider from `get_provider_registry().get(provider_name)`.
  - `src/pdd_agent/phase05/provider_scorecard.py` — `run_provider_scorecard()`, `_is_provider_available()`, `_run_one_provider()`, `_render_scorecard()`, `ProviderScorecardRow`, `_ALL_PROVIDERS`.
  - `src/pdd_agent/cli.py` — 18 argparse subcommands including `prove` (project aliases at the `_PROJECT_ALIASES` dict, currently near line 188).
  - `src/pdd_agent/doctor.py` — `run_doctor()` printing `[OK]/[WARN]/[FAIL]` lines; exit 1 only on FAIL.
  - `configs/model_pricing.yaml` — model → `{input, output}` USD-per-million map.
  - `.github/workflows/ci.yml` — one `test` job, matrix Python 3.11/3.12, pip install, ruff, pytest.

## Research Inputs
- From `research/2026-07-16-pdd-trust-layer-and-unblock-brainstorm.md`:
  - CI was red from birth (3/3 runs) on a missing `python-multipart` declaration and nobody noticed; the trust layer needs a badge, branch protection, a lockfile-enforcing CI leg, and doctor-level environment-integrity checks so recorded state and reproducible state cannot drift apart again.
  - The WTE hardcoding survives one layer below the July-13 parametrization push: all three real providers hardcode a "for waste-to-energy projects" **system prompt** (`openai_provider.py` ~line 67, `anthropic_provider.py` ~line 86, `ollama_provider.py` ~lines 35–40). The demo provider uses no system prompt, so the existing 43-test methodology matrix structurally cannot catch this. A real non-WTE draft would receive contradictory instructions.
  - `pdd-agent prove` defects, all confirmed by reading `provider_scorecard.py`: Ollama treated as unconditionally available while `OllamaProvider` converts failures into `[OLLAMA ERROR …]` placeholder *sections* (misleading scorecard rows); `redraft_count` always 0 because the orchestrator runs with `enable_judge=False`; judge tokens not counted in `estimated_cost_usd`; self-judging by default (judge provider = drafting provider) inflates every row; only `BudgetExhaustedError` caught per provider.
  - The API-key blocker has survived four consecutive pushes, while a subscription-backed frontier model sits on the dev machine: the Claude Code CLI supports headless one-shot use (`claude -p --output-format json`), returning JSON with the result text and token usage — a ~200-line provider mirroring `ollama_provider.py` makes the proof keyless. This was the brainstorm's single highest-leverage recommendation.
  - A small-model Ollama dress rehearsal (`llama3.2:3b`-class) on the CPU-only dev box is the cheap way to shake out nondeterministic-output bugs (marker parsing, redraft convergence, budget accounting) before any real-model run; `ModelConfig.model_name`/`base_url` and the `OLLAMA_MODEL` env var already support it.
  - Recorded-claims drift found: README says "544 tests"; the truthful convention is 686 collected / 679 run / 7 corpus-deselected. README also still calls `OllamaProvider` a stub and the LLM judge "a thin interface stub" — both fixed in prior pushes.

## Assumptions and Constraints
- **ASM-001:** The GitHub repository is `tah-allotrope/pdd-auto`, public, with `main` as the default branch and GitHub Actions enabled (verified via `gh repo view`). Branch protection on a public repo is available on the free plan.
- **ASM-002:** Branch protection must not break the current solo direct-push-to-main workflow — **BINDING DEFAULT:** apply protection with `enforce_admins: false` and required status checks `test (3.11)`, `test (3.12)`, `lock-reproducibility` in non-strict mode. The repo owner (an admin) can still push directly; the checks gate everyone else and surface red status prominently on the repo page.
- **ASM-003:** The exact Claude Code CLI flag set for one-shot headless drafting cannot be verified without the CLI present — **BINDING DEFAULT:** invoke `claude -p --output-format json --model {model}` with the full prompt written to stdin, and pass the system prompt via `--append-system-prompt "{text}"`. Before coding, run `claude --help` on the target machine and confirm both flags exist; if `--append-system-prompt` is absent, fall back to prepending the system-prompt text to the user prompt separated by two newlines (and record that in the provider's module docstring).
- **ASM-004:** The Claude Code CLI's JSON result shape — **BINDING DEFAULT:** a single JSON object with at least `result` (string, the completion text), `is_error` (bool), `usage.input_tokens` (int), `usage.output_tokens` (int), and `total_cost_usd` (float). Parse defensively: missing `usage` fields default to 0; missing `result` with `is_error: false` is treated as a provider error. Verify once against a live `echo "say hi" | claude -p --output-format json` before finalizing the parser, and adjust field names to what the installed CLI version actually emits.
- **ASM-005:** Import name for the `python-multipart` package differs across versions — **BINDING DEFAULT:** the doctor check tries `import python_multipart` first, then `import multipart`; either succeeding counts as installed.
- **ASM-006:** Cross-judge provider preference order — **BINDING DEFAULT:** `["anthropic", "openai", "claude-code", "ollama"]`, first available provider that is not the drafting provider; `PDD_JUDGE_PROVIDER` env var overrides; when none qualifies, fall back to the deterministic judge (`provider_name="demo"`, `use_llm=False`).
- **ASM-007:** `claude-code` provider availability requires no cost ceiling — **BINDING DEFAULT:** available iff `shutil.which("claude")` (or the `CLAUDE_CODE_CLI` override) resolves. Do NOT require `PDD_MAX_COST_USD`: usage is subscription-billed, and `configs/model_pricing.yaml` gets a `claude-code` entry of `{input: 0.0, output: 0.0}` with a comment that cost is subscription-covered. Token budgets still apply (`PDD_MAX_TOKENS`).
- **ASM-008:** Enabling the judge/redraft loop inside `prove` means judge calls happen both in-loop and in the post-hoc scoring pass, roughly doubling judge token use for keyed providers — **BINDING DEFAULT:** accept this; it is the honest cost of measuring redraft behavior. Note it in the scorecard footer.
- **ASM-009:** The Ollama dress-rehearsal model — **BINDING DEFAULT:** `llama3.2:3b` (small enough for a CPU-only Intel i5-8250U to finish 36 sections overnight). Any locally pulled model may be substituted via `OLLAMA_MODEL`.
- **CON-001:** Tests must not require API keys, network, a running Ollama instance, or an installed `claude`/`gws` CLI. All new tests mock `urllib.request.urlopen`, `subprocess.run`, and `shutil.which` as needed.
- **CON-002:** `ruff check .` and `ruff format --check .` must pass on all new/modified files (line length 100).
- **CON-003:** Backward compatibility is the acceptance bar for the system-prompt change: for a WTE project (and for any provider constructed without `set_system_prompt` being called), the system prompt string sent to the API must be byte-identical to today's hardcoded text.
- **DEC-001:** Methodology family resolution reuses the existing `family_slug_for(methodology_ids)` in `src/pdd_agent/agent/section_orchestrator.py` (first ID, uppercased; unknown/empty → `"wte"`). Do not introduce a second resolver.
- **DEC-002:** Failed-section text convention: a provider that cannot draft a section returns text starting with `[{PROVIDER_NAME_UPPERCASED} ERROR` (e.g. `[OLLAMA ERROR`, `[CLAUDE-CODE ERROR`). The scorecard counts these as failed sections. `OllamaProvider` already complies; the new provider must too.
- **DEC-003:** The new provider's registry name is `claude-code` (hyphenated, lowercase) everywhere: registry key, `ProviderScorecardRow.provider`, CLI `--providers` value, pricing key, env-var prefix `CLAUDE_CODE_`.

## Specification
System-prompt construction (PHASE-03), applied identically for every real provider:

1. Resolve `family = family_slug_for(project_input.technology.methodology_ids)` (existing function; `"wte"` when project or IDs are absent).
2. Map family → descriptor with this fixed table:
   - `wte` → `waste-to-energy projects`
   - `rice` → `rice cultivation (alternate wetting and drying) projects`
   - `biochar` → `biochar carbon-removal projects`
   - `cookstove` → `improved cookstove projects`
3. The system prompt is exactly:
   `You are a technical writing assistant specializing in Verra VCS carbon credit Project Design Documents for {descriptor}. Follow the prompt instructions exactly. Cite all sources using the required citation format. Never fabricate data.`
   For `wte` this string is byte-identical to the constant currently hardcoded in all three providers (verify by diffing against `src/pdd_agent/llm/ollama_provider.py` `_SYSTEM_PROMPT` before editing).
4. The orchestrator pushes this string into the provider via an optional `set_system_prompt` hook (same `hasattr` pattern as the existing `set_budget`/`set_project_input` hooks). Providers keep the current WTE text as their internal default so direct construction without the hook behaves exactly as today.

Judge-provider selection for `prove` (PHASE-04), evaluated once per drafting-provider row:

1. If `PDD_JUDGE_PROVIDER` is set, use it (with `use_llm = name not in ("demo", "noop")`).
2. Else iterate `["anthropic", "openai", "claude-code", "ollama"]` in order; pick the first name that (a) is not the drafting provider and (b) passes `_is_provider_available`. Use `use_llm=True`.
3. Else fall back to `("demo", use_llm=False)` — the deterministic rule-based judge.
4. Record the chosen judge name per row and render it in a `Judge` column.

## Phase Summary
| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | CI trust layer: badge, branch protection, lockfile-enforcing CI job, doc truth-sync | None | Updated `.github/workflows/ci.yml`, `README.md`; branch protection applied |
| PHASE-02 | Doctor environment-integrity checks | None | New checks in `src/pdd_agent/doctor.py` + tests |
| PHASE-03 | Family-aware provider system prompts | None | `set_system_prompt` hook in 3 providers + orchestrator wiring + tests |
| PHASE-04 | Honest proof harness (`prove` hardening) | PHASE-03 | Availability probes, failed-section counting, cross-judging, redraft count, judge cost, per-row error isolation, alias fix |
| PHASE-05 | `claude-code` keyless frontier provider | PHASE-03, PHASE-04 | `src/pdd_agent/llm/claude_code_provider.py` + registration + doctor check + tests |
| PHASE-06 | Small-model Ollama dress rehearsal (operational) | PHASE-04 | `docs/ollama-dress-rehearsal.md` runbook + completed-run findings doc |

## Detailed Phases

### PHASE-01 - CI Trust Layer
**Goal**
Make a red CI impossible to miss and a stale lockfile impossible to commit unnoticed, and bring the README's recorded claims back in line with reality. No product-code behavior change.

**Tasks**
- [ ] TASK-01-01: Add the CI status badge as the first line under the H1 in `README.md`.
- [ ] TASK-01-02: Add a `lock-reproducibility` job to `.github/workflows/ci.yml` that enforces `uv.lock` and runs the suite from a locked sync.
- [ ] TASK-01-03: Apply branch protection to `main` requiring the three CI checks (non-strict, admins exempt).
- [ ] TASK-01-04: Truth-sync `README.md`: test count, stale "Ollama provider is a stub" and "LLM-judge is a thin stub" claims in Known Gaps, and the missing `prove` command in the CLI table.

**File Changes**
- `.github/workflows/ci.yml` (modify): Keep the existing `test` job unchanged. Append a second job:
  ```yaml
  lock-reproducibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.11"
      - name: Lockfile is current
        run: uv lock --check
      - name: Locked install
        run: uv sync --locked --all-extras
      - name: Test suite (non-corpus, locked env)
        run: uv run python -m pytest -m "not corpus" -q
  ```
- `README.md` (modify):
  - Insert after the H1 title line: `[![CI](https://github.com/tah-allotrope/pdd-auto/actions/workflows/ci.yml/badge.svg)](https://github.com/tah-allotrope/pdd-auto/actions/workflows/ci.yml)`
  - In the `**Status:**` paragraph, replace `544 tests pass` with `686 tests collected (679 run, 7 corpus-marked deselected), green under CI on Python 3.11/3.12`.
  - In `## Known Gaps`, delete the sentence fragment claiming `The OllamaProvider is currently a stub (registered but returns placeholder text, not a real local-model call)` and the clause claiming the LLM judge `use_llm=True` path `is a thin interface stub, not a tuned judge prompt` — replace the latter with `the use_llm=True judge prompt has not yet been calibrated against real model output`. Leave every other Known Gaps bullet unchanged.
  - In the `## CLI Commands` table, add a row: `| pdd-agent prove | Run a project through every available provider, judge each, write a head-to-head scorecard |`.
- No other files change. Branch protection is an API operation, not a file:
  ```bash
  gh api -X PUT repos/tah-allotrope/pdd-auto/branches/main/protection \
    -H "Accept: application/vnd.github+json" \
    --input - <<'JSON'
  {
    "required_status_checks": {
      "strict": false,
      "checks": [
        {"context": "test (3.11)"},
        {"context": "test (3.12)"},
        {"context": "lock-reproducibility"}
      ]
    },
    "enforce_admins": false,
    "required_pull_request_reviews": null,
    "restrictions": null
  }
  JSON
  ```

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
None — no testable behavior changes in this phase (CI config and docs only; verification is via the live CI run and API reads below).

**Dependencies**
- `gh` CLI authenticated as a repo admin (already used by the repo's workflow).

**Exit Criteria**
- [ ] `gh run list --limit 1` shows the push's CI run `completed success`, with BOTH jobs green (`gh run view <id> --json jobs --jq '[.jobs[].conclusion]'` → `["success","success","success"]` counting matrix legs).
- [ ] `gh api repos/tah-allotrope/pdd-auto/branches/main/protection --jq '.required_status_checks.checks[].context'` lists the three contexts.
- [ ] The badge renders on the repo's GitHub front page (view in browser).
- [ ] `grep -c "544 tests" README.md` → `0`.

**Phase Risks**
- **RISK-01-01:** `uv lock --check` fails on CI if `pyproject.toml` changed without re-locking in some earlier commit. Mitigation: run `uv lock --check` locally first; if stale, run `uv lock` and commit the refreshed lock in the same change.
- **RISK-01-02:** The job-name contexts for branch protection must match GitHub's rendered names exactly (`test (3.11)`, `test (3.12)`, `lock-reproducibility`). Verify with `gh api repos/tah-allotrope/pdd-auto/commits/$(git rev-parse HEAD)/check-runs --jq '.check_runs[].name'` after the first run, then apply protection.

### PHASE-02 - Doctor Environment-Integrity Checks
**Goal**
Teach `pdd-agent doctor` to diagnose the three environment failures that caused or masked the CI outage: missing fresh-install dependencies, PYTHONPATH pollution shadowing the venv, and a stale `uv.lock`. All new checks WARN (never FAIL) per the doctor's existing contract.

**Tasks**
- [ ] TASK-02-01: Add `check_test_deps()` verifying importability of the declared dev/service dependencies that a fresh install needs.
- [ ] TASK-02-02: Add `check_pythonpath()` warning when the `PYTHONPATH` env var is set.
- [ ] TASK-02-03: Add `check_uv_lock()` running `uv lock --check` when `uv` is on PATH and `uv.lock` exists.
- [ ] TASK-02-04: Wire all three into `run_doctor()` and extend `tests/test_doctor.py`.

**File Changes**
- `src/pdd_agent/doctor.py` (modify): Add the three check functions below, following the existing `(status, message)` tuple style, and append them in `run_doctor()` after `check_package_imports()`. Do not change any existing check.
- `tests/test_doctor.py` (modify): Add the test cases specified below, using `monkeypatch` for env vars and `unittest.mock.patch` for `subprocess.run`/`shutil.which`/`importlib.import_module`.

**Function Signatures**
- `check_test_deps() -> list[tuple[str, str]]` — one `("OK"|"WARN", message)` per name in `["pytest", "python_multipart", "uvicorn", "jinja2"]`; for `python_multipart`, `import python_multipart` falling back to `import multipart` (ASM-005); WARN message must include the exact install hint `uv sync --all-extras` or `pip install -e ".[dev,service,export,llm]"`.
- `check_pythonpath() -> tuple[str, str]` — `("OK", "PYTHONPATH not set")` when `os.environ.get("PYTHONPATH")` is falsy; otherwise `("WARN", "PYTHONPATH is set (<value>) — may shadow the project venv; run with PYTHONPATH cleared")`.
- `check_uv_lock(repo_root: Path | None = None) -> tuple[str, str]` — `("OK", "uv not on PATH; lock check skipped")` when `shutil.which("uv")` is None; `("OK", "uv.lock not present")` when the lockfile is missing; else run `["uv", "lock", "--check"]` with `cwd=repo_root or Path.cwd()`, `timeout=30`, `capture_output=True` — returncode 0 → `("OK", "uv.lock is current")`, non-zero → `("WARN", "uv.lock is stale relative to pyproject.toml — run 'uv lock' and commit")`; `subprocess.TimeoutExpired`/`OSError` → `("WARN", "uv lock --check failed to run: <error>")`.

**Test Specs**
- `check_pythonpath()` with `monkeypatch.delenv("PYTHONPATH", raising=False)` → `("OK", ...)`; with `monkeypatch.setenv("PYTHONPATH", "C:/foreign/site-packages")` → status `"WARN"` and message contains `C:/foreign/site-packages`.
- `check_test_deps()` with `importlib.import_module` patched to raise `ImportError` only for `"python_multipart"` and `"multipart"` → exactly one WARN row whose message contains `python_multipart`; all other rows OK.
- `check_uv_lock()` with `shutil.which` patched to return `None` → `("OK", "uv not on PATH; lock check skipped")`.
- `check_uv_lock()` with `shutil.which` → `"/usr/bin/uv"` and `subprocess.run` patched to return `returncode=2` → status `"WARN"`, message contains `stale`.
- `run_doctor()` exit code remains `0` when the only findings are WARN (patch all checks to WARN) — proving the never-FAIL contract holds.

**Dependencies**
- None.

**Exit Criteria**
- [ ] `python -m pytest tests/test_doctor.py -q` → all pass.
- [ ] `pdd-agent doctor` prints the three new lines and exits 0 on the dev machine.
- [ ] `python -m pytest -m "not corpus" -q` → no regressions.

**Phase Risks**
- **RISK-02-01:** `uv lock --check` invoked from a test could hit the real filesystem/network. Mitigation: every test patches `subprocess.run`; no test invokes real `uv`.

### PHASE-03 - Family-Aware Provider System Prompts
**Goal**
Remove the last known WTE-shaped landmine on the real-model path: the hardcoded "for waste-to-energy projects" system prompt in `openai_provider.py`, `anthropic_provider.py`, and `ollama_provider.py`. The orchestrator becomes the single owner of system-prompt text, pushed into providers via an optional hook; WTE output stays byte-identical (CON-003).

**Tasks**
- [ ] TASK-03-01: Add `_FAMILY_SYSTEM_DESCRIPTOR` and `system_prompt_for(methodology_ids)` to `src/pdd_agent/agent/section_orchestrator.py`, implementing the Specification exactly.
- [ ] TASK-03-02: Call the new `set_system_prompt` hook from `SectionOrchestrator.__init__` alongside the existing `set_budget`/`set_project_input` hooks.
- [ ] TASK-03-03: Add `set_system_prompt()` to the three real providers; replace each hardcoded constant usage with the stored value, keeping the current WTE text as the internal default.
- [ ] TASK-03-04: Extend the methodology test matrix so a non-WTE system prompt containing "waste-to-energy" fails CI.

**File Changes**
- `src/pdd_agent/agent/section_orchestrator.py` (modify): Below the existing `family_slug_for()`, add module-level
  ```python
  _FAMILY_SYSTEM_DESCRIPTOR = {
      "wte": "waste-to-energy projects",
      "rice": "rice cultivation (alternate wetting and drying) projects",
      "biochar": "biochar carbon-removal projects",
      "cookstove": "improved cookstove projects",
  }
  ```
  and `system_prompt_for()` per the Specification. In `SectionOrchestrator.__init__`, immediately after the `set_project_input` hook block, add:
  ```python
  if hasattr(self._provider, "set_system_prompt"):
      self._provider.set_system_prompt(
          system_prompt_for(self._project.technology.methodology_ids if self._project else None)
      )
  ```
  Leave `_build_prompt`, `_load_overlay`, and all drafting logic unchanged.
- `src/pdd_agent/llm/ollama_provider.py` (modify): Rename the module constant `_SYSTEM_PROMPT` to `_DEFAULT_SYSTEM_PROMPT` (text unchanged). In `__init__`, add `self._system_prompt = _DEFAULT_SYSTEM_PROMPT`. Add `set_system_prompt()`. In `_call_api`, use `self._system_prompt` in the messages payload instead of the constant. Nothing else changes.
- `src/pdd_agent/llm/anthropic_provider.py` (modify): Move the inline `system_message = (...)` literal in `_call_api` to a module constant `_DEFAULT_SYSTEM_PROMPT` (byte-identical text), add `self._system_prompt = _DEFAULT_SYSTEM_PROMPT` in `__init__` and `set_system_prompt()`, and pass `system=self._system_prompt` in the API call.
- `src/pdd_agent/llm/openai_provider.py` (modify): Same treatment — extract the hardcoded system-role content (~line 67) into `_DEFAULT_SYSTEM_PROMPT`, store on the instance, add the setter, use the instance value in the messages payload.
- `tests/test_prompt_assembly.py` (modify): Add unit tests for `system_prompt_for` (specs below).
- `tests/test_methodology_matrix.py` (modify): Add a parametrized assertion over the four families that `system_prompt_for(<family's methodology_ids>)` contains the family descriptor and, for non-WTE families, does NOT contain `waste-to-energy`.

**Function Signatures**
- `system_prompt_for(methodology_ids: Sequence[str] | None) -> str` — module-level function in `section_orchestrator.py`; returns the full system-prompt string per the Specification (WTE default when IDs are None/empty/unknown).
- `OllamaProvider.set_system_prompt(self, text: str) -> None` — stores `text` for use as the system message on every subsequent `_call_api`. (Identical signature on `AnthropicProvider` and `OpenAIProvider`.)

**Test Specs**
- `system_prompt_for(["ACM0022"])` → string equal to the previous hardcoded constant (assert equality against the literal text, byte-for-byte — this is the CON-003 golden check).
- `system_prompt_for(["VM0051"])` → contains `rice cultivation (alternate wetting and drying) projects`; does not contain `waste-to-energy`.
- `system_prompt_for(["VM0044"])` → contains `biochar carbon-removal projects`; `system_prompt_for(["AMS-II.G"])` → contains `improved cookstove projects`.
- `system_prompt_for(None)` and `system_prompt_for([])` and `system_prompt_for(["UNKNOWN"])` → the WTE string (backward compatible).
- Provider-level: construct `OllamaProvider(ModelConfig(provider_name="ollama", model_name="m"))`, patch `urllib.request.urlopen` to capture the request body, call `draft_section("1","1.1","p",[])`, decode the body JSON → `messages[0]["content"]` equals the WTE default. Then call `set_system_prompt("CUSTOM")` and draft again → `messages[0]["content"] == "CUSTOM"`.
- Orchestrator wiring: build `SectionOrchestrator` with a stub provider exposing `set_system_prompt` (record calls) and a rice `ProjectInput` (reuse `tests/fixtures/methodology_projects.py::make_project_input("rice")`) → the stub received exactly one call whose argument contains `rice cultivation`.

**Dependencies**
- None (self-contained; PHASE-04/05 consume the hook).

**Exit Criteria**
- [ ] `python -m pytest tests/test_prompt_assembly.py tests/test_methodology_matrix.py -q` → all pass, including the new parametrized system-prompt cases.
- [ ] `grep -rn "waste-to-energy" src/pdd_agent/llm/*.py` shows the string only inside `_DEFAULT_SYSTEM_PROMPT` constants (fallback defaults), not in any API-call construction.
- [ ] `python -m pytest -m "not corpus" -q` → green.

**Phase Risks**
- **RISK-03-01:** A byte difference sneaks into the WTE string during extraction (whitespace, wrapping). Mitigation: the golden equality test above compares against the literal; write it FIRST against the current constant, then refactor.

### PHASE-04 - Honest Proof Harness
**Goal**
Fix every known way `pdd-agent prove` can emit a misleading scorecard: phantom Ollama availability, error-placeholder sections counted as drafted, a dead redraft column, judge cost excluded from totals, self-judging, one provider's crash killing the whole run, and the wrong `inegol` alias.

**Tasks**
- [ ] TASK-04-01: Real availability probes in `_is_provider_available` (Ollama HTTP probe; cost-ceiling requirement for keyed providers).
- [ ] TASK-04-02: Per-row error isolation and failed-section counting in `_run_one_provider`.
- [ ] TASK-04-03: Cross-judge selection (`_select_judge_provider`) and judge budget threading (`LLMJudge` gains `token_budget`).
- [ ] TASK-04-04: Real redraft counting via an orchestrator counter; enable the judge/redraft loop in `prove` for real providers.
- [ ] TASK-04-05: Render `Sections failed` and `Judge` columns; fix the `inegol` alias in `cli.py`.

**File Changes**
- `src/pdd_agent/phase05/provider_scorecard.py` (modify):
  - `_is_provider_available`: for `"ollama"`, issue `urllib.request.urlopen` GET to `{os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")}/api/tags` with `timeout=2` (mirror `doctor.check_ollama`); any exception → `(False, "ollama_unreachable")`. For `"openai"`/`"anthropic"`: keep the key check, and additionally return `(False, "missing_cost_ceiling")` when `os.environ.get("PDD_MAX_COST_USD")` does not parse to a positive float (reuse `_parse_positive_float`). Keep `demo`/`noop` always available. (PHASE-05 adds the `claude-code` branch.)
  - `ProviderScorecardRow`: add fields `sections_failed: int = 0` and `judge_provider: str = ""`.
  - `_run_one_provider(provider_name, project_input, enable_judge, available_providers)`: construct the orchestrator with `enable_judge=(provider_name not in ("demo", "noop"))` so the redraft loop actually runs for real providers; after `run()`, set `row.redraft_count = orchestrator.redraft_count` and `row.sections_failed = sum(1 for s in run.sections if s.text.startswith(f"[{provider_name.upper()} ERROR"))`. Wrap the whole body after availability in `try/except BudgetExhaustedError` (existing) plus a final `except Exception as exc:` → `row.skipped_reason = f"provider_error: {exc}"`, `logger.error("scorecard_provider_error", provider=provider_name, error=str(exc))`, return the row (never re-raise). For judging: resolve `(judge_name, judge_use_llm) = _select_judge_provider(provider_name, available_providers)`, call `configure_provider_from_env(judge_name)`, build `LLMJudge(provider_name=judge_name, use_llm=judge_use_llm, methodology_ids=..., token_budget=budget)`, set `row.judge_provider = judge_name`.
  - `_select_judge_provider`: new module function per the Specification.
  - `run_provider_scorecard`: compute `available = [p for p in resolved if _is_provider_available(p)[0]]` once and pass into `_run_one_provider`.
  - `_render_scorecard`: extend the table header/rows with `Sections failed` (after `Sections drafted`) and `Judge` (after `Mean judge score`); add a footer note when any ran row used `enable_judge=True`: `Judge tokens are included in Total tokens / Est. cost; in-loop redraft judging roughly doubles judge calls for real providers.`
- `src/pdd_agent/review/judge.py` (modify): Add keyword-only parameter `token_budget: TokenBudget | None = None` to `LLMJudge.__init__` (import `TokenBudget` from `pdd_agent.llm.budget` under `TYPE_CHECKING` or directly); after resolving `self._provider`, add `if token_budget is not None and hasattr(self._provider, "set_budget"): self._provider.set_budget(token_budget)`. No scoring-logic changes.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): Add `self.redraft_count: int = 0` in `__init__`; increment `self.redraft_count += 1` in `_run_judge_redraft_loop` immediately before each `self._provider.draft_section(...)` redraft call. Nothing else changes.
- `src/pdd_agent/cli.py` (modify): In `_PROJECT_ALIASES`, change `"inegol": "configs/projects/demo_socson_like.yaml"` to `"inegol": "configs/demo/inegol_project_input.yaml"`. Leave `socson` and `rice` unchanged.
- `tests/test_provider_scorecard.py` (modify): Add the specs below.

**Function Signatures**
- `_is_provider_available(provider_name: str) -> tuple[bool, str | None]` — unchanged signature; now returns `(False, "ollama_unreachable")` / `(False, "missing_cost_ceiling")` per the rules above.
- `_select_judge_provider(drafting_provider: str, available_providers: list[str]) -> tuple[str, bool]` — returns `(judge_provider_name, use_llm)` per the Specification (env override → preference order → `("demo", False)`).
- `_run_one_provider(provider_name: str, project_input: ProjectInput, enable_judge: bool, available_providers: list[str]) -> ProviderScorecardRow` — one provider's full draft+judge row; never raises.
- `LLMJudge.__init__(self, provider_name: str = "demo", rubric_path: Path | None = None, pass_threshold: int | None = None, use_llm: bool = False, model_name: str | None = None, methodology_ids: list[str] | None = None, token_budget: TokenBudget | None = None) -> None` — `token_budget`, when given, is attached to the judge's provider so judge tokens are recorded in the same budget as drafting.

**Test Specs**
- Ollama probe: with `urllib.request.urlopen` patched to raise `URLError("refused")`, `_is_provider_available("ollama")` → `(False, "ollama_unreachable")`; patched to return a 200 response with body `{"models": []}` → `(True, None)`.
- Cost ceiling: `monkeypatch.setenv("OPENAI_API_KEY", "sk-test")` without `PDD_MAX_COST_USD` → `_is_provider_available("openai")` → `(False, "missing_cost_ceiling")`; with `PDD_MAX_COST_USD=5.0` → `(True, None)`.
- Judge selection: `_select_judge_provider("ollama", ["demo", "ollama"])` → `("demo", False)`; `_select_judge_provider("ollama", ["demo", "ollama", "anthropic"])` → `("anthropic", True)`; `_select_judge_provider("anthropic", ["anthropic", "openai"])` → `("openai", True)`; with `monkeypatch.setenv("PDD_JUDGE_PROVIDER", "demo")` any inputs → `("demo", False)`.
- Error isolation: run `run_provider_scorecard` over `["demo", "ollama"]` with `_is_provider_available` patched to `(True, None)` for both and the Ollama provider's `draft_section` patched to raise `RuntimeError("boom")` at orchestrator level (patch `SectionOrchestrator.run` selectively or patch `get_provider_registry` to return a provider whose `draft_section` raises) → scorecard file written; `demo` row has `sections_drafted == 36`; `ollama` row has `skipped_reason` containing `provider_error: boom`.
- Failed sections: build a `DraftRun` where 3 of 36 sections have text starting `[OLLAMA ERROR` → row `sections_failed == 3` (unit-test the counting expression via a stubbed run object).
- Rendered output: scorecard markdown contains header cells `Sections failed` and `Judge`; a `demo` row renders `judge_provider == "demo"`.
- Alias fix: invoking the CLI dispatcher with `prove --project inegol --providers demo --output <tmp>` (mock `run_provider_scorecard` and assert the `input_path` argument) → `configs/demo/inegol_project_input.yaml`.
- Redraft counter: construct `SectionOrchestrator` with `enable_judge=True`, `max_redraft_attempts=2`, a provider whose drafts always trigger a critical judge finding (use the deterministic judge with a draft missing required markers) → after drafting one HIGH-sensitivity section, `orchestrator.redraft_count >= 1`.

**Dependencies**
- PHASE-03 (the judge/redraft loop enabled here must not push WTE system prompts at non-WTE projects).

**Exit Criteria**
- [ ] `python -m pytest tests/test_provider_scorecard.py -q` → all pass.
- [ ] `pdd-agent prove --project rice --providers demo --output reports/prove-rice-demo.md` → exit 0; file contains `Sections failed` and `Judge` columns and an `ollama` absence is impossible to misread (not listed unless requested).
- [ ] On a machine with no Ollama running, `pdd-agent prove --project rice --providers auto --output reports/prove-auto.md` lists `ollama` under "Skipped providers" with reason `ollama_unreachable` (manual check).
- [ ] `python -m pytest -m "not corpus" -q` → green.

**Phase Risks**
- **RISK-04-01:** Enabling `enable_judge=True` for real providers changes drafting flow (redrafts mutate sections). This is intended, but demo/noop rows must stay byte-stable: keep `enable_judge=False` for `demo`/`noop` so existing demo artifacts and tests are unaffected.
- **RISK-04-02:** The shared `TokenBudget` can now exhaust *during judging*, raising `BudgetExhaustedError` outside the existing catch. Mitigation: the new blanket `except Exception` in `_run_one_provider` also catches it; the row records `provider_error: budget exhausted...` — acceptable and honest.

### PHASE-05 - `claude-code` Keyless Frontier Provider
**Goal**
Add a drafting provider that shells out to the locally installed Claude Code CLI in headless one-shot mode, giving the pipeline a frontier Anthropic model with zero API key. Fully mocked in tests; graceful degradation when the CLI is absent.

**Tasks**
- [ ] TASK-05-01: Verify the installed CLI's headless contract once (`claude --help`; `echo "say hi" | claude -p --output-format json`) and pin the flags per ASM-003/ASM-004.
- [ ] TASK-05-02: Implement `src/pdd_agent/llm/claude_code_provider.py`.
- [ ] TASK-05-03: Register the provider (`configure_provider`, `configure_provider_from_env`, scorecard `_ALL_PROVIDERS`, availability check) and add pricing.
- [ ] TASK-05-04: Add a `claude` CLI check to `doctor`.
- [ ] TASK-05-05: Write `tests/test_claude_code_provider.py` (all subprocess mocked).

**File Changes**
- `src/pdd_agent/llm/claude_code_provider.py` (create): Mirror `ollama_provider.py`'s structure (module docstring explaining the CLI contract and the verified flag set, `_MAX_RETRIES = 2`, error-section fallback, `_assess_confidence`/`_extract_issues` logic copied or imported). Core call:
  ```python
  subprocess.run(
      [self._cli, "-p", "--output-format", "json", "--model", self._model,
       "--append-system-prompt", self._system_prompt],
      input=prompt, capture_output=True, text=True, encoding="utf-8",
      timeout=self._timeout_seconds,
  )
  ```
  Parse stdout as JSON per ASM-004; `is_error: true`, non-zero returncode, `TimeoutExpired`, `JSONDecodeError`, or missing result text → retry up to `_MAX_RETRIES`, then return an error `DraftSection` whose text starts with `[CLAUDE-CODE ERROR — {section_id}...]` (DEC-002) with `confidence="UNSUPPORTED"` and an issue string `CLAUDE-CODE ERROR: {exc}`. On success: record `input_tokens`/`output_tokens` into the attached budget with `model=f"claude-code"` and `provider="claude-code"`; truncate text to `max_chars`; assess confidence by markers as the other providers do. Implement `set_budget`, `set_system_prompt` (default: the WTE `_DEFAULT_SYSTEM_PROMPT`, imported from or duplicated identically to PHASE-03's constants), and `close()` (no-op).
- `src/pdd_agent/llm/provider.py` (modify): In `configure_provider`, add an `elif config.provider_name == "claude-code":` branch importing and registering `ClaudeCodeProvider(config)`. No other changes.
- `src/pdd_agent/llm/env_config.py` (modify): In `configure_provider_from_env`, before the openai/anthropic block, add:
  ```python
  if provider_name == "claude-code":
      config = ModelConfig(
          provider_name="claude-code",
          model_name=os.environ.get("CLAUDE_CODE_MODEL", "sonnet"),
          max_tokens=int(os.environ.get("CLAUDE_CODE_MAX_TOKENS", "4000")),
          temperature=0.1,
      )
      configure_provider(config)
      return
  ```
  (The CLI does not take a temperature flag; the field is carried for interface uniformity and ignored.)
- `src/pdd_agent/phase05/provider_scorecard.py` (modify): `_ALL_PROVIDERS = ["demo", "ollama", "claude-code", "openai", "anthropic"]`. In `_is_provider_available`, add: `"claude-code"` → `(True, None)` iff `shutil.which(os.environ.get("CLAUDE_CODE_CLI", "claude"))` resolves, else `(False, "claude_cli_not_found")` (ASM-007 — no cost ceiling required).
- `configs/model_pricing.yaml` (modify): Add
  ```yaml
  # claude-code is billed via the operator's Claude subscription; per-token USD cost
  # is not applicable, so both rates are 0.0 (tokens are still budget-tracked).
  claude-code:
    input: 0.0
    output: 0.0
  ```
- `src/pdd_agent/doctor.py` (modify): Add `check_claude_cli() -> tuple[str, str]` — `shutil.which("claude")` absent → `("WARN", "claude CLI not found on PATH — claude-code provider unavailable")`; present → run `["claude", "--version"]` with `timeout=10`, `capture_output=True` → `("OK", f"claude CLI: {first_line}")`, failure → `("WARN", ...)`. Append to `run_doctor()` after `check_external_tools()`.
- `tests/test_claude_code_provider.py` (create): Specs below.
- `tests/test_provider_scorecard.py` (modify): Add availability cases for `claude-code`.

**Function Signatures**
- `ClaudeCodeProvider.__init__(self, config: ModelConfig) -> None` — reads `config.model_name` (default `"sonnet"`), `CLAUDE_CODE_CLI` env override for the binary name (default `"claude"`), `CLAUDE_CODE_TIMEOUT_SECONDS` env (default `300`).
- `ClaudeCodeProvider.draft_section(self, section_id: str, sub_section_id: str, prompt: str, provenance: list[str], max_chars: int = 4000) -> DraftSection` — one section's draft from a single headless CLI call; never raises (error sections per DEC-002).
- `ClaudeCodeProvider.set_system_prompt(self, text: str) -> None` — stores the system prompt passed via `--append-system-prompt`.
- `ClaudeCodeProvider.set_budget(self, budget: TokenBudget) -> None` — attaches the run budget; `check_budget()` is called before each CLI invocation and usage recorded after.
- `check_claude_cli() -> tuple[str, str]` — doctor check per File Changes.

**Test Specs**
All tests patch `subprocess.run` (and `shutil.which` where relevant); none touch the real CLI.
- Success: `subprocess.run` returns `returncode=0`, `stdout=json.dumps({"result": "Drafted text [USER INPUT: name]", "is_error": False, "usage": {"input_tokens": 120, "output_tokens": 340}, "total_cost_usd": 0.01})` → `draft_section("1", "1.1", "p", ["[USER INPUT: name]"])` returns a `DraftSection` with `provider == "claude-code"`, `text` starting `Drafted text`, and an attached `TokenBudget` shows `total_tokens == 460` after the call.
- CLI invocation shape: capture the `subprocess.run` call args → argv equals `["claude", "-p", "--output-format", "json", "--model", "sonnet", "--append-system-prompt", <system prompt>]` and `input` equals the prompt.
- `is_error` result: stdout `{"result": "", "is_error": true}` on both attempts → returned section text starts with `[CLAUDE-CODE ERROR` and `confidence == "UNSUPPORTED"`; `subprocess.run` called exactly `_MAX_RETRIES` times.
- Timeout: `subprocess.run` raises `subprocess.TimeoutExpired(cmd="claude", timeout=300)` → error section, no exception propagates.
- Malformed stdout (`"not json"`) → retried, then error section.
- Budget exhaustion: budget with `max_tokens=1` already recorded past limit → `draft_section` returns the error section citing budget (mirror `OllamaProvider`'s `BudgetExhaustedError` handling), and `subprocess.run` is NOT called after exhaustion.
- Availability: `shutil.which` → `None` ⇒ `_is_provider_available("claude-code") == (False, "claude_cli_not_found")`; `shutil.which` → path ⇒ `(True, None)`.
- Registry: `configure_provider(ModelConfig(provider_name="claude-code", model_name="sonnet"))` then `get_provider_registry().get("claude-code").name == "claude-code"`.

**Dependencies**
- PHASE-03 (`set_system_prompt` hook contract), PHASE-04 (`_ALL_PROVIDERS`, availability plumbing, failed-section convention).

**Exit Criteria**
- [ ] `python -m pytest tests/test_claude_code_provider.py -q` → all pass.
- [ ] `python -m pytest -m "not corpus" -q` → green.
- [ ] On the dev machine (CLI installed): `pdd-agent prove --project rice --providers claude-code --output reports/prove-rice-claude-code.md` → exit 0; scorecard row shows `sections_drafted == 36` and `sections_failed == 0` (manual, one live run — this is the first real-model multi-family draft in the project's history).
- [ ] `pdd-agent doctor` shows an `[OK] claude CLI: ...` line on the dev machine.

**Phase Risks**
- **RISK-05-01:** The installed CLI's JSON field names differ from ASM-004. Mitigation: TASK-05-01 verifies against the live CLI before the parser is written; the parser also tolerates missing fields defensively.
- **RISK-05-02:** Per-section CLI startup latency makes a 36-section run slow (minutes per section). Mitigation: acceptable for a proof; log per-section wall-clock via the existing structlog events so the scorecard's `Wall clock (s)` column captures it honestly.
- **RISK-05-03:** Subscription rate limits interrupt a long run. Mitigation: the retry-then-error-section path means the run completes with explicit `sections_failed > 0` rather than crashing; rerun later.

### PHASE-06 - Small-Model Ollama Dress Rehearsal (Operational)
**Goal**
Complete the first full 36-section local-model run (never achieved — prior attempts timed out on an 8B model on CPU) using a ~3B model, to shake out nondeterministic-output bugs on free tokens and produce a documented findings artifact. This phase is operational: one small runbook doc plus executed commands; code changes only if the run surfaces bugs (fix in place, with tests).

**Tasks**
- [ ] TASK-06-01: Write `docs/ollama-dress-rehearsal.md` (runbook: prerequisites, commands, expected durations, where results land).
- [ ] TASK-06-02: Execute the rehearsal on a machine with Ollama installed: pull the model, run `prove` for the Inegol (WTE) and rice projects through the `ollama` provider.
- [ ] TASK-06-03: Record findings in `docs/<YYYY-MM-DD>-ollama-dress-rehearsal-findings.md` (use the run date): sections drafted/failed, redraft counts, marker-parsing anomalies, wall-clock, and any bugs found (each bug gets a fix + regression test in the same change).

**File Changes**
- `docs/ollama-dress-rehearsal.md` (create): The runbook, containing exactly:
  ```bash
  # Prerequisites: Ollama installed (https://ollama.com/download), repo synced (uv sync --all-extras)
  ollama pull llama3.2:3b
  ollama serve   # if not already running as a service

  # WTE rehearsal (Inegol)
  OLLAMA_MODEL=llama3.2:3b pdd-agent prove --project inegol --providers ollama \
    --output reports/prove-inegol-ollama.md

  # Non-WTE rehearsal (rice VM0051)
  OLLAMA_MODEL=llama3.2:3b pdd-agent prove --project rice --providers ollama \
    --output reports/prove-rice-ollama.md
  ```
  (PowerShell variant: `$env:OLLAMA_MODEL = "llama3.2:3b"; pdd-agent prove ...`.) Plus: expected duration note (CPU-only i5-8250U: allow several hours per project; run overnight), and an instruction that `Sections failed` must be 0 for the rehearsal to count as complete.
- `docs/<YYYY-MM-DD>-ollama-dress-rehearsal-findings.md` (create at execution time): findings template — per-project table (sections drafted, sections failed, redraft count, judge pass rate, wall clock), bug list, and a go/no-go statement for proceeding to a real-model run.

**Function Signatures**
None — no code interfaces change in this phase (unless a surfaced bug requires a fix, which then carries its own signature and test in the fix commit).

**Test Specs**
None — no testable behavior changes in this phase. (Any bug found during the rehearsal must land with its own regression test.)

**Dependencies**
- PHASE-03 (correct system prompt for the rice run), PHASE-04 (honest availability, failed-section counting, redraft counting — the rehearsal's measurements depend on them).
- External: a machine with Ollama installed and ~2 GB free disk for the model. If unavailable, this phase blocks WITHOUT blocking PHASE-05's exit criteria (they are independent).

**Exit Criteria**
- [ ] `reports/prove-inegol-ollama.md` and `reports/prove-rice-ollama.md` exist, each with an `ollama` row showing `Sections drafted = 36` and `Sections failed = 0`.
- [ ] The findings doc exists and states go/no-go for a real-model run.
- [ ] Any bug found is fixed with a regression test and `python -m pytest -m "not corpus" -q` is green.

**Phase Risks**
- **RISK-06-01:** A 3B model may produce text that fails marker-hygiene judging constantly, exhausting redraft attempts on every section. Mitigation: that outcome is itself a valid finding (documents redraft-loop behavior under weak models); sections park for domain review rather than crash. Record pass rates honestly.
- **RISK-06-02:** Multi-hour run interrupted (sleep/reboot). Mitigation: run per-project (two shorter runs), disable machine sleep for the duration, and note that `prove` re-runs are idempotent (fresh run IDs).

## Gotchas
- **Pricing units are USD per 1,000,000 tokens** in `configs/model_pricing.yaml` (`input: 2.50` = $2.50/M). The `claude-code` entry is deliberately `0.0/0.0` (subscription-billed) — do not "fix" it to Anthropic API rates.
- **The failed-section prefix must match the provider's registry name uppercased, including the hyphen**: `claude-code` → `[CLAUDE-CODE ERROR`. The scorecard counting expression `text.startswith(f"[{provider_name.upper()} ERROR")` only works if provider and scorecard agree exactly.
- **`methodology_ids` is a list; resolve the family from the first element, uppercase-normalized.** `AMS-II.G` contains a dot and a hyphen — never strip them. Reuse `family_slug_for`; do not write a second resolver.
- **CON-003 is a byte-equality bar, not a semantic one.** Capture the current system-prompt literal in a test BEFORE refactoring the providers.
- **Tests must never hit the network, keys, Ollama, or the `claude` CLI.** The Ollama availability probe and every `subprocess.run` in the claude-code provider must be patched in tests. CI has none of these — an unmocked path fails CI, which is exactly what the suite is supposed to catch.
- **On the primary Windows dev machine, a foreign `PYTHONPATH` may be injected by other tooling** and shadow the repo venv (symptom: `No module named pytest` or a pydantic_core import error). Clear it: `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q`.
- **Run `ruff format .` before committing** — CI enforces `ruff format --check .` and will fail on an unformatted file even when tests pass.
- **Branch-protection check contexts must match rendered job names exactly** (`test (3.11)`, `test (3.12)`, `lock-reproducibility`) — a typo silently makes the protection meaningless because the check "never reports".
- **`uv run` without `--no-sync` may re-sync the environment** and remove ad-hoc-installed packages; either rely on declared dependencies only, or use `uv run --no-sync` after an explicit `uv sync --all-extras`.
- **Enabling `enable_judge=True` in `prove` applies only to real providers** (`not in ("demo", "noop")`); demo/noop rows must stay deterministic or existing demo artifacts and tests drift.

## Verification Strategy
- **TEST-001:** `ruff check . && ruff format --check .` → exit 0, no findings.
- **TEST-002:** `python -m pytest -m "not corpus" -q` → `0 failed`, ≥ 679 passed, `7 deselected` (count grows with new tests; zero failures is the bar).
- **TEST-003 (PHASE-02):** `python -m pytest tests/test_doctor.py -q` → all pass; `pdd-agent doctor; echo $?` → prints the new PYTHONPATH/lock/test-deps lines, exit `0`.
- **TEST-004 (PHASE-03):** `python -m pytest tests/test_prompt_assembly.py tests/test_methodology_matrix.py -q` → all pass; `grep -rn "waste-to-energy" src/pdd_agent/llm/openai_provider.py src/pdd_agent/llm/anthropic_provider.py src/pdd_agent/llm/ollama_provider.py | grep -v _DEFAULT_SYSTEM_PROMPT` → no output.
- **TEST-005 (PHASE-04):** `python -m pytest tests/test_provider_scorecard.py -q` → all pass; `pdd-agent prove --project rice --providers demo --output reports/prove-rice-demo.md && grep -q "Sections failed" reports/prove-rice-demo.md && grep -q "Judge" reports/prove-rice-demo.md` → exit 0.
- **TEST-006 (PHASE-05):** `python -m pytest tests/test_claude_code_provider.py -q` → all pass.
- **MANUAL-001 (PHASE-01):** Open `https://github.com/tah-allotrope/pdd-auto` — the CI badge renders green; `gh api repos/tah-allotrope/pdd-auto/branches/main/protection --jq '.required_status_checks.checks[].context'` prints the three contexts.
- **MANUAL-002 (PHASE-05, dev machine with `claude` installed):** `pdd-agent prove --project rice --providers claude-code --output reports/prove-rice-claude-code.md` → exit 0; open the scorecard: `Sections drafted = 36`, `Sections failed = 0`, `Judge` column populated.
- **MANUAL-003 (PHASE-06):** `reports/prove-inegol-ollama.md` and `reports/prove-rice-ollama.md` exist with `Sections failed = 0`; findings doc committed.
- **OBS-001:** After every push in this plan, `gh run list --limit 1` shows `completed success` — observed, not assumed. The final state of the Actions tab is the plan's own trust-layer thesis applied to itself.

## Risks and Alternatives
- **RISK-001:** The Claude Code CLI's headless flags/JSON change across versions, breaking the provider silently. Mitigation: the provider's module docstring pins the verified CLI version (`claude --version` output) and the doctor check surfaces the installed version; parse defensively per ASM-004.
- **RISK-002:** Cross-judging with `claude-code` judging `claude-code`-adjacent output could still share model-family bias. Accepted for now: the design goal is removing *self*-judging; judge identity is recorded per row so bias analysis is possible later.
- **RISK-003:** Branch protection with admin-exempt pushes (ASM-002) does not physically block a red push by the owner. Accepted: the goal is visibility (badge + required-check status on the repo page), not enforcement against the sole maintainer; tightening to `enforce_admins: true` is a one-command follow-up once the team grows.
- **ALT-001:** Use the Anthropic Python SDK with an API key instead of the CLI provider. Rejected for now: no key exists, procurement has blocked four consecutive pushes, and the CLI path requires zero new credentials. The SDK path already exists (`anthropic_provider.py`) and becomes preferable the day a key lands — the two coexist in the registry.
- **ALT-002:** Batch multiple sections per CLI call to amortize startup latency. Rejected: it changes the per-section provenance/budget accounting contract every other provider follows; optimize only if the dress-rehearsal wall-clock proves unacceptable.
- **ALT-003:** Make the system prompt part of the assembled user prompt instead of a provider hook. Rejected: Anthropic/OpenAI/Ollama all have first-class system-message channels that carry stronger instruction-following weight; the hook preserves that while keeping the orchestrator the single source of truth.

## Suggested Next Step
Execute PHASE-01. Its exit criteria (a green two-job CI run observed via `gh run list`, branch protection readable via `gh api`, badge rendering, `544 tests` gone from README) are verifiable within minutes and — per this plan's own thesis — every subsequent phase then works under a trust layer that actually reports.
