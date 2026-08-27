---
title: "The Real-Output Gap: What the First Real Model Call Exposed, and What It Costs to Close"
date: "2026-08-21"
type: "brainstorm"
status: "draft"
repo_state: "e14c107 — all 6 phases of the 2026-08-13 grounding-rebuild plan landed; 841 passed / 3 xfailed; plan backlog empty"
---

# Brainstorm: The Real-Output Gap

## How this session differs from the last one

The 2026-08-13 brainstorm found a hollow retrieval index and planned six phases to fix it. All six
landed (`8b77742`, `d595e31`, `fdc32f5`, `e14c107`), the suite is green at 841 tests, and the plan
backlog is empty. This session starts from a genuinely healthier repo — and from one new thing the
last push produced that nothing before it could: **one real model call, stored on disk.**

`data/runs/smoke-4-1.json` holds 4,000 characters of real Sonnet output for Soc Son section 4.1,
bought for $0.1983. It is the only non-synthetic artifact this repository has ever produced. Nearly
every finding below comes from interrogating that one file and the code paths it touches — because
four months of `demo`/`noop` output hid a class of defect that a single real call surfaced
immediately.

Everything below was verified this session against the working tree, the live index, and that run.
Nothing is carried forward from the record.

---

## Finding 1 (headline) — the exporter cannot render what real models actually produce

The whole pipeline terminates in a Word document. I exported `smoke-4-1` to DOCX and read the
paragraphs back. This is what a reviewer would see:

```
'# 4.4.1 Baseline Emissions'
'## Methodology Basis'
'$$BE_y = \sum_t \left( BE_{CH4,t,y} + BE_{WW,t,y} + ... \right) \times \left(1 - RATE_{c'
'| Term | Description |'
'|---|---|'
'| $BE_{CH4,t,y}$ | Baseline methane emissions from the solid waste disposal site (SWDS) ... |'
'| **Total baseline emissions ($BE_y$)** | **487,710.99** | [CALC: baseline_total] |'
```

Literal hash marks, literal pipe rows, raw LaTeX, literal asterisks. Counted in that **single**
section: 12 pipe-table lines, 4 Markdown headings, 1 display-math block, 19 inline `$…$` spans, 7
`**bold**` spans. Extrapolated across 36 sections, a real run produces a Word file with several
hundred broken artifacts in it.

The cause is four lines:

```python
def _split_paragraphs(text: str) -> list[str]:            # docx_export.py:1047
    pieces = [piece.strip() for piece in text.split("\n")]
    return [piece for piece in pieces if piece]
```

Every line of model output becomes one plain paragraph. This was invisible for four months because
`DemoProvider` and `NoopProvider` emit flat prose — no headings, no tables, no math. The demo DOCX
files committed under `reports/demo-packages/` look fine precisely because they were never written
by a model.

Note the irony: PHASE-03 of the last plan did substantial work to render Verra's *deterministic*
tables (8 of 11 wired, prose-then-table dispatch fixed). Meanwhile the tables the *model* writes —
which is where the substantive content lives — render as ASCII garbage.

**This is the single highest-leverage defect in the repository.** It is also the cheapest to prove
fixed: the input is already on disk and already paid for.

---

## Finding 2 — every section is guillotined at 4,000 characters, and the config that claims to control it is dead

The smoke run ends mid-word: `…does not match the provenance-tracked quantification.crediting_period_tota`.

```python
max_chars: int = 4000                                        # provider.py:63, :88, :135
text = strip_assistant_preamble(response.text)[:max_chars]   # claude_code_provider.py:227
```

All four providers declare `max_chars=4000` as a default. `SectionOrchestrator` calls
`draft_section()` at `section_orchestrator.py:744` **without passing it**. So the cap is 4,000
characters, always, for every section, on every provider.

Separately, `GenerationControls.max_tokens_per_section` (`schemas/project_input.py:419`, validated
`ge=100, le=16000`) is read by nothing. A user who raises it to 16,000 gets no change whatsoever.

Two problems compound:

1. **It is a character cut applied to a token budget.** Nothing closes the sentence, nothing retries,
   nothing flags it. The section is silently amputated and stored as if complete.
2. **It is uniform across sections that are not uniform.** Section 1.1 ("Summary Description") needs
   maybe 1,500 characters. Section 4.4 ("Quantification of GHG Emission Reductions") in the
   registered Soc Son PDD runs to tens of thousands. One number cannot serve both.

The arithmetic ceiling this imposes on the product: 36 × 4,000 = 144,000 characters. The registered
Soc Son PDD that this tool exists to reproduce is **183,731 characters**. The pipeline cannot, by
construction, produce a document of the right size — and the `demo` provider currently produces
**9,791 characters total** (mean 271 per section), about 5% of a real PDD.

---

## Finding 3 — 70% of the rebuilt index is unreachable from the drafting path, and the metric that declared the gap closed does not measure reachability

The last push's headline claim was `documents 17 (≥16 ✓)` — the four silent documents recovered.
I queried the live index directly:

| | rows | share |
|---|---|---|
| Total rows in `sections_fts` | 3,026 | 100% |
| Rows with a canonical `section_id` | **889** | **29.4%** |
| Rows with `section_id = ''` | 2,137 | 70.6% |
| Documents with ≥1 reachable row | **13 of 17** | — |

Per-document, the four "recovered" documents contribute **zero** reachable rows:

```
   0/  75  Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2
   0/ 124  DraftProjectDescription
   0/  96  EB111_repan07_ACM0022_v03.0        <- the ACM0022 methodology itself
   0/  71  VCS-Project-Description-HEREKO-v4.1
  55..77   (each of the 13 real PDDs)
```

The drafting path uses exactly two retrieval entry points (`section_orchestrator.py:712`, `:716`):

- `get_examples_for_section()` — SQL starts `WHERE section_id = ?`. Rows with `section_id=''` can
  never match.
- `get_section_heading_examples()` — `WHERE canonical_heading LIKE ?`. For all four fallback
  documents, `canonical_heading` is a single distinct value equal to the document's own filename
  (verified: `EB111_repan07_ACM0022_v03.0.norm`). A lookup for "Baseline Emissions" never matches.

The full-text `search()` would reach them. **The orchestrator never calls it.**

So: **ACM0022's own methodology text has never appeared in a drafting prompt, and cannot.** What the
model gets instead is prose from thirteen other projects' registered PDDs. The smoke run shows
exactly this in action — five citations, all to other projects, and a paragraph reasoning
"Precedent projects under this methodology (Inegol and Bergama, both Turkey) set BE_WW and BE_NG to
zero… For the current project (Soc Son, Vietnam), the same logic is adopted [INFERENCE]."

That is competent precedent-copying. It is not methodology compliance, and a VVB will read it as the
former. The architecture has one grounding channel where the domain needs two:

- **Normative grounding** — what the methodology *requires* (ACM0022, CDM tools, VCS Standard).
  Citable as authority. Currently: unreachable.
- **Precedent grounding** — how other proponents *phrased and structured* it. Citable as style and
  as sanity check, never as authority. Currently: the only channel.

`pdd-agent index-report` reports rows and documents-with-rows. Both metrics passed their thresholds
while the thing they proxy for — can the drafting path actually find this? — did not move at all.
The instrument measures the wrong side of the join.

---

## Finding 4 — corpus citations are never resolved; their mere presence is scored as grounding

Every provider assesses confidence like this:

```python
marker in text for marker in ("[CORPUS:", "[METHODOLOGY:", "[E0", "[USER INPUT:")
```

A substring check. Nothing resolves `[CORPUS: VCS_Bergama_Project-Description.norm, Baseline
Emissions]` back to a row in the index. A model that invents `[CORPUS: VCS_Nonexistent_Project,
Section 9]` gets scored `HIGH` confidence, and the citation ships in the DOCX.

The pattern for doing this correctly **already exists in the repo**, one directory over. The judge's
`_check_evidence_citations()` (`judge.py:263`) extracts `[E###]` IDs, resolves them against
`project_input.evidence_registry`, and raises a **critical** finding for any ID not in the registry.
The right machinery was built for the citation type that barely appears in real output, and not for
the type that dominates it.

The smoke report's citation-verification section is a human doing this by hand, once, for five
citations. That does not scale to 36 sections, and it is exactly the task a computer should own in a
tool whose entire pitch is provenance.

Same gap for `[CALC: BE_CH4]` — resolvable against the calc result's component names, currently
unresolved.

---

## Finding 5 — the calc engine has no incineration project-emission term, and that is a structural reason the oracle is wrong

`acm0022.py` opens by declaring the methodology equation:

```
PE_y = PE_COMP,y + PE_AD,y + PE_GAS,y + PE_RDF_SB,y + PE_INC,y      [Eq.17]
```

`compute_project()` implements:

```
PE_y = PE_EC + PE_FC + PE_CH4 + PE_FLARE
```

There is no `PE_INC`. Grepping the entire `calc/` package for `incinerat`, `fossil_carbon`, or `N2O`
returns one unrelated RDF field. The engine models the anaerobic-digestion pathway in real depth
(biogas yield, methane fraction, engine efficiency, flare destruction, digestate leakage) and models
the **incineration pathway not at all**.

Both oracle projects are mass-burn incineration WTE plants.

This interacts badly with PHASE-05's composition work. Soc Son's declared composition correctly
excludes 42.5% inert/non-degradable mass from `BE_CH4` — plastics generate no landfill methane, so
excluding them from the baseline is right. But that same plastic is then **burned**, and burning
fossil-derived carbon is a project emission under Eq. 17. The engine takes the credit for diverting
it from landfill and never pays the cost of combusting it. Add N2O from combustion, also absent.

That is a one-directional error, and the oracle results are one-directional:

| Project | Engine | Registered | Error |
|---|---|---|---|
| Soc Son, 7-yr total | 5,397,730 tCO2e | 3,808,082 | **+41.7%** |
| İnegöl, 7-yr total | 893,441 tCO2e | 730,000 | **+22.4%** |

Both overstate. The xfail reasons attribute the gap to "no capacity ramp or site-specific
project-emission inputs" — an *input* problem. Half of it is: `capacity_ramp` (Finding 6). The other
half is not an input problem at all. `PE_INC` cannot be supplied as an input because the engine has
no field for it and no term to put it in. **It is a missing model term, and no config will close it.**

The discipline established by the last two pushes — measure, record the residual, never widen
`TOLERANCE` — is the most valuable thing in the test suite. This finding is what it was preserved for.

---

## Finding 6 — `capacity_ramp` is validated, tested, documented, and inert

PHASE-05 added it to `ProjectTechnology` with a `[0,1]` range validator and four schema tests. Grep
for consumers in `src/`:

```
schemas/project_input.py    (definition + validator)
tests/test_input_schema.py  (validator tests)
```

That is all. No calc engine reads it; the year-by-year FOD schedule that would use it doesn't know
it exists. A user who declares a realistic three-year commissioning ramp gets a validated field and
identical numbers.

This matters beyond the dead code: `capacity_ramp` is named in *both* oracle xfail reasons as one of
the two things needed to close the gap. It was added in the same push that wrote those reasons, and
then not wired up. Year 1 of a WTE plant does not run at nameplate — İnegöl's year-1 error is −51.4%
against the registered *average*, which is the shape you get from exactly this omission.

---

## Finding 7 — `approve-all` approves zero sections on a fresh run (the rice-pilot bug, root-caused)

`docs/2026-07-12-rice-pilot-findings.md` records: "a bulk approve-all loop over the remaining 32
sections did not fully apply (a batch/state-machine interaction not investigated further)." It has
sat unhunted since. It is diagnosable from the code, and I reproduced it:

```
1/1.1 ReviewState.DRAFTED -> can approve? False
4/4.4 ReviewState.DRAFTED -> can approve? False
```

The state machine (`review/states.py:33`) permits exactly one edge into `approved`:

```python
"drafted":              {"needs-input", "needs-domain-review", "ready-for-human-edit"},
"needs-domain-review":  {"ready-for-human-edit", "drafted"},
"ready-for-human-edit": {"approved", "needs-domain-review"},   # <- only edge into approved
```

`init_review_state()` puts every section in `drafted`. `POST /api/runs/{id}/approve-all` iterates and
applies `if section_state.state.can_transition_to(APPROVED)`. For a fresh run that condition is false
for all 36 sections. The endpoint returns **HTTP 200** with `sections_approved: 0`, no list of what
was skipped, and no reason.

The same holds for any section sitting in `needs-domain-review` — which is precisely where
assumption-gated sections land, and precisely the rice pilot's situation.

The July fix rewrote the endpoint to be atomic, with a docstring explaining it "fixes the
read-modify-write race that occurred when clients looped the per-section approve endpoint." It fixed
a race that may or may not have existed. The observed behavior was never a race — it is a missing
multi-hop transition plus a silent skip reported as success. Two things needed: walk the legal path
(`drafted → needs-domain-review → ready-for-human-edit → approved`) rather than requiring the caller
to be already at the last hop, and **never return 200 with a silent partial**.

This is on the critical path of the only human-facing surface the product has.

---

## Finding 8 — the family filter is built; the family map is empty

`configs/corpus_families.yaml`, in full:

```yaml
default_family: wte
documents: {}
```

Every one of the 3,026 indexed rows carries `document_family = 'wte'` (verified). The plumbing
PHASE-02 built — the column, the filter through `search()` / `get_section_examples()`, the slug
resolution in the orchestrator — is correct and completely inert, because the map that would give it
something to discriminate on is empty.

Worse than inert, for non-WTE work. `get_examples_for_section(..., document_family='rice')` returns
nothing, and `search.py:200` then does this:

```python
if not raw and document_family:
    logger.warning("retrieval_family_fallback", family=document_family, section_id=section_id)
    raw = _fetch(None)          # unfiltered — i.e. the WTE corpus
```

So `pdd-agent prove --project rice` grounds a rice-methodology PDD in waste-to-energy prose and emits
`[CORPUS: VCS_Bergama_Project-Description.norm, …]` as its provenance. A structlog warning is the
only trace, and it will not be in the DOCX a reviewer reads.

The safe default for a provenance tool is the opposite: return nothing, let the section carry
`[MISSING]`, and make the absence of family-appropriate corpus a loud, document-visible fact. The
methodology-breadth claim (four calc engines, four rubric sets, family-aware system prompts) remains
a code claim rather than an output claim — and now the *reason* is one empty YAML mapping.

Related: VM0044 and AMS-II.G still have no project config at all (`configs/` holds socson, inegol,
rice). Two of four calc engines are unreachable from the CLI.

---

## Finding 9 — the corpus contains 2,677 destroyed characters, and one document's name is mojibake

Counting U+FFFD replacement characters in the normalized corpus:

```
 1047  VCS_Linfen_Project-Description
  858  VCS_Yingoku_Project-Description
  543  VCS_DRAFT_Yanjiang_Project-Description
  204  VCS_Shunping_Project-Description
   +25 across four others
 2677  total
```

The damage clusters in the Chinese-project PDDs — the normalizer's "surrogate character handler" is
eating CJK. Those characters sit inside indexed chunks, and indexed chunks are pasted verbatim into
prompts as `## Corpus Evidence`.

Separately, one document's stem is itself corrupted: `VCS_Ã_demis_Project-Description.norm`, from
"Ödemiş" — double-encoded at ingestion. `document_name` is what the orchestrator formats into
provenance at `section_orchestrator.py:740`, so any section grounded on that document emits
`[CORPUS: VCS_Ã_demis_Project-Description.norm, …]` into the deliverable. A client would see it.

---

## Finding 10 — normalization is broken for 4 of 17 documents; the last push papered over it

The four unreachable documents share a signature:

```
blocks=1  headings=50   Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2
blocks=1  headings=50   DraftProjectDescription
blocks=1  headings=50   EB111_repan07_ACM0022_v03.0
blocks=1  headings=50   VCS-Project-Description-HEREKO-v4.1
```

All four collapse to a single text block, against a suspiciously round 50-entry headings list from an
older extraction path. The thirteen healthy documents have `blocks == headings + 1`.

The 2026-08-20 gap closure chunked the single blob into 71–124 generic chunks so the documents would
appear in `index-report`. That is why those chunks carry `section_id=""`, and why Finding 3 exists.
The commit is honest about being a workaround — it says so in the code comment — but the plan's exit
criteria were written against the metric, the metric moved, and the phase closed.

The actual fix is upstream: `_build_headings_and_blocks()` in `ingest/normalize.py` finds no real
headings in these four files. That is one function, and it is the difference between the ACM0022
methodology being 96 unusable rows and being the normative grounding channel Finding 3 asks for.

---

## Finding 11 — the export gate blocks on the markers the prompt demands

The v2 prompt instructs the model to emit `[MISSING]` for facts it cannot support. The smoke run
complied, correctly flagging that Vietnam's `RATE_compliance` is not established in the evidence
base. Then:

```
export_gate_forced  hard_blocks=['[4.1] Unresolved [MISSING] marker in quantification/methodology
section.']  message='Exporting with --force override; document is watermarked DRAFT.'
```

`_check_missing_markers()` makes `[MISSING]` a hard block. So **honest real-model output always
requires `--force`**, and `--force` stamps the document DRAFT. The better the model behaves, the more
certainly the export is blocked.

The gate conflates two different states: "the model hallucinated, or the numbers disagree" (genuinely
unsafe to export) and "the model correctly reported that a required input is unavailable" (the tool
working as designed — that gap report is part of what the client is paying for). These need different
treatment: the second should produce a **required-inputs appendix** and an unforced export, not a
hard block.

---

## Finding 12 — the smaller true things

- **The run store is unbounded and growing.** 1,690 files in `data/runs/` (was 1,555 in the last
  brainstorm). `/dashboard` and `/api/runs` both `glob("run-*.json")` and `stat()` every one on every
  request (`service/main.py:392`, `:574`). No pagination, no retention. This is invisible until the
  first live demo, and then it *is* the demo.
- **The service still cannot select `claude-code`.** `_get_provider()` handles demo/noop/ollama/
  openai/anthropic and falls back to `demo` with `reason="unknown_provider"` for anything else. The
  only keyless real-model path the repo has is unreachable from the web UI that is meant to be the
  product. Worse than unavailable: it silently substitutes synthetic output for what the operator
  asked to be real.
- **`claude-code` is undocumented in two more places.** `--provider` help text (`cli.py:99`) lists
  "noop, demo, corpus, openai, anthropic, ollama". The README CLI table lists the same set. The one
  provider that actually ran is in neither.
- **README status drift.** Says "814 tests collected"; actual is 841 passed / 3 xfailed. Says real
  providers "have never executed a live drafting run" — no longer true as of 2026-08-20.
- **`get_active_index_doc_count()` still returns a row count** (`index.py:503`, `COUNT(*) FROM
  sections_fts`) and the scorecard labels it as documents. Now doubly wrong given Finding 3: neither
  3,026 nor 17 is the number a reader should be given; 889 reachable rows across 13 documents is.
- **`registry_download.py` is still a stub**, so the corpus is capped at the 17 manually-downloaded
  documents, four of which don't work (Finding 10). Effective corpus: 13 documents.
- **CI never installs the `ingest` extra.** `pip install -e ".[dev,service,export,llm]"` — so
  pdfplumber's real extraction path added in PHASE-06 is only ever exercised in its ImportError
  branch on CI. The 136-table proof was local and manual.
- **`tables` in `.norm.json` has no consumer.** PHASE-06 extracts them and nothing reads them.
  Accepted at the time as RISK-06-03; worth noting it is the natural input to Finding 5's missing
  composition and project-emission parameters, which are published in the registered PDDs' tables.
- **`section_orchestrator.py` is 1,192 lines** doing retrieval, prompt assembly, calc injection,
  structured-content production, provider dispatch, judging, redraft looping, and review gating. It
  is the file every future change touches.

---

## What this adds up to

The last eight months built a genuinely good pipeline: four calc engines, a real review state
machine, an export gate, cost truth, family-aware prompts, a rebuilt index, deterministic Verra
tables. The suite is 841 tests and the discipline around the oracle xfails is exemplary.

But the repository has been optimizing against synthetic providers, and synthetic providers agree
with whatever the pipeline expects. One $0.20 call disagreed, and it disagreed in three places at
once: the exporter can't render real output (F1), the cap amputates it (F2), and the grounding it
cites is precedent rather than methodology (F3/F4). None of those are visible in any committed demo
artifact.

The strategic read: **the gap between this repo and a deliverable is no longer capability, it is
fidelity.** Every remaining defect has the form "works on synthetic input, breaks on real input."
That is a narrow, closeable class of problem — and most of it is closeable offline, against a run
that has already been paid for.

---

## Proposed tracks

### Track A — Make the deliverable renderable (F1, F2, F11) — **build this first**

A Markdown-aware DOCX renderer: `#` headings → real Word headings at the right level; pipe tables →
real `doc.add_table()` reusing the existing table styling; `**bold**`/`*italic*` → runs; `-`/`1.` →
List Bullet / List Number; fenced code → monospace. Display and inline LaTeX → at minimum a readable
plain-text fallback, ideally OMML.

Then: per-section character budgets sourced from the canonical schema (1.1 is not 4.4), plumbed
through `draft_section(max_chars=…)`, with `max_tokens_per_section` finally wired to something. And a
truncation that is *detected and reported* rather than silent — a section cut at its budget should
carry an issue and a review flag, not look complete.

Then: split the export gate's two meanings, so honest `[MISSING]` markers produce a required-inputs
appendix rather than a hard block.

**Why first:** it is the only track where what a human sees changes. It is fully testable offline
against `smoke-4-1.json`, which we already own. And it must precede any full real run, because
without it a $7 run produces a Word file full of pipe characters.

**Effort:** medium. **Dependencies:** none. **Risk:** low — pure rendering, well-covered by tests.

### Track B — Make grounding real (F3, F4, F9, F10)

Fix `_build_headings_and_blocks()` for the four collapsed documents so their spans map to canonical
sections and stop being `section_id=""`. Add a **normative retrieval channel**: a full-text `search()`
path scoped to methodology documents, injected into Section 3/4 prompts under a distinct
`## Methodology Requirements (normative)` heading, separate from `## Corpus Evidence (precedent)`.
Add `verify_citations()` resolving every `[CORPUS: …]` and `[CALC: …]` against the index and the calc
result — modeled directly on the judge's existing `_check_evidence_citations()` — feeding a real
grounding score and a CRITICAL finding for anything unresolvable. Re-point `index-report` at
*reachable* rows and reachable documents. Fix the normalizer's encoding path and re-normalize.

**Why:** F4 is the credibility floor for a provenance tool, and F3 means the tool has never once
consulted the methodology it claims to apply.

**Effort:** medium-large. **Dependencies:** none, but its payoff is only visible in a real run.

### Track C — Make the number defensible (F5, F6)

Add `PE_INC` to the ACM0022 engine: fossil-carbon CO2 from combusting the non-degradable fraction
(the same fraction the composition path already isolates), plus N2O from combustion, per Eq. 17 and
the relevant CDM tool. Consume `capacity_ramp` in the year-by-year schedule. Re-measure both oracles
and record the residual — never widen `TOLERANCE`.

**Why:** this is the only track that can flip the xfails honestly, and it is the difference between
"an honestly-documented wrong number" and "a number a VVB can check."

**Effort:** medium. **Dependencies:** none. **Risk:** real — the gap may not fully close. Acceptable
if the residual is measured and recorded, which is now this repo's house style.

### Track D — Run the proof

Full 36-section Soc Son run on `claude-code`, after A/B/C. Measured rate: $0.1983/section × 36 ≈
**$7.14**, plus judge/redraft — call it $15 with the cap set there. Deliverable: a real PDD DOCX that
renders, plus a grounding scorecard with every citation machine-resolved.

**Why now and not before:** the reason to defer has been "don't spend on a broken pipeline," and that
reason held. After Track A it becomes "spend on a pipeline that can render what it buys."

**Effort:** small. **Dependencies:** A (hard), B and C (strongly preferred).

### Track E — Product surface (F7, F8, F12)

Fix `approve-all` to walk the legal transition path and never report a silent partial as success.
Populate `corpus_families.yaml` and turn the cross-family fallback into a document-visible degradation
rather than a log line. Run-store pagination and retention. `claude-code` in `_get_provider`, in
`--provider` help, and in the README table. Resync the README status line. Fix
`get_active_index_doc_count()`'s name and label. Add the `ingest` extra to CI.

**Why:** F7 sits on the only human-facing surface the product has, and F8 is one empty YAML mapping
standing between "family-aware code" and "family-aware output."

**Effort:** small, highly parallelizable. **Dependencies:** none. Should not gate the main push.

### Track F — Architectural, for after the fidelity work

Not proposed for the next push; recorded because the shape is now visible.

- **A document-level coherence pass.** 36 independent calls produce 36 independent documents. The
  smoke run numbered its own heading `4.4.1` when asked for `4.1`, and separately discovered that the
  calc engine and `ProjectInput` disagree by 22% on baseline emissions — a genuine finding the model
  surfaced that no section-scoped check would ever catch. One cheap pass over the assembled document
  (heading numbering, cross-references, terminology, number agreement) is worth more than any
  per-section improvement.
- **`pdd-agent verify`.** Resolve every citation, recompute every consistency check, emit a VVB-style
  desk-review checklist for a run. This is the "trust layer" the plan history keeps circling; after
  Track B its components all exist.
- **Diff-against-registered as the sales artifact.** `reports/section-diff.md` currently reports
  grounding score and whether a heading matched. A real "here is our 4.1 next to the registered 4.1"
  comparison is the most persuasive thing this repo could produce, and the reference document is
  already in the corpus.
- **Prompt caching / call batching.** The smoke burned 47,523 tokens for 4,000 characters of output —
  roughly 25k of that is CLI harness overhead per the plan's own measurement. Caching the static
  preamble or batching related sections could cut real-run cost several-fold, which matters once runs
  are routine rather than singular.
- **Split `section_orchestrator.py`.** 1,192 lines across seven responsibilities.

---

## What I would do next, if it were my call

**Track A + Track E as one push, with Track C as its closing phase.**

Track A because the exporter defect invalidates every future real run and is provable offline against
an artifact we already bought. Track E because it is small, independent, and F7 is a reproduced bug
on the human path. Track C at the end because it carries genuine risk of not closing and a partial
result is still a good outcome — the same shape that worked for the last plan's Track B.

Track B is the one I would hold for the following push, not because it matters less — F4 is arguably
the deepest issue here — but because it is the largest, it touches ingestion, and its payoff is only
legible once a real run can be rendered and read. Doing A first means Track B's improvements land in
a document someone can actually evaluate.

Track D stays gated behind explicit authorization, and after A it is a $7–15 decision rather than a
$15 leap of faith.

The thing to resist this time is the symmetric temptation to the last one. Last session's trap was
running the proof on a broken index. This session's trap is **fixing grounding again** — it is the
familiar problem, the last push was about it, and there is a satisfying finding waiting there
(F3/F4). But the artifact is broken at the last mile, and no amount of better grounding survives
being rendered as `| $BE_{CH4,t,y}$ | Baseline methane emissions … |` in a Word file.

---

## Assumptions adopted where I would otherwise have asked

Per the unattended-session rule, these were decided rather than raised:

- **ASM-A:** The full real-model run still requires human authorization; it appears here as Track D,
  gated, with the cost now measured rather than estimated ($7.14 for 36 sections at the observed
  rate). No work below assumes it happens.
- **ASM-B:** Rendering fidelity outranks grounding depth for the next push. Justified by F1 — the
  defect is downstream of every other fix, so any improvement made before it is invisible.
- **ASM-C:** LaTeX in model output is treated as something to render, not something to forbid. The
  model reached for it because ACM0022 is an equation-heavy methodology and the registered PDDs it
  learned from contain equations. Prompting it away would degrade the content to protect the
  exporter. If OMML proves expensive, a plain-text math fallback is acceptable for a first pass.
- **ASM-D:** Per-section character budgets belong in `schemas/pdd_section_schema.yaml` next to the
  existing per-section `guidance`, `content_class`, and `review_sensitivity` — not in a new config
  file. Consistent with how every other per-section attribute is already carried.
- **ASM-E:** `PE_INC` is in scope for the ACM0022 engine as a modeled term with declared default
  factors (IPCC fossil-carbon fraction of MSW, N2O EF), overridable per project — not as a required
  input. Required inputs would break the six existing configs, against the repo's CON-004
  backward-compatibility precedent.
- **ASM-F:** The committed demo packages under `reports/demo-packages/` are **not** regenerated as a
  ride-along, even though Track A would visibly improve them. Same reasoning as the last plan's
  ASM-F: a committed client contract deserves its own diff-reviewed change.
- **ASM-G:** Cross-family retrieval fallback should be *removed*, not merely warned about — a rice
  project with no rice corpus should produce `[MISSING]`, not WTE citations. Stated as a
  recommendation rather than a decision because it reverses behavior that ASM-004 of the prior plan
  deliberately chose; flagged for the plan author to confirm.

## Considered and rejected

- **Prompt the model to emit plain prose instead of Markdown.** Rejected. It suppresses the tables
  and equations a Verra PDD is supposed to contain, to work around a renderer limitation. Fix the
  renderer.
- **Raise `max_chars` to a large constant and move on.** Rejected as half a fix. The cap being wrong
  is one problem; being uniform across a 36-section document with a 100× spread in natural section
  length is the other, and only the second determines whether the output resembles a real PDD.
- **Widen the oracle `TOLERANCE` now that the cause of the gap is understood.** Rejected, again and
  emphatically. Understanding *why* the number is wrong is a reason to fix the model, not to accept
  the number.
- **Swap FTS5/BM25 for embeddings.** Rejected again, and for a sharper reason than last time: 70% of
  the index is unreachable because of a `WHERE section_id = ?` clause, not because BM25 ranked badly.
  Embeddings would retrieve the same unreachable rows.
- **Rewrite the review state machine to allow `drafted → approved` directly.** Rejected. The
  intermediate states are the product — they are what makes this a review tool rather than a
  generator. The bug is that `approve-all` doesn't walk them and lies about it, not that they exist.
- **Unstub `registry_download.py` to grow the corpus.** Rejected for this push, third time running.
  Four of the seventeen documents already on disk still don't reach a prompt (F3/F10). Fix those
  first.
- **Split `ProjectInput` into per-family discriminated unions.** Still rejected, consistent with
  DEC-004. No second real non-WTE project has landed since the rice pilot.
