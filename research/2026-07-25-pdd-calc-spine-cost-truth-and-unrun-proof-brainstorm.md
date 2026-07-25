---
title: "PDD-Auto Next Level: The Calc Spine, Cost Truth, and the Still-Unrun Proof"
date: "2026-07-25"
type: "brainstorm"
depth: "standard"
source_request: "Orchestrator-driven brainstorm (unattended): analyze current state, codebase, docs, architecture; propose improvements/features/refactors/architectural changes/optimizations"
slug: "calc-spine-cost-truth-and-unrun-proof"
---

# Brainstorm: PDD-Auto — The Calc Spine, Cost Truth, and the Still-Unrun Proof

## Where the project stands (2026-07-25, verified this session)

This is the sixth brainstorm/plan cycle on this repo (April → July 2026). The prior cycle's brainstorm
(`research/2026-07-23-pdd-run-the-proof-and-close-the-loop-brainstorm.md`) produced
`plans/2026-07-23-run-real-model-proof-plan.md` (4 phases). **Phases 01–02 landed**
(`4266be1` shared `judge_selection.py`, `aae79b3` in-loop redraft fix, `8631e40` final report).
**PHASE-03 (run the real-model proof) and PHASE-04 (capture the Verra registry API) have not run.**

Fresh evidence gathered this session — not copied from prior records:

| Claim | Verified how | Result |
|---|---|---|
| Test suite | `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` | **735 passed, 7 deselected, 82s** (README still says 686) |
| Working tree | `git status --short` | clean |
| `claude` CLI on PATH | `which claude` | `/c/Users/tukum/.local/bin/claude` |
| Proof artifacts exist | `ls reports/` | **zero** `prove-*.md` / `provider-scorecard.md` — still never run |
| Registry corpus | `ls data/corpus/registry` | **does not exist** — still manual-download mode |
| Production retrieval index | `ls data/index/` | **`corpus.fts.db` absent**; only `demo.fts.db` (3 docs) + a leaked `__nonexistent_test.fts.db` |
| Calc engines wired to pipeline | `grep -rn "set_calc_result" --include=*.py .` | **one hit — its own definition.** Zero callers anywhere. |
| Nested `claude -p` works | one real bounded call | **yes**, exit 0, 3.0s |
| Real per-section cost/latency | one real section draft through the actual prompt path | **36.1s, $0.1679** (details below) |

Two of these are new findings that change the shape of the next push. They are covered as Tracks A and B.

---

## Finding 1 — The calculation engines are an island (never named in five prior brainstorms)

`src/pdd_agent/calc/` is **1,796 lines** across ACM0022, VM0051 (rice), VM0044 (biochar), AMS-II.G
(cookstoves) and seven CDM tools, with golden tests. It is **not connected to anything**:

- `SectionOrchestrator.set_calc_result()` (`section_orchestrator.py:997`) has **zero callers** in
  `src/`, `scripts/`, or `tests/`.
- No CLI subcommand computes a calc result (`grep add_parser src/pdd_agent/cli.py` — 20 commands, none
  is `calc`).
- `provider_scorecard._run_one_provider` builds `SectionOrchestrator(...)` **without** `calc_result`
  (`provider_scorecard.py:~93`), so `prove` never injects calc either.
- `service/main.py:_execute_run` likewise constructs the orchestrator with no calc result.
- Therefore `_should_inject_calc()` (`section_orchestrator.py:219`) returns `False` on **every run ever
  executed**; the `[CALC: ...]` citation format and the "authoritative quantification values" prompt
  block (`_format_calc_injection`, lines 234–280) have never fired once.
- `docx_export.py:57` takes `calc_result` — always `None` in practice.
- `review/consistency.py:124` cross-checks draft numbers against a calc result — that branch is dead too.

Only the schema bridge `QuantificationInputs.from_calc_result()` is exercised, and only inside
`tests/test_calc_integration.py`. In every real artifact this repo has produced, **the quantification
numbers come from a human-authored or spreadsheet-mapped YAML and are transcribed into prose by the
provider** — nothing computes or recomputes them.

Two consequences worth stating plainly:

1. **The strongest differentiator is switched off.** A frontier model can write Verra-shaped prose. What
   it cannot do reliably is produce a traceable, methodology-faithful emissions calculation with a
   reproducible audit trail from feedstock tonnages to net tCO2e. That capability is fully built here
   and unplugged.
2. **`_format_calc_injection` is WTE-hardcoded** (its own docstring admits this: the BE_CH4/PE_EC/
   organic-waste-to-AD decomposition is `ACM0022CalcResult`-specific). If someone wires calc for a rice
   or biochar project without generalizing it, it raises `AttributeError` on the first Section 4 draft.
   This is the *fifth* layer of the WTE-shaped-assumption onion the last three pushes have been peeling
   (calc engine → prompt → judge rubric → corpus → **calc injection**).

## Finding 2 — Cost and token accounting for the keyless provider are wrong by ~25×

Two bounded real calls this session (total spend ~$0.25):

**Call 1 — trivial prompt** (`claude -p "Reply with exactly: OK" --output-format json`):
`duration 3.0s`, `total_cost_usd 0.0821625`, `usage: input_tokens 2, output_tokens 4,
cache_creation_input_tokens 12,614, cache_read_input_tokens 21,375`.

**Call 2 — a real drafting call**, using the repo's own `_build_prompt("1","1.1", …)` for the Inegol
project plus `system_prompt_for(...)`, invoked exactly as `ClaudeCodeProvider._call_cli` does:
prompt 1,101 chars / system prompt 247 chars → **36.1s wall-clock, `total_cost_usd 0.167898`**,
`input_tokens 9, output_tokens 1,053, cache_creation_input_tokens 25,346`, 2,026 chars of output.

What this proves:

- **`ClaudeCodeProvider` under-counts tokens ~25×.** It records `input_tokens + output_tokens`
  (`claude_code_provider.py:132-140`) = **1,062**, while the actual billed context was **≈26,400
  tokens** — it ignores `cache_creation_input_tokens` and `cache_read_input_tokens`, which are ~96% of
  the total. The `TokenBudget(max_tokens=500_000)` guard that `prove` sets is therefore effectively
  inert for this provider: a run would have to be ~470 sections long before it tripped.
- **It hardcodes `cost_usd=0.0`** and `configs/model_pricing.yaml` sets `claude-code: input 0.0 /
  output 0.0` on the stated assumption that "usage is billed via the operator's subscription, not a
  per-token API rate" — but the CLI itself returns `total_cost_usd` on every call, right there in the
  JSON the provider already parses. A scorecard from a `claude-code` run will print
  `estimated_cost_usd = $0.00` for a run that measurably costs real money.
- **The dominant cost is per-invocation harness overhead, not the PDD prompt.** The section prompt was
  9 input tokens; the invocation carried ~25k tokens of CLI system context. Cost is essentially
  *per call*, not per prompt — which makes call count, not prompt size, the thing to optimize.

**Extrapolated budget for PHASE-03, from measured numbers:**

| Scenario | Calls | Wall clock | Cost |
|---|---|---|---|
| Inegol, 36 sections, no redrafts | 36 | ~22 min | **~$6** |
| Inegol + rice, no redrafts | 72 | ~45 min | **~$12** |
| Worst case with max redrafts (3/section) | up to 288 | ~3 h | **~$48** |

Not prohibitive — but it is real money with a broken meter, and nobody has written that number down
before. (Helpful accident: after PHASE-02's fix, with no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` and no
Ollama, `resolve_judge_provider("claude-code")` falls through to **`demo`** — the deterministic
rule-based judge, zero extra model calls. So the first proof run's judge cost is $0 *and* the "real LLM
judge" is not actually exercised unless `PDD_JUDGE_PROVIDER=claude-code` is set explicitly. Worth
knowing before writing "judge validated" in a report.)

## Finding 3 — Real output has conversational preamble that goes straight into the DOCX

The measured call returned text beginning:

> "I'll draft a conservative summary paragraph for section 1.1.1 using the project-specific facts
> provided. Since no corpus examples are available, I'll mark elements that typically require
> verification. --- # 1.1.1 Summary Description of the Project …"

`ClaudeCodeProvider.draft_section` does `text = response.text[:max_chars]` (line ~210) with **no
preamble stripping**, so "I'll draft a conservative summary paragraph…" becomes the section body and
lands in the exported DOCX. Neither `demo` nor `noop` ever produced chatter, so no existing test covers
it. This is exactly the class of defect the unrun proof exists to surface — found here for ~$0.17.

Related, unverified but likely: headless `claude -p` runs the full agentic harness with default tool
permissions. For a pure text-generation provider, `--allowed-tools ""` (or equivalent) would cut both
latency and nondeterminism, and removes any chance of the drafting call touching the filesystem.

---

## Improvement tracks (priority order)

### Track A — Make the meter honest, then run the proof (revises last cycle's A2/A3)

- **A1. Fix `ClaudeCodeProvider` accounting before the first full run.** Record
  `input_tokens + output_tokens + cache_creation_input_tokens + cache_read_input_tokens` as
  `tokens_used`, and pass the CLI's own `total_cost_usd` through to `LLMResponse.cost_usd` /
  `TokenBudget.record()`. Small change, one file, fully testable against a captured JSON fixture (no
  network). Without it the run's own scorecard reports $0.00 and the budget ceiling can't stop anything.
  *Design note:* `TokenBudget` currently derives cost from `configs/model_pricing.yaml`; the cleanest
  shape is an optional `cost_usd` override on `record()` used when a provider reports authoritative cost.
- **A2. Strip provider preamble.** Add a small normalizer that drops leading conversational lines before
  the first heading/paragraph of substance (and trailing "Let me know if…" tails). Applies to any real
  provider, not just claude-code; test with the captured real output above as the fixture.
- **A3. Build the production index before the proof.** `data/index/corpus.fts.db` does not exist on this
  machine, so `get_retrieval_index()` silently falls back to `demo.fts.db` — **3 documents**. A "real
  model, corpus-grounded" proof run today would actually be grounded on the 3-doc demo subset while
  17 normalized docs sit in `data/corpus/normalized/`. Run `pdd-agent build-index` as a pre-flight step
  and record which index was used in the scorecard header (it currently records neither).
- **A4. Then run `pdd-agent prove --project inegol --providers claude-code`** with a real
  `PDD_MAX_COST_USD` ceiling set (now meaningful once A1 lands), followed by `--project rice`.
  Budget ~$6/project, ~22 min/project sequentially. Capture wall-clock and cost per section.
- **A5. Batch sections per CLI invocation (the big optimization, now measurable).** Cost and latency are
  dominated by ~25k tokens of per-invocation harness overhead, not by the ~300-token section prompt.
  Drafting 4–6 independent sections in one call, or switching the *drafting* path to the Anthropic API
  when a key exists, would cut cost roughly 5–10× and wall-clock similarly. This supersedes the prior
  brainstorm's A4 ("parallelize sections") as the better first move: parallelism buys wall-clock only,
  batching buys wall-clock *and* cost. Parallelism (bounded 4–6 workers) remains a good follow-on.
- **A6. Record real latency/cost in the scorecard and the review UI.** `ProviderScorecardRow` already
  carries `wall_clock_seconds`, `total_tokens`, `estimated_cost_usd` — with A1 they finally mean
  something. Surfacing per-section cost on the run-detail page is a rendering task, no new collection.

### Track B — Plug in the calc spine (the architectural bet)

The strategic reframe: **stop treating the LLM as the author of the PDD's numbers and make it the
narrator of numbers the engine computes.** Concretely:

- **B1. Add a `calc` dispatch layer.** `src/pdd_agent/calc/methodology.py` already defines a methodology
  interface; add `compute_for(project_input) -> CalcResult | None` that selects the engine from
  `technology.methodology_ids` (ACM0022 → WTE, VM0051 → rice, VM0044 → biochar, AMS-II.G → cookstove)
  and returns `None` when inputs are insufficient. One function, no new engines.
- **B2. Call it from the three entry points that build orchestrators** — `cli.draft`, `provider_scorecard._run_one_provider`,
  `service._execute_run` — passing the result to `SectionOrchestrator(calc_result=…)` and to
  `run_consistency_checks(...)` / `export_docx(...)`. The wiring already exists on the receiving side;
  this is connecting sockets, not building rooms.
- **B3. Generalize `_format_calc_injection` per family** before B2 reaches a non-WTE project, or it
  raises `AttributeError`. Cleanest shape: give each `*CalcResult` a `to_prompt_block()` (or a shared
  `components: dict[str, float]` field) so the orchestrator formats a generic result instead of naming
  ACM0022 fields. This also generalizes `review/consistency.py:_check_calc_result_internal`, which is
  ACM0022-specific for the same reason.
- **B4. Add `pdd-agent calc --input <yaml>`** printing the full component breakdown and writing a
  machine-readable result next to the run. This is the artifact a validator actually argues with, and
  it is the cheapest possible demo of the differentiator — no LLM call at all.
- **B5. Close the loop with `QuantificationInputs.from_calc_result()`**: when a project's YAML
  quantification disagrees with the engine, that is a *finding*, not a silent overwrite. The consistency
  layer already knows how to say this (`consistency.py:528`); it has just never had a calc result to say
  it about.

Sequencing note: B1–B3 are worth landing **before** A4's proof run, so the first real-model artifact
shows computed-and-cited numbers rather than transcribed ones. That is a materially stronger deliverable
for roughly a day of work.

### Track C — Distribution reality (blocks the onboarding item that has survived four brainstorms)

The tool cannot currently run outside a git checkout of this repo:

- `[tool.hatch.build.targets.wheel] packages = ["src/pdd_agent", "schemas"]` — the wheel therefore ships
  **no** `rules/`, `prompts/`, `configs/`, `templates/`, or `schemas/*.yaml` data files, all of which are
  loaded at runtime.
- `REPO_ROOT = Path(__file__).resolve().parents[3]` appears in `service/main.py`, `phase06/*.py`,
  `demo_setup.py`, `phase05/benchmark.py` — meaningless under a site-packages install.
- CWD-relative literals: `Path("configs/corpus_buckets/verra-wte-initial.yaml")` (`ingest/bucket.py:21`),
  `Path("data/corpus/normalized")` (`normalize.py:17`), `Path("data/corpus/raw/verra")`
  (`download.py:32`, `drive.py:239`), `Path("data/index/corpus.fts.db")` (`doctor.py:213`) — the CLI
  only behaves correctly when invoked from the repo root.

**C1.** Move runtime data (`schemas/*.yaml`, `rules/`, `prompts/`, `templates/`) under
`src/pdd_agent/` as package data and load via `importlib.resources`. **C2.** Introduce a single
`PDD_HOME` (default: CWD) for *writable* state (`data/`, `reports/`) and resolve all writes through one
helper instead of CWD-relative literals. **C3.** Add a CI job that `pip install .`s the built wheel into
a clean venv, `cd`s to a temp dir, and runs `pdd-agent doctor` + a `demo`-provider draft — this is the
regression test for "works on someone else's machine," and it is the actual precondition for the Tinh
onboarding item (D2 below) that has now survived five brainstorms unexecuted.

### Track D — Service parity and scale

- **D1. `claude-code` is unreachable from the web UI.** `service/main.py:_get_provider` handles
  `demo`/`noop`/`ollama`/`openai`/`anthropic` and falls through to `reason="unknown_provider"` → `demo`
  for anything else. The one real provider that works keylessly in this environment cannot be selected
  from the service. Three lines to fix; it is the difference between the review UI demoing synthetic
  prose and demoing a real draft.
- **D2. Run storage does not scale and has no retention.** `data/runs/` holds **1,130 JSON files /
  130 MB**; `/dashboard` and `/api/runs` both `glob("run-*.json")`, `stat()` every file, and call
  `_run_status()` per run on every page load. Add pagination + a lightweight index (or SQLite), and a
  `pdd-agent prune-runs --keep N` command. Nothing here needs a database migration story yet — but the
  dashboard is already doing 1,130 file reads per request.
- **D3. Async/atomicity.** `_execute_run` runs in a background task with JSON status files and a
  `sweep_orphaned_runs()` reaper. Fine for one user; the batch-approve race fixed in the last-but-one
  push is the sort of thing that recurs. Revisit only after a second human actually uses it (unchanged
  judgment from prior brainstorms).
- **D4. Auth stays deferred** until D2-the-onboarding (Track G) happens — consistent with prior cycles.

### Track E — Registry corpus and grounding (carried, still genuinely blocked-ish)

- **E1.** PHASE-04 of the current plan (capture the live Verra registry search API with browser
  devtools) is still open and still the unblock for rice/biochar/cookstove corpora. Browser tooling is
  available in this session type; the capture is one interactive search, read from the Network tab.
- **E2.** Until then, non-WTE drafts retrieve WTE excerpts (or, today, 3 demo docs) — and after A3+A4
  there will finally be a measurable before/after for grounding confidence, which is the evidence the
  standing "hybrid retrieval only if BM25 recall fails" deferral has always lacked.
- **E3.** Note the corpus is small in absolute terms: 17 normalized documents, ~420k words, WTE only.
  Whatever "corpus RAG moat" means here, it is 17 documents — worth being precise about in client-facing
  material.

### Track F — Hygiene and doc truth-sync (hours, do alongside anything)

- **F1. README is stale in ways that matter.** Line 5 says "686 tests collected" (actual: 735 passed /
  7 deselected). `llm/ollama_provider.py` is described as a "stub — registered but not yet a real HTTP
  client" (it is a real 230-line HTTP client since 2026-07-12). "Known Gaps" says the FastAPI service
  "forces the `demo` provider and disables corpus retrieval regardless of configuration" — no longer
  true; it resolves openai/anthropic/ollama with documented fallbacks. Stale known-gap lists are worse
  than none: they hide the *real* gaps (calc disconnection, claude-code unavailable in the service).
- **F2. `CLAUDE.md` points at `plans/2026-07-12-...` as "Current push"** — two plans behind.
  `activeContext.md` describes the 2026-07-13 plan as current and says "686 tests." Both should point at
  `plans/2026-07-23-run-real-model-proof-plan.md` with PHASE-03/04 open.
- **F3. Dead code:** the unused `_PROJECT_ALIASES` dict at `cli.py:188` (duplicate of the live one at
  `cli.py:684`) — the current plan's own Gotchas section flags it and deliberately skipped it.
- **F4. Test-artifact leak:** `data/index/__nonexistent_test.fts.db` is a committed-adjacent leftover
  from a test run creating a DB it meant not to create — same class as the `assumption-burden.md` leak
  fixed in `3fe256f`.
- **F5. Module naming debt:** `phase05/` and `phase06/` name plan phases, not domains (`benchmark`,
  `provider_scorecard` / `spreadsheet_mapper`, `vietnam_workflow`, `assumptions`). Cheap rename with
  deprecation shims; improves every future reader's first hour. Low priority, real cost over time.
- **F6. `SectionOrchestrator` is 999 lines** with prompt assembly, retrieval, calc formatting, judging,
  redrafting, review, and persistence in one class. Not urgent, but Track B adds to it — extracting
  prompt assembly (`_build_prompt`, `_format_*`, `_section_*`) into a `PromptBuilder` before B3 lands is
  the natural moment.

### Track G — Product direction (carried, re-sequenced behind A/B)

- **G1. Monitoring-Report (MR) product bet** — unchanged and still correctly sequenced after a real
  artifact exists. Note it gets materially stronger with Track B: MRs are overwhelmingly *numerical*
  recomputation against monitored parameters, which is precisely what the calc spine does.
- **G2. Tinh onboarding** — now correctly understood as *blocked by Track C*, not by willpower: a
  colleague cloning and `pip install`ing hits a tool that only works from the repo root and a wheel
  missing its own rules and prompts. Track C makes the onboarding loop worth running.
- **G3. Service productization / per-family schema split** — deferred, unchanged.

---

## Recommended sequencing

1. **Half a day:** A1 (token/cost truth) + A2 (preamble strip) + A3 (build the real index). All three
   are prerequisites for a *trustworthy* first proof, all are small, all are testable offline.
2. **One day:** B1 → B3 → B2 (calc dispatch, generalized injection, wiring at the three entry points) +
   B4 (`pdd-agent calc`). This is what makes the first real-model artifact worth showing.
3. **The milestone (~1 hour of wall-clock, ~$12):** A4 — `prove --project inegol` then `--project rice`
   with `claude-code`, judge left on its post-fix `demo` default. Write the findings doc.
4. **Then, informed by the numbers A4 produces:** A5 (batching) and A6 (surface cost/latency).
5. **Parallel, independent:** F1–F4 (doc truth-sync and hygiene — do it in the same commit as A1),
   D1 (claude-code in the service, 3 lines), E1 (registry capture).
6. **After Track C:** G2 (onboarding), then D2 (run-store scale) when a second human generates runs.

## Single highest-leverage recommendation

**Wire the calc engines into the pipeline (Track B), and fix the cost meter before the proof run
(Track A1).** The prior cycle correctly identified "run the proof" as the milestone, and it remains
the milestone — but this session's measurements change *what should be true before it runs*. Running it
today would produce an artifact whose numbers were transcribed rather than computed, whose grounding
came from a 3-document demo index, whose scorecard reported $0.00 for a ~$6 run, and whose section
bodies opened with "I'll draft a conservative summary paragraph…". Each of those is a half-day fix; all
four together are the difference between a proof that persuades and a proof that has to be re-run.

And of the four, the calc wiring is the one that changes what the product *is*. Four pushes have
improved how the model writes. The 1,796 lines that make the output arguable in front of a validator
have been sitting unplugged the whole time.

## Assumptions adopted (unattended session — noted per workflow rules)

- **ASM-01:** I spent ~$0.25 of real subscription usage on two bounded `claude` CLI calls (one trivial,
  one real drafting call) because the top recommendation of the last two cycles turns on cost and
  feasibility questions no one had measured. I judged this in scope for "analyze the current state"; I
  did **not** run the full `pdd-agent prove` (est. ~$6 and ~22 min per project), which remains PHASE-03
  of the existing plan and a deliberate operator action.
- **ASM-02:** The cost/latency extrapolations assume per-call overhead stays ~25k tokens and per-section
  latency ~36s. The measured section drafted with **zero** corpus examples (no index built); with 5
  excerpts injected, prompt tokens rise but per-call overhead still dominates, so the cost estimate
  should hold within ~±30%. [Verify against A4's actual scorecard.]
- **ASM-03:** I treat the calc-engine disconnection as unintentional rather than a deliberate design
  choice. Grounded in the code: `set_calc_result`, `_should_inject_calc`, the `[CALC:]` citation format,
  `docx_export(calc_result=...)`, and `consistency._check_calc_vs_project_input` all exist and are
  mutually consistent — an entire receiving apparatus with no sender. That reads as unfinished wiring,
  not intent.
- **ASM-04:** Track B recommends generalizing calc results via `to_prompt_block()` / a shared
  `components` mapping rather than per-family `if` branches in the orchestrator. Adopted as the
  conventional choice for four engines with different component vocabularies; a per-family formatter
  registry is an equally defensible alternative.
- **ASM-05:** Track C recommends package-data + `importlib.resources` + a single `PDD_HOME` over the
  alternative (keep repo-relative paths, document "run from repo root only"). Adopted because G2
  onboarding and any future deployment both depend on it, and because a wheel that omits its own rules
  and prompts will fail confusingly rather than loudly.
- **ASM-06:** Product-direction items (G1–G3) are reaffirmed rather than re-litigated; no evidence
  surfaced this session changes their substance, only their sequencing relative to Track C.
- **ASM-07:** I did not attempt the Verra registry browser capture (Track E1) — it is PHASE-04 of an
  open plan and an outward-facing network action better taken as a deliberate, attended step.

## Suggested next step

Run `/plan` against this brainstorm scoped to **A1 + A2 + A3 + B1–B4**, with **A4 (the proof run)** as
the closing phase of the same plan — i.e. amend rather than replace `plans/2026-07-23-run-real-model-proof-plan.md`,
whose PHASE-03/04 remain valid and unexecuted. Track F1–F4 should ride along in the first commit;
Track C deserves its own follow-on plan once the proof artifact exists.
