---
title: "PDD-Auto Next Level: Run the Proof That's Already Unblocked, Then Close the Loop"
date: "2026-07-23"
type: "brainstorm"
depth: "standard"
source_request: "Orchestrator-driven brainstorm: analyze current state, propose improvements/features/refactors/architecture changes/optimizations"
slug: "run-the-proof-and-close-the-loop"
---

# Brainstorm: PDD-Auto — Run the Proof That's Already Unblocked, Then Close the Loop

## Where the project stands (2026-07-23, fresh evidence gathered this session)

This is the fifth consecutive brainstorm/plan cycle on this repo (April → July 2026). The prior four
pushes built, in order: the core pipeline (corpus RAG, rule-based review, DOCX export, calc engines),
methodology breadth (rice/biochar/cookstove families), a trust layer (CI, branch protection, doctor
checks), and — as of the last push (`plans/2026-07-16-trust-layer-keyless-frontier-proof-plan.md`,
merged in commits `532cecd`..`28bbb8c`) — an honest proof harness and a **keyless frontier provider**
(`ClaudeCodeProvider`, `src/pdd_agent/llm/claude_code_provider.py`, 263 lines, 16 tests) that shells
out to the local `claude` CLI instead of requiring an `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` that has
never existed in this environment across four consecutive pushes.

Fresh verification this session, not taken from prior records:

- **Test suite: 729 passed, 7 deselected**, run via `PYTHONPATH= uv run --no-sync python -m pytest
  -m "not corpus" -q` (up from the 686-collected figure recorded in `activeContext.md` — more tests
  landed in the trust-layer push than that document's snapshot captured; nothing is broken).
- **CI is green and has stayed green.** `gh run list` shows 4 consecutive `success` runs since the
  2026-07-16 fix, including the two most recent commits. Branch protection is live on `main`
  (`test (3.11)`, `test (3.12)`, `lock-reproducibility` all required, confirmed via
  `gh api .../branches/main/protection`).
- **The `claude` CLI is present and on `PATH` in this exact environment**
  (`/c/Users/tukum/.local/bin/claude`) — this is, in fact, the same CLI this analysis is running
  under. `ClaudeCodeProvider` is fully implemented, tested, and registered; `doctor.py` checks for it.
- **The full-scale proof has still never been run.** `reports/` contains zero `prove-*.md` artifacts.
  The trust-layer push's own final report (`reports/2026-07-17-final-phase-03-04-05-06-*.html`)
  explicitly deferred it: it ran one *bounded, small* manual verification call instead of the full
  36-section `pdd-agent prove --project inegol --providers claude-code`, specifically because the
  in-loop redraft judge still self-judges by default (a real provider judging its own output multiplies
  real calls with no ceiling) — and flagged both "run the full proof" and "fix the self-judging redraft
  loop" as the immediate next steps. Neither has happened yet.
- **The Ollama dress rehearsal (PHASE-06 of the same plan) is genuinely blocked**, not just deferred:
  Ollama is not installed on this machine (confirmed via `docs/ollama-dress-rehearsal.md`'s own
  status note — a stale PATH entry, target directory doesn't exist).
- **The Verra registry downloader is still in manual-download mode** (`registry_download.py:156` —
  "Attempts a live search... on any failure" — best-effort only). `data/corpus/registry/` has zero
  populated documents for rice/biochar/cookstove. This has been a stated blocker since 2026-07-12,
  always described as "needs browser-devtools inspection of the search API shape."

## Central diagnosis

**The project has spent four pushes building the machinery to prove itself, and the proof is sitting
right there, unrun, in the same environment that built it.** This isn't a criticism of the prior
work — each piece (family-aware prompts, honest scorecard, cross-judging, the keyless provider) was a
real, necessary, well-tested precondition. But the pattern across `activeContext.md` history is
consistent: every push ends with "ready to run the moment X is available," and X keeps turning out to
already be available by the time anyone re-checks. The claude-code provider is the second instance of
this in a row (the first was C1 itself, sitting unbuilt for three pushes while the subscription sat on
the dev machine). The `claude` CLI's presence in *this very session* is the clearest possible signal
that the next action is to run the thing, not plan the next thing.

A second, smaller instance of the same pattern: this session has `mcp__claude-in-chrome__*` browser
tools available (confirmed in the environment's tool list) — the exact capability the 2026-07-16
brainstorm named as the unblock for the Verra registry search-API capture, which has otherwise been
stuck since 2026-07-12.

Given that, this brainstorm's shape is different from its predecessors: instead of proposing new
architecture, it front-loads **the two blockers that are provably no longer external**, then covers
the remaining architectural/product improvements in priority order below them.

---

## Improvement tracks (priority order)

### Track A — Run the proof (the actual next action, not a future one)

- **A1. Fix the self-judging redraft loop before running anything at scale.** The trust-layer push
  fixed self-judging in `prove`'s post-hoc scoring pass (PHASE-04, cross-judge preference order in
  `provider_scorecard.py`) but explicitly left `section_orchestrator.py`'s in-loop redraft judge
  unfixed — it still defaults to judging a provider's draft with that same provider. For a real
  provider this means unbounded real calls per section with no ceiling, which is exactly the failure
  mode the prior push's final report warned about and worked around with a bounded manual test instead
  of a real run. Mirror PHASE-04's cross-judge preference-order logic
  (`["anthropic", "openai", "claude-code", "ollama"]`, first available non-drafting provider, `demo`
  fallback) into the orchestrator's redraft path. This is a small, well-scoped fix with an obvious
  regression test (assert the judge provider passed to the redraft loop differs from the drafting
  provider when alternatives exist).
- **A2. Run `pdd-agent prove --project inegol --providers claude-code` at full scale.** This is the
  single highest-leverage action available to the project right now. It requires no new code (beyond
  A1), no procurement, no external dependency — the CLI is on `PATH` in the same environment that
  would run it. Pin `PDD_JUDGE_PROVIDER` (or pass `--no-judge`) per the final report's own
  recommendation until A1 lands, to keep the first full run's cost/time bounded and its scorecard
  honest. Expect real wall-clock cost: 36 sequential `claude -p` subprocess calls (see A4) — budget
  10–30+ minutes, not seconds.
- **A3. Run `--project rice` (or another non-WTE family) with the same command.** This is the test
  that actually validates the July-13 methodology-parametrization push's family-aware prompts and
  judge rubrics against a real model, not the demo provider. Every existing comparison
  (`compare_codex_vs_pipeline.py`, the 43-test methodology matrix) has run against `demo` or `noop`
  only — a real-model, non-WTE run is a genuinely new signal, not a repeat of prior verification.
- **A4. Consider parallelizing section drafting for real providers.** `SectionOrchestrator` drafts
  sections strictly sequentially (`grep` confirms no `ThreadPoolExecutor`/`asyncio` in
  `section_orchestrator.py`). That was invisible under `demo`/`noop` (near-instant) but is now a real
  cost: 36 sequential subprocess calls to `claude -p`, each with CLI startup overhead plus generation
  time, turns a "run the proof" task into a genuinely long-running one. A bounded worker pool (e.g.
  4–6 concurrent sections, independent sections have no data dependency on each other within a run)
  would cut wall-clock by roughly the same factor without changing any drafting logic — worth doing
  *before* A2/A3 if the first attempt turns out to take uncomfortably long, otherwise defer until it's
  proven to matter.
- **A5. Once A2/A3 produce real scorecards, run the Codex convergence comparison for real.** The
  existing `compare_codex_vs_pipeline.py` has only ever compared against demo-provider output. A
  real-model comparison is what actually settles the two-track question referenced in
  `docs/2026-06-15-tinh-track-vs-repo-comparison.md` — this is the first opportunity to answer it with
  real, not synthetic, evidence.

### Track B — Self-service the registry blocker (also newly unblocked, this session)

- **B1. Capture the Verra registry search API shape via the browser agent.** This session has
  `claude-in-chrome` tools available. One interactive search on `registry.verra.org/app/search/VCS`
  filtered by methodology (VM0051/VM0044/AMS-II.G), read via `read_network_requests`, gives
  `registry_download.py` the exact POST payload shape it needs to move from "manual-download mode" to
  live. This has been the stated blocker since 2026-07-12 (three pushes) and the 2026-07-16
  brainstorm named this exact capability as the unblock without anyone having the tool active in-session
  to use it. Throttling (`_throttle()`, already present) and download limits should stay as-is — this
  reads the same public search UI a human researcher would use, once, not a scrape.
- **B2. Populate `data/corpus/registry/{rice,biochar,cookstove}/` and swap golden tests from synthetic
  to registered values.** Direct follow-on to B1. Today the FTS5 index has WTE-bucketed corpus only,
  so a real rice/biochar/cookstove draft retrieves WTE excerpts for its RAG context — this is the third
  layer of the same WTE-shaped-assumption onion the last three pushes have been peeling (calc engine →
  prompt → corpus). It also lets `tests/test_rice_vm0051.py` and siblings test against real registered
  numbers instead of documented-but-synthetic fixtures.
- **B3. Re-run A3's rice proof after B2 lands, and diff retrieval quality before/after.** A concrete,
  measurable before/after: does grounding confidence (`HIGH`/`MEDIUM`/`LOW` assignment in
  `_assess_confidence`) improve once rice-specific corpus exists versus falling back to WTE excerpts?
  This is the first real evidence for or against the standing E3 deferral ("retrieval hybridization
  only if BM25 recall fails on non-WTE terminology") — right now nobody knows because there's no
  non-WTE corpus to test recall against.

### Track C — Small, concrete hardening (hours-scale, independent of A/B)

- **C1. `Redraft judge = drafting judge` regression test.** Once A1 lands, add the assertion the final
  report called for so this specific bug class (self-judging silently reappearing) can't regress
  unnoticed a second time — the same failure mode was found and fixed once already in `prove`'s
  post-hoc path (PHASE-04) and left the in-loop path unguarded.
- **C2. `claude-code` provider timeout tuning for a 36-section run.** `_DEFAULT_TIMEOUT_SECONDS = 300`
  per section is reasonable per-call but was never validated against a real multi-section batch. If A2
  surfaces timeouts or unexpectedly slow calls, `CLAUDE_CODE_TIMEOUT_SECONDS` is already
  environment-configurable — no code change needed, just document the observed real-world latency in
  the same runbook style as `docs/ollama-dress-rehearsal.md` once A2 actually runs.
- **C3. Per-run cost/latency telemetry surface (carried from the 2026-07-16 brainstorm's E1, now more
  urgent).** `TokenBudget` already records per-section tokens; the review-UI run-detail page and
  scorecard don't render it yet. Once A2/A3 start burning real (subscription-metered, not
  pay-per-token, but still finite) usage, seeing per-section cost/latency before the next run helps
  size future runs sensibly. Small now that the plumbing exists — this is a rendering task, not new
  data collection.
- **C4. Judge `use_llm=True` prompt calibration (carried from 2026-07-16's E2).** The structured-JSON
  judge prompt has never been calibrated against real model output. A2/A3 are the first opportunity to
  do this cheaply — the claude-code provider makes judge calibration keyless too, not just drafting.

### Track D — Product direction (unchanged in substance, re-sequenced behind A/B)

- **D1. Monitoring-Report (MR) product bet.** Carried intact from the 2026-06-22 and 2026-07-13
  brainstorms: MRs recur every issuance period and reuse ~80% of existing plumbing (corpus, calc,
  review, export, the evidence-registry flow built in the trust-layer push's PHASE-06). Still correctly
  sequenced *after* a real-model proof exists — a recurring-revenue pitch is much stronger with "here is
  a real Inegol draft a frontier model wrote" than with only demo-provider artifacts.
- **D2. Tinh onboarding.** `setup_service.py` exists; the loop (one-command setup → full review cycle
  on a demo run → friction log) has now survived *four* brainstorms unexecuted. The python-multipart
  CI bug (fixed 2026-07-16) would have been his first-contact experience — fresh install, immediate
  crash — which is now fixed and observed green. Nothing blocks this except someone actually running
  it; it doesn't depend on A or B and could happen in parallel.
- **D3. Service productization (auth, multi-user, persistent DB beyond JSON) stays deferred** until D2
  actually happens and a second real human hits the current single-user FastAPI + JSON-file design.
  Building this speculatively before anyone but the repo owner has used the review UI risks solving the
  wrong problem.
- **D4. Per-family `ProjectInput` schema split** — this decision (`DEC-004` in the prior plan) remains
  correctly deferred. `schemas/project_input.py` has no family-specific split today and nothing found
  in this session's review suggests urgency; the methodology-parametrization push proved family
  breadth is achievable without it (prompts/rubrics/tests are family-aware; the underlying schema is
  not, and that hasn't blocked anything yet).

---

## Recommended sequencing

1. **First (small, hours):** A1 (fix in-loop redraft self-judging) — the one piece of code standing
   between "safe to run the proof" and "already safe."
2. **The milestone:** A2 (`prove --project inegol --providers claude-code`, judge pinned/disabled),
   then A3 (`--project rice`). No procurement, no external dependency, no new code required beyond A1
   — genuinely runnable in this session or the next.
3. **Same-session opportunistic:** B1 (browser-agent registry capture) — independent of A, also
   genuinely unblocked right now by tools present in this environment.
4. **Following B1:** B2 (populate registry corpora, swap golden tests) → B3 (re-run rice proof, measure
   retrieval-quality delta).
5. **Parallel, anytime:** C1–C4 (small hardening) and D2 (Tinh onboarding) — none of these block or are
   blocked by A/B.
6. **After A2/A3/A5 produce real evidence:** D1 (Monitoring-Report pitch, now backed by a real-model
   artifact) with D3 revisited only once D2 actually happens.

## Single highest-leverage recommendation

**A1 + A2.** Every prior push in this repo's history has ended by identifying the next blocker and
building the thing to remove it — and the last two pushes both removed blockers (the keyless provider,
the honest proof harness) that then... sat there. The `claude` CLI is on `PATH` in the exact
environment analyzing this codebase right now. The only code change standing between "ready" and "run"
is a small, well-scoped self-judging fix in the redraft loop that mirrors a fix already made once
elsewhere in the same file family. After four pushes of "the milestone is next," the milestone is
achievable without waiting for anything else to happen first.

## Assumptions adopted (orchestrator unattended — noted per workflow rules)

- **ASM-01:** Treated `reports/` containing zero `prove-*.md` artifacts as confirming the full-scale
  proof has never run, consistent with the trust-layer push's own final report language ("the full
  command remains available as a deliberate next step").
  [Verify: re-check `reports/` and `data/runs/` for any new `prove` output before assuming this is
  still true in a later session.]
- **ASM-02:** Did not execute `pdd-agent prove` or any browser-agent capture during this analysis —
  the orchestrator's request was to brainstorm and save findings to `research/`, not to run a
  potentially long-running, subscription-metered command or take a browser action, on an unattended
  session's own initiative. A2/A3/B1 are flagged as the top next actions for a subsequent
  execution-scoped task, not performed here.
- **ASM-03:** Treated the 729-passed / 7-deselected test count observed this session as current
  ground truth, superseding the 686-collected figure in `activeContext.md` (which predates the full
  trust-layer push's final commits) and the 544-tests figure previously in `README.md` (already
  corrected by the trust-layer push itself).
- **ASM-04:** Assumed the `claude` CLI found on `PATH` in this session is authenticated and
  functional for headless one-shot use (`claude -p --output-format json`), consistent with it being
  the same CLI this orchestrator session runs under, but did not independently invoke it to verify —
  that verification is part of A2, not this brainstorm.
- **ASM-05:** Reaffirmed rather than re-litigated the D1/D2/D3/D4 product-direction items from the
  2026-07-16 brainstorm; no new evidence surfaced this session to change their sequencing beyond
  moving them behind the now-more-concrete A/B tracks.

## Suggested next step

Run `/plan` against this brainstorm, scoped to **Track A1 + A2 + A3** ("fix the redraft loop's
self-judging default, then run the first real-model multi-family proof") as the smallest push that
converts four pushes of "ready to run the moment X is available" into an actual completed proof
artifact — with **Track B1** as an equally-unblocked, independent parallel scope if the plan can
accommodate both without conflating them.
