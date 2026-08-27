---
title: "Assembly and Defensible Numbers: what the repo needs after real-output fidelity"
date: "2026-08-27"
author: "unattended analysis session"
inputs:
  - "plans/2026-08-21-real-output-fidelity-plan.md (status: complete)"
  - "research/2026-08-21-pdd-real-output-gap-brainstorm.md"
  - "live repository state at 6062b1c"
---

# Brainstorm: Assembly, Defensible Numbers, and the Grounding the Tool Still Cannot Cite

## How this session differs from the last one

The 2026-08-21 push closed the rendering gap: real Markdown now becomes real Word content, the
export gate stopped punishing honesty, per-section budgets exist, and the ACM0022 engine finally
charges an incinerator for burning plastic. All 49 tasks verified in-repo this morning; the suite
reproduces at **909 passed, 7 deselected, 4 xfailed** in 72s.

So this session did not re-audit rendering. It went looking for what is *now* the binding
constraint, and it ran the calc engine against the registered Soc Son PDD with modified parameters
to find out whether the two remaining `xfail`s are structural or parametric.

The short answer, and the headline of this brief:

> **Both remaining oracle discrepancies are parameter-provenance bugs, not model-structure bugs.
> With IPCC tropical-wet decay rates and a plastics fraction near 9%, the engine reproduces the
> registered Soc Son PDD's seven-year total to +0.3% and its net non-methane charge to 0.2%.**
> Measured this session, offline, with no code changes.

The second theme is the one the last brief flagged and deferred (Track F): **nobody owns the
assembled document.** Thirty-six independent calls produce thirty-six independent documents, and
the exporter staples them together without numbering, deduplication, or cross-section agreement.
That is now visible in a real export.

---

## Finding 1 (headline) — the two oracle `xfail`s are a decay-rate table and a waste fraction

### D-1: the FOD decay rates are the temperate-wet column, labelled "wet tropical"

`src/pdd_agent/calc/constants.py:87` reads:

```python
# Decay rates by waste type (1/year) - IPCC 2006 Table 3.3, wet tropical
DECAY_RATE_BY_WASTE_TYPE = {
    "food_waste": 0.185, "garden_waste": 0.100, "paper_cardboard": 0.060,
    "wood": 0.030, "textiles": 0.060, "municipal_solid_waste": 0.09, ...
}
```

Those are IPCC 2006 Vol.5 Table 3.3's **boreal/temperate, wet** values. The **tropical, wet** column
(MAT > 20 C, MAP > 1000 mm — i.e. Hanoi) is roughly twice as fast: food 0.40, garden 0.17,
paper 0.07, wood 0.035, bulk MSW 0.17. The comment claims the column the code does not use.

Measured, by monkey-patching the table and re-running `compute_for()` on
`configs/projects/vietnam_socson_from_sheet.yaml`:

| BE_CH4 (tCO2e) | y1 | y2 | y3 | y4 | y5 | y6 | y7 | 7-yr | vs registered |
|---|---|---|---|---|---|---|---|---|---|
| engine today | 137,368 | 252,460 | 348,986 | 430,029 | 498,158 | 555,509 | 603,859 | 2,826,368 | **-35.5%** |
| tropical-wet k | 261,521 | 439,368 | 560,956 | 644,671 | 702,850 | 743,772 | 772,996 | **4,126,134** | **-5.9%** |
| registered (Table 9) | 277,866 | 466,829 | 596,016 | 684,963 | 746,778 | 790,258 | 821,308 | 4,384,018 | — |

Not just the total: the *shape* of the curve now tracks the registered schedule year by year, every
year inside 6%. D-1's xfail reason ("baseline methane too low", RISK-05-03, "FOD parameter gap, out
of scope") is correct about the cause and one table away from a fix.

### D-2: the plastics fraction is a documented guess, and it is the whole discrepancy

`vietnam_socson_from_sheet.yaml` splits the registered PDD's 43.8% "glass/plastic/metal/other-inert"
bucket into `plastics: 0.030` + `inert: 0.408`, sourced to *Section 3.2 applicability text*, not to
Table 8. `PE_INC` scales almost linearly with that fraction. Sweeping it, with tropical k applied:

| plastics | PE_INC (tCO2e/y) | net non-methane/y | 7-yr net | vs registered 3,808,082 |
|---|---|---|---|---|
| 0.030 (today) | 187,895 | +169,111 | 5,309,908 | +39.4% |
| 0.070 | 342,714 | +14,292 | 4,226,179 | +11.0% |
| **0.085** | ~421,000 | -43,765 | **3,819,781** | **+0.3%** |
| **0.095** | ~459,000 | **-82,469** | 3,548,849 | -6.8% |
| registered | — | **-82,277** | 3,808,082 | — |

Two independent targets — the crediting-period total and the net non-methane charge — are matched by
plastics fractions of 8.5% and 9.5% respectively. They agree within one percentage point, and 9%
plastics in Hanoi MSW is an entirely ordinary number.

### What this means, stated carefully

This is a two-parameter fit against two targets, so it is **evidence, not proof**. It must not be
committed as a tuned constant. What it justifies is a specific, falsifiable piece of work:

1. Make the FOD parameters **climate-zone-aware**, with the zone derived from
   `location.latitude` / `location.country` and overridable explicitly. Cite the IPCC table for all
   four zones rather than pasting one column and mislabelling it.
2. Read the **registered Table 8** out of the Soc Son PDF (see Finding 2) and use the real
   composition — whatever it says — instead of the applicability-text guess.
3. Re-measure both oracles and Inegol. `TOLERANCE` stays 0.20 and is never widened (DEC-004).

And a warning about sequencing: **D-1 and D-2 must be closed in the same phase.** Fixing D-1 alone
moves the seven-year total from 4,010,142 (+5.3%, currently passing) to 5,309,908 (+39.4%), which
would *break* the test that was flipped green last week. The two errors have been cancelling.

---

## Finding 2 — the registered PDDs' tables were extracted into a code path nothing has ever run

PHASE-06 added `_extract_tables()` (pdfplumber) to `ingest/normalize.py` and a `tables` key to the
normalization record. Every one of the 17 committed `.norm.json` files predates it:

```
keys: ['file','mime_type','parseable','word_count','heading_count','pages','text','headings','text_blocks']
```

No `tables` key at all — across all 17 documents, `tables = 0`. The corpus on disk was never
re-normalized after the feature landed. The last brief recorded "`tables` has no consumer"; the
sharper statement is that **it has no producer either, in any artifact that exists.**

This matters because Finding 1's missing input — Soc Son Table 8, "Components of solid waste" — is
exactly a table in exactly one of those PDFs. The tool's own ingestion path can read it; nothing has
asked it to. Same for Table 9 (the year-by-year baseline methane schedule now hard-coded in
`tests/test_registered_pdd_oracle.py`) and for every other registered project's composition.

The work: re-normalize with the `ingest` extra installed, then add the one consumer that turns a
registered composition table into calc inputs, or into a proposed diff against a project config.
That converts the oracle from "hard-coded numbers a human typed once" into "numbers the pipeline
can re-derive".

---

## Finding 3 — the four unreachable documents are an ingestion-source bug, and the PDFs are on disk

The last brief attributed the four collapsed documents (`blocks=1, headings=50`) to
`_build_headings_and_blocks()` failing to find headings, and proposed rewriting that function. That
diagnosis is wrong, and the real one is much cheaper to fix.

`data/corpus/manifest.jsonl` shows all four with:

```
mime_type: text/plain
local_raw_path: ref\PDD staff test-...\generated_pdd\extracted_text\EB111_repan07_ACM0022_(v03.0).txt
```

They were ingested from **pre-extracted `.txt` files** produced by a colleague's earlier pipeline.
`_extract_text()` has branches for `application/pdf` and DOCX only; text/plain falls through to
`"Unsupported MIME type"`. The single blob and the suspiciously round 50-entry heading list are
artifacts of that other pipeline, faithfully preserved.

The original PDFs are present in the repo:

```
ref/PDD staff May 2026/inputs/EB111_repan07_ACM0022_(v03.0).pdf
ref/PDD staff May 2026/inputs/Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2.pdf
ref/PDD staff May 2026/inputs/DraftProjectDescription.pdf
ref/PDD staff May 2026/inputs/VCS-Project-Description-HEREKO-v4.1_2022-10-24.pdf
```

So the fix is: point the manifest at the PDFs, and/or add a text/plain branch that runs the same
heading pass, then re-normalize and rebuild. The thirteen healthy documents all show
`blocks == headings + 1` through `_extract_pdf`; there is no reason these four would behave
differently. That is the difference between the ACM0022 methodology being **0 of 96 reachable rows**
and being the normative grounding channel the tool has never had.

Current reachability, reproduced this session with `pdd-agent index-report` and a direct query:

```
Total rows 3026 | Reachable rows 889 | Reachable documents 13 of 17
   0/  96  EB111_repan07_ACM0022_v03.0      <- the methodology itself
   0/  75  Bergama_...Monitoring-Report-v4.2
   0/ 124  DraftProjectDescription
   0/  71  VCS-Project-Description-HEREKO-v4.1
```

---

## Finding 4 — grounding still cannot cite the methodology, and citations still resolve to nothing

Two separate defects, both unchanged since the last brief, both now easier to fix than they were.

**(a) No normative channel.** `SectionOrchestrator` calls exactly two retrieval entry points, both
section-id/heading keyed. It never calls `search()`. I ran `search()` by hand on three methodology
queries ("applicability conditions incineration", "baseline emissions BE_CH4 equation", "project
emissions from incineration N2O"): **zero hits from `EB111` in any of them**, twelve hits from other
projects' PDDs. The methodology rows are in FTS5 and are matchable by a raw SQL `MATCH`, but they
lose on BM25 because each row is a ~1,800-character page blob whose `canonical_heading` is the
document's own filename. So even wiring `search()` in would not surface them until Finding 3's
re-ingestion gives them real headings and section-sized chunks. The two fixes are one piece of work.

**(b) Nothing resolves a citation.** All four real providers still score confidence with

```python
marker in text for marker in ("[CORPUS:", "[METHODOLOGY:", "[E0", "[USER INPUT:")
```

and the judge resolves `[E###]` against the evidence registry but leaves `[CORPUS:` and `[CALC:`
alone (`review/judge.py:309` — a substring check). A model that invents a document name is scored
HIGH and ships. Note for whoever builds the resolver: the one real section on disk emits
`[CORPUS: VCS_Inegol_Project-Description.norm; CORPUS: VCS_Bergama_Project-Description.norm]` —
compound, semicolon-joined. The resolver has to parse what models actually write, not what the
prompt asks for.

---

## Finding 5 — the pipeline grounds Soc Son on the registered Soc Son PDD

The most recent 36-section demo run (`run-20260827163336-a769c7.json`, project "Soc Son-like
Waste-to-Power Demonstration Project") carries 141 corpus provenance entries:

```
   54  VCS_Inegol_Project-Description.norm
   48  VCS_Bergama_Project-Description.norm
   39  VCS_Soc_Son_Project-Description.norm     <- the answer key
```

Two consequences. First, **every quality claim made from a Soc Son demo is contaminated** — the tool
is being graded on reproducing a document it is reading. Second, only **3 of 13** reachable
documents supplied any grounding at all across 36 sections, so the effective corpus for a run is a
quarter of the corpus the metrics advertise.

The fix is small: an `exclude_documents=` parameter threaded through `get_examples_for_section()`
and `search()`, and a leave-one-out mode used by the benchmark and any diff-vs-registered
evaluation. It is a precondition for the thing this repo most needs and does not have — see Track D.

---

## Finding 6 — nobody owns the assembled document

I exported the one real-model run (`smoke-4-1`) and read the heading tree out of the DOCX:

```
Heading 1  4 QUANTIFICATION OF GHG EMISSION REDUCTIONS AND REMOVALS
Heading 2  Baseline Emissions
Heading 3  4.4.1 Baseline Emissions          <- the model's own title, echoed, misnumbered
Heading 4  Methodology Basis
Heading 4  Quantified Baseline Emissions
Heading 4  Data Conflict Flag
```

Three defects visible in six lines:

- **Title echo.** The exporter writes the canonical heading; the model writes it again. Every real
  section will do this, because the prompt asks for `## H2` with the section heading.
- **Numbering.** The exporter's subsection headings carry no number ("Baseline Emissions"), while
  the Verra v4.4 template numbers them (1.1, 1.2, ...). The only numbers in the document are the
  ones the model invented, and it invented `4.4.1` for section `4.1`.
- **No document-level pass at all.** Thirty-six sections are drafted independently, in a loop, with
  no step that reads the assembled result. Cross-section number agreement, terminology consistency,
  duplicate content, and internal cross-references are unowned. The one real section found a 22%
  disagreement between the calc engine and `ProjectInput` *by itself* — a finding no section-scoped
  check produces, and no assembled-document check exists to produce it either.

This is the last mile of a document product, and it is cheap: the deterministic part (strip a
leading heading that restates the section title, demote the rest, apply canonical numbering,
renumber tables and figures) is pure rendering work testable offline against `smoke-4-1`. The
non-deterministic part (one coherence pass over the assembled document) is one call, not 36, and it
is the highest-value single LLM call the pipeline could make.

---

## Finding 7 — the budget mechanism instructs the model to do the opposite

PHASE-02 gave each subsection a budget of 2,000-20,000 characters. Three things undercut it:

1. **The live prompt never states a length.** `_build_prompt()` builds the prompt in Python and says
   nothing about how long the section should be. The model has no target.
2. **The document that does state a length says 2,000 — and is dead code.**
   `prompts/section_draft_v2.md:137`: "Keep sections under 2000 characters". No module loads
   `section_draft_v2.md` or `section_draft.md` (grep across `src/` returns nothing; only
   `prompts/methodologies/*.md` and `prompts/extract_project_input.md` are read). Two sources of
   prompt truth, and the stale one is the only one with a length rule — pointing the wrong way for
   the 20,000-character sections.
3. **Characters are passed as tokens.** `openai_provider.py:158` and `ollama_provider.py:147` do
   `max_tokens = min(self._config.max_tokens, max_chars)`. With `ModelConfig.max_tokens = 4000`
   (`llm/provider.py:169`) the API providers are still capped at 4,000 *tokens* regardless of a
   20,000-character budget; `claude_code_provider` sets no output cap at all and truncates the text
   afterwards — so on the one provider that has actually run, every character over budget is
   generated, paid for, and thrown away.

Budgets are currently enforced by amputation, one layer further down than before. The fix is to
state the target length in the prompt, convert chars to tokens with an explicit ratio plus headroom,
and delete the dead prompt files (or make them the source of truth — but not both).

---

## Finding 8 — the first real full run will hit the default budget and lose the work

Three facts that compose badly:

- Default `TokenBudget.max_tokens = 500_000` (`llm/budget.py:81`), configurable only via
  `PDD_MAX_TOKENS` / `PDD_MAX_COST_USD` env vars — there is **no CLI flag** for either.
- The measured `claude-code` rate is ~47.5k tokens per section (CLI harness overhead dominates; our
  prompts are only ~9,000 chars, about 2.3k tokens). 36 sections is roughly 1.7M tokens.
- Budget exhaustion is handled *gracefully* — each remaining section becomes a
  `[BUDGET EXHAUSTED — ...]` placeholder with UNSUPPORTED confidence.

So the default run drafts roughly ten sections and then writes twenty-six placeholders into a
document that exports without complaint. Worse, **nothing is persisted until the loop finishes**:
`_store_draft()` only mutates in-memory state, and `DraftRun.save()` runs after
`draft_all_sections()` returns. A network blip, a CLI timeout, or Ctrl-C thirty sections into a paid
run loses all of it. Drafting is also strictly serial, so the run is 30-60 minutes of wall clock
before anyone sees whether section 1.1 was any good.

Pre-flight estimate, save-after-each-section, `--resume`, bounded concurrency (4-6 workers), and CLI
budget flags are a day of work that turns a $7-15 spend from a leap into a procedure.

---

## Finding 9 — corpus text is still damaged, and the mojibake is now hard-coded in config

Counting U+FFFD across the normalized corpus (all fields):

```
3,141  VCS_Linfen        2,574  VCS_Yingoku        1,629  VCS_DRAFT_Yanjiang
  621  VCS_Shunping         75  across four others         8,040 total
```

The damage clusters in the Chinese-project PDDs and sits inside indexed chunks, which are pasted
verbatim into prompts. Separately, one document's stem is double-encoded — from "Odemis" with its
diacritics — and the last push, reasonably, copied that mojibake **byte-for-byte into
`configs/corpus_families.yaml`** with a comment telling future maintainers not to retype it. The
workaround is correct and the underlying defect is now load-bearing: the corrupted name is what gets
formatted into `[CORPUS: ...]` provenance and printed in a client-visible document. Fixing extraction
encoding means fixing the config in the same commit.

---

## Finding 10 — the tool only runs from its own source checkout

Nineteen call sites resolve assets as `Path(__file__).parent.parent.parent.parent / ...` — prompts,
schema, templates, configs, `data/runs`, `rules/`, `data/methodologies`. The wheel packages
`["src/pdd_agent", "schemas"]` only.

So `pip install pdd-agent` yields a tool that: has no Verra v4.4 template (silently falls back to a
blank `Document()`), no methodology overlays (drafting loses its domain framing), no
`model_pricing.yaml` (cost accounting degrades to zeros), and no `corpus_families.yaml` (every
project becomes WTE). None of this fails loudly. It has never mattered because every run happens in
the checkout — and it will matter on the first day someone runs the service anywhere else, which is
the direction the product is going.

---

## Finding 11 — the smaller true things

- **`pdd-agent --help` crashes on Windows.** `UnicodeEncodeError: 'charmap' codec can't encode
  character '→'` — the `ingest` subcommand help contains an arrow, and any non-UTF-8 stdout (a
  pipe, a cp1252 console) kills the entire help output. The primary development and demo machine is
  Windows 11. Reproduced this session.
- **The test suite writes into the production run store.** A full `pytest` run leaves about 7 new
  `run-*.json` files in `data/runs/` (21 today). The store now holds **1,770 files / 187 MB** with no
  retention policy. Pagination shipped last week; retention did not.
- **`pdd-agent doctor` still reports the headline number** ("3026 rows in sections_fts") while
  `index-report` now reports 889 reachable / 13 documents. Two instruments, two answers.
- **No `run_id` validation in the service.** Run ids from the URL are formatted straight into
  `data/runs/{run_id}.json`. Low risk on localhost; free to fix.
- **README status drift, again.** "live drafting runs are pending API keys" — `claude-code` is
  keyless, present (`claude CLI 2.1.247` per doctor), and has already produced the real section the
  last two pushes were built around.
- **`section_orchestrator.py` grew to 1,280 lines** (from 1,192) during a push that was not about it.
- **Three Verra renderers still have no producer** (`risk_assessment`, `sustainable_development`,
  `data_gaps`).
- **Nothing is cacheable.** The prompt's section-specific header comes first, so two section prompts
  share a 40-character literal prefix out of ~9,000. `CallRecord` already tracks
  `cache_creation_tokens` / `cache_read_tokens`; no provider ever sets `cache_control`. Reordering
  static content (overlay, project facts, instructions) to the front would make about half the
  prompt cacheable for free.

---

## What this adds up to

The last push fixed *how the output looks*. This brief is about *whether the output is right*, and
it splits cleanly in two:

- **The number is one commit away from defensible.** Two parameter corrections reproduce a
  registered, validated PDD to within a percent. That is the single most valuable thing this
  repository could put in front of a VVB or a client, and it is measurable offline today.
- **The document is one pass away from professional.** Numbering, title echo, and cross-section
  coherence are the difference between "36 good sections" and "a PDD".

Everything else — normative grounding, citation resolution, leave-one-out evaluation — is the layer
that makes those two claims *checkable by someone else*, which is the actual product.

---

## Proposed tracks

### Track A — Close both oracle discrepancies together (F1, F2) — **build this first**

Climate-zone-aware FOD parameters (all four IPCC zones, zone derived from latitude/country,
explicitly overridable); re-normalize the corpus so `tables` exists; read the registered Soc Son
Table 8 and use the real composition; re-measure Soc Son *and* Inegol; record residuals.
`TOLERANCE` untouched.

**Why first:** it is the only track that changes what the tool asserts about the world, the evidence
is already measured, and the risk is understood (the two errors cancel today, so the phase must
close both or neither). If Table 8 turns out to say plastics is 3%, that is a finding too — it means
the model structure is wrong somewhere else, and we will have learned it cheaply.

**Effort:** medium. **Dependencies:** none. **Risk:** medium, and bounded — worst case is a measured,
documented residual, which is this repo's house style.

### Track B — Own the assembled document (F6, F7)

Deterministic assembly pass: strip title-echo headings, demote and renumber model headings to the
canonical scheme, number subsections per the Verra template, renumber tables and figures. Then wire
the budget properly: state the target length in the prompt, convert chars to tokens, remove or adopt
the dead prompt files. Then a document-level coherence check over the assembled run (number
agreement across sections, terminology drift, unresolved cross-references) — rule-based first, with
one optional LLM pass behind a flag.

**Why:** it is the visible last mile, it is fully testable offline against `smoke-4-1`, and it must
land before any full real run, for the same reason the renderer had to.

**Effort:** medium. **Dependencies:** none. **Risk:** low.

### Track C — Make grounding citable (F3, F4, F9)

Re-ingest the four text/plain documents from the PDFs that are already on disk; fix the extraction
encoding and the corrupted filename (updating `corpus_families.yaml` in the same commit); rebuild
the index; add a **normative retrieval channel** (`search()` scoped to methodology documents,
injected under its own `## Methodology Requirements (normative)` heading, distinct from precedent);
add `verify_citations()` resolving `[CORPUS: ...]` and `[CALC: ...]` against the index and the calc
result, modelled on the judge's existing `_check_evidence_citations()`, tolerant of the compound
syntax real models emit.

**Why:** F4 is the credibility floor for a provenance tool, and after Track C's re-ingestion the
methodology is retrievable for the first time. Cheaper than the last brief estimated, because the
fix is an ingestion-source correction rather than a heading-heuristic rewrite.

**Effort:** medium-large. **Dependencies:** none, but its payoff is legible only in a real run.

### Track D — The scoreboard the repo does not have (F5)

Leave-one-out exclusion in retrieval, then a `diff-against-registered` harness: draft Soc Son with
the Soc Son PDD excluded from the corpus, and score each generated section against the registered
one (coverage of required elements, number agreement, citation resolution rate). Today every metric
in this repo measures the pipeline against itself — 909 tests, a grounding score that counts
substrings, a judge whose rubric we wrote. This is the first metric that would measure it against
the world.

**Effort:** medium. **Dependencies:** Track C (for citation resolution to be scoreable); Track A (so
the numbers being compared are the fixed ones).

### Track E — Make the real run survivable (F8), then run it

Pre-flight token and cost estimate printed before the first call; save after every section;
`--resume`; bounded concurrency; CLI flags for budget. Then the full 36-section `claude-code` run at
a measured $7-15, which stays gated on explicit human authorization.

**Effort:** small. **Dependencies:** Tracks A and B strongly preferred (spend on a pipeline whose
numbers and layout are right).

### Track F — Deployability and hygiene (F10, F11)

Repo-root resolution helper plus packaged data files (or an explicit `PDD_ASSET_DIR`); ASCII-safe
CLI help; test isolation so the suite stops writing into `data/runs`; a retention policy; align
`doctor` with `index-report`; `run_id` validation; README status resync. Small, parallel, should not
gate the main push.

---

## What I would do next, if it were my call

**Track A + Track B as one push, with Track E's pre-flight and checkpointing as its closing phase.**

Track A because the finding is sitting right there, measured, and "our engine reproduces a
registered PDD to within a percent" is a categorically different sentence from anything this
repository can currently say. Track B because it is cheap, offline, and it is what a human sees.
Track E's first half because it is the difference between the real run being an experiment and being
a procedure.

Track C next, as its own push — it is the largest, it touches ingestion, and it wants the assembled
document to land first so its improvements can be judged. Track D after C, because a scoreboard
built on unresolved citations measures the wrong thing.

The trap to avoid this time: **treating the parameter finding as a fix rather than as a hypothesis.**
It would be very easy to paste `k = 0.40` and `plastics = 0.09` into the constants and watch two
xfails turn green. That would be tuning to the test, and it is the exact failure this repo's oracle
discipline exists to prevent. The parameters have to come from the IPCC table and from Table 8 of
the registered PDF respectively, and if the extracted table disagrees with 9% plastics, the extracted
table wins and the residual gets recorded.

---

## Assumptions adopted where I would otherwise have asked

Per the unattended-session rule, these were decided rather than raised:

- **ASM-A:** Climate zone is *derived* (latitude plus country) with an explicit override field, not a
  new required input — consistent with CON-004 backward compatibility for the six existing configs.
- **ASM-B:** D-1 and D-2 are closed in a single phase. Measured justification: fixing D-1 alone moves
  the seven-year total from +5.3% to +39.4% and breaks a currently-passing test.
- **ASM-C:** `TOLERANCE` stays 0.20. Restated because the temptation is now larger, not smaller.
- **ASM-D:** Re-normalizing the corpus is in scope even though `data/corpus/normalized/` is
  gitignored: the index, `index-report`, and every grounding metric derive from it. The committed
  `demo/corpus` subset is left alone unless a test forces otherwise — it is a demo contract.
- **ASM-E:** Leave-one-out exclusion is an explicit parameter used by the benchmark and evaluation
  paths, defaulting off. Silently changing what existing runs retrieve would invalidate comparisons
  mid-flight.
- **ASM-F:** `prompts/section_draft.md` and `prompts/section_draft_v2.md` are deleted rather than
  wired up. The live prompt is code, it has been code for months, and a stale second source of truth
  that contradicts the shipped budgets is worse than no file. Flagged for confirmation because it
  deletes documentation someone may still be reading.
- **ASM-G:** The committed `reports/demo-packages/` are **not** regenerated as a ride-along, even
  though Tracks A and B would change them visibly. A client-facing contract deserves its own
  diff-reviewed change. (Same call as the last two briefs.)
- **ASM-H:** No money is spent. Track E's run stays gated on explicit authorization; every finding
  above was reproduced offline against artifacts already on disk.

---

## Considered and rejected

- **Paste the tropical decay rates and the 9% plastics fraction and flip the xfails.** Rejected —
  see the trap above. The parameters must be sourced, not fitted.
- **Widen `TOLERANCE` now that both discrepancies are understood.** Rejected, for the third time. An
  explanation is a reason to fix the model.
- **Rewrite `_build_headings_and_blocks()` for the four collapsed documents** (the last brief's
  recommendation). Rejected on evidence: those documents were never processed by that function. They
  arrived as pre-extracted `.txt`, the PDFs are in `ref/`, and re-ingesting them is a manifest change
  plus a re-run.
- **Swap FTS5/BM25 for embeddings.** Rejected again. The methodology is unretrievable because its
  chunks are page blobs titled with a filename; embeddings would embed the same blobs.
- **A document-level LLM coherence pass before the deterministic assembly fixes.** Rejected —
  paying a model to notice that a heading is misnumbered when a renumbering pass is deterministic.
- **Splitting `section_orchestrator.py` now.** Deferred, but with a trigger: extract prompt assembly
  when Track B touches it, since that is the seam Track B already has to open.
- **Unstubbing `registry_download.py` to grow the corpus.** Rejected, fourth time. Four of seventeen
  documents on disk still do not reach a prompt.
- **Adding auth to the FastAPI service.** Rejected as premature; it is a localhost review tool. The
  `run_id` validation in Track F is worth doing regardless.

---

## Evidence appendix — what was reproduced, and how

All commands run this session on the checkout at `6062b1c`, with no code modified.

```
python -m pytest -m "not corpus" -q           -> 909 passed, 7 deselected, 4 xfailed (72s)
pdd-agent index-report                        -> 3026 rows / 17 docs; Reachable 889 / 13
pdd-agent doctor                              -> claude CLI 2.1.247; no API keys; 3026-row index
pdd-agent --help                              -> UnicodeEncodeError (cp1252, arrow glyph)
export_run_to_docx("smoke-4-1")               -> 138 paragraphs, 8 tables, heading tree in F6
sqlite3 data/index/corpus.fts.db              -> per-document reachable-row table in F3
compute_for(socson) with patched k / plastics -> the two tables in F1
json scan of data/corpus/normalized/*.json    -> no `tables` key; 8,040 U+FFFD; blocks/headings
run-20260827163336-a769c7.json                -> 141 provenance entries, 39 from Soc Son itself
```
