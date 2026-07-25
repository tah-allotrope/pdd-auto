---
title: "PDD-Auto Next Level: Auditing the Freshly-Wired Calc Spine, and the Table-Shaped Deliverable Nobody Is Building"
date: "2026-07-25"
type: "brainstorm"
depth: "standard"
source_request: "Orchestrator-driven brainstorm (unattended): analyze current state, codebase, documentation, architecture; propose improvements, features, refactors, architectural changes, optimizations"
slug: "calc-audit-and-table-shaped-deliverable"
supersedes_context: "research/2026-07-25-pdd-calc-spine-cost-truth-and-unrun-proof-brainstorm.md"
---

# Brainstorm: PDD-Auto — Auditing the Calc Spine, and the Table-Shaped Deliverable

## Scope note

This is the **seventh** brainstorm cycle on this repo (April → July 2026), and the second dated
2026-07-25. The earlier one today
(`research/2026-07-25-pdd-calc-spine-cost-truth-and-unrun-proof-brainstorm.md`) produced
`plans/2026-07-25-calc-spine-and-cost-truth-plan.md`, whose PHASE-01…05 **landed in `47a4faf`**.
That cycle's central recommendation — "wire the calc engines into the pipeline" — is done at the
input end.

This brainstorm therefore does something the prior cycles could not: it **audits the output of the
newly-connected calc spine** against the four project configs that actually exist. That audit is
where the new material is. Everything below marked "verified this session" was re-derived from the
repo today, not carried forward from prior records.

---

## Where the project stands (verified 2026-07-25, this session)

| Claim | Verified how | Result |
|---|---|---|
| Test suite | `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` | **752 passed, 7 deselected, 94s** — matches README |
| Working tree | `git status --short` | clean, HEAD = `47a4faf` |
| Calc wired to entry points | `grep -rn compute_for src` | **yes** — `cli.py:519`, `provider_scorecard.py:104`, `service/main.py:350` |
| Calc reaches the DOCX | read `docx_export.py:54,155,192` | **no** — `check_export_gate` takes `calc_result`; `export_run_to_docx` has no such parameter and never forwards one |
| Calc persisted in the run | `DraftRun.to_dict()` (`provider.py:316`) | **no calc field** — result is ephemeral |
| Engine vs. declared numbers | ran `pdd-agent calc` on all 4 configs | **−34% disagreement on both WTE projects** (below) |
| Flagship proof project computable | `pdd-agent calc --input configs/demo/inegol_project_input.yaml` | **returns None** — no grid emission factor |
| Verra structured tables in output | `python-docx` scan of `examples/example-inegol-demo.docx` | **37 tables = 36 × "Confidence \| HIGH" + 1 cover.** Zero Verra content tables |
| `structured_content` producers | `grep -rn structured_content src scripts tests` | **zero** — declared and serialized, never set |
| Preamble stripper safety | direct call on a legitimate 2-subsection body | **silently truncated 135 of 209 chars** (repro below) |
| Production retrieval index | `ls data/index/` | **`corpus.fts.db` absent**; only `demo.fts.db` (233 rows) vs 17 normalized docs |
| Registry corpus | `ls data/corpus/registry` | still does not exist |
| Proof artifacts | `ls reports/ \| grep prove` | still **zero** — the real-model proof has never run |
| Run store | `ls data/runs \| wc -l`, `du -sh` | **1,315 files / 139 MB**, glob-scanned per dashboard request |
| Local interpreter | `pdd-agent doctor` | **Python 3.13.12** — a version CI (3.11/3.12) never tests |

Five of these are new findings. They are Findings 1–5 below.

---

## Finding 1 — The calc spine is plugged in at the front, but not out the back

`47a4faf` connected `compute_for()` to the three orchestrator construction sites. The result now
flows: **ProjectInput → engine → Section-4 prompt → consistency check → discarded.**

It does not flow anywhere else, and the reason is structural rather than an oversight in the wiring:

- **`DraftRun.to_dict()` has no calc field** (`llm/provider.py:316–341`). The calc result lives only
  in `SectionOrchestrator._calc_result` for the lifetime of the process.
- **`check_export_gate()` accepts `calc_result`** (`docx_export.py:57`) and forwards it to
  `check_quantitative_consistency` (line 84). Its only production caller,
  `export_run_to_docx` (line 192), calls it as
  `check_export_gate(run_data, project_input=project_input, force=force)` — **no `calc_result`**.
  `export_run_to_docx` does not have the parameter at all (signature at line 155), so none of its
  six production callers (`cli.py:715`, `review_package.py:111`, `benchmark.py:553`,
  `vietnam_workflow.py:91`, `service/main.py:880`, `scripts/run_inegol_demo.py:74`) could pass one.
  They also could not supply it if it existed: export runs from a saved `run_id` in a separate
  command invocation, and the calc result was never written to disk.
- **`pdd-agent calc --output` writes a JSON** — but it is not associated with any run, so nothing
  downstream can find it.

So the audit trail that justifies the product — "here is the number, here is the formula reference,
here is the CDM tool that produced it" — reaches the language model's prompt and then evaporates
before it reaches the human who has to defend it. **The validator never sees the calculation.**

This is the single cheapest high-value fix available: add `calc_result` (already a dataclass with a
clean field set) to `DraftRun.to_dict()`/`load()`, then pass it through the seven export call sites,
then render it as a real appendix. Roughly a day, no new subsystems.

## Finding 2 — Two sources of numeric truth, no defined precedence, and a 34% disagreement nobody has seen

Running `pdd-agent calc` against every project config that exists:

| Config | YAML declares (net tCO2e/yr) | Engine computes (net tCO2e/yr) | Delta |
|---|---|---|---|
| `configs/projects/demo_socson_like.yaml` | 75,000 | **49,680** | **−34%** |
| `configs/projects/vietnam_socson_from_sheet.yaml` | 544,076 | **357,006** | **−34%** |
| `configs/projects/rice_vm0051_pilot.yaml` | 20,020 | 20,020 | 0 (YAML was back-filled from the engine) |
| `configs/demo/inegol_project_input.yaml` | all `None` | **no result** | n/a |

The rice row is the tell: it agrees exactly because that YAML was generated *from* the engine. The
two WTE configs — including the one that feeds every committed demo and review artifact — were
authored independently and disagree by a third.

Nobody has seen this, for three compounding reasons:

1. Calc is **gated off for `demo` and `noop`** at all three entry points
   (`if args.provider not in ("demo", "noop")`, `cli.py:517`). Those are the only providers that have
   ever produced an artifact.
2. The result is never persisted (Finding 1), so no retrospective comparison is possible.
3. `_check_calc_vs_project_input` (`consistency.py:486`) — the check designed to catch precisely
   this — has never had a calc result to run against.

Worse, the architecture as it now stands will *fight itself* on the first real run:

- The prompt tells the model the calc values are **"the authoritative quantification values"**
  (`dispatch.py:61`, and the ACM0022 branch at `section_orchestrator.py:264`).
- Calc is injected **only into Section 4** (`_is_quantification_section`,
  `section_orchestrator.py:231`). Section 1.10 — which the consistency layer requires to carry the
  *same* net number (`consistency.py:137–164`) — receives only the YAML facts.
- `check_quantitative_consistency` compares **both** 1.10 and 4.4 against `ProjectInput`, not against
  the engine.

Net effect on the first `prove --project socson --providers claude-code` run: Section 4.4 states
49,680 (calc), Section 1.10 states 75,000 (YAML), and the consistency layer flags 4.4 as wrong. The
proof run's own review output will accuse the calc engine of being the error.

**Recommendation:** declare precedence explicitly and encode it once. The defensible choice is
*engine wins when it can compute; ProjectInput.quantification becomes a cross-check, not a source*.
Concretely: `compute_for()` result overrides `QuantificationInputs` for prompt facts across **all**
sections that carry numbers (not just Section 4), a disagreement above a tolerance becomes a
**finding** in the consistency report rather than a silent overwrite, and the YAML fields become
`declared_*` for provenance. This is the `QuantificationInputs.from_calc_result()` bridge that
already exists and is exercised only in `tests/test_calc_integration.py`.

## Finding 3 — The flagship engine's dominant baseline term is structurally unreachable

Every WTE calc above shows `BE_CH4 (methane from SWDS) = 0.00`. That is not a data gap — it is a
modelling defect.

`acm0022.py:55`:

```python
organic_diverted = ws.annual_tonnes * self._inp.biomethanization_fraction
```

BE_CH4 is computed on the waste routed to **anaerobic digestion**, not on the waste **diverted from
the landfill**. Measured sensitivity (run this session on `demo_socson_like`):

| `biomethanization_suitable_fraction` | BE_CH4 | Baseline total | Net ER |
|---|---|---|---|
| 0.0 (absent → default) | **0** | 49,680 | 49,680 |
| 0.3 | 5,383 | 55,063 | 51,063 |
| 1.0 | 17,944 | 67,624 | 54,292 |

For a mass-burn or RDF WTE plant — which Soc Son and İnegol both are — `biomethanization_fraction`
is legitimately 0 or near it, yet **all** the incinerated organic waste avoids landfill methane. Under
ACM0022 that avoided methane is the *primary* baseline term and the entire economic case for the
project type. The engine currently returns zero for it and reports a baseline consisting only of
displaced grid electricity.

This explains the −34% in Finding 2 almost exactly, and it means the calc spine — now that it is
switched on — would make the drafted PDD *less* accurate than the human-authored YAML, not more.

Two related gaps in the same engine:

- **Project emissions and leakage are 0.00 on every WTE config.** `_map_acm0022`
  (`dispatch.py:86–138`) populates 6 of ~25 `ACM0022CalcInput` fields; auxiliary fuel, grid draw,
  ash handling and RDF end-use all default to zero. A PDD claiming a waste incinerator has zero
  project emissions will not survive validation.
- **`monitoring_params=[]` is hardcoded for the ACM0022 branch** (`dispatch.py:260`), while the rice
  engine returns 5. Monitoring parameters are a mandatory PD element and the foundation of the
  Monitoring-Report product bet.

**The registered PDDs settle which side is wrong.** Both projects exist as validated VCS PDDs in
`data/corpus/normalized/`, with published headline figures extracted this session:

| Project | Registered PDD figure | Repo YAML | Engine | Engine vs. registered |
|---|---|---|---|---|
| Soc Son | **Total estimated ERs 3,808,082 tCO2e** | 3,808,532 (+0.01%) | 2,499,042 | **−34%** |
| İnegöl | **Total estimated ERs 730,000 tCO2e; avg. annual ≈ 104,285 tCO2e/yr** | all `None` | cannot compute | n/a |

The Soc Son YAML is calibrated to the registered document to within 450 tCO2e. The engine is the
outlier, not the YAML — which inverts the natural reading of Finding 2 and makes the precedence
decision in A4 conditional on B1 landing first.

İnegöl closes the argument arithmetically. Its registered PDD publishes the grid emission factor
components directly: `EFgrid,BM,y = 0.3541`, `EFgrid,OM,y = 0.7279`, combined margin
`EFgrid,CM,y = 0.5 × 0.3541 + 0.5 × 0.7279 = 0.5410 tCO2/MWh`. Against the config's
`energy_generation_mwh_year: 49,935.315`, displaced grid electricity accounts for
`49,935.315 × 0.5410 ≈ 27,015 tCO2e/yr` — about **26%** of the registered 104,285 tCO2e/yr. The
remaining ~77,000 tCO2e/yr can only be avoided landfill methane: exactly the term the engine returns
zero for.

**Recommendation:** this is the highest-severity item in the repo. Separate `waste_diverted_from_swds`
from `waste_to_ad` in `ACM0022CalcInput`; default the former to total throughput. Add a golden test
asserting that a mass-burn configuration (`biomethanization_fraction = 0`) produces a **non-zero**
BE_CH4. Extend `_map_acm0022` to carry the PE inputs `ProjectInput` already has, and emit
`required_monitoring_params` for ACM0022 as the other three engines do.

## Finding 4 — The deliverable is prose plus 36 confidence badges; a VCS PD is a table document

A `python-docx` scan of the shipped flagship example, `examples/example-inegol-demo.docx`:

```
36 x  "Confidence | HIGH"        (per-section metadata table)
 1 x  "Project title | INEGOL INTEGRATED SOLID WAST..."   (cover metadata)
```

That is the entire table content of the marquee artifact. Meanwhile `docx_export.py` contains **11
Verra-shaped table renderers** — `render_ghg_boundary_table`, `render_applicability_table`,
`render_monitoring_fixed_params_table`, `render_monitoring_tracked_params_table`,
`render_emissions_summary_table`, `render_risk_assessment_table`,
`render_sustainable_development_table`, `render_data_gaps_table`, and three more — dispatched from
`_TABLE_RENDERERS` (line 689) keyed on `section["structured_content"]["table_type"]` (line 244).

**Nothing anywhere sets `structured_content`.** `grep -rn structured_content src scripts tests`
returns two hits, both in `llm/provider.py` — the dataclass field declaration and its serialization.
`tests/test_docx_export_tables.py` unit-tests all eleven renderers in isolation, which is why they
have never been noticed as unreachable. The reference template
`templates/VCS-Project-Description-Template-v4.4-FINAL2.docx` contains 10 tables; the pipeline
reproduces none of them.

This is a second complete subsystem in the same state the calc engines were in a week ago: built,
tested, and unplugged. It reframes what "next level" means for the deliverable. A VVB does not read
prose looking for a GHG source boundary — they read the boundary **table**. Prose with a confidence
badge stapled to each section is a draft aid; the table set is the document.

Compounding this, **the corpus normalization discards table structure**. A normalized doc
(`data/corpus/normalized/*.norm.json`) carries only `text`, `headings`, and `text_blocks` of
`{heading, text}`. So even if a producer existed, RAG could never retrieve an exemplar table from the
17 registered PDDs in the corpus — the shape of the thing being imitated is not in the index.

**Recommendation, and this is the strategic one:** make the calc spine the first `structured_content`
producer. `PddCalcResult` → `emissions_summary` table, and → `monitoring_tracked_params` /
`monitoring_fixed_params` tables from `required_monitoring_params`. That single connection closes
Finding 1 (calc reaches the deliverable), Finding 3's monitoring gap, and Finding 4's producer gap at
once, and it produces exactly the artifact a validator argues with. Table-aware normalization
(preserving `tables[]` in `.norm.json`) is the follow-on that lets the other eight renderers be
filled by retrieval or by the model.

## Finding 5 — The new preamble stripper silently truncates legitimate section bodies

`src/pdd_agent/llm/output_normalize.py` shipped in `47a4faf` and is wired into all four real
providers. Its trailer scan (`_TRAILER_RE`, lines 19–23) walks the **entire body** rather than the
tail, and truncates at the first line matching `note: i've` / `let me know` / `would you like` /
`i hope this helps` / `feel free to` / `shall i`.

Reproduced this session:

```python
body = """# 4.1 Baseline Emissions

Baseline emissions are 49,680 tCO2e/year.

Note: I've applied the national grid emission factor of 0.92 tCO2/MWh.

# 4.2 Project Emissions

Project emissions are 0 tCO2e/year.
"""
strip_assistant_preamble(body)
# -> "# 4.1 Baseline Emissions\n\nBaseline emissions are 49,680 tCO2e/year."
# 135 of 209 characters discarded, including all of 4.2
```

"Note: I've assumed…" is not conversational filler in this domain — it is exactly how an assumption
disclosure is phrased, and the pipeline's own prompts encourage assumption transparency. The fix is
small: bound the trailer scan to the last ~3 non-empty lines, and require the trailer line to be the
final substantive content rather than merely present. Add the case above as a regression fixture.

Note the failure mode: it is silent and lossy, it only fires on real-provider output, and the real
providers have never run end-to-end. This is the second defect in a row (after the preamble bug that
motivated the module) found by inspecting the real path rather than the test path.

## Finding 6 — A single-year snapshot where the template demands a year-by-year schedule

`ACM0022CalcInput.calculation_year` defaults to **1** (`models.py:204`), BE_CH4 uses a first-order
decay model at that single year, and the crediting total is then
`crediting_total = net * crediting_period_years` (`acm0022.py:195`, and identically in
`dispatch.py:278` for the other three families).

Linear extrapolation of a FOD baseline is wrong in a direction that matters: landfill methane in the
counterfactual **accumulates** year over year as waste piles up, so year 7 emissions substantially
exceed year 1. And VCS PD section 4.4 requires a **per-year** estimate table — which is precisely
what `render_emissions_summary_table` (`docx_export.py:573`) is built to render, iterating
`data["entries"]` of `{period, value}`.

So the exporter wants a schedule, the template wants a schedule, and the engine produces one number.
Making `compute_for()` return `annual_schedule: list[YearResult]` alongside the summary is a
contained change that feeds the existing renderer directly.

## Finding 7 — İnegol, the designated proof project, cannot compute at all

`pdd-agent prove --project inegol` maps to `configs/demo/inegol_project_input.yaml`, whose
`quantification` block is **entirely `None`** — no `grid_emission_factor`, no
`grid_emission_factor_source`, no declared baseline/project/net. `compute_for()` therefore returns
`None`, and the flagship proof run would produce a PDD with no computed numbers — the exact scenario
the calc-spine push was meant to prevent.

The inputs are nearly there: `energy_generation_mwh_year: 49,935.315` and
`annual_waste_throughput: 262,970.37` are present, and the missing grid emission factor **does not
need to be invented** — the project's own registered PDD in the corpus publishes
`EFgrid,BM,y = 0.3541` and `EFgrid,OM,y = 0.7279`, giving a combined margin of
**0.5410 tCO2/MWh** with a citable source. The config is also missing
`biomethanization_suitable_fraction` despite `technology_type: combined_wte_ad`, which is why it
would return BE_CH4 = 0 even once the GEF is supplied. This is a **pre-flight blocker for the
pending proof run** and a ten-minute fix that nobody would notice until $6 and 22 minutes had been
spent.

## Finding 8 — Grounding provenance is unrecorded and degrades silently

`get_retrieval_index()` (`retrieval/index.py:277–294`) falls back from the absent `corpus.fts.db` to
`demo.fts.db` **with no log line and no record in the run**. `demo.fts.db` holds 233 indexed section
rows from a 3-document subset; `data/corpus/normalized/` holds 17 documents.

`ProviderScorecardRow` (`provider_scorecard.py:39–53`) records provider, sections, judge scores,
tokens, cost and wall-clock — but **no field for which index was used, how many corpus documents
backed the run, or which methodology the calc engine dispatched to**. A "corpus-grounded real-model
proof" produced today would silently be grounded on 3 documents and the scorecard would not say so.

`pdd-agent doctor` does warn `[WARN] No retrieval index at data\index\corpus.fts.db`, but does not
mention that the consequence is a silent 3-document fallback rather than no retrieval.

Two small changes: log the index selection at WARNING when falling back, and add
`retrieval_index` / `corpus_doc_count` / `calc_methodology` columns to the scorecard.

A related data-quality note: one normalized filename is mojibake —
`VCS_Ã_demis_Project-Description.norm.json` (should be `Ödemiş`), indicating an encoding path in
`ingest/normalize.py` that mangles non-ASCII source filenames.

---

## Improvement tracks (priority order)

### Track A — Make the calc spine load-bearing end to end

The prior cycle connected the input side. This track connects the output side, which is where the
value is.

- **A1. Persist the calc result.** Add `calc_result: dict | None` to `DraftRun.to_dict()` / `load()`
  (`llm/provider.py:316`), populated by the orchestrator. Serialize `PddCalcResult` (it is a plain
  dataclass; `raw_result` needs an `asdict`-safe shape or exclusion). Without this, nothing else in
  this track is possible.
- **A2. Carry it to all seven export call sites** so `export_run_to_docx(calc_result=…)` stops being
  dead. Add a "Appendix — Quantification Audit Trail" rendering component name, value, unit,
  formula reference, and the engine's own warnings.
- **A3. Surface the calc warnings.** `waste_type 'plastics' not in DOC_BY_WASTE_TYPE; excluded from
  the calc` and `waste split evenly across N declared waste types` are material modelling assumptions
  that currently print to a console nobody reads. They belong in the assumption register and the
  reviewer-issues appendix.
- **A4. Define numeric precedence once** (Finding 2): engine wins where it can compute; ProjectInput
  becomes a cross-check; disagreement above tolerance is a consistency **finding**. Inject calc facts
  into **every** number-bearing section, not just Section 4, so 1.10 and 4.4 cannot diverge by
  construction.
- **A5. Stop gating calc on the provider name.** The engine is deterministic and LLM-free; there is
  no reason `demo`/`noop` runs cannot compute and export it. This is what would let the committed
  client-demo artifact show computed numbers. *Trade-off, stated:* it changes the committed
  `reports/demo-packages/` output, which is a deliberate artifact contract — so do it as an explicit
  regeneration with the diff reviewed, not as a side effect.

### Track B — Fix the flagship engine's domain correctness (highest severity)

- **B1. Decouple BE_CH4 from the AD fraction** (Finding 3). Add
  `waste_diverted_from_swds_tonnes` to `ACM0022CalcInput`, defaulting to total throughput; keep
  `biomethanization_fraction` for the AD pathway only. Golden test: mass-burn config
  (`biomethanization_fraction = 0`) must yield non-zero BE_CH4.
- **B2. Populate the project-emission inputs** `_map_acm0022` currently drops — auxiliary fuel, grid
  draw, RDF end-use. Extend `ProjectInput.technology`/`quantification` where the fields do not exist
  yet; a PDD asserting zero project emissions for an incinerator is not defensible.
- **B3. Emit ACM0022 monitoring parameters** (`dispatch.py:260` hardcodes `[]`), matching the other
  three engines. Prerequisite for both Track C and the MR product bet.
- **B4. Year-by-year ER schedule** (Finding 6) — `compute_for()` returns an annual series;
  `crediting_period_total` becomes its sum rather than `annual × years`.
- **B5. Validate against a registered PDD — the oracle already exists in the repo.** Headline figures
  extracted from the corpus this session: Soc Son **3,808,082 tCO2e** total ERs, İnegöl **730,000
  tCO2e** total / **104,285 tCO2e/yr** average. Asserting the engine lands within a stated tolerance
  of these is the only real evidence that any of this is correct — and it costs nothing, needs no
  network, and no API key. **This is the missing test layer under the entire calc spine**: today's
  golden tests assert the engine reproduces its own arithmetic, not that it reproduces a validated
  PDD. Do this **first** — it is what tells you whether B1 fixed the problem or merely moved it.

### Track C — Make the deliverable table-shaped

- **C1. Calc → `structured_content`.** First producer: `emissions_summary` from B4's schedule,
  `monitoring_tracked_params` / `monitoring_fixed_params` from B3. Unblocks three of the eleven dead
  renderers with zero new rendering code.
- **C2. Deterministic producers for the structural tables** — `ghg_boundary`, `applicability`,
  `proponent`, `cover_metadata` — from `ProjectInput` + `rules/verra/*_rules.yaml`. These are
  lookup-and-format, not generation; no LLM required.
- **C3. Table-aware corpus normalization.** Preserve `tables[]` in `.norm.json` and index them so
  retrieval can return exemplar tables. Without this, the model is asked to imitate a document shape
  that is absent from its evidence.
- **C4. Model-generated tables last**, for the genuinely narrative ones (`risk_assessment`,
  `sustainable_development`, `data_gaps`), with JSON-shaped output validated against the renderer's
  expected keys.

### Track D — Pre-flight the proof run (small, and it is blocking a $12 milestone)

The proof run remains the milestone. These are the things that would make it worth its cost:

- **D1. Fix the truncating stripper** (Finding 5) before any real-provider output is generated.
- **D2. Give İnegol a grid emission factor** with a real citation (Finding 7), or re-point
  `prove --project inegol` at a computable config.
- **D3. Build `data/index/corpus.fts.db`** — `pdd-agent build-index --corpus-dir
  data/corpus/normalized`. 17 documents instead of 3.
- **D4. Record grounding provenance in the scorecard** (Finding 8): index path, corpus doc count,
  calc methodology, calc-vs-declared delta.
- **D5. Then run it** — `prove --project socson --providers claude-code`, then `--project rice`.
  Prior cycle's measured budget: ~$6 and ~22 min per project, judge defaulting to the free
  deterministic `demo` path unless `PDD_JUDGE_PROVIDER` is set explicitly.
- **D6. Batching remains the right optimization** (measured last cycle: ~25k tokens of per-invocation
  harness overhead vs. ~300 tokens of section prompt — cost is per *call*, not per prompt). Drafting
  4–6 independent sections per invocation cuts cost and latency 5–10×. Sequence it after D5 so the
  first proof is apples-to-apples with the current architecture.

### Track E — Distribution (carried unchanged; still the onboarding blocker)

`[tool.hatch.build.targets.wheel] packages = ["src/pdd_agent", "schemas"]` ships no `rules/`,
`prompts/`, `configs/`, or `templates/` — all loaded at runtime. `REPO_ROOT = parents[3]` appears in
`phase06/*.py`, `benchmark.py`, `demo_setup.py`, and CWD-relative literals persist in `bucket.py`,
`normalize.py`, `download.py`, `doctor.py`. **CI installs `pip install -e .`**, so the wheel path is
never exercised. Package data via `importlib.resources`, a single `PDD_HOME` for writable state, and
a CI job that installs the built wheel into a clean venv and runs `doctor` + a `demo` draft from a
temp directory. Unchanged from the prior brainstorm; it has now survived six cycles.

### Track F — Service parity and scale (carried)

- **F1.** `claude-code` is still unreachable from the web UI — `_get_provider`
  (`service/main.py:99–139`) handles `demo`/`noop`/`ollama`/`openai`/`anthropic` and falls through to
  `unknown_provider` → `demo`. The one provider that works keylessly here cannot be selected. ~3 lines.
- **F2.** `data/runs/` is now **1,315 files / 139 MB**, and both `/dashboard` and `/api/runs`
  `glob("run-*.json")` + `stat()` + `_run_status()` every file per request. Add pagination, a
  lightweight index, and `pdd-agent prune-runs --keep N`.
- **F3.** No cost/token/latency display in the UI — `dashboard.html` mentions cost only in a
  `missing_cost_ceiling` warning. With the accounting fix from `47a4faf`, the numbers now exist and
  are worth rendering.
- **F4.** Auth stays deferred until a second human uses the service.

### Track G — Registry corpus and breadth (carried)

`data/corpus/registry` still does not exist; `ingest/registry_download.py` remains manual-download
mode. Family readiness is uneven and worth stating precisely:

| Family | Engine | Rules | Prompt | Project config | Corpus |
|---|---|---|---|---|---|
| WTE / ACM0022 | ✅ | ✅ | ✅ | ✅ ×3 | 17 docs |
| Rice / VM0051 | ✅ | ✅ | ✅ | ✅ ×1 | **0** |
| Biochar / VM0044 | ✅ | ✅ | ✅ | **0** | **0** |
| Cookstove / AMS-II.G | ✅ | ✅ | ✅ | **0** | **0** |

Two of four families have no project input at all, so their engines have never been dispatched
outside unit tests. Authoring one config each is hours of work and would immediately exercise
`compute_for()`'s non-WTE branches end to end. The registry capture (one interactive browser session
against the Verra search API) remains the unblock for their corpora.

### Track H — Hygiene, refactor, and doc truth

- **H1.** `SectionOrchestrator` is now **1,011 lines** carrying prompt assembly, retrieval, calc
  formatting, judging, redrafting, review, and persistence. Track A and Track C both add to it.
  Extracting a `PromptBuilder` (`_build_prompt`, `_format_calc_injection`, `_format_retrieval_results`,
  `_section_*`) is the natural precondition for A4's multi-section calc injection.
- **H2.** `_format_calc_injection` still carries a full ACM0022-specific formatter branch
  (`section_orchestrator.py:255–299`) duplicating `PddCalcResult.to_prompt_block()` at a different
  fidelity. Once B1–B4 give the ACM0022 result a proper component list, collapse to one path.
- **H3.** Committed artifacts are stale. The newest `reports/demo-packages/` run is
  **2026-05-30** — it predates family-aware prompts, the judge rubric, the calc spine, preamble
  normalization, and cost truth. The artifact you would show a client is five pushes behind the code.
  Regenerate as part of A5.
- **H4.** `reports/review-packages/*/manifest.json` embeds absolute
  `C:\Users\tukum\Downloads\pdd-auto\...` paths in committed files. Store repo-relative.
- **H5.** README "Known Gaps" is now partly stale in the other direction — it still lists the
  `claude-code`-in-service gap (true) alongside items resolved in `47a4faf`. More importantly it does
  not list any of Findings 1–8. Stale gap lists hide real gaps.
- **H6.** Local venv runs **Python 3.13.12** while CI tests only 3.11/3.12. Either add 3.13 to the
  matrix or pin the dev environment; today "green locally" and "green in CI" test different
  interpreters.
- **H7.** `phase05/` and `phase06/` name plan phases rather than domains (`benchmark`,
  `provider_scorecard`, `spreadsheet_mapper`, `vietnam_workflow`, `assumptions`). Cheap rename with
  deprecation shims. Low urgency, compounding cost.
- **H8.** `lessons.md` has recorded zero rules across seven cycles despite a standing instruction to
  maintain it. Either use it or drop it from the workflow.
- **H9.** Statement coverage is **82%** overall (6,660 statements, 1,216 uncovered) — healthy in
  aggregate, but the distribution is where the risk sits. Lowest: `ingest/download.py` **15%**,
  `ingest/normalize.py` **24%**, `export/drive_upload.py` **29%**, `ingest/bucket.py` **46%**, and
  **`cli.py` at 47%** across 993 lines. The ingest and Drive modules are network-bound and their
  coverage is a defensible trade-off; `cli.py` is not — it is the primary user surface, it is where
  the calc wiring, provider selection, and export gating decisions are made, and half of it is
  unexercised. `calc/dispatch.py` sits at **77%**, meaning the newly-landed dispatch layer's
  incomplete-input and non-WTE branches are only partly covered — directly relevant to Findings 2, 3
  and 7.

### Track I — Product direction (carried, re-sequenced)

- **I1. The Monitoring-Report bet gets materially stronger with Tracks B and C.** An MR is
  overwhelmingly numeric recomputation against monitored parameters rendered into tables — which is
  exactly `required_monitoring_params` (B3) plus the annual schedule (B4) plus the table producers
  (C1). The MR product is closer than the PD product to what this codebase is actually good at.
- **I2. Colleague onboarding remains blocked by Track E**, not by willpower.
- **I3. Per-family schema split** — deferred, unchanged. `ProjectInput` now carries WTE, rice,
  biochar and cookstove sub-models; revisit when a fifth family arrives.

---

## Recommended sequencing

1. **Half a day — safety before spend:** D1 (truncating stripper), D2 (İnegol GEF), D3 (build the
   real index), D4 (grounding columns). All offline, all testable, all prerequisites for a proof run
   worth its cost.
2. **Two to three days — correctness before persuasion:** B1 (BE_CH4), B5 (validate against
   registered PDDs), B3 (monitoring params), B4 (annual schedule). B5 first if you want the cheapest
   possible confidence check; B1 first if you want the biggest number to move.
3. **One to two days — the deliverable:** A1 → A2 → A3 → A4 (persist, export, surface, precedence),
   then C1 (calc → `emissions_summary` + monitoring tables). This is the point at which the DOCX
   contains something a validator can argue with.
4. **The milestone (~1 hour wall-clock, ~$12):** D5 — `prove --project socson`, then `--project rice`.
   Write the findings doc.
5. **Then, informed by real numbers:** D6 (batching), F3 (surface cost in the UI).
6. **Parallel and independent:** F1 (three lines), H3/H4/H5 (artifact and doc truth-sync), Track G
   registry capture.
7. **Its own plan afterwards:** Track E (packaging), then I2 (onboarding).

## Single highest-leverage recommendation

**Audit the calc engine against a real registered PDD (B5), fix BE_CH4 (B1), and then carry the
result all the way into the DOCX as a table (A1–A2 + C1).**

The prior cycle's recommendation — wire the calc engines in — was right and is done. But wiring an
engine in is only valuable if the engine is correct and its output reaches a human. Right now it is
neither: on the flagship methodology it computes a baseline missing its dominant term, it disagrees
with every human-authored config by a third, and its result is discarded before export. The repo has
1,796 lines of methodology code whose only assertion of correctness is that it reproduces its own
arithmetic — while 17 registered PDDs with published, validated ER figures sit in
`data/corpus/normalized/` unused as a test oracle.

And the second-order insight from this session is that the calc spine is not the only unplugged
subsystem: eleven Verra table renderers sit behind a `structured_content` field that no code path
ever populates, so the shipped flagship artifact contains 36 identical confidence badges and nothing
a validator reads. **The pattern across seven cycles is consistent — this project builds receiving
apparatus faster than it builds senders.** The highest-leverage discipline change is not a new
capability; it is a rule that no subsystem is considered done until an artifact on disk demonstrates
it firing end to end.

---

## Assumptions adopted (unattended session — noted per workflow rules)

- **ASM-01:** I spent **$0** this session. All findings come from static analysis plus the
  deterministic, LLM-free `pdd-agent calc` / `pytest` / `doctor` paths. I did not run the real-model
  proof (PHASE-06 of the current plan, ~$6/project), and I did not make outward-facing network calls
  — no registry capture, no Drive I/O.
- **ASM-02:** Finding 3 asserts a **domain** defect (BE_CH4 should not be gated on the AD fraction),
  not merely a coding one. Grounded in ACM0022's own Eq.1 framing carried in the module docstring
  (`acm0022.py:7`), where BE_CH4 is avoided SWDS methane from waste diverted from the landfill, and
  in the observed 34% gap against two independently-authored configs. A methodology specialist should
  confirm before B1 lands; I have adopted it as the working reading because the alternative — that a
  mass-burn WTE project genuinely has zero avoided landfill methane — is not credible.
- **ASM-03:** I treat the `structured_content` producer gap (Finding 4) as unfinished wiring rather
  than intent, on the same evidence pattern as the calc-spine finding a week ago: renderer, dispatch
  map, dataclass field, serialization, and unit tests all exist and are mutually consistent, with no
  sender.
- **ASM-04:** Track A4 adopts "engine wins, ProjectInput cross-checks" as the numeric precedence rule.
  The defensible alternative — ProjectInput wins, engine advises — is weaker because it makes the
  calc spine decorative, which is the state the last cycle just spent a push escaping.
- **ASM-05:** Track A5 recommends removing the `demo`/`noop` calc gate despite it changing committed
  demo artifacts. Adopted because the artifact contract exists to keep the demo *clean*, not to keep
  it *number-free*, and computed numbers strictly improve it. Flagged as an explicit,
  diff-reviewed regeneration rather than a silent change.
- **ASM-06:** Track C sequences deterministic table producers (C1, C2) ahead of model-generated ones
  (C4). Adopted as the conventional choice; generating all eleven table types from the model is a
  defensible alternative that trades determinism for coverage.
- **ASM-07:** Coverage figures quoted in H9 are from a single `pytest --cov=pdd_agent` run in the
  project venv (Python 3.13). Branch coverage was not measured; the numbers are statement coverage.
- **ASM-08:** Carried items (Tracks E, F, G, I) are reaffirmed on re-verification of their underlying
  evidence, not copied. Where the evidence moved — run count 1,130 → 1,315, 130 MB → 139 MB — the new
  numbers are used.

## Suggested next step

Run `/plan` against this brainstorm scoped to **D1–D4 (pre-flight) + B1/B3/B4/B5 (engine
correctness) + A1–A4 and C1 (carry the result to the deliverable)**, with **D5 (the proof run)** as
the closing phase. Tracks E and C3–C4 each deserve their own follow-on plan once the proof artifact
exists.
