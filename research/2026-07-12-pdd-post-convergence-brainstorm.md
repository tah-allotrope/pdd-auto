---
title: "PDD-Auto Post-Convergence: Close the Reality Gap"
date: "2026-07-12"
type: "brainstorm"
depth: "standard"
source_request: "Analyze current state and brainstorm what takes pdd-auto to the next level"
slug: "pdd-post-convergence"
---

# Brainstorm: PDD-Auto Post-Convergence — Close the Reality Gap

## Where the project stands (2026-07-12)

The July 5 "Next Level" push (`plans/2026-07-05-pdd-next-level-plan.md`) is implementation-complete as of commit `7e0b47d`:

- **Providers:** OpenAI (`gpt-4o` default), Anthropic (`claude-sonnet-5` default), Ollama — all implemented, none ever executed against a real API. Per-run cost ceiling in `llm/budget.py`.
- **Quality machinery:** judge rubric (`rules/verra/judge_rubric.yaml`), capped redraft loop in `agent/section_orchestrator.py`, tiered export gate in `export/docx_export.py`.
- **Service:** FastAPI app + Jinja2 section-review UI (`src/pdd_agent/service/`), 12 API tests passing.
- **Breadth:** pluggable methodology interface + calc engines for ACM0022, AMS-II.G, VM0051, VM0044 with golden tests (synthetic values).
- **Tests:** 541 test functions; last recorded full run 534 passed, 7 corpus-marked deselected.

Standing blockers from `docs/2026-07-05-convergence.md`: no API keys in the environment, Seraphin greenfield data externally blocked, `ingest/registry_download.py` is a stub, `compare_codex_vs_pipeline.py` never run against Tinh's refreshed artifacts.

## Central diagnosis

Three months of building have produced a mature *skeleton* around an intelligence layer that has still **never once run for real** — and, more subtly, the new service **cannot reach the real path even if keys arrived today**. Three compounding gaps:

1. **The proof gap.** Every artifact ever produced (Soc Son, Inegol, Vietnam) is deterministic `demo`/`noop` output. The VVB-desk-review-grade claim (DEC-002 from the July 5 brainstorm) remains unverified.
2. **The service reality gap.** `service/main.py:110-116` *hard-forces* the demo provider regardless of `PDD_SERVICE_PROVIDER`, and lines 43-45 *disable corpus retrieval entirely* (monkeypatched to return `[]`) to dodge SQLite thread affinity. So the surface being handed to Tinh as "the converged tool" drafts without RAG and without any LLM — it demos the review workflow, not the product.
3. **The corpus reality gap.** Three of four methodology families have calc engines and rules but zero corpus documents, and their golden tests assert synthetic numbers. The "breadth" exists in `calc/` but not in the drafting pipeline.

The next level is not more features — it is **making the existing machine real**, then hardening the service into something two people actually use daily.

## Improvement tracks (priority order)

### Track A — Unblock and run the real-LLM proof (highest value, partially key-independent)

- **A1. Exercise the full real path via Ollama *now*, before keys arrive.** `OllamaProvider` is implemented and registered, costs nothing, and needs no keys. Run the Inegol draft end-to-end with a local model (e.g. an 8-13B instruct model) to shake out prompt-assembly bugs, `[MISSING]`/`[INFERENCE]` marker parsing, judge-loop behavior, and budget accounting on real nondeterministic output. Quality will be poor — that's fine; the goal is that when frontier keys land, the run is a model swap, not a debugging session. This converts a hard external blocker into a soft one.
- **A2. Add `.env` loading + a `pdd-agent doctor` command.** Keys are read only from the OS environment (`cli.py:36`); there is no dotenv loader anywhere in `src/`, yet the convergence doc says keys are "not in the environment or `.env`" — a `.env` file would silently do nothing today. Add `python-dotenv` (or a 10-line loader), and a `doctor` subcommand that validates keys, `anthropic`/`openai` imports, LibreOffice, `gws`, and index presence with green/red output. This is the difference between "send Tinh a key" and "debug Tinh's environment over chat."
- **A3. Tune and enable the real LLM judge.** `review/judge.py` defaults to `use_llm=False`; the "LLM judge" in every run so far is regex/rule scoring. Write and test the actual judge prompt (rubric → structured findings JSON), with the deterministic scorer retained as the offline fallback and as a sanity cross-check. Per the July 5 decisions, use a cheap tier (e.g. `claude-haiku-4-5`) for iteration and a frontier tier for sign-off runs — the pricing table in `llm/budget.py` already carries both.
- **A4. Automate the provider scorecard.** Extend `phase05/benchmark.py` so a single command runs Inegol on openai + anthropic + ollama, judges each, and emits the head-to-head scorecard (DEC-004). Record per-provider cost from `TokenBudget` in the scorecard.

### Track B — Make the service real (the Tinh handoff depends on this)

- **B1. Fix retrieval thread-safety properly instead of amputating RAG.** The right fix is small: give `RetrievalIndex` a per-thread connection (`threading.local()` or `sqlite3.connect(..., check_same_thread=False)` with a lock — reads are safe under WAL). Then delete the module-level monkeypatch in `service/main.py:43-45`. Until this lands, the service drafts corpus-blind, which guts the pipeline's core differentiator in the exact surface being demoed.
- **B2. Allow real providers in the service behind an explicit opt-in.** Replace the hard force-to-demo with: `PDD_SERVICE_PROVIDER=anthropic` honored *only if* the matching API key is present *and* `PDD_MAX_COST_USD` is set, else fall back to demo with a visible dashboard banner. The budget ceiling already exists; the service just refuses to use it.
- **B3. Replace import-time monkeypatching with dependency injection.** `service/main.py:56-88` rebinding `DraftRun.save` / `ReviewStateStore.save/load` at import is a landmine: importing the service module mutates persistence behavior process-wide (including in any test that transitively imports it). Thread `runs_dir` through as an explicit parameter or a small `PersistenceConfig` object. Same instinct applies to the retrieval monkeypatch (B1).
- **B4. Durable background runs.** Drafting executes in FastAPI `BackgroundTasks` — in-process, lost on reload/crash, invisible if the process dies mid-run. A minimal fix: a `runs` status table (or a `status.json` per run) written at start/finish, plus a startup sweep that marks orphaned "running" runs as failed. No Celery needed at this scale.
- **B5. Surface judge results and run cost in the UI.** The section API already returns judge findings (`main.py:525`); make sure the section-review template renders findings, redraft history, and per-run estimated cost — that audit trail is the sellable artifact per DEC-009.
- **B6. Run the actual Tinh onboarding loop.** The convergence doc names it but it hasn't happened: Tinh runs `setup_service.py` on his machine, completes one full review cycle on a demo Inegol run, and friction gets logged as issues. Do this *before* investing in more service features — his friction list should drive the service backlog.

### Track C — Make the corpus real (breadth is currently calc-only)

- **C1. Implement `ingest/registry_download.py`.** Verra's registry (registry.verra.org) exposes a public JSON search API used by its own UI; a resilient client filtered by methodology (VM0051, VM0044, AMS-II.G, ACM0022) with rate limiting and a local manifest would replace the stub. This unlocks: real corpora for the three new families, and replacing synthetic golden-test numbers with registered-PDD values (convergence-doc remaining-work items 4 and 2's prerequisite).
- **C2. End-to-end draft for one non-WTE family.** The new families have engines and rules but have never been drafted. Build a realistic VM0051 rice `ProjectInput` (synthetic but grounded in a registered rice PDD once C1 lands), run it through draft → judge → review → export, and fix what breaks. This de-risks the Vietnam rice prospect (the designated Seraphin substitute) before a real prospect shows up, and exercises the section schema's assumed WTE shape (see D2).
- **C3. Corpus bucketing rules for the new families.** `configs/corpus_buckets/` only knows WTE keywords; each family needs its own bucket config before `build-index` can serve family-scoped retrieval.

### Track D — Architecture debts worth paying soon (not urgent, but compounding)

- **D1. Split `cli.py` (749 lines, argparse, ~17 subcommands).** Move each command's handler into the module that owns the behavior (or a `cli/` package); keep the parser thin. Do this opportunistically when touching commands, not as a big-bang refactor.
- **D2. Pressure-test `ProjectInput` against non-WTE families.** The schema was born WTE-shaped and extended for Inegol; rice hydrology and cookstove fleet parameters live as extensions. Before the rice run (C2), decide: one wide schema with optional family blocks (simplest, current trajectory) vs. a discriminated union per family. Recommendation: keep the wide schema until the second real non-WTE project, then revisit — premature abstraction across families that haven't been drafted yet is the bigger risk.
- **D3. Unify the evidence registry.** Tinh's `[E###]` evidence-citation discipline is enforced at export-gate level, but there is no single evidence registry object flowing intake → draft → judge → DOCX appendix. Making evidence IDs first-class (registered at intake, cited in prompts, validated by the judge, rendered as an appendix) is the strongest anti-hallucination and audit-trail feature the product can claim.
- **D4. Config-driven model pricing.** `_DEFAULT_PRICING` in `llm/budget.py` is hardcoded and will drift; move it to a YAML alongside the rubric, and have `doctor` (A2) warn when a configured model has no pricing entry.

### Track E — Repo hygiene (cheap, do immediately)

- **E1. The working tree has 551 uncommitted deletions** (the old `ref/PDD staff test-20260520...` snapshot) plus untracked `ref/PDD staff April 2026/` and `ref/PDD staff May 2026/` folders. Decide and commit: the deletions look like an intentional snapshot swap, but half-applied state like this invites accidental `git checkout .` data loss. Recommendation: commit the deletion, move bulky reference snapshots out of git (Drive) and `.gitignore` `ref/`, keeping only the comparison docs in-repo.
- **E2. Commit the strays:** `research/2026-07-05_pdd-next-level-brainstorm.md` (the strategy doc of record is untracked!), `uv.lock`, `reports/assumption-burden.md`; delete `tmp_wte_model.xlsx` from the root if it's a scratch copy of the cached workbook.
- **E3. Add a project `CLAUDE.md`.** The user's global workflow expects one (tech stack, test commands, provider constraints, artifact contracts); every session currently rediscovers this from README + activeContext. Ten lines would pay for themselves weekly. Same for a seed `lessons.md`.
- **E4. README refresh** (convergence-doc remaining-work item 5): still says "204 tests," omits the service quickstart, the judge, the calc breadth, and the Anthropic provider.

### Track F — Strategic / product opportunities (post-proof)

- **F1. Run `compare_codex_vs_pipeline.py` on Inegol as the convergence test** once a real-LLM Inegol draft exists — pipeline-with-real-LLM vs. Tinh's Codex output is the comparison that actually settles the two-track question (the May 21 comparison was pipeline-demo vs. Codex).
- **F2. Monitoring Reports as the adjacent product.** A PDD is drafted once; monitoring reports recur every issuance period and share ~80% of this plumbing (corpus, calc engines, DOCX templating, review workflow). Once one real PDD is proven, MR generation is the natural revenue-recurring extension — and Tinh's Drive folder already contains joint PD/MR reference documents (Bergama).
- **F3. Per-run cost/latency telemetry** rolled into the scorecard and dashboard — needed anyway to keep DEC-012's "low hundreds $/month" honest once real runs start.

## Recommended sequencing

1. **Week 1:** E1-E4 (hours, not days) + A1 (Ollama real-path shakeout) + A2 (`.env` + `doctor`).
2. **Week 1-2:** B1-B3 (service fixes: retrieval, provider opt-in, de-monkeypatch) — small diffs, big honesty gain.
3. **On keys arriving:** A3-A4 (real judge + provider scorecard) → the Inegol VVB-grade proof → F1 convergence comparison.
4. **Parallel track:** C1 registry downloader → C3 buckets → C2 rice end-to-end → golden tests on registered values.
5. **Then:** B6 Tinh onboarding loop; D-track debts as touched; F2 only after the proof.

## Assumptions adopted (orchestrator unavailable — noted per workflow rules)

- **ASM-01:** API keys remain the binding external blocker; nothing here waits on them except A3/A4 and the proof itself. Ollama (A1) is assumed installable on the user's Windows machine.
- **ASM-02:** The `ref/` deletions in the working tree are an intentional snapshot replacement (April/May 2026 folders supersede the May 20 test snapshot), not an accident — but I did not commit anything; E1 flags it for an explicit decision.
- **ASM-03:** Verra's registry JSON API is still publicly reachable without auth (true as of knowledge cutoff; verify before building C1).
- **ASM-04:** Tinh's role as expert reviewer (DEC-013) still holds; B6 assumes his availability.
- **ASM-05:** No new methodology families are added before rice/biochar/cookstoves have drafted at least once; breadth investment goes to making existing breadth real, not wider.

## Suggested next step

Run `/plan pdd-reality-gap` against this brainstorm to produce the phased implementation plan (Tracks E+A first).
