---
title: "PDD Reality Gap: Make the Existing Machine Real"
date: "2026-07-12"
status: "complete — all six phases shipped and closed by reports/2026-07-12-final-pdd-reality-gap.html (commit 274092c): real Ollama provider, de-monkeypatched service, JSON-parsing judge, registry downloader, rice VM0051 pilot."
request: "Turn research/2026-07-12-pdd-post-convergence-brainstorm.md into a multi-phase implementation plan closing the reality gap: repo hygiene, Ollama real-path shakeout, .env/doctor, service fixes (RAG thread-safety, provider opt-in, de-monkeypatch), real judge + provider scorecard on keys, registry corpus downloader, rice end-to-end"
plan_type: "multi-phase"
research_inputs:
  - "research/2026-07-12-pdd-post-convergence-brainstorm.md"
---

# Plan: PDD Reality Gap — Make the Existing Machine Real

## Objective

Close the gap between what `pdd-agent` claims and what has actually run: exercise the real-LLM drafting path end-to-end (locally via Ollama now, via OpenAI/Anthropic when API keys arrive), make the FastAPI review service use real retrieval and real providers instead of hard-forced demo output, and make the methodology breadth real by downloading registered PDDs and drafting one non-WTE (rice/VM0051) project end-to-end. Every demo artifact produced to date is deterministic `demo`/`noop` output; this plan converts the mature skeleton into a working product.

## Context Snapshot

- **Current state:** Python pipeline (`src/pdd_agent/`) with corpus RAG (SQLite FTS5), Pydantic `ProjectInput` schema, calc engines for ACM0022/AMS-II.G/VM0051/VM0044, judge+redraft loop, tiered DOCX export gate, and a FastAPI section-review service. 541 test functions (last full run: 534 passed, 7 corpus-marked deselected). But: `OllamaProvider` is a stub that returns placeholder text; the service forces the `demo` provider and monkeypatches corpus retrieval to return `[]`; the judge's LLM path (`use_llm=True`) discards findings and only regex-extracts a score; `ingest/registry_download.py` is a stub; the working tree has 551 uncommitted deletions under `ref/`; there is no `.env` loading anywhere.
- **Desired state:** (1) A real local-LLM Inegol draft run completes through draft → judge → redraft → export with no parser/pipeline crashes; (2) the service drafts with corpus retrieval enabled and can opt into real providers behind key + cost-ceiling gates, with no import-time monkeypatching; (3) a `pdd-agent doctor` command and `.env` support make environment setup diagnosable; (4) registered PDDs can be fetched from the public Verra registry per methodology; (5) a rice/VM0051 project drafts end-to-end through the service; (6) the git working tree is clean and the README is accurate.
- **Key repo surfaces:** `src/pdd_agent/llm/` (providers, budget), `src/pdd_agent/agent/section_orchestrator.py`, `src/pdd_agent/review/judge.py`, `src/pdd_agent/service/main.py` + templates, `src/pdd_agent/retrieval/index.py` + `search.py`, `src/pdd_agent/ingest/registry_download.py`, `src/pdd_agent/phase05/benchmark.py`, `src/pdd_agent/cli.py`, `configs/corpus_buckets/`, `rules/verra/judge_rubric.yaml`, `pyproject.toml`.
- **Out of scope:** Multi-tenant SaaS, auth, cloud deployment; monitoring-report generation; automating regulation-mandated human steps (validation, FPIC); Seraphin (externally blocked); new methodology families beyond the existing four; big-bang `cli.py` refactor.

## Environment & Conventions

- **Stack:** Python 3.11+ (Windows 11 dev machine; POSIX shells available via Git Bash), hatchling build backend, pip-installable editable package. `uv.lock` exists but README and scripts use pip — either works; commands below use pip for portability.
- **Setup:** `pip install -e ".[dev,service,export,llm]"` from the repo root. (`llm` extra = `openai`, `anthropic`; `service` extra = FastAPI/uvicorn/Jinja2.)
- **Build / Run:** No build step. CLI: `pdd-agent <subcommand>` (entry point `pdd_agent.cli:main`). Service: `uvicorn pdd_agent.service.main:app --reload`, then http://localhost:8000/dashboard.
- **Test:** `python -m pytest -m "not corpus" -q` (full suite minus corpus-dependent tests; expect 534+ passed, 7 deselected before this plan). Single file: `python -m pytest tests/test_service.py -v`. `pytest.ini_options` sets `addopts = "-v --tb=short"` and defines the `corpus` marker.
- **Conventions & traps:** Ruff, line length 100, `target-version = py311`. Logging via `structlog` (`logger = structlog.get_logger()`; event-style calls like `logger.warning("event_name", key=value)`). Dataclasses for internal state, Pydantic v2 for `ProjectInput` (lives at `schemas/project_input.py`, imported as `from schemas.project_input import ProjectInput` — `schemas/` is a top-level package, not under `src/`). Section keys are strings like `"1.10"`, `"4.4"`; emission units are tCO2e. Environment variables follow `PDD_*` (pipeline) and `{PROVIDER}_API_KEY` / `{PROVIDER}_MODEL` (providers). Optional external tools (`gws` CLI, LibreOffice) must degrade gracefully — never make them hard requirements.
- **Repo map:**
  - `src/pdd_agent/llm/` — `provider.py` (BaseProvider ABC, DraftSection, DraftRun, ModelConfig, registry, `configure_provider()`), `openai_provider.py`, `anthropic_provider.py`, `ollama_provider.py` (stub), `budget.py` (TokenBudget, `_DEFAULT_PRICING`).
  - `src/pdd_agent/agent/section_orchestrator.py` — drafting pipeline; judge/redraft loop at `_run_judge_redraft_loop`.
  - `src/pdd_agent/review/` — `judge.py` (LLMJudge), `checks.py`, `consistency.py`, `states.py` (ReviewStateStore).
  - `src/pdd_agent/service/` — `main.py` (FastAPI app), `templates/*.html`, `static/style.css`, `README.md`.
  - `src/pdd_agent/retrieval/` — `index.py` (RetrievalIndex, single SQLite conn), `search.py` (module-level singleton + `get_examples_for_section`).
  - `src/pdd_agent/ingest/` — Drive ingestion + `registry_download.py` stub.
  - `src/pdd_agent/cli.py` — argparse CLI (~17 subcommands), `_configure_api_provider()` at line ~29.
  - `configs/` — project inputs, corpus bucket configs, source mappings. `rules/verra/` — methodology + judge rubric YAML. `tests/` — pytest suite.

## Research Inputs

- From `research/2026-07-12-pdd-post-convergence-brainstorm.md`:
  - Central diagnosis: three compounding gaps — the proof gap (real LLM never run), the service reality gap (`service/main.py` forces demo provider and amputates RAG), the corpus reality gap (three families have calc engines but zero corpus documents and synthetic golden tests).
  - The Ollama path is the key-independent unblock: exercising the full real path with a local model converts the API-key blocker from hard to soft. (Verified during planning: `OllamaProvider.draft_section` is a stub returning placeholder text — it must be implemented first.)
  - `.env` files silently do nothing today: keys are read only from `os.environ` (`cli.py`), and no dotenv loader exists in `src/`.
  - Service monkeypatches at import time (`DraftRun.save`, `ReviewStateStore.save/load`, retrieval functions) are process-wide landmines; `save`/`load` already accept `output_dir`, so dependency injection is a small diff.
  - Repo hygiene: 551 uncommitted `ref/` deletions (data-loss risk), untracked `uv.lock` and the July-5 strategy brainstorm, stray `tmp_wte_model.xlsx` at root, README still says "204 tests".
  - Verra's registry (registry.verra.org) exposes the public JSON search API its own UI uses; a rate-limited client filtered by methodology unlocks real corpora for VM0051/VM0044/AMS-II.G.
- From `research/2026-07-05_pdd-next-level-brainstorm.md` (decisions carried forward as DEC entries below): dual-provider benchmarking, cheap-tier judge for iteration / frontier tier for sign-off, tiered export gate semantics, local-only deployment.

## Assumptions and Constraints

- **ASM-001:** No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` is available at execution time — **BINDING DEFAULT:** all phases except the key-gated tasks in PHASE-04 must complete and verify with `ollama`, `demo`, or `noop` providers only; key-gated tasks are implemented and unit-tested with mocks, and their live runs are recorded as manual verification steps to execute when keys arrive.
- **ASM-002:** Local Ollama availability/model — **BINDING DEFAULT:** assume Ollama is installable on the dev machine (https://ollama.com/download, Windows installer) and use model `llama3.1:8b` (`ollama pull llama3.1:8b`). If the machine cannot run it, substitute `qwen2.5:7b`; if Ollama cannot be installed at all, complete PHASE-02 with mocked-HTTP unit tests and record the live run as a manual verification step.
- **ASM-003:** Verra registry API shape — **BINDING DEFAULT:** implement the client against `POST https://registry.verra.org/uiapi/asset/asset/search` (JSON body with methodology filter, the endpoint the registry web UI calls), verified by inspecting the network traffic of https://registry.verra.org/app/search/VCS before coding. If the endpoint has changed or blocks non-browser clients, fall back to writing a documented manual-download manifest format (`manifest.json` schema in PHASE-05) and a loader that consumes manually downloaded PDFs — the downstream pipeline must not depend on live scraping succeeding.
- **ASM-004:** Disposition of `ref/` — **BINDING DEFAULT:** the 551 deletions of `ref/PDD staff test-20260520T145916Z-3-001/` are an intentional snapshot replacement. Commit the deletions, add `ref/` to `.gitignore` (keeping the untracked `ref/PDD staff April 2026/` and `ref/PDD staff May 2026/` folders on disk, out of git), and note in the commit message that reference snapshots now live in Google Drive.
- **ASM-005:** `tmp_wte_model.xlsx` at the repo root is a scratch duplicate of the cached workbook `data/source_inputs/spreadsheets/WtE plants carbon model early draft.xlsx` — **BINDING DEFAULT:** verify the cached copy exists, then delete the root file. If the cached copy is missing, move the root file into `data/source_inputs/spreadsheets/` instead.
- **ASM-006:** Dotenv mechanism — **BINDING DEFAULT:** add `python-dotenv>=1.0` to the base `dependencies` in `pyproject.toml` and call `load_dotenv()` (no-op when `.env` absent) at the top of `pdd_agent.cli.main()` and at import of `pdd_agent.service.main`. Never commit a `.env` file; add `.env` to `.gitignore`.
- **ASM-007:** Ollama HTTP client — **BINDING DEFAULT:** use stdlib `urllib.request` against `POST {base_url}/api/chat` with `"stream": false` (no new dependency; the service must keep running keyless and dependency-light). Do not add the `ollama` pip package.
- **ASM-008:** Judge model tiers — **BINDING DEFAULT:** judge provider/model come from `PDD_JUDGE_PROVIDER` (default: same provider as drafting) and `PDD_JUDGE_MODEL` (default: `claude-haiku-4-5-20251001` when judge provider is `anthropic`, `gpt-4o-mini` when `openai`, the drafting model otherwise). Frontier-tier sign-off runs override via these same env vars.
- **ASM-009:** Rice pilot input values — **BINDING DEFAULT:** build `configs/projects/rice_vm0051_pilot.yaml` as a synthetic-but-realistic Vietnam AWD (alternate wetting and drying) rice project: 5,000 ha in the Mekong Delta, two cropping seasons/year, baseline continuous flooding, VM0051 methodology ID, values consistent with the existing `calc/rice_vm0051.py` golden-test inputs (`tests/test_rice_vm0051.py`). Mark all quantitative fields with `demo_curated` provenance. Replace with real prospect data when one lands.
- **CON-001:** Demo/noop providers remain the default everywhere; real providers are opt-in via env vars only. Tests must never require API keys, network access, or a running Ollama instance (mock all HTTP).
- **CON-002:** Per-run cost ceiling: real-provider runs must run with `PDD_MAX_COST_USD` set; the service must refuse to start a real-provider run without it.
- **CON-003:** Optional tools (`gws`, LibreOffice) stay optional; `doctor` reports them but never fails on their absence.
- **DEC-001:** Dual-provider (OpenAI + Anthropic) head-to-head benchmarking picks the default drafting model; Ollama is a shakeout/dev tier, not a quality tier.
- **DEC-002:** Tiered export gate semantics are already implemented and unchanged: hard-block only calc contradictions, invalid `[E###]` citations, unresolved `[MISSING]` in Sections 3–4; everything else exports as watermarked DRAFT.
- **DEC-003:** Local-only deployment; outputs shared via Drive.
- **DEC-004:** Wide `ProjectInput` schema with optional family blocks is retained for the rice pilot; a per-family discriminated union is deferred until a second real non-WTE project exists.

## Specification

Service provider-selection logic (replaces the current force-to-demo in `src/pdd_agent/service/main.py`), applied by `_get_provider()` on every run creation:

1. Read `name = os.environ.get("PDD_SERVICE_PROVIDER", "demo").lower()`.
2. If `name` in `{"demo", "noop"}` → return that provider from the registry. Done.
3. If `name == "ollama"` → configure via `configure_provider_from_env("ollama")` and return it. No key or cost ceiling required (local inference is free).
4. If `name` in `{"openai", "anthropic"}`:
   a. If `os.environ.get(f"{name.upper()}_API_KEY")` is missing → log `service_provider_fallback` with `reason="missing_api_key"`, set the dashboard banner flag, return `demo`.
   b. If `os.environ.get("PDD_MAX_COST_USD")` is missing or not parseable as a positive float → log `service_provider_fallback` with `reason="missing_cost_ceiling"`, set the banner flag, return `demo`.
   c. Otherwise configure via `configure_provider_from_env(name)` and return it.
5. Any other value → log `service_provider_fallback` with `reason="unknown_provider"`, banner flag, return `demo`.

The dashboard banner flag is a module-level function `provider_status() -> dict` returning `{"requested": str, "effective": str, "reason": str | None}`; templates render a visible warning when `requested != effective`.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Repo hygiene + environment foundation (.env, doctor, git cleanup, docs) | None | Clean git tree, `pdd-agent doctor`, `.env` support, accurate README, project `CLAUDE.md` |
| PHASE-02 | Implement OllamaProvider and shake out the real-LLM path on Inegol | PHASE-01 (doctor/.env helpful, not blocking) | Working local-LLM Inegol draft→judge→export run; provider bugs fixed |
| PHASE-03 | Service reality fixes: RAG thread-safety, provider opt-in, de-monkeypatch, durable run status | PHASE-02 (provider selection reuses env config) | Service drafts with retrieval + optional real providers; no import-time patching |
| PHASE-04 | Real LLM judge (structured findings) + automated provider scorecard | PHASE-02, PHASE-03 | `pdd-agent scorecard`, tuned judge JSON path, key-gated live-run checklist |
| PHASE-05 | Verra registry downloader + corpus buckets for rice/biochar/cookstoves | PHASE-01 | `pdd-agent fetch-registry`, family bucket configs, downloaded corpora + index |
| PHASE-06 | Rice/VM0051 end-to-end through the service | PHASE-03, PHASE-05 | `rice_vm0051_pilot.yaml`, full draft→review→export run, findings doc |

## Detailed Phases

### PHASE-01 - Repo Hygiene and Environment Foundation

**Goal**
A clean git working tree, `.env` support so API keys can actually be loaded, a `pdd-agent doctor` diagnostic command, and documentation that matches reality.

**Tasks**
- [x] TASK-01-01: Verify `data/source_inputs/spreadsheets/WtE plants carbon model early draft.xlsx` exists, then delete `tmp_wte_model.xlsx` from the repo root (per ASM-005).
- [x] TASK-01-02: Stage and commit the 551 `ref/PDD staff test-20260520T145916Z-3-001/` deletions; add `ref/` and `.env` to `.gitignore`; leave `ref/PDD staff April 2026/` and `ref/PDD staff May 2026/` on disk untracked (per ASM-004). Commit message must state that reference snapshots live in Google Drive.
- [x] TASK-01-03: Commit the untracked keepers: `uv.lock`, `research/2026-07-05_pdd-next-level-brainstorm.md`, `research/2026-07-12-pdd-post-convergence-brainstorm.md`, `reports/assumption-burden.md`. Leave `reports/demo-packages/**` run folders untracked (generated artifacts).
- [x] TASK-01-04: Add `python-dotenv>=1.0` to `[project].dependencies` in `pyproject.toml`; call `load_dotenv()` at the top of `main()` in `src/pdd_agent/cli.py` and at module import in `src/pdd_agent/service/main.py` (per ASM-006).
- [x] TASK-01-05: Create `src/pdd_agent/doctor.py` with environment checks (see Function Signatures) and wire a `doctor` subcommand into `_build_parser()` / the dispatch table in `src/pdd_agent/cli.py`.
- [x] TASK-01-06: Create a project-root `CLAUDE.md` (~15 lines): stack, install command, test commands (`python -m pytest -m "not corpus" -q`), provider constraint (CON-001), artifact contracts (`reports/review-packages/` internal vs `reports/demo-packages/` client-demo), pointer to `activeContext.md` and the newest plan. Create a seed `lessons.md` with an empty "Rules" section.
- [x] TASK-01-07: Refresh `README.md`: current test count, service quickstart (`python scripts/setup_service.py` then `uvicorn pdd_agent.service.main:app`), Anthropic provider + judge + calc-breadth mentions, remove the stale "204 tests" and "no real LLM provider wired" phrasing (replace with "real providers implemented; live runs pending API keys"), add `doctor` to the CLI table.
- [x] TASK-01-08: Run the full test suite and commit.

**File Changes**
- `tmp_wte_model.xlsx` (delete): remove after ASM-005 verification.
- `.gitignore` (modify): append `ref/` and `.env` lines. Leave existing entries alone.
- `pyproject.toml` (modify): add `"python-dotenv>=1.0"` to `[project].dependencies`. Leave extras untouched.
- `src/pdd_agent/cli.py` (modify): add `from dotenv import load_dotenv` and call `load_dotenv()` as the first statement of `main()`; register the `doctor` subparser and dispatch to `pdd_agent.doctor.run_doctor`. Leave all other subcommands alone.
- `src/pdd_agent/service/main.py` (modify): add `load_dotenv()` immediately after imports. (All other service changes belong to PHASE-03 — do not touch monkeypatches here.)
- `src/pdd_agent/doctor.py` (create): diagnostic checks module.
- `CLAUDE.md` (create), `lessons.md` (create), `README.md` (modify) per tasks above.
- `tests/test_doctor.py` (create): unit tests for check functions.

**Function Signatures**
- `run_doctor() -> int` — runs all checks, prints one `[OK]`/`[WARN]`/`[FAIL]` line each to stdout, returns process exit code 0 if no `[FAIL]`, else 1.
- `check_python_version() -> tuple[str, str]` — returns `(status, message)` where status is `"OK"` if `sys.version_info >= (3, 11)` else `"FAIL"`.
- `check_package_imports() -> list[tuple[str, str]]` — one `(status, message)` per optional package (`openai`, `anthropic`, `fastapi`, `docx`, `dotenv`); `"WARN"` when missing (they are extras), never `"FAIL"`.
- `check_api_keys() -> list[tuple[str, str]]` — for `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`: `"OK"` with the key masked to first 8 chars + `…` when present, `"WARN"` when absent.
- `check_ollama(base_url: str = "http://localhost:11434") -> tuple[str, str]` — GET `{base_url}/api/tags` with a 2-second timeout; `"OK"` listing model names on success, `"WARN"` on connection failure.
- `check_external_tools() -> list[tuple[str, str]]` — `soffice --version` and `gws --version` via `subprocess.run` (`shutil.which` first); `"WARN"` when absent (CON-003).
- `check_retrieval_index(db_path: Path = Path("data/index/corpus.fts.db")) -> tuple[str, str]` — `"OK"` with document count when the SQLite file exists and has a `docs`-equivalent FTS table, `"WARN"` otherwise.
- `check_model_pricing() -> tuple[str, str]` — `"WARN"` if `OPENAI_MODEL`/`ANTHROPIC_MODEL` is set to a model absent from `pdd_agent.llm.budget._DEFAULT_PRICING`, else `"OK"`.

**Test Specs**
- `check_python_version()` on the running interpreter → `("OK", ...)`.
- `check_api_keys()` with `monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234567890")` → OpenAI entry is `("OK", ...)` and the message contains `"sk-test1"` but NOT the full key; with the var deleted → `("WARN", ...)`.
- `check_ollama(base_url="http://127.0.0.1:1")` (nothing listening) → `("WARN", ...)` and returns within ~2 s.
- `check_retrieval_index(db_path=tmp_path / "missing.db")` → `("WARN", ...)`.
- `run_doctor()` with all-warn environment → exit code 0 (warnings don't fail); force one FAIL by mocking `check_python_version` → exit code 1.
- CLI smoke: `pdd-agent doctor` exits 0 in the dev environment.
- `.env` loading: write `tmp .env` with `PDD_MAX_COST_USD=1.0`, run `load_dotenv` path, assert `os.environ` picks it up (use `monkeypatch.chdir`).

**Dependencies**
- None.

**Exit Criteria**
- [ ] `git status --short` shows an empty working tree (no `D`, no stray `??` except intentionally ignored paths).
- [ ] `pdd-agent doctor` runs and exits 0 on the dev machine.
- [ ] `python -m pytest -m "not corpus" -q` passes (≥ 534 passed plus new doctor tests).
- [ ] `README.md` contains a "Service Quickstart" section and no "204 tests" string: `grep -c "204 tests" README.md` → `0`.

**Phase Risks**
- **RISK-01-01:** Committing `ref/` deletions while the April/May folders are untracked could confuse a later `git clean -fd` into deleting them. Mitigation: `.gitignore` the whole `ref/` directory in the same commit and say so in the commit message.

### PHASE-02 - OllamaProvider Implementation and Real-Path Shakeout

**Goal**
Replace the `OllamaProvider` stub with a real HTTP client mirroring `OpenAIProvider`'s structure, then run the Inegol project end-to-end (draft → judge → redraft → review → DOCX export) on a local model to flush out every bug in prompt assembly, response parsing, marker handling, and budget accounting — without spending a dollar or needing a key.

**Tasks**
- [x] TASK-02-01: Rewrite `src/pdd_agent/llm/ollama_provider.py`: implement `_call_api()` using stdlib `urllib.request` POST to `{base_url}/api/chat` with body `{"model": ..., "messages": [system, user], "stream": false, "options": {"temperature": ..., "num_predict": max_tokens}}` (per ASM-007). Reuse the same system prompt text, retry loop (3 attempts, exponential backoff on connection errors), `[INFERENCE]`-marker issue detection, confidence assignment, and `DraftSection` construction as `openai_provider.py` (copy the structure; do not import from it). Token counts come from the response's `prompt_eval_count` / `eval_count` fields; pass them to `self._budget.record_call()` the same way the OpenAI provider does, with cost 0.0 (add an `"ollama-local"` pricing entry of `{"input": 0.0, "output": 0.0}` to `_DEFAULT_PRICING` in `src/pdd_agent/llm/budget.py`, keyed fallback when the model name is unknown and provider is ollama).
- [x] TASK-02-02: Extend `_configure_api_provider()` in `src/pdd_agent/cli.py` to accept `"ollama"`: no API key required; `ModelConfig(provider_name="ollama", model_name=os.environ.get("OLLAMA_MODEL", "llama3.1:8b"), base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"), ...)`. Rename the function to `configure_provider_from_env(provider_name: str) -> None` and move it to `src/pdd_agent/llm/env_config.py` so the service can import it in PHASE-03 without importing `cli`; keep a thin alias in `cli.py`.
- [x] TASK-02-03: Write `tests/test_ollama_provider.py` mocking `urllib.request.urlopen` (never a live call), covering the specs below.
- [x] TASK-02-04 (manual, dev machine): install Ollama, `ollama pull llama3.1:8b`, verify `pdd-agent doctor` shows Ollama `[OK]`.
- [x] TASK-02-05 (manual): run the Inegol draft on Ollama with judge enabled: `PDD_MAX_COST_USD=1 pdd-agent draft --input configs/demo/inegol_project_input.yaml --provider ollama` (check the actual `draft` flag names in `cli.py` before running; add `--enable-judge` pass-through to `SectionOrchestrator(enable_judge=True)` if the CLI does not already expose one — if missing, add the flag as part of this phase).
- [x] TASK-02-06 (manual): export the run (`pdd-agent export --run-id <run-id>`) and open the DOCX. Triage every crash/garbage output found in TASK-02-05/06 into fixes within this phase: typical expected failures are marker-regex misses on chatty model output, over-long sections blowing `max_chars`, and JSON-ish judge responses. Fix parser robustness in the provider (not by loosening the export gate).
- [x] TASK-02-07: Record results in `docs/2026-07-XX-ollama-shakeout.md` (actual date): sections drafted, judge pass rate, redraft count, wall time, bugs found+fixed. This document is the "real path executed" evidence.

**File Changes**
- `src/pdd_agent/llm/ollama_provider.py` (modify/rewrite): full implementation as above; keep class name `OllamaProvider` and `name = "ollama"`.
- `src/pdd_agent/llm/env_config.py` (create): `configure_provider_from_env()` moved from `cli.py`, extended for ollama.
- `src/pdd_agent/cli.py` (modify): alias `_configure_api_provider = configure_provider_from_env` (import), extend the provider choices on the `draft` subcommand to include `ollama`; add `--enable-judge` flag if absent. Leave other subcommands alone.
- `src/pdd_agent/llm/budget.py` (modify): add `"ollama-local": {"input": 0.0, "output": 0.0}` to `_DEFAULT_PRICING` and make unknown-model lookup fall back to zero-cost for provider `ollama` (currently unknown models should not crash budget accounting).
- `tests/test_ollama_provider.py` (create).
- `docs/2026-07-XX-ollama-shakeout.md` (create, manual task output).

**Function Signatures**
- `OllamaProvider.__init__(config: ModelConfig) -> None` — stores config; default `base_url` `http://localhost:11434`, default model `llama3.1:8b`.
- `OllamaProvider._call_api(prompt: str, max_tokens: int) -> LLMResponse` — POSTs to `/api/chat`, returns `LLMResponse(text, provider="ollama", model, tokens_used, cost_usd=0.0, raw={...})`; raises the same terminal error type the OpenAI provider raises after 3 failed attempts.
- `OllamaProvider.draft_section(section_id: str, sub_section_id: str, prompt: str, provenance: list[str], max_chars: int = 4000) -> DraftSection` — mirrors `OpenAIProvider.draft_section` semantics (marker scan, confidence, issues).
- `configure_provider_from_env(provider_name: str) -> None` — in `env_config.py`; for `openai`/`anthropic` requires `{NAME}_API_KEY` (silently no-op without it, matching current behavior); for `ollama` always configures.

**Test Specs**
- Mocked `urlopen` returning `{"message": {"content": "Section text here."}, "model": "llama3.1:8b", "prompt_eval_count": 120, "eval_count": 300}` → `draft_section(...)` returns `DraftSection` with `text == "Section text here."`, `provider == "ollama"`, no `REVIEW REQUIRED` issue, and budget records `tokens_used == 420` at cost `0.0`.
- Mocked response containing `"[INFERENCE] the plant likely..."` → `DraftSection.issues` contains an entry mentioning `[INFERENCE]` (same behavior as `openai_provider.py` line ~240).
- Mocked `urlopen` raising `URLError` on all attempts → terminal error raised after 3 attempts; with failures on attempts 1–2 and success on 3 → returns normally (assert `urlopen` called 3 times).
- `configure_provider_from_env("ollama")` with no env vars set → registry contains an `"ollama"` provider whose `_model == "llama3.1:8b"`.
- Budget: unknown model `"mystery"` on provider ollama → `record_call` does not raise and adds cost `0.0`.

**Dependencies**
- PHASE-01 recommended first (doctor validates the Ollama install) but not blocking.
- External: Ollama installed locally for the manual tasks (ASM-002 fallback applies).

**Exit Criteria**
- [ ] `python -m pytest tests/test_ollama_provider.py -v` → all pass, no network access (verify by running with Wi-Fi off or trusting the mocks).
- [ ] `python -m pytest -m "not corpus" -q` → green.
- [ ] Manual: an Inegol run with `--provider ollama` completes all 36 sections without an unhandled exception, and `pdd-agent export --run-id <run-id>` produces a DOCX (watermarked DRAFT is acceptable and expected).
- [ ] `docs/2026-07-XX-ollama-shakeout.md` exists with the run metrics and the fixed-bugs list.

**Phase Risks**
- **RISK-02-01:** An 8B model may emit output so noisy the export gate hard-blocks everything, making the shakeout look like failure. Mitigation: the goal is *pipeline* robustness, not prose quality — a completed run with a DRAFT watermark and many judge failures is a success; document quality separately.
- **RISK-02-02:** 36 sections × up to 3 redrafts on local CPU inference could take hours. Mitigation: support `PDD_MAX_REDRAFTS=0` env override (already parameterized as `max_redraft_attempts`) for the first pass; run the judge-enabled pass overnight if needed.

### PHASE-03 - Service Reality Fixes

**Goal**
The FastAPI service drafts with corpus retrieval enabled, can opt into real providers behind explicit key + cost-ceiling gates, persists via dependency injection instead of import-time monkeypatching, and survives restarts without lying about run status.

**Tasks**
- [x] TASK-03-01: Make `RetrievalIndex` thread-safe: replace the single `self._conn` in `src/pdd_agent/retrieval/index.py` with a `threading.local()` holding one connection per thread (keep the WAL + synchronous pragmas per connection). Add `close()` handling that closes the calling thread's connection only.
- [x] TASK-03-02: Delete the module-level retrieval monkeypatch in `src/pdd_agent/service/main.py` (lines ~39–45, the loop overriding `get_examples_for_section` / `get_section_heading_examples`) and the per-run re-disable inside `_execute_run` (line ~253). Corpus retrieval now runs in the service whenever the index DB exists (the existing `_warn_no_index_once` path already degrades gracefully when it doesn't).
- [x] TASK-03-03: Delete the `DraftRun.save` / `ReviewStateStore.save` / `ReviewStateStore.load` rebindings in `service/main.py` (lines ~50–88). Add a `runs_dir: Path | None = None` parameter to `SectionOrchestrator.__init__` in `src/pdd_agent/agent/section_orchestrator.py`, stored as `self._runs_dir` and passed to every internal `self._run.save(...)` / review-state `save(...)`/`load(...)` call. Service call sites pass `_service_runs_dir()` explicitly (orchestrator constructor + every direct `DraftRun.load`/`ReviewStateStore.load` in route handlers — grep `service/main.py` for `.load(` and `.save(` and thread the dir through each).
- [x] TASK-03-04: Implement the provider-selection logic from `## Specification` in `_get_provider()`, using `configure_provider_from_env` from PHASE-02. Add `provider_status() -> dict` and render a warning banner in `templates/base.html` (or `dashboard.html`) when `requested != effective`.
- [x] TASK-03-05: Durable run status: in `_execute_run`, write `data/runs/{run_id}.status.json` with `{"status": "running", "started_at": ISO-8601 UTC}` before drafting, and `{"status": "complete"|"failed", "finished_at": ..., "error": str | null}` in a `finally` block. Add a FastAPI startup hook that sweeps `*.status.json` and rewrites any `"running"` entry to `{"status": "failed", "error": "orphaned by service restart"}`. Run list/detail endpoints read this file to report status instead of inferring.
- [x] TASK-03-06: Update `src/pdd_agent/service/README.md`: provider opt-in matrix (env vars, key + `PDD_MAX_COST_USD` requirements), retrieval note, status semantics.
- [x] TASK-03-07: Extend `tests/test_service.py` for the new behavior; add `tests/test_retrieval_threading.py`.

**File Changes**
- `src/pdd_agent/retrieval/index.py` (modify): thread-local connection storage; public API (`build`, `search`, `get_section_examples`) unchanged.
- `src/pdd_agent/service/main.py` (modify): remove both monkeypatch blocks; new `_get_provider` logic; `provider_status()`; status-file writes + startup sweep; pass `runs_dir` explicitly everywhere. Leave route paths and template names unchanged.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): add `runs_dir` parameter as described; default `None` preserves current behavior for the CLI. Do not change judge/redraft logic.
- `src/pdd_agent/service/templates/base.html` or `dashboard.html` (modify): provider warning banner block.
- `src/pdd_agent/service/README.md` (modify): documentation updates.
- `tests/test_service.py` (modify), `tests/test_retrieval_threading.py` (create).

**Function Signatures**
- `SectionOrchestrator.__init__(..., runs_dir: Path | None = None) -> None` — existing params unchanged; `runs_dir` overrides the default `data/runs` persistence directory for `DraftRun`/review-state saves.
- `_get_provider(provider_name: str | None = None) -> BaseProvider` — implements the Specification logic; never raises for a bad name (falls back to demo).
- `provider_status() -> dict[str, str | None]` — `{"requested": ..., "effective": ..., "reason": ...}` reflecting the most recent `_get_provider` resolution.
- `RetrievalIndex._get_conn(self) -> sqlite3.Connection` — returns the calling thread's connection, creating it on first use.

**Test Specs**
- Threading: build a small index in `tmp_path`, run `index.search("waste incineration")` from 4 threads via `ThreadPoolExecutor` → no `sqlite3.ProgrammingError`, all results non-erroring and identical.
- Provider selection (monkeypatched env): `PDD_SERVICE_PROVIDER=anthropic` with no `ANTHROPIC_API_KEY` → `_get_provider().name == "demo"` and `provider_status()["reason"] == "missing_api_key"`. With `ANTHROPIC_API_KEY=x` but no `PDD_MAX_COST_USD` → demo, reason `missing_cost_ceiling`. `PDD_SERVICE_PROVIDER=ollama` → `name == "ollama"` (no key needed). Unset → demo, reason `None`.
- Persistence DI: with `PDD_SERVICE_RUNS_DIR` pointed at `tmp_path`, create a run through `POST /api/runs` (demo provider, TestClient) → `{run_id}.json`, `review-state-{run_id}.json`, and `{run_id}.status.json` all appear under `tmp_path`, and importing `pdd_agent.service.main` does NOT alter `DraftRun.save` (assert `DraftRun.save is` the original function object).
- Status lifecycle: after the background task finishes, `{run_id}.status.json` has `"status": "complete"`. Write a fake `{run_id}.status.json` with `"running"`, restart the app (new TestClient) → sweep rewrites it to `"failed"` with the orphaned-error message.
- Existing 12 service tests still pass unchanged in behavior (routes, templates).

**Dependencies**
- PHASE-02 (imports `configure_provider_from_env` from `env_config.py`).

**Exit Criteria**
- [ ] `grep -n "monkeypatch\|DraftRun.save = \|ReviewStateStore.save = \|get_examples_for_section = lambda" src/pdd_agent/service/main.py` → no matches.
- [ ] `python -m pytest tests/test_service.py tests/test_retrieval_threading.py -v` → all pass.
- [ ] `python -m pytest -m "not corpus" -q` → green.
- [ ] Manual: start the service with the corpus index present, create a demo run, and confirm section provenance includes corpus retrieval examples (previously always empty in the service).

**Phase Risks**
- **RISK-03-01:** Other tests may import `pdd_agent.service.main` and currently rely on the monkeypatched persistence redirection. Mitigation: run the full suite after TASK-03-03 and fix call sites to pass `output_dir`/`runs_dir` explicitly rather than restoring patches.
- **RISK-03-02:** SQLite WAL allows concurrent readers, but the service also *writes* (index build) in rare paths. Mitigation: the service never builds the index; document that `build-index` is CLI-only.

### PHASE-04 - Real LLM Judge and Provider Scorecard

**Goal**
The judge's LLM path returns structured findings (not just a regex-scraped score), judge model tiers are configurable, and one command produces a head-to-head provider scorecard. Live frontier-model runs are implemented and checklisted, executing whenever keys arrive.

**Tasks**
- [x] TASK-04-01: Harden `LLMJudge._llm_judge_section` in `src/pdd_agent/review/judge.py`: parse the full JSON object from the response (extract the first `{...}` block, `json.loads`, tolerate markdown fences), populating `categories["critical"]`, `categories["advisory"]`, and `findings` from the parsed payload. Keep the existing deterministic fallback on parse failure. Keep `_extract_score` as the last-resort score parser.
- [x] TASK-04-02: Judge tier config (per ASM-008): `LLMJudge.__init__` gains `model_name: str | None = None`; resolution order: explicit arg → `PDD_JUDGE_MODEL` env → tier default by provider. `SectionOrchestrator._run_judge_redraft_loop` reads `PDD_JUDGE_PROVIDER` (default: drafting provider name) instead of hardcoding the drafting provider, and sets `use_llm=True` automatically when the resolved judge provider is not `demo`/`noop`.
- [x] TASK-04-03: Create `src/pdd_agent/phase05/provider_scorecard.py`: run the same `ProjectInput` through N providers sequentially, judge every section, and write a markdown scorecard table (per provider: sections drafted, judge pass rate %, mean judge score, redraft count, total tokens, estimated cost USD from `TokenBudget`, wall-clock seconds).
- [x] TASK-04-04: Wire a `scorecard` subcommand into `src/pdd_agent/cli.py`: `pdd-agent scorecard --input configs/demo/inegol_project_input.yaml --providers ollama,openai,anthropic --output reports/provider-scorecard.md`. Providers whose keys are missing are skipped with a logged warning, not a crash.
- [x] TASK-04-05: Tests with mocked providers (`tests/test_provider_scorecard.py`; extend `tests/test_judge.py`).
- [x] TASK-04-06 (key-gated, manual): when `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` exist — run `PDD_MAX_COST_USD=20 pdd-agent scorecard --input configs/demo/inegol_project_input.yaml --providers ollama,openai,anthropic`; review `reports/provider-scorecard.md`; pick the default drafting model; export the winning run and hand the DOCX to the domain expert for VVB-grade review (DEC-001). Record the outcome in `docs/` with the date.

**File Changes**
- `src/pdd_agent/review/judge.py` (modify): JSON findings parsing (`_parse_judge_json`), `model_name` param, tier resolution. Deterministic scorer untouched.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): judge provider/tier resolution in `_run_judge_redraft_loop` only.
- `src/pdd_agent/phase05/provider_scorecard.py` (create).
- `src/pdd_agent/cli.py` (modify): `scorecard` subcommand.
- `tests/test_provider_scorecard.py` (create), `tests/test_judge.py` (modify).

**Function Signatures**
- `LLMJudge.__init__(provider_name: str = "demo", rubric_path: Path | None = None, pass_threshold: int | None = None, use_llm: bool = False, model_name: str | None = None) -> None` — existing semantics plus judge-model override.
- `_parse_judge_json(text: str) -> dict[str, Any] | None` — module-level helper; returns the parsed judge payload (`score`, `passed`, `critical`, `advisory`) or `None` when no valid JSON object is found.
- `run_provider_scorecard(input_path: Path, providers: list[str], output_path: Path, enable_judge: bool = True) -> Path` — executes runs, writes the markdown scorecard, returns `output_path`.

**Test Specs**
- `_parse_judge_json('Here you go:\n```json\n{"score": 82, "passed": true, "critical": [], "advisory": ["cite E002"]}\n```')` → dict with `score == 82`, `advisory == ["cite E002"]`.
- `_parse_judge_json("no json here, score: 75")` → `None` (and `_llm_judge_section` then falls back: with a mocked provider returning that text, result equals the deterministic judge's result for the same section).
- Judge tier: `monkeypatch.setenv("PDD_JUDGE_MODEL", "claude-haiku-4-5-20251001")` → `LLMJudge(provider_name="anthropic").model_name == "claude-haiku-4-5-20251001"` (mock the registry so no real provider is constructed).
- Scorecard with providers `["demo", "noop"]` on the Inegol input → `reports/provider-scorecard.md` (in `tmp_path`) contains one table row per provider with all seven columns populated; requesting provider `"openai"` with no key → row absent, warning logged, exit without exception.
- Full suite stays green: `python -m pytest -m "not corpus" -q`.

**Dependencies**
- PHASE-02 (ollama as a scorecard row), PHASE-03 (env_config reuse). Key-gated TASK-04-06 additionally depends on external API keys (ASM-001).

**Exit Criteria**
- [ ] `pdd-agent scorecard --input configs/demo/inegol_project_input.yaml --providers demo --output reports/provider-scorecard.md` completes and the file renders a valid markdown table.
- [ ] `python -m pytest tests/test_judge.py tests/test_provider_scorecard.py -v` → all pass.
- [ ] Key-gated checklist (TASK-04-06) is written into `docs/` even if not yet executed, so the live run is a copy-paste exercise when keys land.

**Phase Risks**
- **RISK-04-01:** Judge-on-judge cost blowup: 36 sections × 3 providers × redrafts. Mitigation: `PDD_MAX_COST_USD` is mandatory for real-provider scorecard rows; scorecard aborts a provider's run cleanly on `BudgetExhaustedError` and records the partial row as such.

### PHASE-05 - Registry Corpus Downloader and Family Buckets

**Goal**
`ingest/registry_download.py` actually downloads registered PDD PDFs from the public Verra registry per methodology, and the three new families get corpus bucket configs so `build-index` can serve family-scoped retrieval.

**Tasks**
- [x] TASK-05-01: Before coding, verify the registry API shape (ASM-003): open https://registry.verra.org/app/search/VCS in a browser with devtools Network tab, filter by methodology (e.g. VM0051), and record the search endpoint, request body, and the path from a project record to its PDD document download URL. Write findings into the module docstring.
- [x] TASK-05-02: Implement `download_registered_pdds()` in `src/pdd_agent/ingest/registry_download.py`: search by `methodology_id`, resolve project document lists, download up to `limit` PDD PDFs into `output_dir` with filenames `{project_id}_{sanitized_title}.pdf`, ≥ 2 seconds between HTTP requests, 3 retries with backoff on 5xx/timeouts, and a browser-like `User-Agent`. Write `output_dir/manifest.json`: a list of `{"project_id": str, "title": str, "methodology": str, "source_url": str, "local_path": str, "downloaded_at": ISO-8601 UTC}`. If the API is unreachable/changed, log one clear error and still write an empty manifest with a `"note"` field explaining manual-download mode (the ASM-003 fallback: PDFs placed manually in `output_dir` get picked up by a `refresh_manifest(output_dir)` helper).
- [x] TASK-05-03: Add CLI subcommand `fetch-registry`: `pdd-agent fetch-registry --methodology VM0051 --limit 10 --output-dir data/corpus/registry/vm0051`.
- [x] TASK-05-04: Create bucket configs mirroring `configs/corpus_buckets/verra-wte-initial.yaml`'s structure: `configs/corpus_buckets/verra-rice-vm0051.yaml` (keywords: rice, paddy, AWD, alternate wetting drying, methane, CH4, irrigation, VM0051), `configs/corpus_buckets/verra-biochar-vm0044.yaml` (biochar, pyrolysis, feedstock, carbon sink, VM0044), `configs/corpus_buckets/verra-cookstove-amsiig.yaml` (cookstove, improved stove, fuelwood, fNRB, thermal efficiency, AMS-II.G, KPT). Copy the exact YAML key structure from the WTE file.
- [x] TASK-05-05: Tests with mocked HTTP (`tests/test_registry_download.py`): never hit the live registry in tests.
- [x] TASK-05-06 (manual, network): run `fetch-registry` for VM0051, VM0044, AMS-II.G (limit 10 each); then `pdd-agent normalize`-equivalent + `pdd-agent build-index` over the new corpus dirs (follow the existing `ingest → normalize → bucket → build-index` flow documented in README; check exact flags in `cli.py`). Record document counts in `docs/corpus-readiness.md`.
- [x] TASK-05-07 (manual, follow-up): where a downloaded registered PDD for a family contains explicit quantification numbers, replace the synthetic golden-test expectations in `tests/test_rice_vm0051.py` / `tests/test_biochar_vm0044.py` / `tests/test_cookstove_amsiig.py` with the registered values, citing project ID and PDD page in the test docstring. Only swap values that are directly stated in the PDD — do not reverse-engineer.

**File Changes**
- `src/pdd_agent/ingest/registry_download.py` (modify/rewrite): full implementation replacing the stub; keep the existing public function name.
- `src/pdd_agent/cli.py` (modify): `fetch-registry` subcommand.
- `configs/corpus_buckets/verra-rice-vm0051.yaml`, `verra-biochar-vm0044.yaml`, `verra-cookstove-amsiig.yaml` (create).
- `tests/test_registry_download.py` (create).
- `docs/corpus-readiness.md` (modify): add per-family document counts after TASK-05-06.
- `tests/test_rice_vm0051.py` / `tests/test_biochar_vm0044.py` / `tests/test_cookstove_amsiig.py` (modify, TASK-05-07 only).

**Function Signatures**
- `download_registered_pdds(methodology_id: str, output_dir: Path | str, limit: int = 10) -> list[dict[str, Any]]` — downloads PDFs, writes manifest, returns the manifest records (empty list + noted manifest in fallback mode).
- `refresh_manifest(output_dir: Path | str) -> list[dict[str, Any]]` — scans `output_dir` for `*.pdf` not in the manifest and appends records with `"source_url": "manual"`.
- `_search_projects(methodology_id: str, limit: int) -> list[dict[str, Any]]` — internal; returns raw project records from the registry search API.

**Test Specs**
- Mocked search response with 3 projects, each with one PDD document URL; mocked downloads returning `b"%PDF-1.4..."` → `download_registered_pdds("VM0051", tmp_path, limit=2)` creates exactly 2 `.pdf` files and a `manifest.json` with 2 records whose `local_path` files exist.
- Mocked search raising a connection error → returns `[]`, `manifest.json` exists with `"note"` mentioning manual mode, no exception propagates.
- Rate limiting: with time mocked, assert ≥ 2 s spacing between consecutive download calls.
- `refresh_manifest` on a dir containing one manual `foo.pdf` and an empty manifest → one record with `source_url == "manual"`.
- Bucket configs: `yaml.safe_load` each new file → same top-level keys as `configs/corpus_buckets/verra-wte-initial.yaml`.

**Dependencies**
- PHASE-01 (hygiene) only. Independent of PHASES 02–04; can run in parallel with them.
- External: live registry access for TASK-05-06 (fallback per ASM-003).

**Exit Criteria**
- [ ] `python -m pytest tests/test_registry_download.py -v` → all pass with no network.
- [ ] `pdd-agent fetch-registry --methodology VM0051 --limit 2 --output-dir data/corpus/registry/vm0051` either downloads ≥ 1 PDF or exits 0 in documented manual mode.
- [ ] Three bucket config files load without YAML errors.

**Phase Risks**
- **RISK-05-01:** Registry blocks scripted clients (Cloudflare or similar). Mitigation: the manual-mode manifest path is a first-class outcome, not an error; the plan's downstream phases consume the manifest regardless of how PDFs arrived.

### PHASE-06 - Rice VM0051 End-to-End Pilot

**Goal**
One non-WTE project drafts end-to-end — intake → draft → judge → section review in the service UI → gated DOCX export — proving the methodology-breadth claim on the designated Seraphin substitute (Vietnam rice) and flushing out WTE-shaped assumptions in the schema, prompts, and section taxonomy.

**Tasks**
- [x] TASK-06-01: Create `configs/projects/rice_vm0051_pilot.yaml` per ASM-009: a valid `ProjectInput` (validate with a small script or test against `schemas/project_input.py`) for a synthetic Vietnam AWD rice project, methodology VM0051, quantification values consistent with `calc/rice_vm0051.py` golden tests, all quantitative fields marked `demo_curated` provenance. Create the companion `configs/projects/rice_vm0051_pilot.assumptions.yaml` following the structure of `configs/projects/demo_socson_like.assumptions.yaml`.
- [x] TASK-06-02: Run the calc engine against the pilot input and confirm `calc/rice_vm0051.py` produces baseline/project/net tCO2e numbers matching the input's quantification section (adapt a small integration test in `tests/test_rice_vm0051.py`).
- [x] TASK-06-03: Draft via CLI first (faster iteration): `pdd-agent draft --input configs/projects/rice_vm0051_pilot.yaml --provider demo` (and `--provider ollama` if PHASE-02's manual setup is live). Catalogue every WTE-specific breakage: schema validators that assume waste tonnage, section prompts that mention incineration, review checks keyed to WTE quantities (`review/consistency.py` net-tCO2e relations should be methodology-neutral — verify), export table types that don't fit. Fix each minimally; do not redesign the schema (DEC-004).
- [x] TASK-06-04: Repeat through the service: start the service, `POST /api/runs` with the pilot YAML (or the dashboard upload form), complete one full section-review cycle (approve ≥ 1 section, inline-edit ≥ 1, redraft ≥ 1), download the gated DOCX.
- [x] TASK-06-05: Write `docs/2026-07-XX-rice-pilot-findings.md` (actual date): what broke, what was fixed, judge pass rates, remaining WTE-coupling debt, and a go/no-go note on whether the schema needs the per-family split (input to revisiting DEC-004).
- [x] TASK-06-06: Add a pytest covering the pilot end-to-end with the demo provider (marker-free, no corpus dependency): draft all sections, run review checks, export DOCX to `tmp_path`, assert file exists and no unhandled exceptions.

**File Changes**
- `configs/projects/rice_vm0051_pilot.yaml` (create), `configs/projects/rice_vm0051_pilot.assumptions.yaml` (create).
- `tests/test_rice_pilot_e2e.py` (create): end-to-end demo-provider test.
- `tests/test_rice_vm0051.py` (modify): pilot-input ↔ calc-engine integration test.
- Fix-up files as discovered in TASK-06-03 (expected candidates: `schemas/project_input.py` validators, `prompts/` templates, `src/pdd_agent/review/consistency.py`, `src/pdd_agent/export/docx_export.py` table selection) — each change minimal and covered by an existing or new test.
- `docs/2026-07-XX-rice-pilot-findings.md` (create).

**Function Signatures**
- None — no planned interface changes; fix-ups discovered in TASK-06-03 must preserve existing signatures where possible.

**Test Specs**
- `ProjectInput` loads `rice_vm0051_pilot.yaml` without validation errors → model field `methodology` (check the exact field name in `schemas/project_input.py`) equals `"VM0051"`.
- Calc integration: pilot hydrology/area inputs through `calc/rice_vm0051.py`'s public entry → net emission reductions within 0.5% of the value stated in the pilot YAML's quantification block.
- End-to-end (demo provider): draft run covers every section key in `schemas/pdd_section_schema.yaml`'s taxonomy with non-empty text; review checks run without raising; DOCX export writes a file > 20 KB.
- Consistency checks on the rice run: baseline − project − leakage == net relation holds (methodology-neutral check passes on non-WTE numbers).

**Dependencies**
- PHASE-03 (service works with DI + retrieval), PHASE-05 (rice bucket config; corpus optional — the demo run must succeed without corpus per the graceful-degradation convention).

**Exit Criteria**
- [ ] `python -m pytest tests/test_rice_pilot_e2e.py tests/test_rice_vm0051.py -v` → all pass.
- [ ] Manual: service round-trip (TASK-06-04) completed; DOCX downloaded.
- [ ] `docs/2026-07-XX-rice-pilot-findings.md` exists with the WTE-coupling debt list.
- [ ] `python -m pytest -m "not corpus" -q` → green.

**Phase Risks**
- **RISK-06-01:** The 36-section VCS taxonomy may materially misfit rice (e.g., WTE-specific quantification tables). Mitigation: sections that cannot apply get drafted with explicit "not applicable to this methodology" text driven by the section schema's content class — never silently skipped; log each as a finding in the pilot doc.

## Gotchas

- `schemas/` is a top-level package (`from schemas.project_input import ProjectInput`), not under `src/pdd_agent/` — new code must keep that import path.
- `pytest` `addopts` includes `-v --tb=short`; adding `-q` on the command line overrides verbosity but keeps short tracebacks. The `corpus` marker gates tests needing `data/corpus/normalized/` — always run `-m "not corpus"` unless the corpus is built.
- Importing `pdd_agent.service.main` currently mutates `DraftRun.save`, `ReviewStateStore.save/load`, and retrieval functions process-wide (until PHASE-03 removes this). Any test written before PHASE-03 that imports the service module can silently change persistence behavior for later tests in the same process.
- `DraftRun.save`/`load` and `ReviewStateStore.save`/`load` already accept `output_dir: Path | None` — the DI fix threads directories through call sites; do not add new persistence mechanisms.
- The dev machine is Windows: set env vars as `$env:PDD_MAX_COST_USD = "20"` in PowerShell (the `VAR=x cmd` prefix form in this plan's example commands is Bash syntax; both shells are available via Git Bash).
- Section keys: `_section_key()` returns `sub_section_id` when present else `section_id`; the export gate's Sections-3–4 rule matches on `section_key.startswith(("3", "4"))` — a hypothetical section "30" would false-positive; keep keys dotted (`"3.1"`).
- Ollama's `/api/chat` response nests text at `response["message"]["content"]` (not OpenAI's `choices[0].message.content`); token counts are `prompt_eval_count`/`eval_count` and may be absent on some models — default to 0, never KeyError.
- `configure_provider()` in `llm/provider.py` registers providers by name into a module-level registry; calling it twice re-registers (safe), but tests must reset/monkeypatch the registry to avoid cross-test leakage.
- Emission units are tCO2e everywhere; the consistency checks compare floats — keep tolerances (existing code uses relative tolerance; mirror it, don't use `==`).
- `git clean -fd` after PHASE-01's `.gitignore` change would delete the untracked `ref/PDD staff April 2026/` and `May 2026/` folders — never run it in this repo.

## Verification Strategy

- **TEST-001:** `python -m pytest -m "not corpus" -q` → exit 0 at the end of every phase (baseline 534 passed, 7 deselected; count grows each phase).
- **TEST-002 (PHASE-01):** `git status --short` → empty output; `pdd-agent doctor; echo $?` → prints check lines and `0`.
- **TEST-003 (PHASE-02):** `python -m pytest tests/test_ollama_provider.py -v` → all pass offline.
- **MANUAL-001 (PHASE-02):** `pdd-agent draft --input configs/demo/inegol_project_input.yaml --provider ollama` → completes 36 sections, prints a run-id; `pdd-agent export --run-id <run-id>` → DOCX exists.
- **TEST-004 (PHASE-03):** `python -m pytest tests/test_service.py tests/test_retrieval_threading.py -v` → all pass; `grep -c "= lambda" src/pdd_agent/service/main.py` → `0`.
- **MANUAL-002 (PHASE-03):** start service, create a demo run, kill the process mid-run, restart → run shows status `failed` with the orphaned message on the dashboard.
- **TEST-005 (PHASE-04):** `pdd-agent scorecard --input configs/demo/inegol_project_input.yaml --providers demo --output reports/provider-scorecard.md` → exit 0 and the file contains a header row with 7 metric columns.
- **MANUAL-003 (PHASE-04, key-gated):** with keys + `PDD_MAX_COST_USD=20`, three-provider scorecard completes under the ceiling; winning DOCX handed to domain expert.
- **TEST-006 (PHASE-05):** `python -m pytest tests/test_registry_download.py -v` → all pass offline; `python -c "import yaml,glob; [yaml.safe_load(open(p)) for p in glob.glob('configs/corpus_buckets/verra-*.yaml')]"` → no error.
- **TEST-007 (PHASE-06):** `python -m pytest tests/test_rice_pilot_e2e.py -v` → all pass.
- **OBS-001:** structlog events to watch during manual runs: `service_provider_fallback` (should NOT appear when a real provider is correctly configured), `llm_judge_unparseable` (should trend to zero as PHASE-04 lands), `public_registry_download_not_yet_implemented` (must never appear after PHASE-05).

## Risks and Alternatives

- **RISK-001:** API keys never arrive → the VVB-grade proof stalls. Mitigation: every phase completes and verifies keyless; the Ollama path (PHASE-02) plus the key-gated checklist (TASK-04-06) means the live run is minutes of work when keys land, not weeks.
- **RISK-002:** Local-model output quality makes the shakeout demoralizing and tempts loosening the export gate. Mitigation: DEC-002 gate semantics are frozen; PHASE-02's success metric is "no crashes", explicitly not prose quality.
- **RISK-003:** Removing the service monkeypatches (PHASE-03) breaks hidden dependents. Mitigation: exit criterion runs the full suite; the DI parameter defaults preserve CLI behavior exactly.
- **RISK-004:** Verra registry inaccessible to scripts. Mitigation: manual-manifest mode is a designed outcome (ASM-003); corpus building proceeds on manually downloaded PDFs.
- **ALT-001:** Use the `ollama` pip package or `httpx` instead of stdlib urllib — rejected: adds a dependency for one POST endpoint; the service must stay dependency-light and keyless-runnable.
- **ALT-002:** Celery/RQ for durable service runs — rejected: single-user local service; a status JSON + startup sweep covers the actual failure mode (restart during a run) at ~50 lines.
- **ALT-003:** Per-family discriminated-union `ProjectInput` before the rice pilot — rejected per DEC-004: redesigning the schema before a second real non-WTE project exists is premature; the pilot's findings doc gathers the evidence to decide.
- **ALT-004:** Skip Ollama and wait for keys — rejected: leaves the entire real-LLM code path (prompt assembly, marker parsing, judge loop, budget accounting) unexercised for an unbounded external wait.

## Suggested Next Step

Execute PHASE-01 (hours of work, immediately unblocks a clean tree and diagnosable environment), then PHASE-02 and PHASE-05 in parallel — they are independent; PHASE-03 follows PHASE-02.
