# PDD Reality Gap — Make the Existing Machine Real

**Plan:** `plans/2026-07-12-pdd-reality-gap-plan.md`
**Status:** PHASE-01 COMPLETE — repo hygiene, `.env`, `pdd-agent doctor`, docs refresh
**Last commit:** 3fe256f — Fix test-isolation leak: assumption-burden.md written on every test run

**Prior push:** `plans/2026-07-05-pdd-next-level-plan.md` (closed 2026-07-05, see `docs/2026-07-05-convergence.md`). That push built the skeleton (Anthropic provider, judge/redraft loop, FastAPI service, calc breadth) but never proved any of it against a real LLM or exercised the service's real code paths. This plan closes that gap.

## Phase progress

- [x] PHASE-01: Repo hygiene and environment foundation
  - [x] TASK-01-01: Verify/remove `tmp_wte_model.xlsx` (duplicate of tracked cached workbook)
  - [x] TASK-01-02: Commit `ref/` snapshot deletions; gitignore `ref/` and `.env`
  - [x] TASK-01-03: Commit stray tracked-worthy files (`uv.lock`, two brainstorm briefs, `reports/assumption-burden.md`, two orphaned demo-package run folders)
  - [x] TASK-01-04: `.env` support via `python-dotenv` (`find_dotenv(usecwd=True)`) in both CLI and service
  - [x] TASK-01-05: `pdd-agent doctor` diagnostic command + `tests/test_doctor.py`
  - [x] TASK-01-06: Project `CLAUDE.md` and seed `lessons.md`
  - [x] TASK-01-07: README refresh (test count, service quickstart, provider/judge/registry status corrections)
  - [x] TASK-01-08: Full suite green, working tree clean
- [ ] PHASE-02: OllamaProvider implementation + real-path shakeout — **not started**
- [ ] PHASE-03: Service reality fixes (RAG thread-safety, provider opt-in, de-monkeypatch) — **not started**
- [ ] PHASE-04: Real LLM judge + provider scorecard — **not started, key-gated tasks blocked on API keys**
- [ ] PHASE-05: Verra registry downloader + family corpus buckets — **not started**
- [ ] PHASE-06: Rice VM0051 end-to-end pilot — **not started**

## Unplanned fixes made during PHASE-01

Two real bugs surfaced while verifying PHASE-01's exit criteria (not in the original task list, fixed because they blocked verification and are small, root-cause fixes):

1. **Packaging bug:** the installed `pdd-agent` console script has never worked outside the repo root — `schemas/` (a top-level package used throughout the pipeline) was never declared in the hatchling wheel build target, so every subcommand failed with `ModuleNotFoundError: No module named 'schemas'` unless the repo root happened to be on `sys.path` (e.g. via `python -c` from the repo root, or pytest's rootdir handling). Fixed via `[tool.hatch.build.targets.wheel].packages = ["src/pdd_agent", "schemas"]` in `pyproject.toml`.
2. **Test-isolation leak:** running the full suite unconditionally dirtied tracked `reports/assumption-burden.md`, because `SectionOrchestrator.run_review()` called `write_assumption_burden_report()` with no output path in three places (`service/main.py`, `phase05/benchmark.py`, and three tests), always falling back to the hardcoded repo-relative default — even though the surrounding code in each case already threads an explicit output directory for every other artifact. Added an `assumption_burden_path` constructor parameter to `SectionOrchestrator` and threaded it through.

## Constraints (carried forward, still binding)

- Tests must never require API keys, network access, or a running Ollama instance — mock all HTTP.
- Demo/noop providers remain the safe default everywhere; real providers are opt-in via env vars.
- Local-only deployment; no cloud/container infra this push.

## Blockers

1. No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` available in the environment — blocks PHASE-04's key-gated live-run tasks. PHASE-02 (Ollama) is the key-independent unblock for exercising the real-LLM code path in the meantime.
2. Seraphin greenfield data remains externally blocked; PHASE-06's rice pilot is the designed substitute.
3. Verra registry API shape needs live verification before PHASE-05 implementation (see plan ASM-003).

## Test results

- `python -m pytest -m "not corpus" -q`: **544 passed, 7 deselected** (up from 534 — 10 new `tests/test_doctor.py` cases)
- `pdd-agent doctor` exits 0 from both the repo root and an arbitrary external directory.
- `git status --short` is empty after a full test run (previously always dirtied `reports/assumption-burden.md`).

## Changed files (PHASE-01)

- `.gitignore` — `ref/`, `.env`
- `pyproject.toml` — `python-dotenv` dependency, `[tool.hatch.build.targets.wheel].packages` fix
- `src/pdd_agent/doctor.py` (new), `tests/test_doctor.py` (new)
- `src/pdd_agent/cli.py` — `.env` loading, `doctor` subcommand, int-return exit-code plumbing
- `src/pdd_agent/service/main.py` — `.env` loading, assumption-burden path redirection
- `src/pdd_agent/agent/section_orchestrator.py` — `assumption_burden_path` constructor parameter
- `src/pdd_agent/phase05/benchmark.py` — assumption-burden path now honors `reports_dir`
- `tests/test_e2e_doc_to_pdd.py`, `tests/test_e2e_inegol_draft.py`, `tests/test_section_orchestrator.py` — redirect assumption-burden writes to `tmp_path`
- `CLAUDE.md` (new), `lessons.md` (new), `README.md` — docs refresh
- Removed: `ref/PDD staff test-20260520T145916Z-3-001/` (551 files), `tmp_wte_model.xlsx`
- Committed: `uv.lock`, two research briefs, `reports/assumption-burden.md`, two demo-package run folders, `plans/2026-07-12-pdd-reality-gap-plan.md`

## Suggested next step

Execute PHASE-02 (OllamaProvider implementation + Inegol shakeout on a local model) — it is independent of PHASE-05 and can run in parallel with it.
