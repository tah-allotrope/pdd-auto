---
title: "PDD-Auto After the Reality Gap: Turnkey Proof, Multi-Family Intelligence, and the Monitoring-Report Bet"
date: "2026-07-13"
type: "brainstorm"
depth: "standard"
source_request: "Analyze current state and brainstorm what takes pdd-auto to the next level"
slug: "pdd-post-reality-gap-next-level"
---

# Brainstorm: PDD-Auto After the Reality Gap

## Where the project stands (2026-07-13)

The `2026-07-12-pdd-reality-gap-plan` is **complete** — all 6 phases, 606 tests passing (verified green this session, 87s), working tree clean. That push made the machine *real in code*: a real `OllamaProvider`, a thread-safe `RetrievalIndex` with the service's RAG amputation removed, provider opt-in behind cost ceilings, a real structured-JSON LLM judge, `pdd-agent scorecard`, a best-effort Verra registry downloader, and a rice VM0051 end-to-end pilot that flushed out 3 real bugs no WTE-shaped test had ever caught.

So the prior brainstorm's Tracks A–E are largely executed. What is left is the part that no amount of code can close by itself, plus a set of debts and product bets that the reality-gap push deliberately deferred.

**The four external blockers that survive (from the reality-gap final report):**
1. No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — the frontier-LLM drafting path has *still never run once*. This is the same blocker that has survived three consecutive "prove it real" pushes.
2. CPU-only dev hardware can't complete a 36-section Ollama run in reasonable time.
3. Verra registry's search API shape needs browser-devtools inspection before real corpora for rice/biochar/cookstove can be populated.
4. No real (non-synthetic) non-WTE prospect has been identified; the rice pilot is synthetic.

## Central diagnosis

The honest one-line status: **the code is real, the intelligence has never run, and the breadth is real everywhere except the two places the LLM actually reads.** Three compounding realities define the next level:

1. **The proof is still the whole game — and it is now a *packaging* problem, not a *code* problem.** Every acceptance-criteria checkbox that matters (VVB-desk-review-grade output, provider scorecard, redraft-loop behavior on nondeterministic text) is gated on a key that keeps not arriving. The highest-leverage engineering move left is to make the proof **turnkey**: the moment a key lands (or an hour of GPU time appears), a single command must run Inegol on frontier + local, judge it, diff providers, and emit the scorecard — with *zero* debugging. The reality-gap push got most of the way here (`docs/2026-07-12-provider-scorecard-checklist.md`); the remaining work is to collapse that checklist into one command and prove it end-to-end on Ollama so the frontier run is a model-string swap.

2. **Breadth is calc-real but prompt-blind.** This is the sharpest *new* finding of this analysis. The schema (`RiceCultivationParams`, `BiocharProductionParams`, `technology_type` literals) and the calc engines (`rice_vm0051`, `biochar_vm0044`, `cookstove_amsiig`) are genuinely multi-family. But the two artifacts the LLM actually consumes are still single-family:
   - `prompts/section_draft_v2.md` opens: *"You are a technical writing assistant specializing in Verra VCS carbon credit PDDs **for waste-to-energy projects**"* and its entire Anti-Hallucination Protocol cites `[CALC: ...]` as *"the **ACM0022** calculation engine."*
   - `rules/verra/judge_rubric.yaml` is `bucket: "verra-wte-initial"`, and `NO_FABRICATED_FACTS` hardcodes *"Quantitative claims in Sections 1.10 and 4.x must match ProjectInput and the **ACM0022** calc engine."*

   The rice pilot only worked because it ran the *demo* provider (which got a rice-specific text template bolted on). A **real-LLM rice draft would be prompted as a WTE project and judged against a WTE rubric.** The breadth claim is therefore half-true: real for arithmetic, unproven for prose. Making the prompt + rubric methodology-parametrized is the true "make breadth real for the intelligence layer" — and it's a prerequisite for any real non-WTE proof.

3. **The product surface is a single-user demo, and the recurring-revenue product hasn't been started.** The FastAPI service is real now but is single-user, unauthenticated, in-process background tasks, with a *known-unresolved* batch-approve-all defect logged in the rice pilot findings. And a PDD is a one-time artifact; **Monitoring Reports** — which recur every issuance period and reuse ~80% of this plumbing — remain entirely unbuilt (the only `monitoring` hits in `src/` are calc-engine method names, not an MR pipeline).

The next level is: **(A) make the proof turnkey and multi-family so it survives the key/hardware unblock without a debugging session; (B) pay the architectural debts that breadth is now actively straining; (C) place the Monitoring-Report bet that turns a one-shot consulting tool into a recurring product.**

---

## Improvement tracks (priority order)

### Track A — Turnkey, multi-family proof (highest leverage; unblocks the moment keys/GPU arrive)

- **A1. One-command provider scorecard.** Collapse `docs/2026-07-12-provider-scorecard-checklist.md` into `pdd-agent prove --project inegol` that runs the draft on every configured+available provider (ollama now; +openai/anthropic when keyed), judges each with the real LLM judge, diffs them, and writes a head-to-head scorecard with per-provider cost from `TokenBudget`. `phase05/provider_scorecard.py` already exists — wire it to a single CLI verb and make "no key present" a graceful skip, not an error. *Rationale: the last three pushes each rediscovered the run-mechanics; encode them once so the frontier run is `export ANTHROPIC_API_KEY=... && pdd-agent prove`.*
- **A2. Methodology-parametrized drafting prompt.** Split `section_draft_v2.md` into a methodology-neutral core + per-family overlays (WTE/ACM0022, rice/VM0051, biochar/VM0044, cookstove/AMS-II.G) selected by `technology_type`. The `[CALC: ...]` authority, the fabricated-facts protocol, and the "which sections carry the quantification" mapping all need to become family-aware. **This is the single most important non-key-gated change** — without it, the frontier-key proof can only ever validate WTE.
- **A3. Methodology-parametrized judge rubric.** Same treatment for `judge_rubric.yaml`: a shared skeleton with family-specific `NO_FABRICATED_FACTS` bindings (rice quantification lives in different subsections than WTE's 1.10/4.x). The judge already reads a rubric file; make rubric selection a function of the project's methodology.
- **A4. Ollama full-draft dress rehearsal on adequate hardware.** The code path is verified-correct-under-failure but has never *completed* a 36-section local run (blocker #2). Rent an hour of GPU (or a bigger box) and complete one full Inegol + one full rice run through Ollama. This is the cheapest way to shake out nondeterministic-output bugs (marker parsing, redraft-loop convergence, budget accounting) **before** spending frontier dollars — and it exercises A2/A3 for real. Assumption ASM-01: a few dollars of cloud GPU is acceptable; if not, a colleague's gaming PC works.

### Track B — Architectural debts breadth is now straining (do soon; each compounds)

- **B1. Evidence registry: from static field to living flow.** `EvidenceRegistry`/`EvidenceItem` exist on `ProjectInput` and are validated at the export gate (`docx_export.py:_check_evidence_registry`) and by the judge — but nothing *populates* it from intake, injects registered `[E###]` IDs into the drafting prompt, or auto-renders it as a DOCX appendix from a single source of truth. Close the loop: register evidence at intake (`ingest/extract.py` + `phase06/spreadsheet_mapper.py`), pass the registry into the section prompt so the LLM cites real IDs, validate in the judge (already partial), render the appendix from the registry object. This is the strongest anti-hallucination + audit-trail feature the product can *sell*, and it's ~60% built.
- **B2. Split the three 800-line modules.** `cli.py` (814), `service/main.py` (840), `agent/section_orchestrator.py` (854), `export/docx_export.py` (879) are all past the point where a single file earns its length. `cli.py` especially: ~17 subcommands in one argparse blob. Move each command's handler into the module that owns the behavior; keep the parser thin. Do it opportunistically when touching a command, not as a big-bang.
- **B3. Methodology-parametrized *test matrix*.** There is currently **zero `pytest.mark.parametrize` in the suite** and every fixture is WTE-shaped — which is *exactly why* the rice pilot found 3 bugs the 601-test suite missed. Add a family dimension: parametrize the core draft→review→consistency→export path over `{wte, rice, biochar, cookstove}` fixtures so WTE-shaped assumptions fail loudly in CI instead of during the next pilot. This is the systemic fix for the class of bug the rice pilot represented.
- **B4. Config-driven model pricing.** `_DEFAULT_PRICING` in `llm/budget.py` is hardcoded and will drift as model prices change (and Claude/OpenAI model IDs churn — this session's context already names newer models). Move it to a YAML alongside the rubric; have `pdd-agent doctor` warn when a configured model has no pricing entry. Cheap insurance against silently mispricing a real run.
- **B5. Fix (or formally triage) the batch-approve-all service defect.** The rice pilot logged that "a bulk approve-all loop over the remaining 32 sections did not fully apply — a batch/state-machine interaction not investigated further." A human reviewing 36 sections in the web UI *will* hit this. It's the core loop of the sellable review workflow. Reproduce it with a test, then fix the state-machine race.

### Track C — The Monitoring-Report bet (turns a one-shot tool into a recurring product)

- **C1. Prototype an MR pipeline on shared plumbing.** A PDD is drafted once; a Monitoring Report recurs every issuance/verification period and reuses the corpus, calc engines, DOCX templating, review workflow, and evidence registry almost wholesale. The delta is: a monitoring-period data intake (metered/measured values vs. the PDD's *ex-ante* estimates), a variance/quantification section, and MR-specific templates. Tinh's Drive already has joint PD/MR reference docs (Bergama). This is the clearest path from "expensive one-time deliverable" to "recurring-revenue product," and it should start with **one** real MR reusing the existing machine, not a new subsystem. *Recommendation: scope this as the next major plan once the real-LLM PDD proof lands — it's the highest-value strategic direction, but sequencing it before the proof would build MR on unproven output.*
- **C2. Per-run cost + latency telemetry.** There is no telemetry today. Before real runs start burning real dollars, roll per-section token/cost/latency into the scorecard and surface it on the dashboard. Needed to keep the "low hundreds $/month" budget claim honest, and it's the substrate MR economics will need too.

### Track D — Operational hardening (cheap, high-leverage for the two-person handoff)

- **D1. Add CI (there is none).** No `.github/workflows`. A two-person tool about to be handed to Tinh, with a 606-test suite that takes 87s and a hard constraint that "tests never require keys/network/Ollama," is the *ideal* CI candidate: a single GitHub Actions job running `pytest -m "not corpus"` + `ruff` on every push. This is the highest value-per-hour item in the entire brainstorm and should probably be done first, before anything else — it protects every other change here.
- **D2. Finish the Tinh onboarding loop (never actually run).** `setup_service.py` exists; the convergence doc names the onboarding but it hasn't happened. Have Tinh run the one-command setup, complete one full review cycle on a demo Inegol run, and log friction as issues. His friction list should drive the Track-B5/service backlog rather than guesswork.
- **D3. Swap synthetic golden-test values for registered ones** once B-unblocked corpora land (blocker #3). The rice/biochar/cookstove calc engines assert synthetic-but-documented numbers; replacing them with values from real registered PDDs is what upgrades "golden test" from "we agree with ourselves" to "we match a validated project."

### Track E — Strategic / opportunistic (post-proof)

- **E1. Run `compare_codex_vs_pipeline.py` on a *real-LLM* Inegol draft** as the actual two-track convergence test. Every prior comparison was pipeline-*demo* vs. Codex; the comparison that settles the two-track question is pipeline-with-real-LLM vs. Tinh's Codex output.
- **E2. Registry downloader → live mode.** `ingest/registry_download.py` is best-effort with a manual-download fallback; the devtools inspection of Verra's search API (blocker #3) upgrades it to real, which unlocks C-track corpora and D3.
- **E3. Revisit the per-family schema split (DEC-004) only on the *second* real non-WTE project.** The rice pilot re-confirmed no-go: the wide schema with three semantically-WTE-but-technically-satisfiable required fields (`waste_type`, `annual_waste_throughput`, `installed_capacity_mw`) handled rice fine with placeholders. Hold this until a real prospect's data makes the wide schema genuinely painful, not merely imprecise. Premature discriminated-union abstraction across families that haven't drafted for real is the bigger risk.

---

## Recommended sequencing

1. **Immediately (hours):** D1 (CI) — protect everything else first.
2. **This week (non-key-gated, unblocks the proof's breadth):** A2 + A3 (parametrize prompt + rubric) → B3 (parametrized test matrix, which validates A2/A3) → A1 (one-command scorecard).
3. **On GPU access:** A4 (Ollama full-draft dress rehearsal on Inegol + rice) — the cheap rehearsal before frontier dollars.
4. **On keys arriving:** A1 run for real → the VVB-grade Inegol proof → E1 convergence comparison. This is still *the* milestone; it has been the milestone for three pushes.
5. **In parallel, debt paydown as touched:** B1 (evidence registry flow), B2 (module splits), B4 (pricing YAML), B5 (batch-approve fix), D2 (Tinh onboarding).
6. **After the proof lands:** C1 (Monitoring Report prototype) + C2 (telemetry) as the next major plan — the strategic pivot from one-shot deliverable to recurring product.

## Single highest-leverage recommendation

If only one thing gets done: **D1 (CI) this hour, then A2+A3+B3 this week** — parametrize the prompt, the rubric, and the tests over methodology families. That is the one body of work that (a) needs no API key, (b) directly determines whether the imminent frontier-key proof validates *breadth* or only *WTE*, and (c) closes the exact "the LLM only ever sees WTE" gap that this analysis newly surfaced. Everything else waits on a key, a GPU, or the proof — this doesn't.

## Assumptions adopted (orchestrator unavailable — noted per workflow rules)

- **ASM-01:** A few dollars of cloud GPU (or a colleague's GPU machine) is an acceptable way to clear hardware-blocker #2 for A4; treated as a soft, self-serviceable blocker rather than an external one.
- **ASM-02:** API keys remain the binding external blocker for the frontier proof; the entire Track-A design assumes the goal is to make the key-arrival a *model-string swap*, not a debugging session.
- **ASM-03:** The Monitoring-Report adjacency (Track C) is the right *next* strategic bet, but is correctly sequenced *after* the real-LLM PDD proof — building MR on unproven drafting output would repeat the "productize before proving" trap (ALT-001 from the July-5 brainstorm).
- **ASM-04:** The prompt/rubric WTE-hardcoding is a genuine gap and not intentional scoping — confirmed by reading `prompts/section_draft_v2.md` and `rules/verra/judge_rubric.yaml` directly; both name WTE/ACM0022 in load-bearing instructions, and the rice pilot only sidestepped this by using the demo provider.
- **ASM-05:** Verra's registry JSON API is still publicly reachable without auth (assumed from prior brainstorms; verify with devtools before E2).
- **ASM-06:** No new methodology *families* are added before rice/biochar/cookstoves draft for real via a live LLM; breadth investment goes to making existing breadth reach the intelligence layer (A2/A3), not going wider.

## Suggested next step

Run `/plan` against this brainstorm. Recommended first plan scope: **Track A2+A3+B3 + Track D1** — "make breadth real for the LLM path, under CI" — as the non-key-gated push that readies the frontier-key proof to validate all four families at once.
