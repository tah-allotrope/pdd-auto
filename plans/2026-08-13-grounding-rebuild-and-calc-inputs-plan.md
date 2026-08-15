---
title: "Rebuild the Grounding Layer, Render the Verra Tables, and Give the Calc Engine Its Inputs"
date: "2026-08-13"
status: "open"
request: "Implement the 2026-08-13 brainstorm: rebuild the retrieval/grounding layer (Track A), render prose+tables and wire the deterministic Verra renderers (Track C), give the ACM0022 engine real waste-composition inputs (Track B), with a sub-$1 single-section real-model smoke check as a mid-plan gate (Track D)."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-08-13-pdd-hollow-grounding-and-calc-inputs-brainstorm.md"
---

# Plan: Rebuild the Grounding Layer, Render the Verra Tables, and Give the Calc Engine Its Inputs

## Objective

The retrieval index this project's architecture is named for ("corpus-bucketed RAG") contains 1,015
rows holding only **270 distinct texts**, 97.7% of them truncated at exactly 500 characters, drawn
from **13 of the 17** normalized corpus documents. Every provenance citation, grounding metric, and
judge grounding score is computed over that substrate. Separately, the ACM0022 calculation engine
silently drops **one third of Soc Son's declared waste throughput** and splits the remainder evenly
across waste types whose real proportions are published in the project's own registered PDD.

This plan rebuilds the index on real section spans, makes the exported DOCX render Verra's tables
alongside its prose, and feeds the calc engine the composition data it has been guessing at — then
spends about $0.20 on the first real-model call this repository has ever made in anger.

## Context Snapshot

- **Current state:**
  - `data/index/corpus.fts.db`: 1,015 rows, **270 distinct `text` values (73.4% duplication)**, 992
    rows exactly 500 characters long, **13 distinct `document_name` values** out of 17 normalized
    documents on disk. The four documents contributing zero rows are
    `EB111_repan07_ACM0022_v03.0` (the ACM0022 methodology itself),
    `Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2`, `DraftProjectDescription`, and
    `VCS-Project-Description-HEREKO-v4.1`.
  - `src/pdd_agent/parse/section_parser.py:121` `_find_content_page()` returns the first non-TOC page
    whose text contains the heading string, truncated to 500 characters. Every heading landing on the
    same PDF page therefore receives byte-identical "content", including running headers and page
    numbers. `src/pdd_agent/retrieval/index.py:119` re-truncates it to 500.
  - The normalized JSON files **already contain the correct data and it is unused**: each
    `data/corpus/normalized/*.norm.json` carries a `text_blocks` list of `{heading, text}` segments
    built by `src/pdd_agent/ingest/normalize.py:156` `_build_headings_and_blocks()`. Soc Son has 190
    headings and 191 text blocks; page 5 alone holds 2,463 characters.
  - `RetrievalIndex.build()` inserts empty strings for `content_class` and `review_sensitivity`
    (`index.py:126`), while `RetrievalIndex.search()` exposes a `content_class` equality filter
    (`index.py:164-166`) that `search()` in `retrieval/search.py:109` documents. **Any caller passing
    `content_class` receives zero results, always.**
  - Retrieval has no methodology/family filter. All 17 corpus documents are waste-to-energy, so
    `configs/projects/rice_vm0051_pilot.yaml` drafts a VM0051 rice PDD grounded on WTE prose and cites
    it as provenance.
  - `src/pdd_agent/export/docx_export.py:710-720` `_TABLE_RENDERERS` holds eleven VCS v4.4 table
    renderers. Three have a producer (`cover_metadata`, `emissions_summary`,
    `monitoring_tracked_params`). Setting `structured_content` **replaces** the section's prose
    (dispatch at `docx_export.py:261-289`).
  - `src/pdd_agent/calc/dispatch.py:167-182` computes `per_type_tonnes = annual_waste_throughput /
    len(tech.waste_type)` **before** filtering out waste types absent from `DOC_BY_WASTE_TYPE`, then
    emits one stream per surviving type at that tonnage. Measured on
    `configs/projects/vietnam_socson_from_sheet.yaml`: declared 1,460,000 t/yr, `plastics` excluded,
    **973,333 t/yr (66.67%) reaches the engine**. Mass is not conserved.
  - `tests/test_registered_pdd_oracle.py` carries three `strict=True` xfails: Soc Son
    crediting-period total **+39.5%**, İnegöl annual net **−51.4%**, İnegöl crediting-period total
    **+22.4%** against registered figures.
  - No real LLM provider has ever drafted a section outside a one-off measurement. Every artifact in
    `reports/` came from `DemoProvider` or `NoopProvider`.
- **Desired state:**
  - The index holds real section spans — several thousand chunks with a duplication rate under 15%,
    covering at least 16 of the 17 normalized documents, with the ACM0022 methodology text
    retrievable.
  - `pdd-agent index-report` makes corpus health a one-command check, and a document that yields no
    indexable sections is reported loudly instead of vanishing.
  - Retrieval can be filtered to a methodology family, so a rice project stops citing WTE PDDs.
  - The exported DOCX renders **prose and table** in the same subsection, and 8 of the 11 Verra table
    types have a producer.
  - The ACM0022 engine consumes a published waste composition when one is declared, conserves mass in
    every case, and the three oracle xfails carry re-measured numbers (flipped to passing where the
    fix genuinely closes the gap).
  - One real `claude-code` section draft has been executed and read by a human, for under $1.
- **Key repo surfaces:**
  - `src/pdd_agent/parse/section_parser.py` — corpus → canonical schema mapper, 300 lines
  - `src/pdd_agent/retrieval/index.py` — FTS5 index build/search, 340 lines
  - `src/pdd_agent/retrieval/search.py` — query API, 215 lines
  - `src/pdd_agent/ingest/normalize.py` — PDF/DOCX text extraction, `text_blocks` producer
  - `src/pdd_agent/export/docx_export.py` — 1,057 lines, `_TABLE_RENDERERS`, `export_run_to_docx`
  - `src/pdd_agent/agent/section_orchestrator.py` — 1,071 lines, prompt assembly, structured content
  - `src/pdd_agent/calc/dispatch.py` — `build_engine_inputs`, `_map_acm0022`, `compute_for`
  - `src/pdd_agent/calc/constants.py` — `DOC_BY_WASTE_TYPE`, `DECAY_RATE_BY_WASTE_TYPE`
  - `src/pdd_agent/cli.py` — 1,013 lines, 22 subcommands, `add_parser` registry at line 43 and
    dispatch table at line 422
  - `schemas/project_input.py` — Pydantic v2 `ProjectInput` (top-level package, outside `src/`)
  - `rules/verra/*_rules.yaml`, `rules/verra/rubrics/*.yaml` — per-family rules and judge rubrics
  - `configs/projects/`, `configs/demo/` — six project YAML files
- **Out of scope:**
  - The full 36-section real-model proof run (estimated $12–16). PHASE-04 deliberately buys a single
    section instead. Do not run `pdd-agent prove` against a real provider under this plan.
  - Regenerating the committed client-demo artifacts under `reports/demo-packages/`.
  - Unstubbing `src/pdd_agent/ingest/registry_download.py` (needs interactive browser capture).
  - Splitting `ProjectInput` into per-family discriminated unions.
  - Replacing FTS5/BM25 with embedding-based retrieval.
  - Run-store pagination, retention, and the service's `_get_provider` claude-code gap.
  - The three model-generated table types: `risk_assessment`, `sustainable_development`, `data_gaps`.

## Environment & Conventions

- **Stack:** Python 3.11+ (`requires-python = ">=3.11"` in `pyproject.toml`; the checked-out `.venv`
  is Python 3.13 and uv-managed). Pydantic v2, structlog, python-docx, openpyxl, PyYAML, pypdf,
  python-dotenv. Optional extras: `dev` (pytest, pytest-cov, ruff), `service`
  (fastapi, uvicorn, jinja2, python-multipart), `export` (python-docx), `llm` (openai, anthropic).
  Build backend is hatchling; `uv.lock` is committed and enforced in CI.
- **Setup:**
  ```bash
  pip install -e ".[dev,service,export,llm]"
  ```
  Lockfile-faithful equivalent when `uv` is available:
  ```bash
  uv sync --locked --all-extras
  ```
- **Build / Run:** No build step. Editable install exposing the `pdd-agent` console script
  (`[project.scripts] pdd-agent = "pdd_agent.cli:main"`). Examples:
  ```bash
  pdd-agent doctor
  pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml
  pdd-agent build-index --corpus-dir data/corpus/normalized --index-db data/index/corpus.fts.db
  ```
- **Test:** Full suite:
  ```bash
  python -m pytest -m "not corpus" -q
  ```
  Single file:
  ```bash
  python -m pytest tests/test_retrieval_search.py -v
  ```
  Single test:
  ```bash
  python -m pytest "tests/test_calc_dispatch.py::TestComputeFor::test_socson_returns_acm0022_with_warning" -v
  ```
  The `corpus` pytest marker gates 7 tests that require `data/corpus/normalized/` (gitignored). CI
  deselects them; so should you unless that directory is populated locally.
  **Baseline before this plan: 798 passed, 7 deselected, 3 xfailed, ~89 s.**
- **Lint / format** (both are CI gates and must pass at the end of every phase):
  ```bash
  ruff check .
  ruff format --check .
  ```
- **Conventions & traps:**
  - Ruff line length 100, `target-version = "py311"`, `.claude` excluded, `E402` globally ignored.
  - Logging is structlog **event-style**: `logger.warning("event_name", key=value)` — an event name as
    the first positional argument, never an interpolated sentence. Every existing call site follows
    this and lint will not catch a violation.
  - `ProjectInput` and its sub-models are **Pydantic v2**, living in `schemas/project_input.py`, a
    top-level package deliberately outside `src/`. Everything else uses stdlib `dataclasses`.
  - **Units, everywhere in this plan:** emissions are **tCO2e**; annual rates are **tCO2e/year**;
    grid emission factors are **tCO2/MWh**; waste mass is **tonnes/year**; electricity is
    **MWh/year**; money is **USD**. Never mix an annual figure with a crediting-period total without
    naming which is which.
  - Tests must never require an API key, network access, a running Ollama instance, or the presence of
    `data/corpus/`. Mock all HTTP. Anything needing the corpus carries the `corpus` marker.
  - `demo` and `noop` providers are deterministic and are the safe default. `openai`/`anthropic`
    require both `{PROVIDER}_API_KEY` and a positive `PDD_MAX_COST_USD`. `claude-code` requires the
    `claude` CLI on PATH and an authenticated subscription session.
  - `reports/demo-packages/` is the client-demo artifact area (readable synthetic output, zero
    placeholders, committed to git). `reports/review-packages/` is the internal reviewer area
    (placeholders expected). Do not blur them, and do not regenerate either under this plan.
  - `data/index/` and `data/corpus/` are gitignored. Rebuilding the index changes no committed file.
  - Shell examples use POSIX syntax. On Windows PowerShell replace `VAR=value cmd` with
    `$env:VAR = "value"; cmd`.
  - If your shell environment sets `PYTHONPATH`, it can shadow the repo's virtualenv and produce
    import errors unrelated to your change. Clear it for the duration:
    `PYTHONPATH= python -m pytest -m "not corpus" -q`.
- **Repo map:**
  ```
  src/pdd_agent/
    ingest/        drive, download, normalize (pypdf text extraction), bucket, registry_download
    parse/         section_parser.py — normalized doc -> canonical schema mapping
    retrieval/     index.py (SQLite FTS5 BM25), search.py (query API)
    calc/          ACM0022 + VM0051 + VM0044 + AMS-II.G engines, CDM tools 03-07/12/14, dispatch
    llm/           provider ABC, DraftRun/DraftSection, budget, 4 real providers, output_normalize
    agent/         section_orchestrator.py — prompt assembly, retrieval, judging, structured content
    review/        checks.py, consistency.py, judge.py, states.py, tbd_tracker.py
    export/        docx_export.py, pdf_export.py, review_package.py, table_helpers.py
    phase05/       benchmark.py, provider_scorecard.py  (plan-phase names, not domain names)
    phase06/       spreadsheet_mapper.py, vietnam_workflow.py, assumptions.py
    cli.py         22 subcommands; service/main.py  FastAPI review UI
  schemas/         project_input.py (Pydantic v2), pdd_section_schema.yaml (5 sections/36 subsections)
  rules/verra/     wte_/rice_/biochar_/cookstove_ methodology rules + rubrics/
  configs/         projects/*.yaml, demo/inegol_project_input.yaml, model_pricing.yaml
  data/corpus/raw/verra/       26 source PDFs (~64 MB, gitignored, present locally)
  data/corpus/normalized/      17 registered VCS PDDs as .norm.json (gitignored, present locally)
  tests/           58 test files
  ```

## Research Inputs

- From `research/2026-08-13-pdd-hollow-grounding-and-calc-inputs-brainstorm.md`:
  - The index holds 1,015 rows carrying **270 distinct texts (73.4% duplication)**; **992 of 1,015
    rows (97.7%) are exactly 500 characters**; only **13 of 17** documents are represented. Measured
    directly against `data/index/corpus.fts.db`.
  - Live retrieval measured through `get_examples_for_section`: section **4.4 returns 5 examples
    containing 2 distinct texts**, both from `VCS_Bergama_Project-Description.norm`; section 3.3
    returns 3 distinct of 5; section 1.10 returns 3 distinct of 5. Sample text begins
    `'Joint Project Description & Monitoring Report: VCS Version 4. 2 \n106 \nQexport,RDF_SB,y  = '` —
    running headers and page numbers are indexed as content.
  - `_find_content_page()` is the cause: it returns a *page*, not a section, truncated at 500
    characters, so all headings on one page collapse to one identical string.
  - The correct data is already present and ignored: `text_blocks` in each `.norm.json` holds
    `{heading, text}` segments between headings.
  - The registered Soc Son PDD publishes its waste composition verbatim — *"Table 8. Components of
    solid waste: Wood and wood products 0.0%, Pulp, paper and cardboard 2.7%, Food, food waste,
    beverages and tobacco 51.9%, Textiles 1.6%, Garden, yard and park waste 0.0%, Glass, plastic,
    metal, other inert waste 43.8%"* — while the engine assumes an even split across declared types.
  - 8 of 11 Verra table renderers have no producer, and four of those eight (`proponent`,
    `audit_history`, `ghg_boundary`, `applicability`) are deterministic projections of data the repo
    already holds in `ProjectInput` and `rules/verra/*_rules.yaml`.
  - `structured_content` currently **suppresses** the section's prose, which is why calc tables were
    restricted to 4.4 and 5.2. Registered PDDs carry narrative *and* table in these sections.
  - `ClaudeCodeProvider` reads `total_cost_usd` from the CLI verbatim; its docstring describes it as
    the cost "billed to the operator's subscription". Measured rate: **36.1 s and $0.167898 per
    section draft**, dominated by ~25,000 tokens of per-invocation CLI harness overhead.
- From `docs/2026-07-12-rice-pilot-findings.md` (still-binding prior decision):
  - **DEC-004 stands:** do not split `ProjectInput` into per-family discriminated unions. The wide
    schema with optional family blocks handled the rice pilot correctly. New family-specific fields
    must be **optional with a fallback**, never required.

## Assumptions and Constraints

- **ASM-001:** The pairing rule between `headings` and `text_blocks` in a normalized document is
  unspecified in any doc. — **BINDING DEFAULT:** they are aligned by construction in
  `_build_headings_and_blocks()` — one block is emitted per heading, plus one leading block with
  `heading == ""` when the document has text before its first heading. Implement the pairing exactly
  as specified in **S-1** below, including its verification step and its per-document fallback.
- **ASM-002:** The target chunk size for indexing is unspecified. — **BINDING DEFAULT:** 2,000
  characters maximum per chunk with 200 characters of overlap carried from the previous chunk, and a
  minimum chunk length of 80 characters except when a block yields only one chunk. Tune later using
  `pdd-agent index-report`; do not tune inside this plan.
- **ASM-003:** Which methodology family each corpus document belongs to is not recorded anywhere. —
  **BINDING DEFAULT:** create `configs/corpus_families.yaml` mapping document stem → family slug, and
  default any unlisted document to `"wte"`. All 17 documents currently on disk are waste-to-energy,
  so the initial file may legitimately be a comment plus an empty `documents:` mapping.
- **ASM-004:** Whether a family-filtered search that returns nothing should fail or fall back is
  unspecified. — **BINDING DEFAULT:** fall back to an unfiltered search and emit
  `logger.warning("retrieval_family_fallback", family=..., section_id=...)`. A rice project must keep
  getting grounding, and the warning is what makes the contamination visible.
- **ASM-005:** The ACM0022 GHG project-boundary rows are not encoded anywhere in the repo. —
  **BINDING DEFAULT:** author them into `rules/verra/wte_methodology_rules.yaml` using the eleven rows
  listed in **S-3**, each carrying `source: "ACM0022 v03.0 Section 5 (Project Boundary)"`. After
  PHASE-02 makes `EB111_repan07_ACM0022_v03.0` retrievable, verify each row against that document and
  correct any that disagree, recording the correction in the commit message.
- **ASM-006:** The exact waste composition to declare for Soc Son and İnegöl. — **BINDING DEFAULT:**
  use the figures in **S-2**, taken from the registered PDDs, and set each entry's `source` string to
  name the document and table. Where the registered PDD publishes no composition (İnegöl), leave
  `waste_composition` absent so the even-split fallback and its warning still apply.
- **ASM-007:** Whether excluded waste types should forfeit their mass or have it redistributed. —
  **BINDING DEFAULT:** redistribute. Divide by the number of **kept** types, not declared types, so
  total mass entering the engine always equals `annual_waste_throughput`. Emit a warning naming the
  excluded types and the redistributed tonnage.
- **ASM-008:** The model for the PHASE-04 smoke check. — **BINDING DEFAULT:** the
  `ClaudeCodeProvider` default (`sonnet`, `_DEFAULT_MODEL` at `claude_code_provider.py:54`), one
  section, `PDD_MAX_COST_USD=1`.
- **ASM-009:** Whether re-indexing invalidates the committed demo artifacts. — **BINDING DEFAULT:**
  no. `DemoProvider` ignores retrieval content and returns deterministic templated prose, and
  `data/index/` is gitignored. Do not regenerate `reports/demo-packages/` or
  `reports/review-packages/`.
- **CON-001:** Tests must not require an API key, network access, a running Ollama instance, or the
  presence of `data/corpus/`. Every phase except PHASE-04 must be fully verifiable offline.
- **CON-002:** `ruff check .` and `ruff format --check .` are CI gates and must pass at the end of
  every phase.
- **CON-003:** `DraftRun.load()` must keep tolerating the ~1,555 run JSON files already in
  `data/runs/`. Any new field is read with `.get()`, never `data["..."]`.
- **CON-004:** PHASE-04 spends real money against a Claude subscription. It is capped at
  `PDD_MAX_COST_USD=1` and drafts exactly one section. Do not widen it.
- **DEC-001:** Per DEC-004 in `docs/2026-07-12-rice-pilot-findings.md`, `ProjectInput` is **not** split
  per family. New fields (`waste_composition`, `capacity_ramp`) are optional with fallbacks.
- **DEC-002:** The three `strict=True` oracle xfails in `tests/test_registered_pdd_oracle.py` are the
  acceptance signal for PHASE-05. **Never widen `TOLERANCE`.** If a gap does not close, re-measure and
  rewrite the xfail reason with the new numbers.
- **DEC-003:** The legacy `_find_content_page()` path is retained as a per-document fallback, not
  deleted. Some `.norm.json` files may predate `_build_headings_and_blocks()`.

## Specification

### S-1. Section-span chunking (the PHASE-02 change)

Replaces `_find_content_page()` as the source of indexed text. Applied per normalized document.

Inputs: `headings` (list of `{text, level, page}`) and `text_blocks` (list of `{heading, text}`) from
the document's `.norm.json`; `page_texts` (map from 1-based page number to page text) built from its
`pages` list.

```
1. blocks := text_blocks
2. if blocks is non-empty and blocks[0]["heading"] == "":
       blocks := blocks[1:]                        # drop the pre-first-heading preamble
3. if len(blocks) != len(headings)
      or any k where blocks[k]["heading"] != headings[k]["text"]:
       log WARNING corpus_block_alignment_failed (document=..., blocks=..., headings=...)
       fall back to the legacy _find_content_page() path FOR THIS DOCUMENT ONLY, and stop.
4. for k in 0 .. len(headings)-1:
       h    := headings[k]
       body := blocks[k]["text"].strip()
       if body == "":                       skip this heading
       if _is_toc_page(page_texts.get(h["page"], "")):  skip this heading
       emit chunks(body) for heading k
```

`chunks(body)` splits one block's text:

```
if len(body) <= 2000:            yield body                      # single chunk
else:
    paragraphs := body.split("\n")
    accumulate paragraphs into a buffer while len(buffer) <= 2000
    when the buffer would exceed 2000:
        yield buffer
        buffer := last 200 characters of the yielded buffer, then continue accumulating
    yield any non-empty trailing buffer
discard any yielded chunk shorter than 80 characters unless it is the only chunk for this block
```

Symbol annotations:

- `headings[k]["page"]` — 1-based PDF page number on which heading `k` was detected.
- `_is_toc_page(text)` — existing helper at `src/pdd_agent/parse/section_parser.py:112`; returns
  `True` for a table-of-contents page. Reuse it unchanged.
- **2000** — maximum characters per emitted chunk (ASM-002).
- **200** — characters of overlap carried from the tail of the previous chunk into the next, so a
  sentence spanning a chunk boundary is still retrievable (ASM-002).
- **80** — minimum characters for a chunk to be worth indexing (ASM-002).
- `chunk_index` — 0-based position of the chunk within its heading's block; emitted as a new FTS5
  column so one heading can legitimately produce several rows.

### S-2. Waste-composition-weighted stream mapping (the PHASE-05 change)

Current behaviour (`src/pdd_agent/calc/dispatch.py:167-182`):

```
n_types        = len(technology.waste_type)
per_type_tonnes = annual_waste_throughput / n_types
kept           = [wt for wt in technology.waste_type if wt in DOC_BY_WASTE_TYPE]
waste_streams  = [{waste_type: wt, annual_tonnes: per_type_tonnes} for wt in kept]
```

Corrected behaviour, in order:

```
1. If technology.waste_composition is non-empty:
       for each entry e in waste_composition where e.waste_type in DOC_BY_WASTE_TYPE:
           annual_tonnes := annual_waste_throughput × e.mass_fraction
           emit {waste_type: e.waste_type, annual_tonnes: annual_tonnes}
       excluded_fraction := Σ mass_fraction of entries whose waste_type is NOT in DOC_BY_WASTE_TYPE
       if excluded_fraction > 0:
           warn "waste_composition: {excluded_fraction:.1%} of mass is non-degradable or unmapped
                 and contributes no BE_CH4"
       Do NOT rescale the remaining fractions — inert mass genuinely generates no landfill methane.

2. Otherwise (no composition declared) — the fallback:
       kept  := [wt for wt in technology.waste_type if wt in DOC_BY_WASTE_TYPE]
       if kept is empty: return None (unchanged behaviour)
       per_type_tonnes := annual_waste_throughput / len(kept)        # len(KEPT), not len(declared)
       emit one stream per kept type at per_type_tonnes
       if len(kept) < len(technology.waste_type):
           warn "waste types {excluded} are not in DOC_BY_WASTE_TYPE; their mass was redistributed
                 across {kept}"
       if len(kept) > 1:
           warn "waste split evenly across N declared waste types"   (existing string, unchanged)
```

Symbol annotations:

- `annual_waste_throughput` — `ProjectInput.technology.annual_waste_throughput`, **tonnes/year**, the
  total mass entering the project.
- `mass_fraction` — dimensionless 0–1 share of `annual_waste_throughput` for one waste type. The
  declared fractions **may sum to less than 1.0** (inert mass is legitimately excluded from the
  degradable inventory) but must not sum to more than 1.0.
- `DOC_BY_WASTE_TYPE` — `src/pdd_agent/calc/constants.py:41`; maps a waste-type key to its degradable
  organic carbon fraction. Keys today: `food_waste`, `garden_waste`, `paper_cardboard`, `wood`,
  `textiles`, `nappies`, `rubber_leather`, `municipal_solid_waste`.
- **The `len(kept)` change is the mass-conservation fix.** Today Soc Son declares three waste types,
  one (`plastics`) is unmapped, and the divisor stays 3 — so only 973,333 of 1,460,000 tonnes/year
  (66.67%) reaches the engine.

Soc Son's declared composition, transcribed from `VCS_Soc_Son_Project-Description.norm.json`
("Table 8. Components of solid waste"), mapped onto `DOC_BY_WASTE_TYPE` keys:

| `waste_type` key | `mass_fraction` | Registered PDD label |
|---|---|---|
| `food_waste` | 0.519 | Food, food waste, beverages and tobacco 51.9% |
| `paper_cardboard` | 0.027 | Pulp, paper and cardboard 2.7% |
| `textiles` | 0.016 | Textiles 1.6% |
| `wood` | 0.000 | Wood and wood products 0.0% |
| `garden_waste` | 0.000 | Garden, yard and park waste 0.0% |
| `rubber_leather` | 0.013 | Rubber and leather 1.3% |

The remaining 42.5% (glass, plastic, metal and other inert waste) is deliberately **not declared** —
it is non-degradable and generates no landfill methane. Do not add it, and do not rescale the six
fractions above to sum to 1.0.

**Do not declare a `waste_composition` for İnegöl.** Its registered PDD publishes IPCC default DOC
values per waste type but not the plant's own intake composition, so it must keep exercising the
fallback path (ASM-006).

### S-3. ACM0022 GHG project-boundary rows (the PHASE-03 change, per ASM-005)

Authored into `rules/verra/wte_methodology_rules.yaml` under `methodologies.ACM0022.ghg_boundary`,
as a list of mappings with keys `scenario`, `source`, `gas`, `included`, `justification`, `source_ref`.

| scenario | source | gas | included | justification |
|---|---|---|---|---|
| Baseline | Decomposition of waste at the solid waste disposal site | CH4 | Yes | Dominant baseline source; quantified as BE_CH4 using the CDM Tool 04 first-order-decay model. |
| Baseline | Decomposition of waste at the solid waste disposal site | CO2 | No | CO2 from decomposition of organic waste is of biogenic origin and is not accounted under ACM0022. |
| Baseline | Decomposition of waste at the solid waste disposal site | N2O | No | Excluded for simplification. This exclusion is conservative. |
| Baseline | Electricity generation in the grid displaced by the project | CO2 | Yes | Quantified as BE_EC using the combined-margin grid emission factor derived per CDM Tool 07. |
| Baseline | Electricity generation in the grid displaced by the project | CH4, N2O | No | Excluded for simplification. This exclusion is conservative. |
| Project | On-site fossil fuel consumption (auxiliary firing, site vehicles) | CO2 | Yes | Quantified as PE_FC. |
| Project | On-site electricity consumption | CO2 | Yes | Quantified as PE_EC. |
| Project | Anaerobic digestion and biogas handling | CH4 | Yes | Physical methane leakage from digesters and gas handling; quantified as PE_CH4. |
| Project | Flaring of residual biogas | CH4 | Yes | Quantified as PE_FLARE. |
| Project | Combustion of waste or refuse-derived fuel | CO2 | No | The biogenic fraction is excluded; any fossil fraction is addressed under the methodology governing an RDF fuel-substitution claim. |
| Project | Combustion of waste or refuse-derived fuel | N2O | No | Excluded for simplification. This exclusion is conservative. |

Every row carries `source_ref: "ACM0022 v03.0 Section 5 (Project Boundary)"`. Per ASM-005, verify each
row against `EB111_repan07_ACM0022_v03.0` once PHASE-02 makes it retrievable, and correct any that
disagree.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Make corpus health measurable and indexing failures loud | None | `pdd-agent index-report`, `docs_with_zero_sections` in build stats |
| PHASE-02 | Rebuild the index on real section spans, with family filtering | PHASE-01 | S-1 chunking, `content_class`/`review_sensitivity`/`document_family`/`chunk_index` columns, family-filtered search |
| PHASE-03 | Render prose *and* tables; wire five more Verra renderers | None (parallel with 01/02) | `_add_section_prose`, `_build_structured_content`, `ghg_boundary` rules block, 8 of 11 tables live |
| PHASE-04 | One real `claude-code` section draft, capped at $1 | PHASE-02, PHASE-03 | `--only-section` CLI flag, `reports/2026-08-13-single-section-smoke.md` |
| PHASE-05 | Give the calc engine real composition and conserve mass | PHASE-04 | `waste_composition`/`capacity_ramp` fields, S-2 mapping, re-measured oracle xfails |
| PHASE-06 | Table-aware ingestion behind an optional extra | PHASE-05 | `pdfplumber` `ingest` extra, `tables[]` in `.norm.json` |

## Detailed Phases

### PHASE-01 - Make Corpus Health Measurable

**Goal**

Before changing the indexer, build the instrument that proves whether the change worked. Add a
one-command corpus-health report and make a normalized document that yields no indexable sections
impossible to miss. Everything here is offline and costs nothing.

**Tasks**

- [ ] TASK-01-01: Return per-document section counts and a zero-yield document list from
      `RetrievalIndex.build()`.
- [ ] TASK-01-02: Log a WARNING for every document that yields zero indexable sections.
- [ ] TASK-01-03: Add an `index_health()` function that reports duplication and truncation metrics.
- [ ] TASK-01-04: Add the `pdd-agent index-report` subcommand.
- [ ] TASK-01-05: Print the zero-yield document list at the end of `pdd-agent build-index`.
- [ ] TASK-01-06: Add tests for `index_health()` against a synthetic in-memory index.

**File Changes**

- `src/pdd_agent/retrieval/index.py` (modify): in `build()`, accumulate
  `rows_by_document: dict[str, int]` while inserting, and after the loop compute
  `docs_with_zero_sections = sorted(name for name, n in rows_by_document.items() if n == 0)`. A
  document that was parsed but produced no rows must still appear in `rows_by_document` with value
  `0` — initialise its entry as soon as `docs_indexed` is incremented, before the inner loop. Add
  `rows_by_document` and `docs_with_zero_sections` to the returned stats dict. For each zero-yield
  document emit `logger.warning("corpus_document_yielded_no_sections", document=name)`. Leave the
  existing `skipping_doc` warning, `_SCHEMA_VERSION`, and the FTS5 table definition untouched in this
  phase.
- `src/pdd_agent/retrieval/index.py` (modify): add a module-level `index_health(db_path: Path | None
  = None, corpus_dir: Path | None = None) -> dict[str, Any]`. It opens the database read-only, and
  returns the keys listed under **Function Signatures**. When `corpus_dir` is given, it also globs
  `*.norm.json` there and reports `missing_documents` — normalized stems with no row in the index.
  Return `{"error": "index not found", "db_path": str(path)}` when the file does not exist; never
  raise.
- `src/pdd_agent/cli.py` (modify): register a new subparser next to the existing `build-index` block
  at line 51:
  ```python
  index_report = sub.add_parser(
      "index-report", help="Report retrieval-index health: coverage, duplication, truncation"
  )
  index_report.add_argument("--index-db", default="data/index/corpus.fts.db",
                            help="FTS5 database path")
  index_report.add_argument("--corpus-dir", default="data/corpus/normalized",
                            help="Normalized corpus directory, for coverage comparison")
  index_report.add_argument("--json", action="store_true",
                            help="Emit the report as JSON instead of text")
  ```
  Add `"index-report": lambda: _run_index_report(args, log),` to the dispatch table at line 422. Add
  `_run_index_report(args, log) -> int` following the shape of the existing `_run_build_index`:
  return `0` on success, `1` when `index_health` returns an `error` key.
- `src/pdd_agent/cli.py` (modify): in `_run_build_index`, after printing the existing stats, print
  `Documents with zero indexable sections: <comma-separated list>` when the list is non-empty, and
  nothing when it is empty.
- `tests/test_retrieval_search.py` (modify): add the `index_health` tests below. Do not alter
  existing tests.
- `README.md` (modify): add one row to the CLI commands table:
  `| `pdd-agent index-report` | Report retrieval-index health: document coverage, duplication rate, truncation |`.
  Also correct the status line's test count from 752 to the number the suite actually reports at the
  end of this phase.

**Function Signatures**

- `RetrievalIndex.build(self, normalized_dir: Path | None = None, schema_path: Path | None = None) -> dict[str, Any]`
  — unchanged signature; the returned dict gains `rows_by_document: dict[str, int]` and
  `docs_with_zero_sections: list[str]` alongside the existing `docs_indexed`, `chunks_indexed`,
  `db_path`, `schema_version`, `built_at`.
- `index_health(db_path: Path | None = None, corpus_dir: Path | None = None) -> dict[str, Any]` —
  returns `{"db_path": str, "total_rows": int, "distinct_texts": int, "duplication_rate": float,
  "documents": int, "rows_by_document": dict[str, int], "mean_text_chars": float,
  "median_text_chars": int, "rows_at_500_chars": int, "missing_documents": list[str]}`.
  `duplication_rate` is `1 - distinct_texts / total_rows`, rounded to 3 decimal places, and is `0.0`
  when `total_rows` is `0`.
- `_run_index_report(args: argparse.Namespace, log: Any) -> int` — prints the health report and
  returns a process exit code.

**Test Specs**

- Build a temporary FTS5 index containing 4 rows where 3 share the identical `text` value `"AAA"` and
  one has `"BBB"`, then `index_health(db_path=tmp)` → `total_rows == 4`, `distinct_texts == 2`,
  `duplication_rate == 0.5`.
- `index_health(db_path=tmp_path / "does-not-exist.db")` → returns a dict whose `"error"` key equals
  `"index not found"`; it must not raise.
- An index with zero rows → `duplication_rate == 0.0` and `total_rows == 0` (no ZeroDivisionError).
- `index_health(db_path=tmp, corpus_dir=tmp_corpus)` where `tmp_corpus` holds `alpha.norm.json` and
  `beta.norm.json` but the index only has rows for `alpha` → `missing_documents == ["beta"]`.
- Two rows of length 500 and one of length 120 → `rows_at_500_chars == 2`, `median_text_chars == 500`.
- `RetrievalIndex.build()` over a corpus directory containing one document whose `sections_mapped` is
  empty → returned `docs_with_zero_sections` contains that document's stem, and `rows_by_document`
  maps it to `0`.

**Dependencies**

- None. All work is offline and needs no corpus.

**Exit Criteria**

- [ ] `python -m pytest tests/test_retrieval_search.py -v` passes including the new cases.
- [ ] `pdd-agent index-report --index-db data/index/corpus.fts.db --corpus-dir data/corpus/normalized`
      exits 0 and reports **total_rows 1015, distinct_texts 270, duplication_rate 0.734, documents 13**,
      with `missing_documents` naming `EB111_repan07_ACM0022_v03.0`,
      `Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2`, `DraftProjectDescription`, and
      `VCS-Project-Description-HEREKO-v4.1`. (Run against the pre-PHASE-02 index; if
      `data/corpus/normalized/` is absent, skip this criterion and record that it was skipped.)
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both pass.

**Phase Risks**

- **RISK-01-01:** `index_health` opening a SQLite file concurrently with a build could read a partial
  index. Mitigation: it is a read-only diagnostic invoked manually; document in its docstring that it
  reports whatever is committed at read time, and do not add locking.

### PHASE-02 - Rebuild the Index on Real Section Spans

**Goal**

Replace page-fragment indexing with true section-span chunking (S-1), populate the two columns that
are currently always empty, add a methodology-family column and filter, and recover the four
documents that contribute nothing today. This is the change every other trust mechanism in the
repository is standing on.

**Tasks**

- [ ] TASK-02-01: Emit `section_spans` from `parse_corpus`, implementing S-1 steps 1–4.
- [ ] TASK-02-02: Implement the S-1 chunker with its 2000/200/80 character rules.
- [ ] TASK-02-03: Keep `_find_content_page` as the per-document fallback when alignment fails.
- [ ] TASK-02-04: Add `document_family` and `chunk_index` columns and bump `_SCHEMA_VERSION`.
- [ ] TASK-02-05: Populate `content_class` and `review_sensitivity` from the canonical section schema.
- [ ] TASK-02-06: Create `configs/corpus_families.yaml` and a loader.
- [ ] TASK-02-07: Thread a `document_family` filter through `RetrievalIndex.search`, `search()`,
      and `get_examples_for_section()`, with the ASM-004 fallback.
- [ ] TASK-02-08: Pass the project's family slug from `SectionOrchestrator` into retrieval.
- [ ] TASK-02-09: Rebuild the local index and record the before/after `index-report` numbers.

**File Changes**

- `src/pdd_agent/parse/section_parser.py` (modify): add a `section_spans` key to the dict returned by
  the per-document parse function, alongside the existing `sections_mapped`. Each entry is
  `{"canonical_section_id": str, "canonical_sub_section_id": str | None, "canonical_heading": str,
  "heading_text": str, "chunk_index": int, "text": str}`. Build it by implementing **S-1** exactly.
  Keep `_find_content_page`, `_is_toc_page`, `_best_match`, `text_preview`, `sections_mapped`, and
  `coverage` **unchanged** — `sections_mapped` is consumed elsewhere and its `text_preview` remains
  the fallback payload. Add a module-level `_chunk_block(body: str) -> list[str]` implementing the
  chunker.
- `src/pdd_agent/retrieval/index.py` (modify): in `build()`, replace the
  `for entry in doc_result.get("sections_mapped", [])` loop with one over
  `doc_result.get("section_spans", [])`, falling back to `sections_mapped` (current behaviour) when
  `section_spans` is absent or empty. Extend the FTS5 table with two columns —
  `document_family` and `chunk_index` — declared after `review_sensitivity`. Insert
  `content_class` and `review_sensitivity` from the canonical section schema entry for the row's
  `sub_section_id` (falling back to the section-level values, then to `""`), and `document_family`
  from the loader below. Bump `_SCHEMA_VERSION`. Leave `search_by_heading`, `get_section_examples`,
  `stats`, and `close` structurally unchanged apart from the new columns in their SELECT lists.
- `src/pdd_agent/retrieval/index.py` (modify): add `document_family: str | None = None` to
  `RetrievalIndex.search()` after `content_class`, appending `document_family = ?` to `where_parts`
  when it is truthy. Add the same parameter to `get_section_examples()`.
- `src/pdd_agent/retrieval/index.py` (modify): extend `_row_to_doc` to carry the two new columns.
- `configs/corpus_families.yaml` (create):
  ```yaml
  # Maps a normalized corpus document stem (the .norm.json filename without its
  # extension) to a methodology-family slug: wte | rice | biochar | cookstove.
  # Any document not listed here defaults to "wte" (see default_family).
  default_family: wte
  documents: {}
  ```
- `src/pdd_agent/retrieval/index.py` (modify): add
  `load_corpus_families(path: Path | None = None) -> tuple[str, dict[str, str]]` returning
  `(default_family, mapping)`. Missing file → `("wte", {})`, no exception.
- `src/pdd_agent/retrieval/search.py` (modify): add `document_family: str | None = None` to `search()`
  and `get_examples_for_section()`, forwarding it to the index. When the filtered call returns an
  empty list **and** `document_family` was not `None`, retry once unfiltered and emit
  `logger.warning("retrieval_family_fallback", family=document_family, section_id=section_id)`
  (ASM-004). `search.py` already imports `structlog` and defines a module logger — reuse it.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): at the two call sites currently invoking
  `get_examples_for_section(section_id, sub_section_id, k=k)` (lines 600 and 614), pass
  `document_family=self._family_slug()`. `_family_slug()` already exists at line 162. Change nothing
  else about prompt assembly.
- `tests/test_retrieval_search.py` (modify): add the family-filter and fallback tests below.
- `tests/test_section_parser.py` (modify): add the S-1 chunking tests below.
- `README.md` (modify): in the "Retrieval & Drafting (PHASE-03)" bullet for
  `src/pdd_agent/retrieval/index.py`, state that the index stores section spans chunked at 2,000
  characters with 200-character overlap, and carries `document_family` for methodology-scoped
  retrieval. Remove the "Corpus normalization discards table structure" bullet from Known Gaps only
  if PHASE-06 lands; leave it in place for now.

**Function Signatures**

- `_chunk_block(body: str) -> list[str]` — splits one section body into chunks of at most 2,000
  characters with 200 characters of overlap, discarding chunks shorter than 80 characters unless the
  body yields exactly one chunk.
- `load_corpus_families(path: Path | None = None) -> tuple[str, dict[str, str]]` — returns the default
  family slug and the document-stem-to-family mapping; `("wte", {})` when the file is absent.
- `RetrievalIndex.search(self, query: str, section_id: str | None = None, content_class: str | None = None, document_family: str | None = None, k: int = 5) -> list[dict[str, Any]]`
  — BM25 hits filtered by any supplied criteria.
- `search(query: str, section_id: str | None = None, content_class: str | None = None, k: int = DEFAULT_K, index: RetrievalIndex | None = None, document_family: str | None = None) -> list[RetrievalResult]`
  — ranked corpus hits, with the ASM-004 unfiltered retry.
- `get_examples_for_section(section_id: str, sub_section_id: str | None = None, k: int = DEFAULT_K, index: RetrievalIndex | None = None, document_family: str | None = None) -> list[RetrievalResult]`
  — non-ranked example texts for a section, with the same retry.

**Test Specs**

- `_chunk_block("x" * 1500)` → returns a list of length 1 whose single element is the input.
- `_chunk_block("x" * 5000)` → returns 3 or more chunks, every chunk at most 2,000 characters, and
  `chunks[1]` starts with the last 200 characters of `chunks[0]`.
- `_chunk_block("short")` → `["short"]` — the 80-character minimum does not suppress a body that
  yields only one chunk.
- A synthetic `.norm.json` with `headings == [{"text": "1.1 Summary", "level": 1, "page": 1}]` and
  `text_blocks == [{"heading": "", "text": "preamble"}, {"heading": "1.1 Summary", "text": "Body text about the project."}]`
  → the parse result's `section_spans` has exactly one entry, `entry["text"] == "Body text about the project."`,
  `entry["chunk_index"] == 0`. The leading `heading == ""` block is dropped (S-1 step 2).
- A synthetic `.norm.json` whose `text_blocks` headings do not match its `headings` list → the parse
  result's `section_spans` is empty, `sections_mapped` is still populated, and a
  `corpus_block_alignment_failed` warning was emitted (S-1 step 3).
- A heading whose page text contains `"TABLE OF CONTENTS"` → produces no `section_spans` entry.
- A heading whose block text is `"   "` → produces no `section_spans` entry.
- Build an index with two documents, `alpha` family `wte` and `beta` family `rice`, then
  `search("waste", document_family="rice")` → every result's `document_name` is `beta`.
- `search("termpresentonlyinwte", document_family="rice")` → returns the unfiltered results (non-empty)
  and a `retrieval_family_fallback` warning was emitted (ASM-004).
- `search("waste", content_class="METHODOLOGY_DEPENDENT")` against an index built from a document
  whose 3.2 subsection carries that content class → returns at least one result. (Today this returns
  zero for every input, because the column is always `""`.)

**Dependencies**

- PHASE-01 (`index-report` is how this phase's result is measured).
- `data/corpus/normalized/` must be present locally to run the rebuild in TASK-02-09. The unit tests
  must not require it.

**Exit Criteria**

- [ ] `pdd-agent build-index --corpus-dir data/corpus/normalized --index-db data/index/corpus.fts.db`
      exits 0.
- [ ] `pdd-agent index-report --index-db data/index/corpus.fts.db --corpus-dir data/corpus/normalized`
      reports **`documents` >= 16**, **`duplication_rate` <= 0.15**, **`mean_text_chars` >= 800**, and
      a `missing_documents` list not containing `EB111_repan07_ACM0022_v03.0`.
- [ ] The ACM0022 methodology text is retrievable:
      ```bash
      python -c "from pdd_agent.retrieval.search import search; print([r.document_name for r in search('applicability conditions alternative waste treatment', k=10)])"
      ```
      → the printed list contains `EB111_repan07_ACM0022_v03.0`.
- [ ] Section 4.4 retrieval is no longer degenerate:
      ```bash
      python -c "from pdd_agent.retrieval.search import get_examples_for_section as g; e=g('4','4.4',k=5); print(len(e), len({x.text for x in e}), len({x.document_name for x in e}))"
      ```
      → at least 4 distinct texts and at least 3 distinct documents.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both pass.

**Phase Risks**

- **RISK-02-01:** Longer, more varied retrieval changes the text injected into every drafting prompt,
  so future runs will differ from past ones. Mitigation: `data/index/` is gitignored and
  `DemoProvider` ignores retrieval content, so no committed artifact changes (ASM-009). The change is
  attributable through `index-report`'s before/after numbers, which TASK-02-09 records.
- **RISK-02-02:** Bumping `_SCHEMA_VERSION` without deleting the old database file can leave a
  database whose `sections_fts` lacks the new columns, producing `sqlite3.OperationalError` on
  SELECT. Mitigation: `build()` already runs `DROP TABLE IF EXISTS sections_fts` first; verify that
  the drop precedes the new CREATE and add a test that builds twice over the same path.
- **RISK-02-03:** The four currently-missing documents may still yield nothing if their headings never
  match the alias index — the cause could be heading detection, not chunking. Mitigation: PHASE-01's
  `corpus_document_yielded_no_sections` warning names them explicitly. If a document still yields
  zero after this phase, record which and why in the commit message rather than forcing it; the exit
  criterion asks for 16 of 17, not 17 of 17.

### PHASE-03 - Render Prose *and* Tables, and Wire Five More Verra Renderers

**Goal**

Take the exported DOCX from 3 of 11 Verra tables to 8 of 11, and stop a table from deleting the
narrative it is supposed to accompany. Independent of PHASE-01/02 — it can be executed in parallel.

**Tasks**

- [ ] TASK-03-01: Extract the duplicated prose-emitting block into `_add_section_prose`.
- [ ] TASK-03-02: Change the dispatch so prose renders first and the table follows.
- [ ] TASK-03-03: Render the audit-history table as front matter after the cover metadata table.
- [ ] TASK-03-04: Add the S-3 `ghg_boundary` block to `rules/verra/wte_methodology_rules.yaml` and a
      `MethodologyRules.ghg_boundary(mid)` accessor.
- [ ] TASK-03-05: Add `_build_structured_content` producing `proponent`, `applicability`,
      `ghg_boundary`, and `monitoring_fixed_params` payloads.
- [ ] TASK-03-06: Split calc monitoring parameters between 5.1 (fixed) and 5.2 (tracked) on
      `section_ref`.
- [ ] TASK-03-07: Update the Known Gaps list in `README.md`.

**File Changes**

- `src/pdd_agent/export/docx_export.py` (modify): add
  `_add_section_prose(doc: Any, section: dict[str, Any], is_demo: bool) -> None` containing exactly
  the body currently duplicated in both arms of the `structured` branch (lines 268-289): split the
  section text into paragraphs, add each, highlight with `FFF2CC` when `is_demo` is false and
  `section.get("confidence")` is in `{"LOW", "UNSUPPORTED"}`, and fall back to a single
  `"[No content drafted yet]"` paragraph styled `Intense Quote` when the text is empty. Then rewrite
  the dispatch so it reads: call `_add_section_prose(...)` **first, unconditionally**; then, when
  `structured` is a dict whose `table_type` resolves to a renderer, call that renderer. When
  `table_type` does not resolve, add no table and leave the prose as the only output. Behaviour for
  sections with no `structured_content` is unchanged.
- `src/pdd_agent/export/docx_export.py` (modify): immediately after the existing
  `render_cover_metadata_table(doc, cover_data)` call, add
  `_add_audit_history_front_matter(doc, run_data, project_input)`. It renders a level-2 heading
  `"Audit History"` followed by `render_audit_history_table(doc, {"audits": [...]})`, built from
  `project_input.project.audit_history` (each `AuditHistoryEntry` mapped as `audit_type`, `period`,
  `program`, `vvb_name`, `number_of_years`). When `project_input` is `None` or its `audit_history` is
  empty, the function returns immediately and adds nothing — no heading.
- `rules/verra/wte_methodology_rules.yaml` (modify): add a `ghg_boundary:` list under
  `methodologies.ACM0022`, containing the eleven rows in **S-3**, each with keys `scenario`, `source`,
  `gas`, `included`, `justification`, `source_ref`. Add nothing to `ACM0003` in this phase. Leave
  `applicability_conditions`, `parameters`, `double_counting_risks`, and `formula_references`
  untouched.
- `src/pdd_agent/domain/methodology_rules.py` (modify): add
  `ghg_boundary(self, mid: str) -> list[dict[str, Any]]` following the shape of the existing
  `applicability_conditions` accessor at line 51 — return `[]` when the methodology or the key is
  absent.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): rename
  `_build_calc_structured_content` to `_build_structured_content` and extend it. It keeps returning
  the existing `emissions_summary` payload for `"4.4"` and the `monitoring_tracked_params` payload
  for `"5.2"`, and gains:
  - `"1.5"` → `{"table_type": "proponent", "data": {"org_name": project.proponent_name,
    "contact_name": "-", "title": "-", "address": <"{city}, {region}, {country}" from
    ProjectInput.location>, "telephone": "-", "email": project.proponent_contact_email}}`. Return
    `None` when `self._project` is `None`.
  - `"3.2"` → `{"table_type": "applicability", "data": {"entries": [...]}}` with one entry per
    condition from `self._methodology_rules.applicability_conditions(mid)` for the project's first
    methodology ID, mapping `mid` → `methodology`, condition `text` → `condition`, and
    `justification` → the matching `ProjectInput.methodology_applicability.eligibility_checklist`
    value rendered as `"Confirmed"` when `True`, `"Not confirmed — see Section 3.6"` when `False`,
    and `"Not assessed"` when the condition `id` is absent from the checklist.
  - `"3.3"` → `{"table_type": "ghg_boundary", "data": {"entries": [...]}}` from
    `self._methodology_rules.ghg_boundary(mid)`, mapping each row's `scenario`, `source`, `gas`,
    `justification` straight through and `included` to the literal string `"Yes"` or `"No"`.
  - `"5.1"` → `{"table_type": "monitoring_fixed_params", "data": {"entries": [...]}}` from calc
    monitoring parameters whose `section_ref` is **not** `"5.2"`, mapping `name` → `parameter`,
    `unit` → `unit`, `name` → `description`, `source` → `source`, the parameter's value from
    `ProjectInput.quantification` where one exists (grid emission factor for `ACM0022-PARAM-04`)
    else `"-"` → `value`, and `"Fixed at validation"` → `comments`.
  Return `None` for every other section key and whenever the data needed for that key is absent.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): change the `"5.2"` branch so it includes
  only monitoring parameters whose `section_ref == "5.2"`. Today all four ACM0022 parameters land in
  5.2; after this change `ACM0022-PARAM-04` (grid emission factor, `section_ref: "4.1"`) moves to the
  5.1 fixed-parameters table and 5.2 carries three.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): update the assignment at line 693 to call
  the renamed `_build_structured_content`.
- `tests/test_docx_export.py` (modify): add the prose-and-table and audit-history tests below.
- `tests/test_docx_export_tables.py` (modify): add the end-to-end render assertions below.
- `tests/test_section_orchestrator.py` (modify): add the `_build_structured_content` tests below and
  update any existing test referencing `_build_calc_structured_content` by name.
- `README.md` (modify): replace the Known Gaps bullet beginning "Eight of the eleven Verra table
  renderers…" with one naming the three that remain unwired (`risk_assessment`,
  `sustainable_development`, `data_gaps`) and stating that they require model generation with schema
  validation.

**Function Signatures**

- `_add_section_prose(doc: Any, section: dict[str, Any], is_demo: bool) -> None` — appends the
  section's narrative paragraphs, or a single `"[No content drafted yet]"` placeholder when empty.
- `_add_audit_history_front_matter(doc: Any, run_data: dict[str, Any], project_input: Any | None) -> None`
  — appends an "Audit History" heading and table; no-op when there are no audit entries.
- `MethodologyRules.ghg_boundary(self, mid: str) -> list[dict[str, Any]]` — the GHG project-boundary
  rows for a methodology ID, or `[]`.
- `SectionOrchestrator._build_structured_content(self, section_key: str) -> dict[str, Any] | None` —
  the `structured_content` payload for that subsection, or `None` when the section has no table or the
  data it needs is absent.

**Test Specs**

- Export a run whose section 4.4 has both `text="Net reductions are 357,006 tCO2e/yr."` and an
  `emissions_summary` payload → the document contains a paragraph equal to
  `"Net reductions are 357,006 tCO2e/yr."` **and** a table whose header row is
  `["Calendar year of crediting period", "Estimated GHG emission reductions or removals (tCO2e)"]`.
  (Today the paragraph is absent.)
- Export a run whose section 2.1 has `text="No net harm."` and no `structured_content` → one
  paragraph `"No net harm."`, no new table. Unchanged behaviour.
- Export a run whose section 3.3 carries `structured_content={"table_type": "nonexistent_type", "data": {}}`
  → the section's prose still renders and no table is added; the export does not raise.
- `_build_structured_content("1.5")` on an orchestrator whose `ProjectInput.project.proponent_name`
  is `"Mekong Delta Rice Sustainability Company"` → `result["table_type"] == "proponent"` and
  `result["data"]["org_name"] == "Mekong Delta Rice Sustainability Company"`.
- `_build_structured_content("3.2")` for an ACM0022 project → `result["table_type"] == "applicability"`
  and `len(result["data"]["entries"]) == 3` (ACM0022 declares `ACM0022-AC-01` through `-AC-03`), and
  `result["data"]["entries"][0]["methodology"] == "ACM0022"`.
- `_build_structured_content("3.3")` for an ACM0022 project → `result["table_type"] == "ghg_boundary"`,
  `len(result["data"]["entries"]) == 11`, and every entry's `included` is exactly `"Yes"` or `"No"`.
- `_build_structured_content("5.1")` with an ACM0022 calc result → exactly one entry, whose
  `parameter` is `"Grid emission factor"`.
- `_build_structured_content("5.2")` with the same calc result → exactly **three** entries (was four),
  none of them the grid emission factor.
- `_build_structured_content("2.1")` → `None`.
- `_build_structured_content("1.5")` with `self._project is None` → `None`.
- Export a run for a project whose `ProjectInput.project.audit_history` is empty → the document's
  paragraph texts contain no `"Audit History"`.
- Export a run for a project with one `AuditHistoryEntry(audit_type="Validation", period="2020-2027",
  program="VCS", vvb_name="Earthood", number_of_years=7)` → the document contains a paragraph
  `"Audit History"` and a table whose header row is
  `["Audit type", "Period", "Program", "Validation/verification body name", "Years"]` with 2 rows.

**Dependencies**

- None. Executable in parallel with PHASE-01 and PHASE-02.

**Exit Criteria**

- [ ] `python -m pytest tests/test_docx_export.py tests/test_docx_export_tables.py tests/test_section_orchestrator.py -v`
      passes.
- [ ] An exported DOCX for a run carrying a calc result and a `ProjectInput` contains both the prose
      and the table in section 4.4, and contains the proponent, applicability, GHG boundary, and
      fixed-parameters tables.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both pass.

**Phase Risks**

- **RISK-03-01:** Existing tests may assert that a section carrying `structured_content` has **no**
  prose — that was the old contract. Mitigation: expect one or more failures in
  `tests/test_docx_export_tables.py`; update each to assert prose *and* table rather than deleting
  the assertion, and note the old expectation in a comment beside each change.
- **RISK-03-02:** Moving `ACM0022-PARAM-04` from the 5.2 table to 5.1 changes an assertion the
  previous push locked in (`len(result["data"]["entries"]) == 4` for 5.2). Mitigation: that assertion
  is listed above as changing to 3; update it deliberately, not mechanically.
- **RISK-03-03:** The S-3 boundary rows are authored from methodology knowledge, not extracted from
  the ACM0022 document. Mitigation: ASM-005 requires verifying them against
  `EB111_repan07_ACM0022_v03.0` once PHASE-02 makes it retrievable. Until then every row carries an
  explicit `source_ref`, so a reviewer can see exactly what is being claimed.

### PHASE-04 - One Real Model Call, Capped at One Dollar

**Goal**

Execute the first real-provider section draft this repository has ever run deliberately, read the
output, and write down what it revealed. Both previously-discovered output defects — the
conversational preamble and the truncating trailer stripper — surfaced only on real model output, and
neither would have been caught by any test. This phase buys that class of discovery for roughly $0.20.

It also builds the mechanism that makes real-model checks repeatable and bounded: a `--only-section`
flag on `pdd-agent draft`.

**Tasks**

- [ ] TASK-04-01: Add `--only-section` to `pdd-agent draft` and a `only_sections` parameter to the
      orchestrator.
- [ ] TASK-04-02: Verify pre-flight state.
- [ ] TASK-04-03: Run one real `claude-code` section draft with `PDD_MAX_COST_USD=1`.
- [ ] TASK-04-04: Read the drafted text and record the findings.
- [ ] TASK-04-05: Write `reports/2026-08-13-single-section-smoke.md`.

**File Changes**

- `src/pdd_agent/agent/section_orchestrator.py` (modify): add
  `only_sections: list[str] | None = None` as the last keyword parameter of `__init__`, storing it as
  `self._only_sections`. In `draft_all_sections()` (line 904), skip any `(sid, ssid)` whose `ssid` is
  not in `self._only_sections` when that list is non-empty. Leave `draft_project_details()`,
  `run()`, and `run_review()` unchanged.
- `src/pdd_agent/cli.py` (modify): add to `draft_parser`:
  ```python
  draft_parser.add_argument(
      "--only-section",
      action="append",
      dest="only_sections",
      help="Draft only this sub-section id (e.g. 4.1). Repeatable. Default: all 36 sections.",
  )
  ```
  Pass `only_sections=getattr(args, "only_sections", None)` through to the `SectionOrchestrator`
  construction inside `_run_draft`.
- `reports/2026-08-13-single-section-smoke.md` (create): hand-written. Must record, at minimum: the
  exact command run; the provider, model, and `claude --version`; measured wall-clock seconds and
  `total_cost_usd`; the full drafted section text verbatim; whether the text opened with a
  conversational preamble and whether `strip_assistant_preamble` removed it; whether the text ended
  mid-sentence; whether any `[CORPUS: …]` citation appeared and which document it named; and any
  structlog event from `budget_exhausted`, `retrieval_index_fallback`, `retrieval_family_fallback`,
  or `calc_engine_skipped` observed on stderr.
- `tests/test_section_orchestrator.py` (modify): add the `only_sections` tests below.

**Function Signatures**

- `SectionOrchestrator.__init__(..., only_sections: list[str] | None = None)` — when non-empty,
  `draft_all_sections()` drafts only the listed sub-section ids; `None` or empty drafts all 36.

**Test Specs**

- `SectionOrchestrator(provider=DemoProvider(), project_input=pi, only_sections=["4.1"]).draft_all_sections()`
  → returns a list of length 1 whose single element has `sub_section_id == "4.1"`.
- `SectionOrchestrator(..., only_sections=["4.1", "4.2"]).draft_all_sections()` → length 2, in schema
  order `["4.1", "4.2"]`.
- `SectionOrchestrator(..., only_sections=None).draft_all_sections()` → length 36. Unchanged default.
- `SectionOrchestrator(..., only_sections=[]).draft_all_sections()` → length 36 — an empty list is
  treated as "no filter", not "draft nothing".
- `SectionOrchestrator(..., only_sections=["9.9"]).draft_all_sections()` → length 0, no exception.

**Dependencies**

- PHASE-02 (the point is to exercise the rebuilt grounding) and PHASE-03 (so the export path under
  test is the final one).
- The `claude` CLI on PATH and authenticated. Verify with `claude --version`; `pdd-agent doctor`
  reports it as `[OK] claude CLI: <version>`.
- Real subscription usage of roughly **$0.20** for one section at the measured rate of $0.167898 and
  36.1 s per section draft.

**Exit Criteria**

- [ ] `python -m pytest tests/test_section_orchestrator.py -v` passes with the new cases.
- [ ] `pdd-agent doctor` reports `[OK]` for both the `claude` CLI and the retrieval index.
- [ ] The following completes with exit code 0:
      ```bash
      PDD_MAX_COST_USD=1 pdd-agent draft \
        --input configs/projects/vietnam_socson_from_sheet.yaml \
        --provider claude-code \
        --only-section 4.1 \
        --run-id smoke-4-1
      ```
      (PowerShell: `$env:PDD_MAX_COST_USD = "1"; pdd-agent draft --input ... --only-section 4.1 --run-id smoke-4-1`)
- [ ] `python -c "import json;d=json.load(open('data/runs/run-smoke-4-1.json'));print(len(d['sections']), d['sections'][0]['sub_section_id'])"`
      prints `1 4.1`.
- [ ] `reports/2026-08-13-single-section-smoke.md` exists and records every item listed in its File
      Changes entry.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both pass.

**Phase Risks**

- **RISK-04-01:** The run JSON filename convention may prefix the supplied `--run-id`. Mitigation: if
  `data/runs/run-smoke-4-1.json` does not exist, list `data/runs/` for the newest file and use that
  path in the exit-criterion command; record the actual filename in the smoke report.
- **RISK-04-02:** A new defect class surfaces, as happened twice before on real output. Mitigation:
  that is the phase's purpose. Record it in the smoke report with the exact triggering output, add a
  failing test, fix it, and re-run the single section — the total spend stays under $1.
- **RISK-04-03:** `PDD_MAX_COST_USD=1` may trip `BudgetExhaustedError` mid-section if the CLI reports
  a higher cost than the measured $0.168. Mitigation: that is a safe failure. Record the reported
  cost in the smoke report and re-run once with `PDD_MAX_COST_USD=2`. Do not raise it further.

### PHASE-05 - Give the Calc Engine Its Composition, and Conserve Mass

**Goal**

Stop the ACM0022 engine from discarding a third of Soc Son's throughput, and let a project declare the
waste composition its registered PDD publishes instead of having the engine assume an even split. Then
re-measure the three registered-PDD oracle xfails honestly.

**Tasks**

- [ ] TASK-05-01: Add `WasteFraction` and the optional `waste_composition` / `capacity_ramp` fields.
- [ ] TASK-05-02: Implement the S-2 mapping in `_map_acm0022`, including the `len(kept)` fix.
- [ ] TASK-05-03: Add a mass-conservation regression test.
- [ ] TASK-05-04: Declare Soc Son's published composition in its config.
- [ ] TASK-05-05: Re-measure the three oracle xfails and update them per DEC-002.
- [ ] TASK-05-06: Surface the composition source strings as calc warnings so they reach the DOCX
      reviewer-issues appendix.

**File Changes**

- `schemas/project_input.py` (modify): add above `ProjectTechnology`:
  ```python
  class WasteFraction(BaseModel):
      waste_type: str = Field(..., min_length=1, description="Key into DOC_BY_WASTE_TYPE")
      mass_fraction: float = Field(
          ..., ge=0.0, le=1.0,
          description="Share of annual_waste_throughput, dimensionless 0-1",
      )
      source: str = Field(..., min_length=1, description="Where this fraction was published")
  ```
  Add to `ProjectTechnology`, after `biomethanization_suitable_fraction`:
  ```python
  waste_composition: list[WasteFraction] = Field(
      default_factory=list,
      description=(
          "Published waste-composition split. When non-empty it replaces the "
          "even split across waste_type. Fractions may sum to less than 1.0 — "
          "inert mass generates no landfill methane and is legitimately omitted."
      ),
  )
  capacity_ramp: list[float] | None = Field(
      None,
      description=(
          "Optional per-crediting-period-year capacity utilisation, dimensionless "
          "0-1, index 0 = year 1. Reserved for a future ramp-aware baseline; "
          "validated but not yet consumed by the calc engine."
      ),
  )
  ```
  Add a model validator on `ProjectTechnology` rejecting a `waste_composition` whose
  `mass_fraction` values sum above `1.0 + 1e-9`, with the message
  `"waste_composition mass fractions sum to {total:.4f}, which exceeds 1.0"`. Add a validator
  rejecting any `capacity_ramp` element outside `[0.0, 1.0]`. Change **no existing field**; both new
  fields must be optional so all six existing config YAML files keep validating.
- `src/pdd_agent/calc/dispatch.py` (modify): rewrite the waste-stream block of `_map_acm0022`
  (lines 167-182) to implement **S-2** exactly. Keep the `if not kept: return None` guard, the
  `grid_emission_factor` / `grid_emission_factor_source` guards, `swds_diversion_fraction = 1.0`, and
  every other key in `mapped` unchanged. When `waste_composition` is used, append one warning per
  entry of the form
  `f"waste_composition: {e.waste_type} {e.mass_fraction:.1%} — {e.source}"`, so the provenance reaches
  the reviewer-issues appendix that already renders calc warnings prefixed `CALC: `.
- `configs/projects/vietnam_socson_from_sheet.yaml` (modify): under `technology`, add the
  `waste_composition` list from **S-2**, each entry carrying
  `source: "VCS Soc Son registered PDD, Table 8 — Components of solid waste"`. Leave `waste_type`,
  `annual_waste_throughput`, and every other field exactly as they are — `waste_type` still drives the
  fallback and the applicability narrative.
- `configs/demo/inegol_project_input.yaml` (modify): **no change.** İnegöl deliberately keeps
  exercising the fallback path (ASM-006).
- `tests/test_calc_dispatch.py` (modify): add the mapping and mass-conservation tests below.
- `tests/test_input_schema.py` (modify): add the validator tests below.
- `tests/test_registered_pdd_oracle.py` (modify): after re-measuring, apply DEC-002 — for each of the
  three xfails, either remove the `xfail` marker (when the measured error is within `TOLERANCE`) or
  rewrite its `reason` string with the newly measured figures and the date. **Do not change
  `TOLERANCE`.**
- `tests/test_acm0022_calc.py`, `tests/test_calc_integration.py` (modify): update any expected
  baseline/net values that move because Soc Son's stream tonnage rises from 973,333 to 1,460,000 t/yr.
  Record the previous value in a comment beside each changed assertion so the diff shows the magnitude
  of the correction.
- `README.md` (modify): under "Quantification precedence", add two sentences stating that
  `technology.waste_composition`, when declared, replaces the even split across `waste_type`, and that
  waste types absent from `DOC_BY_WASTE_TYPE` have their mass redistributed across the mapped types
  rather than dropped.

**Function Signatures**

- `WasteFraction(waste_type: str, mass_fraction: float, source: str)` — one published waste-composition
  row; `mass_fraction` is a dimensionless 0–1 share of `annual_waste_throughput`.
- `ProjectTechnology.waste_composition: list[WasteFraction]` — empty by default; non-empty selects the
  S-2 step 1 path.
- `ProjectTechnology.capacity_ramp: list[float] | None` — per-year utilisation, validated but not yet
  consumed.
- `_map_acm0022(pi: ProjectInput) -> tuple[dict[str, Any], list[str]] | None` — unchanged signature.

**Test Specs**

- **Mass conservation, fallback path.** `build_engine_inputs` on
  `configs/projects/vietnam_socson_from_sheet.yaml` **with `waste_composition` removed** →
  `sum(s["annual_tonnes"] for s in inputs["waste_streams"]) == pytest.approx(1_460_000.0)`. Today this
  sums to 973,333.33 (66.67% of declared). The warning list contains a string mentioning `plastics`
  and the word `redistributed`.
- **Composition path.** `build_engine_inputs` on the shipped
  `configs/projects/vietnam_socson_from_sheet.yaml` → `waste_streams` has 6 entries; the entry with
  `waste_type == "food_waste"` has `annual_tonnes == pytest.approx(1_460_000.0 * 0.519)`
  (= 757,740.0); the entry with `waste_type == "wood"` has `annual_tonnes == 0.0`.
- **Inert mass is not rescaled.** For the same config,
  `sum(s["annual_tonnes"] for s in waste_streams) == pytest.approx(1_460_000.0 * 0.575)` — the six
  declared fractions sum to 0.575, and the remaining 42.5% of inert mass is correctly absent.
- **Unmapped composition entry.** A `ProjectInput` whose `waste_composition` includes
  `WasteFraction(waste_type="plastics", mass_fraction=0.03, source="test")` → no stream is emitted for
  `plastics`, and the warnings contain a string containing `"3.0%"` and `"non-degradable or unmapped"`.
- **Validator, over-unity.** `ProjectTechnology.model_validate({... "waste_composition": [{"waste_type": "food_waste", "mass_fraction": 0.7, "source": "t"}, {"waste_type": "wood", "mass_fraction": 0.4, "source": "t"}] ...})`
  → raises `ValidationError` whose message contains `"exceeds 1.0"`.
- **Validator, exactly 1.0.** The same with fractions `0.6` and `0.4` → validates successfully.
- **Validator, ramp bounds.** `capacity_ramp=[0.5, 1.0, 1.5]` → raises `ValidationError`;
  `capacity_ramp=[0.5, 1.0]` → validates.
- **Backward compatibility.** Every file matched by `configs/projects/*.yaml` and
  `configs/demo/*.yaml` still validates through `ProjectInput.model_validate(yaml.safe_load(...))`
  with no `waste_composition` present.
- **İnegöl unchanged.** `build_engine_inputs` on `configs/demo/inegol_project_input.yaml` → exactly one
  stream, `waste_type == "municipal_solid_waste"`, `annual_tonnes == pytest.approx(262_970.37)`.

**Dependencies**

- PHASE-04 (so the smoke check exercised the pipeline before its numbers change).

**Exit Criteria**

- [ ] ```bash
      python -c "import yaml;from pdd_agent.calc.dispatch import build_engine_inputs;from schemas.project_input import ProjectInput;pi=ProjectInput.model_validate(yaml.safe_load(open('configs/projects/vietnam_socson_from_sheet.yaml',encoding='utf-8')));_,i,_=build_engine_inputs(pi);print(round(sum(s['annual_tonnes'] for s in i['waste_streams'])))"
      ```
      → prints `839500` (1,460,000 × 0.575). Before this phase the same command prints `973333`.
- [ ] `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` exits 0, reports
      `Methodology: ACM0022`, a `BE_CH4 (methane from SWDS)` component greater than 0, and prints one
      `waste_composition:` warning line per declared fraction.
- [ ] `python -m pytest tests/test_registered_pdd_oracle.py -v` reports 0 failed. Each of the three
      previously-xfailing tests is either passing with its marker removed, or still xfailing with a
      `reason` string containing a figure measured during this phase and the date `2026-08-13` or
      later.
- [ ] The measured Soc Son crediting-period total and its relative error against 3,808,082 tCO2e are
      recorded in the commit message.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both pass.

**Phase Risks**

- **RISK-05-01:** Conserving mass raises the tonnage entering the engine by 50% on Soc Son (973,333 →
  1,460,000 t/yr before composition weighting), which alone pushes the crediting-period total further
  above the registered figure — the opposite of the direction needed. Composition weighting then pulls
  it back down, because 42.5% of the real stream is inert and `food_waste` (DOC 0.15, k 0.185) has a
  very different decay profile from mixed `municipal_solid_waste` (DOC 0.17, k 0.09). Mitigation: the
  two changes must land in the same commit and be measured together, and the honest outcome is
  whatever the oracle reports. Under no circumstances widen `TOLERANCE` (DEC-002).
- **RISK-05-02:** Soc Son's config declares both `municipal_solid_waste` and `food_waste` in
  `waste_type` — mixed MSW's DOC of 0.17 already embeds its food fraction, so the current fallback
  double-counts organics. The composition list deliberately omits `municipal_solid_waste` to avoid
  this. Do not add it back "for completeness".
- **RISK-05-03:** `capacity_ramp` is validated but unused, which invites a future reader to assume it
  is wired. Mitigation: its field description says so explicitly; keep that wording.

### PHASE-06 - Table-Aware Ingestion Behind an Optional Extra

**Goal**

Preserve table structure when normalizing source PDFs, so the numeric tables that registered PDDs
publish stop being flattened into prose. This is the lowest-priority phase and the only one that adds
a dependency; it is placed last so that a partial delivery of this plan still lands everything above.

**Tasks**

- [ ] TASK-06-01: Add `pdfplumber` under a new optional `ingest` extra.
- [ ] TASK-06-02: Extract tables during normalization into a `tables` key, degrading gracefully.
- [ ] TASK-06-03: Report table extraction in `pdd-agent doctor`.
- [ ] TASK-06-04: Add tests that require neither `pdfplumber` nor the corpus.

**File Changes**

- `pyproject.toml` (modify): add a new optional-dependency group after `llm`:
  ```toml
  ingest = [
      "pdfplumber>=0.11.0",
  ]
  ```
  Do **not** add it to the base `dependencies` list — text extraction must keep working with `pypdf`
  alone. Regenerate `uv.lock` with `uv lock` and commit it; CI enforces `--locked`.
- `src/pdd_agent/ingest/normalize.py` (modify): add
  `_extract_tables(pdf_path: Path) -> list[dict[str, Any]]`. It imports `pdfplumber` inside the
  function body and returns `[]` immediately on `ImportError`, emitting
  `logger.warning("pdfplumber_not_installed", path=str(pdf_path))` once per process. For each page it
  calls `page.extract_tables()` and returns one entry per table:
  `{"page": int, "table_index": int, "rows": list[list[str]]}`, with every cell coerced to `str` and
  `None` cells rendered as `""`. Wrap the whole extraction in `try/except Exception` and return
  whatever was collected so far on failure, logging `table_extraction_failed` with the page number —
  a malformed PDF must never fail normalization. Call it from the PDF branch and add the result to the
  output dict under the key `"tables"`. Add `"tables": []` to the two other output-dict initialisers
  (lines 127 and 221 and the error path at 271) so the key is always present. Change nothing about
  `pages`, `text`, `headings`, or `text_blocks`.
- `src/pdd_agent/doctor.py` (modify): add one check reporting `[OK] pdfplumber importable` or
  `[WARN] pdfplumber not installed — corpus tables will not be extracted (pip install -e ".[ingest]")`,
  following the shape of the existing optional-package checks. It must be a WARN, never a failure.
- `tests/test_normalize.py` (modify): add the tests below.
- `README.md` (modify): remove the Known Gaps bullet "Corpus normalization discards table structure
  from ingested source PDDs…" and add `ingest` to the extras listed in the install command.

**Function Signatures**

- `_extract_tables(pdf_path: Path) -> list[dict[str, Any]]` — one entry per detected table as
  `{"page": int, "table_index": int, "rows": list[list[str]]}`; returns `[]` when `pdfplumber` is not
  installed or extraction fails.

**Test Specs**

- With `pdfplumber` absent (simulate by monkeypatching the import to raise `ImportError`),
  `_extract_tables(Path("anything.pdf"))` → `[]`, and normalization of that file still produces a
  dict whose `"text"` is non-empty and whose `"tables"` is `[]`.
- With a stub module whose `open()` yields one page returning
  `[[["A", "B"], ["1", None]]]` from `extract_tables()` → `_extract_tables(...)` returns
  `[{"page": 1, "table_index": 0, "rows": [["A", "B"], ["1", ""]]}]` — note the `None` cell becomes
  `""`.
- With a stub page whose `extract_tables()` raises `RuntimeError` → `_extract_tables` returns `[]` and
  does not propagate the exception.
- A normalized DOCX (non-PDF) input → the output dict contains `"tables": []`.

**Dependencies**

- PHASE-05 (so the higher-value work has already landed).
- `pdfplumber` is **not currently installed** in this environment and is not a declared dependency.
  Install with `pip install -e ".[dev,service,export,llm,ingest]"`.
- Re-running normalization requires `data/corpus/raw/verra/` (26 PDFs, ~64 MB, gitignored but present
  locally).

**Exit Criteria**

- [ ] `python -m pytest tests/test_normalize.py -v` passes **without** `pdfplumber` installed.
- [ ] `pdd-agent doctor` reports a line for `pdfplumber` — `[OK]` when installed, `[WARN]` when not,
      and exits with the same status either way.
- [ ] After `pip install -e ".[ingest]"` and re-running normalization over
      `data/corpus/raw/verra/VCS_Soc_Son_Project-Description.pdf`, the resulting `.norm.json` contains
      a non-empty `tables` list. (Skip and record as skipped if the raw corpus is absent.)
- [ ] `uv lock` produces no further diff and `uv sync --locked --all-extras` succeeds.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both pass.

**Phase Risks**

- **RISK-06-01:** `pdfplumber` is markedly slower than `pypdf` and normalizing 26 PDFs may take
  several minutes. Mitigation: it runs only during ingestion, which is a manual, occasional command —
  not in any test and not in the drafting path.
- **RISK-06-02:** Adding a dependency to `pyproject.toml` without regenerating `uv.lock` breaks CI,
  which runs `uv sync --locked`. Mitigation: the exit criteria include `uv lock` explicitly.
- **RISK-06-03:** `tables` in the `.norm.json` has no consumer yet, so this phase adds data nothing
  reads. Mitigation: accept it. Wiring tables into retrieval or into the calc-input extraction is a
  separate, evidence-driven change; extracting them first is what makes that change possible.

## Gotchas

- **`_find_content_page` must not be deleted.** It is the per-document fallback for any `.norm.json`
  that predates `_build_headings_and_blocks()` (DEC-003), and S-1 step 3 depends on it existing.
- **`text_blocks[0]` is usually not a section.** When a document has text before its first heading,
  `_build_headings_and_blocks()` emits a leading block with `heading == ""`. Soc Son has 190 headings
  and 191 blocks for exactly this reason. Dropping it is S-1 step 2; forgetting to drop it shifts
  every subsequent pairing by one and silently mislabels the entire document.
- **Corpus heading text includes table-of-contents dot leaders.** The first heading in Soc Son's
  normalized JSON is literally
  `'1.1 Summary Description of the Project ................................................................................ 4'`.
  That is why S-1 step 4 skips headings whose source page is a TOC page — without it, the index fills
  with contents listings.
- **`content_class` search has always returned zero.** `RetrievalIndex.build` inserts `""` for that
  column (`index.py:126`) while `search` filters on equality. Any test written today asserting that a
  `content_class` filter returns nothing is asserting the bug, not the contract.
- **Setting `structured_content` currently deletes the section's prose.** That is the behaviour
  PHASE-03 changes; until it lands, adding a producer for a new section silently removes that
  section's narrative from the DOCX.
- **`per_type_tonnes` is computed before the `DOC_BY_WASTE_TYPE` filter.** The divisor is
  `len(tech.waste_type)` but only `len(kept)` streams are emitted, so every unmapped waste type
  silently deletes its share of the throughput. Soc Son loses 486,667 of 1,460,000 tonnes/year this
  way. The fix is `len(kept)`, and it is easy to miss because nothing fails when it is wrong.
- **`municipal_solid_waste` already embeds the organic fraction.** Its `DOC` of 0.17 is a weighted
  average across the whole mixed stream. Declaring both `municipal_solid_waste` and `food_waste` for
  the same project double-counts organics — which is exactly what Soc Son's `waste_type` list does
  today, and why S-2's composition list omits `municipal_solid_waste`.
- **Waste-composition fractions may legitimately sum to less than 1.0.** Glass, plastic, metal and
  inert waste generate no landfill methane. Rescaling the degradable fractions up to 1.0 would
  manufacture emissions that do not exist. The validator therefore rejects sums **above** 1.0 only.
- **Annual versus crediting-period totals.** `net_emission_reductions_tco2e` is tCO2e **per year**;
  `crediting_period_total_tco2e` is tCO2e across all years. The registered İnegöl figures are 104,285
  (annual average) and 730,000 (total). Mixing them produces a clean 7× error that looks plausible.
- **`ACM0022CalcInput.calculation_year` defaults to 1**, the smallest first-order-decay year. Correct
  for the scalar fields, wrong if you assume it represents a typical year.
- **structlog event-style logging.** Write `logger.warning("retrieval_family_fallback", family=slug)`,
  never `logger.warning(f"falling back to {slug}")`. Lint will not catch a violation.
- **`DraftRun.load()` must use `.get()`.** There are roughly 1,555 run JSON files in `data/runs/` and
  the FastAPI dashboard loads all of them on every page request (CON-003).
- **`ruff format --check .` is a CI gate.** Run `ruff format .` before committing; a correct change
  still fails CI on formatting.
- **Environment variables are read at call time, not import time** (`PDD_MAX_COST_USD`,
  `PDD_CALC_AUTHORITATIVE`, `PDD_MAX_TOKENS`). Keep that pattern so tests can monkeypatch them.
- **Windows shell differences.** Commands here are POSIX. In PowerShell, `VAR=x cmd` is a parse error —
  use `$env:VAR = "x"; cmd`.
- **`schemas/` is a top-level package outside `src/`.** Import it as `from schemas.project_input
  import ProjectInput`, never `from pdd_agent.schemas...`.

## Verification Strategy

- **TEST-001:** `python -m pytest -m "not corpus" -q` → `0 failed`. Baseline before this plan is
  **798 passed, 7 deselected, 3 xfailed**. Expect roughly 830+ passed on completion, with the xfail
  count at 3 or lower.
- **TEST-002:** `ruff check . && ruff format --check .` → both report success.
- **TEST-003:** corpus health after PHASE-02:
  ```bash
  pdd-agent build-index --corpus-dir data/corpus/normalized --index-db data/index/corpus.fts.db
  pdd-agent index-report --index-db data/index/corpus.fts.db --corpus-dir data/corpus/normalized
  ```
  → `documents` at least 16, `duplication_rate` at most 0.15, `mean_text_chars` at least 800.
  Before this plan the same command reports 13 documents, 0.734, and ~497.
- **TEST-004:** retrieval is no longer degenerate:
  ```bash
  python -c "from pdd_agent.retrieval.search import get_examples_for_section as g; e=g('4','4.4',k=5); print('examples',len(e)); print('distinct_texts',len({x.text for x in e})); print('distinct_docs',len({x.document_name for x in e}))"
  ```
  → `distinct_texts` at least 4 and `distinct_docs` at least 3. Before this plan: 2 and 1.
- **TEST-005:** the methodology document is reachable:
  ```bash
  python -c "from pdd_agent.retrieval.search import search; print([r.document_name for r in search('applicability conditions alternative waste treatment', k=10)])"
  ```
  → the list contains `EB111_repan07_ACM0022_v03.0`.
- **TEST-006:** exported tables and prose after PHASE-03:
  ```bash
  pdd-agent draft --input configs/projects/vietnam_socson_from_sheet.yaml --provider demo --run-id verify-tables
  pdd-agent export --run-id verify-tables --force
  python - <<'PY'
  import docx, glob
  path = sorted(glob.glob("data/runs/*verify-tables*.docx"))[-1]
  d = docx.Document(path)
  headers = [" | ".join(c.text.strip() for c in t.rows[0].cells) for t in d.tables]
  for needle in ("Organization name", "Methodology/tool", "Scenario | Source | Gas",
                 "Data/parameter | Unit | Description | Value"):
      assert any(needle in h for h in headers), f"missing table: {needle}"
  print("tables:", len(d.tables))
  PY
  ```
  → all four assertions pass.
- **TEST-007:** mass conservation after PHASE-05:
  ```bash
  python -c "import yaml;from pdd_agent.calc.dispatch import build_engine_inputs;from schemas.project_input import ProjectInput;pi=ProjectInput.model_validate(yaml.safe_load(open('configs/projects/vietnam_socson_from_sheet.yaml',encoding='utf-8')));_,i,w=build_engine_inputs(pi);print('tonnes',round(sum(s['annual_tonnes'] for s in i['waste_streams'])));print('streams',len(i['waste_streams']))"
  ```
  → prints `tonnes 839500` and `streams 6`. Before this plan: `tonnes 973333`, `streams 2`.
- **TEST-008:** `python -m pytest tests/test_registered_pdd_oracle.py -v` → `0 failed`, and every
  remaining `xfail` reason cites a figure measured on or after 2026-08-13.
- **MANUAL-001:** Open the DOCX from TEST-006 and confirm that section 4.4 shows both its narrative
  paragraph and the year-by-year emissions table, and that no section lost prose it previously had.
- **MANUAL-002:** Read the section text drafted in PHASE-04 in full. Confirm it does not open with a
  conversational sentence, does not end mid-sentence, and that any `[CORPUS: …]` citation names a
  document that genuinely appears in `data/corpus/normalized/`.
- **MANUAL-003:** Read three `section_spans` entries produced by PHASE-02 for three different
  documents and confirm each is coherent prose from the section its heading names — not a running
  header, not a contents listing, not the previous section's tail.
- **OBS-001:** During the PHASE-04 run, watch stderr for the structlog events `budget_exhausted`,
  `retrieval_index_fallback`, `retrieval_family_fallback`, `corpus_block_alignment_failed`,
  `corpus_document_yielded_no_sections`, and `calc_engine_skipped`. Any of them invalidates a premise
  of the run and must be recorded in `reports/2026-08-13-single-section-smoke.md`.
- **OBS-002:** `pdd-agent doctor` → `[OK]` for the retrieval index and, before PHASE-04, `[OK]` for the
  `claude` CLI.

## Risks and Alternatives

- **RISK-001:** Re-chunking changes the text injected into every drafting prompt, so section output
  from real providers will differ from anything measured before. Mitigation: no committed artifact
  depends on retrieval content (`DemoProvider` ignores it, `data/index/` is gitignored), and
  `index-report`'s before/after numbers make the change attributable. This is the intended effect, not
  a side effect.
- **RISK-002:** PHASE-05's two corrections push the Soc Son total in opposite directions and may not
  land inside ±20%. Mitigation: DEC-002 — re-measure, record honestly, never widen the tolerance. A
  documented xfail with fresh numbers is a successful outcome for this phase; a green test bought by
  loosening the band is a failure.
- **RISK-003:** PHASE-04 is the only phase that spends real money and the only one that cannot be
  replayed for free. Mitigation: it is capped at one section and `PDD_MAX_COST_USD=1`, roughly $0.20 at
  the measured rate, and the `--only-section` flag makes every future real-model check equally bounded.
- **RISK-004:** The plan touches the indexer, the exporter, and the calc mapper — three areas with
  large existing test suites. Mitigation: each phase's exit criteria run the full suite, and phases
  are ordered so a partial delivery still leaves the tree green and strictly better than it started.
- **ALT-001:** *Replace FTS5/BM25 with embedding-based retrieval.* Rejected. The failure is that the
  index contains duplicated 500-character page fragments; embedding the same fragments retrieves the
  same fragments. Measure BM25 over correct chunks first, using `index-report` and TEST-004, before
  adding a model dependency to a retrieval layer whose selling point is that it costs nothing.
- **ALT-002:** *Run the full 36-section real-model proof instead of one section.* Rejected for this
  plan. It costs an estimated $12–16, was explicitly declined on 2026-08-05, and buys a grounding
  scorecard that is only meaningful once PHASE-02 has landed. One section for $0.20 catches the same
  class of output defect that the two previously-discovered bugs belonged to.
- **ALT-003:** *Split `ProjectInput` into per-family discriminated unions while adding
  `waste_composition`.* Rejected, consistent with DEC-004 in `docs/2026-07-12-rice-pilot-findings.md`.
  The wide schema with optional family blocks has handled every project to date; revisit only when a
  second real non-WTE project's data makes it genuinely painful.
- **ALT-004:** *Rescale waste-composition fractions to sum to 1.0.* Rejected. Inert mass genuinely
  generates no landfill methane; normalising it away would inflate the baseline by roughly 74% on Soc
  Son, manufacturing emission reductions that the registered PDD does not claim.
- **ALT-005:** *Delete `_find_content_page` once section spans work.* Rejected for this plan.
  It is the documented per-document fallback (DEC-003) and costs nothing to keep. Remove it only after
  `index-report` has shown zero `corpus_block_alignment_failed` events across a full rebuild.

## Suggested Next Step

Execute PHASE-01. It is entirely offline, adds no behaviour to the drafting path, and produces the
measurement instrument — `pdd-agent index-report` — that every later claim in this plan is checked
against. Run it against the current index first and record the numbers (expect 1,015 rows, 270
distinct texts, 0.734 duplication, 13 documents); those become the before-figures for PHASE-02's exit
criteria. Then begin PHASE-02 by implementing `_chunk_block` and the S-1 pairing rule in
`src/pdd_agent/parse/section_parser.py`, and confirm the new `section_spans` tests fail before the
indexer is changed to consume them.
