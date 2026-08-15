---
title: "PDD-Auto Next Level: The Grounding Layer Is Hollow, and the Calc Engine Has No Inputs"
date: "2026-08-13"
type: "brainstorm"
depth: "standard"
source_request: "Orchestrator-driven brainstorm (unattended): analyze current state, codebase, docs, architecture; propose improvements/features/refactors/architectural changes/optimizations"
slug: "pdd-hollow-grounding-and-calc-inputs"
---

# Brainstorm: PDD-Auto — The Grounding Layer Is Hollow, and the Calc Engine Has No Inputs

## Context: this is a fresh start, not a resumption

As of 2026-08-13 the plan backlog is **empty**. Every plan under `plans/` now carries a terminal
status: the three that were open on 2026-08-05 (`2026-07-16-trust-layer`, `2026-07-23-run-real-model-proof`,
`2026-07-25-calc-correctness-and-audit-trail`) were closed by explicit user decision to clear the
backlog and start fresh, and `activeContext.md` records "No new plan has been chosen yet."

So this brainstorm is not constrained by an in-flight plan. It is the seventh analysis cycle on this
repo (April → August 2026), and the first with a clean slate since April.

## Where the project stands (verified this session, not copied from records)

| Claim | Verified how | Result |
|---|---|---|
| Test suite | `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` | **798 passed, 7 deselected, 3 xfailed, 89s** (README still says 752) |
| Source size | `find src/pdd_agent -name "*.py" \| wc -l` | 71 modules; 58 test files |
| Working tree | `git status --short` | clean after the triage commit `8dc23c8` |
| `claude` CLI | `pdd-agent doctor` | **`[OK] claude CLI: 2.1.229`** — present and authenticated |
| API keys / Ollama | `pdd-agent doctor` | none set; Ollama unreachable |
| Production retrieval index | `ls data/index/` | `corpus.fts.db` exists, **1015 rows** |
| Normalized corpus on disk | `ls data/corpus/normalized/` | **17** `.norm.json` documents |
| Documents actually in the index | `SELECT COUNT(DISTINCT document_name)` | **13** — four documents contribute nothing |
| Distinct text in the index | `SELECT COUNT(*) FROM (SELECT DISTINCT text …)` | **270 of 1015 rows — 73.4% are duplicates** |
| Index rows truncated at 500 chars | `SELECT COUNT(*) … length(text)>=500` | **992 of 1015 (97.7%)** |
| Real-model proof artifacts | `ls reports/` | **still zero** `prove-*.md` / `provider-scorecard-socson.md` |
| Registered-PDD oracle | `pytest tests/test_registered_pdd_oracle.py` | 3 passed, **3 strict xfails** (engine is +39.5% / +22.4% / −51.4% vs registered figures) |
| Verra table renderers with a producer | `grep structured_content src/` | **3 of 11** (`cover_metadata`, `emissions_summary`, `monitoring_tracked_params`) |
| Run store size | `ls data/runs/ \| wc -l` | **1,555 files**, scanned unpaginated on every dashboard request |

Two findings below are new — no prior brainstorm in `research/` names either. They are the reason I
would not start the next push on any of the items the closed plans left behind.

---

## Finding 1 (headline) — the RAG corpus is 270 unique 500-character page fragments

This is the most important thing in the repo right now, and it undermines the claim the architecture
is named for. The README's first architectural sentence is "corpus-bucketed RAG approach." Here is
what the corpus actually contains.

**The indexing path throws away the documents.** `src/pdd_agent/parse/section_parser.py:121`
defines `_find_content_page(start_page, canonical_heading)`. For each detected heading it scans
forward for the first non-TOC page whose text contains the heading string, and returns
`pg_text.strip()[:500]` (line 128). If no page matches, it returns the first non-TOC page's first
500 characters (line 132). That value becomes `text_preview`, and
`src/pdd_agent/retrieval/index.py:119` re-truncates it (`text_snippet = text_preview[:500]`) before
inserting it as the FTS5 `text` column.

Three consequences, all measured:

1. **Every indexed "section" is one truncated page, not a section.** 992 of 1015 rows (97.7%) are
   exactly 500 characters, i.e. cut mid-word. Sample row text begins
   `'Joint Project Description & Monitoring Report: VCS Version 4. 2 \n106 \nQexport,RDF_SB,y = '` —
   the running header and page number are indexed as content.
2. **Adjacent subsections get byte-identical text.** Any headings that land on the same PDF page
   resolve to the same page fragment. Bergama's rows for `1.2`, `1.3`, and `1.4` are identical
   strings. Repo-wide: **1015 rows carry only 270 distinct texts — 73.4% duplication.**
3. **The retrieval a drafting prompt actually sees is 2–3 distinct snippets, mostly from one
   document.** Measured live via `get_examples_for_section`:

   | Section | Examples returned (k=5) | Distinct texts | Top source |
   |---|---|---|---|
   | 4.4 Net GHG Emission Reductions | 5 | **2** | Bergama (both) |
   | 3.3 Baseline Scenario | 5 | **3** | Bergama |
   | 1.10 Project Scale and Estimated ERs | 5 | **3** | Bergama |

**Four of the seventeen documents contribute zero rows**, including the one document the
methodology-dependent sections most need: `EB111_repan07_ACM0022_v03.0.norm.json` — the ACM0022
methodology itself. Also absent: `Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2`,
`DraftProjectDescription`, `VCS-Project-Description-HEREKO-v4.1`. They are silently dropped by
`parse_corpus`'s heading matcher with no error surfaced to the operator; `pdd-agent doctor` cheerfully
reports `[OK] data\index\corpus.fts.db — 1015 rows in sections_fts`.

**Two dead code paths fall out of the same defect.** `RetrievalIndex.build` inserts empty strings for
`content_class` and `review_sensitivity` (`index.py:126`), but `RetrievalIndex.search` exposes a
`content_class` equality filter (`index.py:164-166`) that `search()` in `retrieval/search.py:109`
advertises in its docstring. **Any caller passing `content_class` gets zero results, always.** The
`review_sensitivity` column is likewise permanently empty.

**Why this matters more than anything else on the list.** Every downstream trust mechanism is
computed over this substrate: section provenance records, `[CORPUS: …]` citations in drafted prose,
the grounding metrics in `reports/demo-scorecard.md`, the judge's grounding criterion, and the
"Grounding" provenance block added specifically to make proof runs honest. All of them faithfully
report retrieval that is 73% duplicated, truncated mid-sentence, and missing the methodology
document. Running the real-model proof on top of this would produce a scorecard whose grounding
column is precise and meaningless.

**What the fix looks like.** Index real section spans, not heading-adjacent page fragments:
carry `text_blocks[]` (already produced by `ingest/normalize.py`) from one heading to the next,
chunk them at ~1,500–2,000 characters with overlap, populate `content_class`/`review_sensitivity`
from the schema, add a `document_family` column so a rice project cannot retrieve WTE prose, and
fail loudly when a normalized document yields zero mapped sections. Expected effect: from 270 unique
fragments to on the order of several thousand real chunks, with the ACM0022 methodology text
reachable for the first time.

---

## Finding 2 — the calc engine's remaining error is an *input* problem, and the inputs are in the corpus

The closed calc-correctness plan left three `strict=True` xfails in
`tests/test_registered_pdd_oracle.py`, each honestly documented rather than tolerance-widened:

| Oracle | Registered figure | Engine | Error |
|---|---|---|---|
| Soc Son crediting-period total | 3,808,082 tCO2e | 5,312,566 | **+39.5%** |
| İnegöl annual net | 104,285 tCO2e/yr | 50,690 (year 1) | **−51.4%** |
| İnegöl crediting-period total | 730,000 tCO2e | 893,441 | **+22.4%** |

The xfail reasons all name the same root cause: "the repo's config carries no waste-composition
split, no ramp-up profile, and no site-specific project-emission inputs." That is verifiably true at
`src/pdd_agent/calc/dispatch.py:167-182`:

```python
n_types = len(tech.waste_type)
per_type_tonnes = tech.annual_waste_throughput / n_types if n_types else 0
...
warnings.append("waste split evenly across N declared waste types")
```

`ProjectInput.technology` carries `waste_type: list[str]` and a single scalar
`annual_waste_throughput`. The engine therefore splits total tonnage **evenly** across declared waste
types before feeding CDM Tool 04's first-order-decay model — and Tool 04's degradable-organic-carbon
fraction varies by roughly an order of magnitude between food waste, garden waste, paper, wood, and
textiles. The dominant term of the dominant methodology is being driven by an arithmetic mean over
categories that are not remotely equal in the real waste stream.

**The missing inputs are published in the documents already sitting in `data/corpus/normalized/`.**
Registered VCS PDDs publish their waste-composition tables, their capacity ramp-up schedules, and
their project-emission line items — that is exactly the material the corpus was ingested for. This is
why Findings 1 and 2 are one piece of work, not two: the tables that would close the calc gap are
inside PDFs whose ingestion currently discards table structure entirely (`ingest/normalize.py`
contains no table handling at all — grep for `table` returns nothing).

**What the fix looks like.** Add `waste_composition: list[WasteFraction]` (type, mass fraction,
source string) and an optional `capacity_ramp: list[float]` to `ProjectTechnology`, both optional so
every existing config keeps validating; use them in `_map_acm0022` when present and keep the
even-split fallback with its warning when absent. Then populate them for Soc Son and İnegöl **from
the registered PDDs' own published tables**, and see how much of the ±20% band closes. The xfails
become the acceptance test, and unlike a golden test they cannot be satisfied by editing expectations.

---

## Finding 3 — the deliverable is prose where Verra expects tables

`_TABLE_RENDERERS` in `src/pdd_agent/export/docx_export.py:710-720` holds eleven renderers matching
the VCS v4.4 template. Three now have a producer. Eight do not: `audit_history`, `proponent`,
`ghg_boundary`, `applicability`, `monitoring_fixed_params`, `risk_assessment`,
`sustainable_development`, `data_gaps`.

The interesting split is that these eight are not one problem:

- **Four are pure `ProjectInput` projections** — `proponent`, `audit_history`, `ghg_boundary`,
  `applicability` — deterministic mappings from data the schema already carries plus
  `rules/verra/*_rules.yaml`. No model call, no judgment. This is cheap, high-visibility work.
- **`monitoring_fixed_params`** is the calc engine's other half: the parameters available at
  validation (section 5.1), a sibling of the `monitoring_tracked_params` table already wired.
- **Three genuinely need generation with schema validation** — `risk_assessment`,
  `sustainable_development`, `data_gaps` — and should wait for a real model run.

There is also a live constraint worth designing around rather than inheriting: setting
`structured_content` **suppresses the section's prose** (`docx_export.py:244-256`). That is why the
closed plan restricted calc tables to 4.4 and 5.2 only. A VVB expects narrative *and* table in most
of these sections, so rendering both — prose, then table — is a small, contained change to the
dispatch block that unblocks all eight renderers at once. I would do that first.

---

## Finding 4 — the unrun proof, and an honest look at the cost blocker

Seven planning cycles have deferred the first real-model drafting run. Every artifact this repo has
ever produced came from `DemoProvider` or `NoopProvider`. The last attempt was declined on 2026-08-05
over an estimated $12–16 of spend.

Three observations, offered as analysis rather than as an argument to overrule that decision:

1. **The estimate's basis is a measured number, and it is a subscription number, not an invoice.**
   `ClaudeCodeProvider` reads `total_cost_usd` straight from the CLI's JSON
   (`claude_code_provider.py:140-155`), and its own docstring calls that "the authoritative cost
   billed to the operator's subscription." On a subscription plan that figure is API-equivalent
   notional value, and it counts against usage limits rather than producing a separate charge. The
   real cost of a 36-section run is plan usage plus ~22 minutes of wall clock — a materially
   different decision from "$16 leaves the account."
2. **A proof run costs the same whether the grounding is good or hollow.** Given Finding 1, running
   it today buys a scorecard whose grounding column is honest about a corpus that isn't. The
   sequencing argument is strong: fix retrieval, then spend the run.
3. **A meaningful fraction of the proof's value is available for free.** A single-section real call
   (measured previously at 36.1 s / $0.168) exercises the whole prompt-assembly → normalize →
   judge → consistency path. A "one section, one project, read the output by hand" checkpoint costs
   roughly $0.17 and would have caught both the preamble bug and the truncation bug. That belongs in
   the plan regardless of whether the full run is authorized.

**Recommendation:** keep the full proof as the closing phase of the next push, gated on explicit
authorization, and add a sub-$1 single-section smoke check as a mid-plan gate that needs no such
authorization.

---

## Finding 5 — the smaller true things

- **Breadth is claimed on a WTE-only corpus.** Family-aware machinery is genuinely built and good:
  `system_prompt_for()` (`section_orchestrator.py:90`), per-family rules in `rules/verra/` and
  rubrics in `rules/verra/rubrics/` for wte/rice/biochar/cookstove, and four calc engines. But all
  17 corpus documents are WTE, retrieval has **no family filter**, and `pdd-agent prove --project
  rice` therefore grounds a rice PDD in waste-to-energy prose and cites it as provenance. Until the
  index carries a family column, "methodology breadth" is a code claim, not an output claim.
- **VM0044 and AMS-II.G are unreachable from the CLI.** `configs/` contains socson, inegol, and rice
  only. Two of the four calc engines have no project config at all — their golden tests assert their
  own arithmetic and nothing more.
- **The run store is unbounded.** 1,555 files in `data/runs/`; both `dashboard` and `/api/runs`
  `glob("run-*.json")` and `stat()` every one on every request (`service/main.py:391`, `:573`). No
  pagination, no retention. This is the kind of thing that is invisible until the first live demo.
- **The service still can't select `claude-code`.** `_get_provider` (`service/main.py:99-124`)
  handles demo/noop/ollama/openai/anthropic and falls back to `demo` with
  `reason="unknown_provider"` for everything else — so the one keyless frontier path the repo has
  is unreachable from the web UI that is meant to be the product surface.
- **An unexplained state-machine bug is on record and unhunted.** `docs/2026-07-12-rice-pilot-findings.md`
  notes "a bulk approve-all loop over the remaining 32 sections did not fully apply (a batch/state-machine
  interaction not investigated further)." That is squarely on the path a human reviewer walks through 36
  sections in the web UI.
- **Grounding provenance is mislabeled.** `get_active_index_doc_count()` (`index.py:314`) returns
  `COUNT(*) FROM sections_fts` — a *row* count — and the scorecard renders it as
  `- Corpus documents: {n} indexed section rows`. The trailing words are accurate; the field name
  and label are not. Given Finding 1, "13 documents / 270 unique chunks" is the number that should
  appear.
- **README drift.** Status line says 752 tests (actual 798) and "Real LLM providers … have never
  executed a live drafting run" is still true but the Known Gaps list no longer matches the tree.
- **`ingest/registry_download.py` is still a stub.** Its docstring records that the Verra OData
  request shape "could not be fully reconstructed … without browser devtools." This caps the corpus
  at whatever was manually downloaded — 17 documents — which is the ceiling on Finding 1's fix.

---

## Proposed tracks

Sized in rough implementation effort, dependencies noted. **Track A is the one I would build.**

### Track A — Rebuild the grounding layer (the corpus is the product)
Re-chunk on real section spans instead of heading-adjacent page fragments; populate
`content_class`/`review_sensitivity`; add a `document_family` column and a family filter through
`search()` / `get_examples_for_section()`; fail loudly when a normalized document yields zero mapped
sections (recovering the four dropped documents, ACM0022 among them); add a corpus-health command
(`pdd-agent index-report`) that prints documents indexed, chunks, duplication rate, and mean chunk
length so this class of defect can never hide again. Offline, no spend, fully testable.
**Dependencies:** none. **Unblocks:** everything else.

### Track B — Table-aware ingestion, and the calc inputs it yields
Preserve table structure in `ingest/normalize.py` (pdfplumber already exposes `extract_tables()`);
add optional `waste_composition` and `capacity_ramp` to `ProjectTechnology`; use them in
`_map_acm0022`, keeping the even-split fallback and its warning; populate them for Soc Son and İnegöl
from the registered PDDs' published tables; measure the three oracle xfails and flip whichever
genuinely close. **Dependencies:** Track A (shares the ingestion path). **Risk:** the gap may not
fully close — the discipline the closed plan established (record the residual, never widen the
tolerance) must carry forward.

### Track C — Prose *and* tables, and the four deterministic renderers
Change the exporter's dispatch so `structured_content` renders after the section's prose rather than
instead of it; then wire `proponent`, `audit_history`, `ghg_boundary`, `applicability` from
`ProjectInput` + rules YAML, and `monitoring_fixed_params` from the calc engine. Takes the deliverable
from 3 of 11 Verra tables to 8 of 11. **Dependencies:** none (parallel with A).

### Track D — The proof, staged
A sub-$1 single-section real `claude-code` call as a mid-plan gate (no authorization needed), then
the full 36-section Soc Son run as an explicitly-gated closing phase, with `PDD_MAX_COST_USD=15` and
the findings document the closed plan specified. **Dependencies:** A, B, C — the run should be spent
on the fixed pipeline, not the current one.

### Track E — Product-surface hygiene
Run-store pagination + retention; `claude-code` in the service's `_get_provider`; reproduce and fix
the bulk approve-all state-machine bug from the rice pilot; correct the grounding provenance label;
resync the README. Small, independent, and the difference between a demo that survives being clicked
on and one that doesn't. **Dependencies:** none.

---

## What I would do next, if it were my call

**Plan Track A + Track C as one push, with Track B as its closing phase and Track D's cheap
single-section gate folded in.**

The reasoning: Track A is the only item that changes what every other component is standing on, it
costs nothing, and it is provable offline. Track C is independent, cheap, and it is what a reader of
the output actually sees. Track B is the payoff — it is the first time the repo would have a
defensible number rather than an honestly-documented wrong one — but it depends on A's ingestion work
and carries real risk of not fully closing, so it belongs at the end where a partial result is still
a good outcome.

Track D's full proof run stays out until a human authorizes it; Track D's $0.17 smoke check goes in
regardless. Track E is a good parallel track for a second agent or a slow afternoon, and should not
gate the main push.

The thing to resist is the gravitational pull of the proof run. It has been deferred seven times, and
each deferral makes it feel more overdue — but running it against 270 duplicated 500-character
fragments would produce exactly the artifact this repo has been careful not to produce: a confident
number that isn't true.

---

## Assumptions adopted where I would otherwise have asked

Per the unattended-session rule, these were decided rather than raised:

- **ASM-A:** The 2026-08-05 decision to decline the proof-run spend still stands. I have not planned
  the full run as unconditional work; it appears only as an explicitly-gated closing phase, with a
  sub-$1 alternative that needs no authorization.
- **ASM-B:** Fixing retrieval outranks running the proof. Justified by Finding 1 — the run's headline
  deliverable is a grounding-provenance scorecard, and grounding is the broken thing.
- **ASM-C:** New `ProjectInput` fields are optional with fallbacks preserved. Six configs and 1,555
  run JSONs exist; a required field would break all of them, and the repo's own CON-004 precedent is
  backward compatibility.
- **ASM-D:** Chunk target ~1,500–2,000 characters with overlap. No source specifies this; it is the
  conventional default for BM25 over document sections and can be tuned once
  `pdd-agent index-report` makes the effect measurable.
- **ASM-E:** Rendering prose *and* table (rather than table-replaces-prose) is what a VVB expects.
  Inferred from the registered PDDs in the corpus, which carry both.
- **ASM-F:** Re-indexing changes retrieved text and therefore future section output. Acceptable —
  `data/index/` is gitignored and no committed artifact changes. Committed demo packages under
  `reports/demo-packages/` should **not** be regenerated as part of this work (the closed plan's
  ASM-007 precedent).

## Considered and rejected

- **Swap FTS5/BM25 for embeddings.** Rejected. The retrieval failure is that the index contains
  duplicated 500-char page fragments; embedding the same fragments retrieves the same fragments.
  BM25 over correct chunks should be evaluated before adding a model dependency to a pipeline whose
  selling point is that retrieval costs nothing.
- **Split `ProjectInput` into per-family discriminated unions.** Rejected, consistent with DEC-004
  in `docs/2026-07-12-rice-pilot-findings.md`: the wide schema handled the rice pilot once three
  WTE-shaped fields were populated. Revisit when a second *real* non-WTE project's data makes it
  genuinely painful.
- **Unstub `registry_download.py` to grow the corpus.** Rejected for this push. It needs interactive
  browser devtools capture, and the immediate constraint is that 4 of the 17 documents already on
  disk aren't indexed and the other 13 are indexed at 3% fidelity. Fix the ones we have first.
- **Regenerate the committed demo packages to show the new tables.** Rejected — a committed client
  contract deserves its own diff-reviewed change, not a ride-along.
- **Widen the oracle tolerance to turn the three xfails green.** Rejected emphatically. Those xfails
  are the most valuable artifact the last push produced.
