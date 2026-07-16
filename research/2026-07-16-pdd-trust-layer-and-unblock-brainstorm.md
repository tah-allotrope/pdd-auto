---
title: "PDD-Auto After Parametrization: Repair the Trust Layer, Self-Service the Blockers, Run the Proof"
date: "2026-07-16"
type: "brainstorm"
depth: "standard"
source_request: "Analyze current state and brainstorm what takes pdd-auto to the next level"
slug: "pdd-trust-layer-and-unblock"
---

# Brainstorm: PDD-Auto After the Methodology-Parametrization Push

## Where the project stands (2026-07-16, fresh evidence gathered this session)

The `2026-07-13-methodology-parametrized-pipeline-plan` is **complete** — all 6 phases committed
(`a3371de`), working tree was clean at session start. Prompts, judge rubrics, and the test matrix
are methodology-parametrized over the four families; `pdd-agent prove` exists; the evidence
registry flows intake → prompt → DOCX appendix; the batch-approve race has an atomic endpoint.

This analysis did not take the recorded status at face value. Fresh verification found three
material facts the repo's own records did not know:

1. **CI has been red since the day it was born.** All 3 GitHub Actions runs (the only 3 that ever
   executed, 2026-07-13 → 2026-07-14) failed identically: `tests/test_service.py` fails
   *collection* on a fresh install with `RuntimeError: Form data requires "python-multipart"`.
   The dependency was never declared in the `service` extra — the original dev environment had it
   installed ad hoc, so local runs passed while every fresh install (CI, any new machine, Tinh's
   onboarding) breaks. The plan's OBS-001 exit criterion ("confirm the Actions run is green") was
   checklisted but evidently never observed.
   **Fixed this session:** commit `c24d476` declares `python-multipart>=0.0.9` and refreshes
   `uv.lock` (which was also stale — it lacked `python-dotenv`, a *core* dependency, and the
   entire `service`/`llm` extras). Verified locally before pushing: a fresh
   `uv sync --all-extras` reproduces the CI error exactly; with the fix, **679 passed, 0 failed,
   7 corpus-deselected** in 100s. (The recorded "686 tests" = 686 collected; 679 run + 7
   deselected. README's "544 tests" is two pushes stale.)

   **And the first post-fix CI run immediately earned its keep:** with collection unblocked, the
   suite ran on Linux for the first time ever and exposed **11 failures across 4 real
   cross-platform bug classes** the Windows-only history had masked:
   - `extract_project_input()` calls `Path(source).exists()` on raw document text; on Linux this
     raises `OSError: File name too long` (7 e2e tests). Fixed with a safe path-probe helper.
   - `tests/test_drive_inventory.py` silently required the real `gws` CLI (installed on the dev
     box, absent on CI) — a violation of the repo's own "tests never require external tools"
     constraint that had never been noticed. Fixed by mocking `_check_gws_available`.
   - A thread-identity test assumed a `ThreadPoolExecutor` runs 4 tasks on 4 distinct threads;
     on fast Linux runners a worker gets reused, legitimately yielding the same thread-local
     connection twice. Fixed with a barrier.
   - The Vietnam validation report renders paths with the OS separator, and its test hardcoded
     the Windows backslash form. Fixed by rendering POSIX paths (stable report output on all
     platforms).
   All four fixes verified locally and pushed this session.

2. **The WTE hardcoding survives one layer below where the last push fixed it.** The
   parametrization push made the *user* prompt and judge rubric family-aware, but all three real
   providers still carry a hardcoded **system prompt** that begins: *"You are a technical writing
   assistant specializing in Verra VCS carbon credit Project Design Documents **for
   waste-to-energy projects**"* — `openai_provider.py:67`, `anthropic_provider.py:86`,
   `ollama_provider.py:35-40`. The `demo` provider doesn't use a system prompt, which is why the
   43-test methodology matrix (demo-provider-based) cannot see this. **The frontier proof, as
   currently wired, would system-prompt a rice/biochar/cookstove draft as a WTE assignment while
   the user prompt says otherwise** — a direct contradiction handed to the model.

3. **`pdd-agent prove` would produce a misleading scorecard on any machine without Ollama.**
   `_is_provider_available()` returns `True` unconditionally for `ollama`; `OllamaProvider`
   converts connection failures into `[OLLAMA ERROR ...]` placeholder *sections* rather than
   raising. Net effect: `prove --providers auto` on a no-Ollama box yields an "ollama" row with
   36 "drafted" sections that are all error placeholders — judged, scored, and printed as if a
   real run happened. Two smaller defects in the same file: the `Redraft count` column is dead
   (always 0 — the orchestrator runs with `enable_judge=False`, so the redraft loop never fires
   in prove), and judge-call tokens are not counted in `estimated_cost_usd` (the judge gets no
   budget threading).

**External-blocker status (carried from activeContext):** no `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`
in the environment (confirmed — no `.env` exists either); CPU-only dev hardware; Verra registry
POST payload shape still unknown; no real non-WTE prospect. But see the central diagnosis — two of
these four are no longer truly external.

## Central diagnosis

Three findings define the next level:

1. **The trust layer failed silently, and only the trust layer can prevent that.** CI — installed
   specifically as "the cheapest insurance protecting everything else" — was red for its entire
   lifetime and nothing surfaced it: no branch protection, no badge, no notification habit, and a
   plan-closure process that marked "CI green" complete without looking. The lockfile was stale,
   the committed `.venv` lacks dev extras, and the recorded test count didn't match a fresh
   environment. None of these individually is serious; together they mean **the repo's recorded
   state and its reproducible state had drifted apart**, which is precisely the failure mode this
   project cannot afford when its output is a compliance document.

2. **Two of the four "external" blockers are now self-serviceable, and one was never re-examined.**
   - *The API-key blocker (survived four consecutive pushes) has an unexplored bypass:* this
     machine runs Claude Code under an active subscription. A `ClaudeCodeProvider` that shells
     out to the headless CLI (`claude -p <prompt> --output-format json`) gives the pipeline a
     frontier Anthropic model **today, with zero API key**, through the existing `BaseProvider`
     seam (~200 lines, mirroring `ollama_provider.py`'s structure). The proof stops being blocked
     on procurement.
   - *The Verra-registry blocker is stated as "needs browser-devtools inspection" — and the
     orchestrated agent environment now has browser devtools.* Claude-in-Chrome's
     `read_network_requests` can capture the exact search POST payload from one interactive
     search on `registry.verra.org/app/search/VCS`. That single capture upgrades
     `registry_download.py` from best-effort to live, unlocking real corpora for
     rice/biochar/cookstove and the golden-test upgrade (synthetic → registered values).
   - The GPU and real-prospect blockers remain genuinely external (though the Ollama dress
     rehearsal can shrink via a small model — `llama3.2:3b` — since `ModelConfig.base_url` and
     `model_name` are already configurable).

3. **The proof harness itself needs one hardening pass before it is worth pointing a real model
   at.** The provider system prompts (finding 2), the phantom-Ollama scorecard row, the dead
   redraft column, uncounted judge cost, and one design smell — `prove` defaults to
   **self-judging** (judge provider = drafting provider unless `PDD_JUDGE_PROVIDER` overrides),
   which will overstate every provider's pass rate in the head-to-head — together mean the first
   real `prove` run would emit an artifact with known lies in it. All are hours-scale fixes.

The next level is: **(A) make the trust layer actually trustworthy; (B) harden the proof harness;
(C) self-service the two serviceable blockers and run the real proof; (D) then the Monitoring-
Report bet, unchanged from the July-13 analysis, as the post-proof strategic move.**

---

## Improvement tracks (priority order)

### Track A — Repair and fortify the trust layer (started this session; finish in hours)

- **A1. CI dependency fix + Linux-portability fixes — DONE.** Commit `c24d476` plus a follow-up
  commit (this session) fixing the 11 Linux failures the unblocked suite surfaced. The first-ever
  green CI run is pending observation at session close; the run URL and conclusion are reported
  in the session summary.
- **A2. Make red CI impossible to miss.** Add the Actions status badge to `README.md`; enable
  branch protection on `main` requiring the `test` check; end every future plan's exit criteria
  with *observed* CI evidence (run URL + conclusion), not a local-equivalent command. A
  `gh run list --limit 1` check belongs in the session-start ritual (or a scheduled agent that
  pings on red).
- **A3. Reproducibility leg in CI.** The current CI resolves latest deps via `pip`; the lockfile
  is never exercised, so it will drift stale again. Add a second job (or swap the install step)
  using `uv sync --locked --all-extras` so the lock is enforced, plus a `pip` leg to catch
  missing-declaration bugs like this one from both directions.
- **A4. Environment-integrity checks in `doctor`.** `pdd-agent doctor` diagnoses Ollama and API
  keys but not its own Python environment. Add: import-check for `pytest`, `fastapi`,
  `python-multipart`, `uvicorn`; a PYTHONPATH-pollution warning (this session found the repo
  venv shadowed by a foreign `PYTHONPATH` injected by the orchestrating environment — the
  committed `.venv` also lacks dev extras); and a stale-lock check (`uv lock --check`).
- **A5. Truth-sync the docs.** README says "544 tests"; activeContext says "686 passing"; fresh
  reality is 679 passed / 686 collected. Pick one convention (collected, non-corpus) and state it
  once.

### Track B — Harden the proof harness before any real dollars/tokens flow (hours, non-key-gated)

- **B1. Parametrize the provider system prompts.** Move the system prompt out of the three
  provider modules and into prompt assembly (the orchestrator already owns family overlays), or
  thread the family slug into `ModelConfig`. Extend the methodology matrix with an assertion the
  demo provider can't dodge: for a non-WTE project, the *system* prompt handed to any real
  provider contains no "waste-to-energy". This is the last known WTE-shaped landmine on the
  frontier-proof path.
- **B2. Real Ollama availability probe.** `_is_provider_available("ollama")` should GET
  `{base_url}/api/tags` with a ~2s timeout and return `(False, "ollama_unreachable")` on failure
  (mocked in tests). Additionally, `_run_one_provider` should count `[OLLAMA ERROR`-prefixed
  sections and either fail the row or report `sections_failed` explicitly — an error placeholder
  is not a drafted section.
- **B3. Cross-judging by default in `prove`.** Self-judging inflates every row. Default the judge
  to the strongest *available* provider that is not the drafting provider (fall back to
  deterministic when none), and record the judge identity in the scorecard header. Keep
  `PDD_JUDGE_PROVIDER` as the override.
- **B4. Honest scorecard metrics.** Either wire the redraft loop into `prove` (run orchestrator
  with `enable_judge=True` and count actual redrafts) or drop the dead column; thread the
  `TokenBudget` into judge calls so `estimated_cost_usd` covers draft + judge; add a
  `sections_failed` column per B2.
- **B5. Catch provider exceptions per row.** `_run_one_provider` catches only
  `BudgetExhaustedError`; any other provider exception kills the whole scorecard. Catch
  per-provider, record as a failed row, continue — `prove` must always emit its artifact.

### Track C — Self-service the two serviceable blockers, then run the proof (the milestone)

- **C1. `ClaudeCodeProvider`: the keyless frontier path.** New `llm/claude_code_provider.py`
  shelling out to `claude -p --output-format json` (subprocess, like the `gws` wrapper —
  consistent with the repo's no-SDK pattern). Availability check = `claude --version` succeeds.
  Register in the provider registry; add to `prove`'s auto list. Caveats to encode: latency is
  minutes not seconds for 36 sections (run serially with progress logging); token accounting
  comes from the CLI's JSON `usage` field; cost is subscription-covered, so record it as
  `$0.00 (subscription)` rather than fabricating a number. **ASM-02 (adopted):** using the
  operator's own Claude subscription for this internal drafting tool is acceptable; if the
  operator disagrees, this track reverts to waiting on keys and everything else here stands.
- **C2. Verra registry capture via the browser agent.** One attended-or-agent Chrome session:
  open `registry.verra.org/app/search/VCS`, run one methodology-filtered search, read the
  captured `/uiapi/asset/asset/search` POST body via devtools/`read_network_requests`, encode it
  in `registry_download.py`, and flip live mode on. Then bulk-populate
  `data/corpus/registered/{rice,biochar,cookstove}/` and swap the calc golden tests from
  synthetic to registered values (the long-standing D3). This also feeds per-family retrieval:
  today the FTS index has only WTE-bucketed corpus, so a real rice draft retrieves WTE excerpts —
  corpus breadth is the *third* layer of the same WTE-shaped-assumption onion (calc → prompt →
  corpus).
- **C3. Run the proof: `pdd-agent prove --project inegol` and `--project rice` with
  claude-code + ollama + any keyed providers.** Then the two comparisons that settle old
  questions: pipeline-real-LLM vs. Codex reference (`compare_codex_vs_pipeline.py` — every prior
  comparison used the demo provider), and WTE vs. rice judged quality (does breadth hold for
  prose, not just arithmetic). Domain-expert sign-off on the Inegol DOCX remains the acceptance
  bar.
- **C4. Ollama dress rehearsal on a small model.** Before C3, one full 36-section run with
  `llama3.2:3b` (or `qwen3:4b`) on the current CPU box overnight — `ModelConfig.model_name`
  already supports it. The goal is not quality; it is shaking out nondeterministic-output bugs
  (marker parsing, redraft convergence, budget accounting) on free tokens.

### Track D — Post-proof strategy (unchanged in direction, sharpened in sequencing)

- **D1. Monitoring-Report product bet.** Carried intact from the July-13 brainstorm: MRs recur
  every issuance period, reuse ~80% of this plumbing (corpus, calc, review, export, evidence
  registry), and turn a one-shot deliverable into recurring revenue. Correctly sequenced *after*
  C3's proof. The evidence-registry flow built in PHASE-06 is the natural MR backbone (measured
  vs. ex-ante variance needs exactly that audit trail).
- **D2. Tinh onboarding — still never run.** `setup_service.py` exists; the loop (one-command
  setup → full review cycle on a demo run → friction log) has survived three brainstorms
  unexecuted. Note: **the python-multipart bug fixed this session would have been his first
  experience** — fresh install, service intake form, immediate crash. That is the argument for
  A3/A4 in one sentence. Run the onboarding after CI is observed green.
- **D3. Service productization (auth, multi-user, persistent DB) stays deferred** until a second
  human actually uses the review UI (D2) and the proof lands. Single-user FastAPI + JSON
  persistence is correct for the current team size.

### Track E — Opportunistic / small

- **E1. Per-run telemetry surface.** `TokenBudget` already records per-section tokens; render it
  in the run-detail page and scorecard (cost/latency per section) before real runs start burning
  money. Small now that the budget plumbing exists.
- **E2. Judge `use_llm` prompt tuning.** The structured-JSON judge is real but its prompt has
  never been calibrated against a real model's outputs; do this with claude-code provider (C1)
  on demo drafts — cheap, keyless, and it de-risks the judge before it referees the proof.
- **E3. Retrieval hybridization (embeddings alongside FTS5 BM25)** — only if C2's corpus
  expansion shows BM25 recall failing on non-WTE terminology; do not build speculatively.

---

## Recommended sequencing

1. **Done this session:** A1 (CI dependency fix pushed, `c24d476`; first green run pending
   observation).
2. **Hours:** A2–A5 (badge, branch protection, locked-install CI leg, doctor env checks, doc
   truth-sync) + B1–B5 (proof-harness hardening). All non-key-gated, all small.
3. **One focused day:** C1 (`ClaudeCodeProvider`) + C4 (small-model Ollama rehearsal overnight).
4. **One agent-browser session:** C2 (registry capture → live downloader → corpora → golden
   swap).
5. **The milestone:** C3 — the real-model proof + Codex convergence comparison + expert sign-off.
6. **After the proof:** D1 (Monitoring-Report plan) with D2 (Tinh onboarding) in parallel; E-track
   opportunistically.

## Single highest-leverage recommendation

**C1, the `ClaudeCodeProvider`.** The frontier proof has been "the milestone" for four
consecutive pushes, blocked each time on a key that never arrives — while a subscription-backed
frontier model sits on the very machine running the pipeline. One provider module (~200 lines,
pattern-matched to `ollama_provider.py`) converts the project's oldest external blocker into an
internal afternoon task. Do B1 first (system-prompt parametrization) so the proof it enables
validates all four families, not WTE-with-a-contradiction.

## Assumptions adopted (orchestrator unattended — noted per workflow rules)

- **ASM-01:** Fixing the failing CI (declare python-multipart, refresh lock, commit, push) was
  in-scope for this analysis session, per the standing instruction "fix failing CI tests without
  being asked." The change is minimal (1 dependency line + lockfile) and was verified locally
  (679 passed) before pushing.
- **ASM-02:** Using the operator's Claude Code subscription as a drafting provider (C1) is
  acceptable for this internal tool. If not, C1 is dropped and the proof reverts to key-gated;
  the rest of this brainstorm is unaffected.
- **ASM-03:** The browser-agent capture of the Verra registry POST shape (C2) is acceptable use —
  it reads the same public search UI a human would, one search, throttled downloads (the module
  already enforces 2s intervals and a limit).
- **ASM-04:** "686 tests" in activeContext meant 686 *collected* (679 run + 7 corpus-deselected);
  treated as a documentation-precision issue, not a missing-tests regression, since 0 tests fail.
- **ASM-05:** The Monitoring-Report bet (D1) remains correctly sequenced after the proof;
  reaffirmed rather than re-litigated from the July-13 analysis.
- **ASM-06:** No new methodology families before the existing four draft for real; corpus breadth
  (C2) counts as deepening existing families, not widening.

## Suggested next step

Run `/plan` against this brainstorm. Recommended first plan scope: **Tracks A2–A5 + B1–B5 + C1 +
C4** — "trustworthy CI, honest proof harness, keyless frontier provider" — the non-external-
blocked push that ends with `pdd-agent prove --project inegol --providers claude-code,ollama,demo`
producing the first real-model, multi-family, honestly-scored proof artifact in the project's
history.
