---
title: "Real-Output Fidelity: Render What Models Write, Size What They Produce, and Charge the Emissions They Cause"
date: "2026-08-21"
status: "complete — all 5 phases (49 tasks) landed in 6375b82; verified in-repo: markdown_docx.py renderer, 36 schema max_chars budgets, required_inputs export-gate split, path_to_approved/pagination/claude-code, PE_INC + capacity_ramp with 909 tests passing"
request: "Implement the 2026-08-21 brainstorm: make the DOCX exporter render real model output (Markdown tables, headings, emphasis, math), replace the uniform 4,000-character section cap with per-section budgets and honest truncation reporting, split the export gate's two meanings, fix the product-surface defects that block a human reviewer, and close the two measured discrepancies between the ACM0022 engine and the registered Soc Son PDD."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-08-21-pdd-real-output-gap-brainstorm.md"
  - "research/2026-08-13-pdd-hollow-grounding-and-calc-inputs-brainstorm.md"
---

# Plan: Real-Output Fidelity

## Objective

This repository drafts Verra VCS Project Design Documents and exports them to Word. It has produced
exactly one section of real (non-synthetic) model output, and that one section proved that the
exporter cannot render what real models write, that every section is silently amputated at 4,000
characters, and that the export gate blocks precisely the honest behaviour the prompts ask for.
Separately, the ACM0022 calculation engine reports **zero project emissions** for a 52 MW
incinerator burning 1.46 million tonnes of waste a year.

This plan makes the Word deliverable render real output faithfully, gives each of the 36 sections a
length budget matched to what it actually has to say, teaches the export gate to distinguish "the
model lied" from "the model correctly reported a missing input", repairs the review UI defects that
stop a human from working through a document, and charges the ACM0022 engine for the emissions an
incinerator actually causes — measured against a year-by-year oracle extracted from the registered
Soc Son PDD.

## Context Snapshot

- **Current state:**
  - `src/pdd_agent/export/docx_export.py:1047` (`_split_paragraphs`) splits model output on `\n` and
    adds each line as a plain Word paragraph. Real model output is Markdown, so a real export
    contains literal `# heading` lines, literal `| pipe | table |` rows, raw `$$LaTeX$$`, and literal
    `**bold**`. Measured in the single real section on disk (`data/runs/smoke-4-1.json`): 12 pipe-table
    lines, 4 Markdown headings, 1 display-math block, 19 inline `$…$` spans, 7 `**bold**` spans.
  - All four LLM providers declare `max_chars: int = 4000` on `draft_section()`
    (`src/pdd_agent/llm/provider.py:63`, `:88`, `:135`; `llm/openai_provider.py:156`;
    `llm/anthropic_provider.py:161`; `llm/ollama_provider.py:145`; `llm/claude_code_provider.py:186`)
    and truncate with `text[:max_chars]`. `SectionOrchestrator` calls `draft_section()` at
    `src/pdd_agent/agent/section_orchestrator.py:744` **without passing `max_chars`**, so the cap is
    always 4,000 characters. `GenerationControls.max_tokens_per_section`
    (`schemas/project_input.py:419`) is read by no code at all.
  - `_check_missing_markers()` (`src/pdd_agent/export/docx_export.py:130`) hard-blocks export when a
    Section 3 or 4 body contains `[MISSING]`. The v2 drafting prompt instructs the model to emit
    `[MISSING]` for unsupported facts, so honest real output always requires `--force`, which stamps
    the document "DRAFT — NOT FOR FILING (EXPORT GATE OVERRIDE)".
  - `POST /api/runs/{run_id}/approve-all` (`src/pdd_agent/service/main.py:659`) only transitions
    sections for which `state.can_transition_to(APPROVED)` is true. `_TRANSITIONS`
    (`src/pdd_agent/review/states.py:33`) allows exactly one edge into `approved`, from
    `ready-for-human-edit`. `init_review_state()` starts every section in `drafted`. The endpoint
    therefore approves **zero** sections on a fresh run and returns HTTP 200 saying so.
  - `configs/corpus_families.yaml` contains `documents: {}`, so all 3,026 indexed rows carry
    `document_family = 'wte'` and a non-WTE project silently falls back to WTE grounding
    (`src/pdd_agent/retrieval/search.py:200`).
  - `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` reports
    `Project emissions: 0.00 tCO2e/year` and a 7-year total of 5,397,730 tCO2e against the registered
    3,808,082 tCO2e (+41.7%).
  - `data/runs/` holds ~1,690 files; `/dashboard` and `/api/runs` `glob()` and `stat()` all of them
    on every request with no pagination or retention.
  - Test suite: 841 passed, 7 deselected, 3 xfailed, 0 failed.
- **Desired state:**
  - A real-model DOCX renders Markdown headings as Word headings, Markdown pipe tables as real Word
    tables using the existing `add_styled_table()` styling, emphasis as bold/italic runs, lists as
    Word lists, and math as legible text — with zero literal `|`, `#`, `**`, or `$$` artifacts.
  - Each of the 36 subsections carries its own character budget (2,000 to 20,000) sourced from the
    canonical schema; truncation, when it happens, is recorded as a section issue and a review flag
    rather than being silent.
  - The export gate blocks on contradiction and fabrication, and converts `[MISSING]` markers into a
    "Required Inputs" appendix that exports without `--force`.
  - `approve-all` walks the legal transition path, and never reports a silent partial as success.
  - The ACM0022 engine computes non-zero project emissions for an incinerator, consumes
    `capacity_ramp`, and is measured against a seven-row year-by-year oracle from the registered PDD.
- **Key repo surfaces:** `src/pdd_agent/export/docx_export.py`, `src/pdd_agent/export/table_helpers.py`,
  `src/pdd_agent/llm/provider.py` and the four provider modules, `src/pdd_agent/agent/section_orchestrator.py`,
  `schemas/pdd_section_schema.yaml`, `schemas/project_input.py`, `src/pdd_agent/review/states.py`,
  `src/pdd_agent/service/main.py`, `src/pdd_agent/calc/acm0022.py`, `src/pdd_agent/calc/models.py`,
  `src/pdd_agent/calc/constants.py`, `src/pdd_agent/calc/dispatch.py`,
  `configs/projects/vietnam_socson_from_sheet.yaml`, `tests/test_registered_pdd_oracle.py`.
- **Out of scope:**
  - Fixing `ingest/normalize.py` heading detection for the four collapsed corpus documents, adding a
    normative (methodology-text) retrieval channel, and machine-resolving `[CORPUS: …]` citations.
    These are real and important; they are a separate push and this plan does not touch them.
  - Spending money on a full 36-section real-model run. No task in this plan calls a paid provider.
  - Regenerating the committed client-demo packages under `reports/demo-packages/`.
  - Unstubbing `src/pdd_agent/ingest/registry_download.py`.
  - Widening `TOLERANCE` in `tests/test_registered_pdd_oracle.py` — explicitly forbidden (DEC-004).

## Environment & Conventions

- **Stack:** Python 3.11+ (CI matrix runs 3.11 and 3.12; local development has been on 3.13).
  Pydantic v2, structlog, python-docx, FastAPI, SQLite FTS5. Dependency management supports both
  `pip` and `uv` (a committed `uv.lock` is checked by CI).
- **Setup:**
  ```bash
  pip install -e ".[dev,service,export,llm,ingest]"
  ```
  or, with uv:
  ```bash
  uv sync --locked --all-extras
  ```
- **Build / Run:** No build step. The CLI entry point is `pdd-agent` (`src/pdd_agent/cli.py:main`).
  Diagnose the environment with:
  ```bash
  pdd-agent doctor
  ```
- **Test:** full suite:
  ```bash
  python -m pytest -m "not corpus" -q
  ```
  single file:
  ```bash
  python -m pytest tests/test_docx_export.py -v
  ```
  single test:
  ```bash
  python -m pytest tests/test_docx_export.py::TestMarkdownRendering::test_pipe_table_becomes_word_table -v
  ```
  Lint and format gates (both must pass; CI runs them):
  ```bash
  ruff check .
  ruff format --check .
  ```
  Lockfile gate:
  ```bash
  uv lock --check
  ```
- **Conventions & traps:**
  - Line length 100 (`[tool.ruff]` in `pyproject.toml`). `E402` is globally ignored.
  - structlog event-style logging: `logger.warning("event_name", key=value)` — an event name as the
    first positional argument, everything else as keyword arguments. Never f-string log messages.
  - Pydantic v2 `BaseModel` for `ProjectInput` and its sub-models in `schemas/project_input.py`
    (a top-level `schemas/` package that sits **outside** `src/`). Plain dataclasses everywhere else.
  - python-docx is imported lazily through the `_docx_attr(module_name, attr_name)` helper in
    `src/pdd_agent/export/docx_export.py` and `src/pdd_agent/export/table_helpers.py`. Follow that
    pattern for any new python-docx symbol; do not add module-level `from docx import …`.
  - Tests must never require API keys, network access, or a running Ollama instance. Mock all HTTP.
  - Tests that need `data/corpus/normalized/` must be marked `@pytest.mark.corpus`; the default suite
    command deselects them. No task in this plan should add a `corpus`-marked test.
  - Units: all emissions in **tonnes CO2-equivalent per year** (`tCO2e/year`) unless a name says
    otherwise; waste masses in **tonnes per year (wet weight)**; electricity in **MWh/year**; grid
    emission factors in **tCO2/MWh**; money in **USD**. Global warming potentials follow **IPCC AR5**
    (`GWP_CH4 = 28.0` already in `src/pdd_agent/calc/constants.py:12`).
  - `data/index/` and `data/runs/` are gitignored. `reports/demo-packages/` **is** committed.
  - If your shell environment exports `PYTHONPATH`, clear it before running the suite — a polluted
    `PYTHONPATH` shadows the local package (recorded in `activeContext.md` under "Environment notes").
    With uv, run commands as `uv run --no-sync <command>`.
- **Repo map:**
  ```
  src/pdd_agent/
    cli.py                       # argparse CLI; every subcommand dispatches to a _run_* function
    agent/section_orchestrator.py# per-section retrieval -> prompt -> provider -> review gate
    llm/                         # provider.py (ABC + Noop/Demo), openai/anthropic/ollama/claude_code
    export/docx_export.py        # export gate, DOCX assembly, 11 Verra table renderers
    export/table_helpers.py      # add_styled_table() and OOXML cell primitives
    review/states.py             # 5-state review workflow + ReviewStateStore
    review/checks.py, judge.py   # rule-based compliance checks and the LLM-judge
    retrieval/index.py, search.py# SQLite FTS5 index and query API
    calc/acm0022.py, dispatch.py # ACM0022 engine and the ProjectInput -> engine-input mapper
    calc/constants.py, models.py # IPCC/CDM defaults; Pydantic engine input/output models
    service/main.py              # FastAPI review UI and JSON API
  schemas/pdd_section_schema.yaml# canonical 5-section / 36-subsection PDD taxonomy
  schemas/project_input.py       # Pydantic ProjectInput
  configs/projects/*.yaml        # project inputs; vietnam_socson_from_sheet.yaml is the reference
  tests/                         # pytest; ~841 tests, no network, no keys
  ```

## Research Inputs

- From `research/2026-08-21-pdd-real-output-gap-brainstorm.md`:
  - The DOCX exporter cannot render real model output. Exporting the only real run on disk
    (`data/runs/smoke-4-1.json`) produces paragraphs reading `'| Term | Description |'`,
    `'|---|---|'`, `'# 4.4.1 Baseline Emissions'`, and
    `'$$BE_y = \sum_t \left( ... \right)'`. Invisible for four months because `DemoProvider` and
    `NoopProvider` emit flat prose only.
  - The 4,000-character cap is a character cut applied to a token budget, is uniform across sections
    with a 100× spread in natural length, and imposes a 144,000-character ceiling on a document whose
    registered reference (`VCS_Soc_Son_Project-Description`) is 183,731 characters. The `demo`
    provider currently emits 9,791 characters across all 36 sections (mean 271).
  - `POST /approve-all` approves zero sections on a fresh run; reproduced. The July 2026 fix
    addressed a read-modify-write race hypothesis, not the observed behaviour, which is a missing
    multi-hop transition plus a silent skip reported as HTTP 200 success.
  - `configs/corpus_families.yaml` has an empty `documents: {}` map, so the family filter built in the
    previous push is inert and non-WTE projects silently borrow WTE grounding.
  - `capacity_ramp` was added to `ProjectTechnology` with validators and tests and has zero consumers
    in `src/`, despite being named in both oracle xfail reasons as a fix for the measured gap.
  - `acm0022.py`'s docstring declares `PE_y = PE_COMP + PE_AD + PE_GAS + PE_RDF_SB + PE_INC` (Eq. 17)
    while `compute_project()` implements `PE_EC + PE_FC + PE_CH4 + PE_FLARE`. There is no incineration
    term; both oracle projects are mass-burn incinerators.
  - Recommended sequencing: renderability first (it is downstream of everything and provable offline
    against a run already paid for), product surface in parallel, calc correctness as the closing
    phase because it carries genuine risk of not fully closing.
- From `research/2026-08-13-pdd-hollow-grounding-and-calc-inputs-brainstorm.md`:
  - House rule, carried forward and reaffirmed here: when a calculation gap does not fully close,
    **record the residual and never widen the tolerance**. The three oracle xfails are described in
    that brief as "the most valuable artifact the last push produced".
  - New `ProjectInput` fields must be optional with fallbacks preserved; six project configs and
    ~1,690 run JSON files exist and a required field would break all of them.

## Assumptions and Constraints

- **ASM-001:** Markdown emitted by drafting models is CommonMark-ish but not guaranteed valid. —
  **BINDING DEFAULT:** implement a small, dependency-free block scanner (no new third-party Markdown
  library). Anything the scanner does not recognise falls through to a plain paragraph, exactly as
  today. Never raise on malformed input.
- **ASM-002:** LaTeX rendering as OOXML Math (OMML) is expensive and risky. — **BINDING DEFAULT:**
  do **not** generate OMML. Render `$$…$$` display math as a single centred italic paragraph and
  inline `$…$` as an italic run, in both cases with the `$` delimiters and the backslashes of
  common LaTeX commands stripped by the rules in Specification S-1 step 7. Keep the raw source of
  every display-math block in a "Formulas (verbatim source)" appendix so nothing is lost.
- **ASM-003:** Per-section character budgets have no published source. — **BINDING DEFAULT:** derive
  them from the `content_class` of each subsection using the tier table in Specification S-2. They
  are *ceilings*, not targets.
- **ASM-004:** `max_tokens_per_section` in `GenerationControls` is ambiguous (tokens vs characters)
  and unused. — **BINDING DEFAULT:** keep the field, keep its name, and interpret it as a **global
  ceiling in characters** that caps every per-section budget. A section's effective budget is
  `min(schema_budget_chars, generation_controls.max_tokens_per_section)`. Raise the field's
  validation upper bound from 16,000 to 40,000 so the largest schema budget (20,000) is reachable
  with headroom. Document the character interpretation in the field description.
- **ASM-005:** IPCC per-waste-type dry-matter, carbon-fraction, and fossil-carbon-fraction defaults
  are not currently in the repo. — **BINDING DEFAULT:** use the table in Specification S-5b, which
  follows IPCC 2006 Guidelines Volume 5 Chapter 2 Table 2.4 (dry matter, total carbon) and Chapter 5
  Table 5.2 (fossil carbon fraction). Record the citation in the constant's docstring.
- **ASM-006:** The N2O emission factor for MSW incineration is not currently in the repo. —
  **BINDING DEFAULT:** `0.05 kg N2O per tonne of wet waste incinerated` (IPCC 2006 Volume 5 Chapter 5
  Table 5.6, continuous stoker-type MSW incineration), with `GWP_N2O = 265.0` (IPCC AR5, consistent
  with the existing `GWP_CH4 = 28.0`).
- **ASM-007:** The oxidation factor for the incineration carbon balance is not currently in the repo.
  — **BINDING DEFAULT:** `OF = 1.0` (complete oxidation), the IPCC default for modern MSW
  incineration. Expose it as an overridable engine input.
- **ASM-008:** It is unknown whether adding `PE_INC` and `capacity_ramp` will bring either oracle
  inside the 20% tolerance. — **BINDING DEFAULT:** do not attempt to force it. Re-measure, record
  the residual verbatim in the `xfail` reason with the date `2026-08-21` and the new numbers, and
  flip an `xfail` to a passing test **only** if it genuinely passes. Never edit `TOLERANCE`.
- **ASM-009:** Run-store retention could delete artifacts a user still wants. — **BINDING DEFAULT:**
  never delete anything. Add pagination only (default page size 50, `?limit=` and `?offset=` query
  parameters, newest first). Retention is out of scope.
- **CON-001:** No task may call a paid LLM provider or require an API key, network access, or a
  running Ollama instance. Every test must pass offline.
- **CON-002:** New `ProjectInput` / `ACM0022CalcInput` fields must be optional with defaults that
  reproduce today's behaviour, so the six existing configs in `configs/` and the ~1,690 run JSON
  files in `data/runs/` continue to load.
- **CON-003:** `reports/demo-packages/` is a committed client artifact area. Do not regenerate the
  DOCX files there, even though PHASE-01 would improve them.
- **DEC-001:** Markdown rendering is fixed **in the exporter**, not by prompting models to avoid
  Markdown. Verra PDDs contain tables and equations; suppressing them to protect the renderer would
  degrade the deliverable.
- **DEC-002:** Per-section budgets live in `schemas/pdd_section_schema.yaml`, next to the existing
  per-subsection `guidance`, `content_class`, and `review_sensitivity` keys — not in a new config file.
- **DEC-003:** Cross-family retrieval fallback is **kept** (it is existing, deliberately-chosen
  behaviour) but is escalated from a log-only warning to a section-level issue that reaches the DOCX.
  Removing the fallback entirely is deferred.
- **DEC-004:** `TOLERANCE` in `tests/test_registered_pdd_oracle.py` stays at `0.20`. Under no
  circumstances raise it.

## Specification

### S-1. Markdown block-scanning rules (the PHASE-01 change)

Input: one section's `text` string. Output: an ordered list of render operations applied to the
python-docx `Document`. Process the text as a list of lines, top to bottom, with a cursor.

1. **Fenced code block.** A line whose stripped form starts with ``` opens a fence. Consume lines
   until the next line whose stripped form starts with ``` (or end of text). Emit every consumed
   inner line as one paragraph with a monospace run (font name `Consolas`, size 9 pt). Do not
   interpret any Markdown inside a fence.
2. **ATX heading.** A line matching `^(#{1,6})\s+(.*)$` emits a Word heading. Map the count of `#`
   to a python-docx heading level with `level = min(count + 2, 4)` — the exporter already emits
   level 1 for the section and level 2 for the subsection, so a model's `#` becomes level 3 and
   never competes with the document's own outline.
3. **Display math.** A line whose stripped form is exactly `$$`, or which starts and ends with `$$`,
   opens a display-math block. If the delimiters are on their own lines, consume until the closing
   `$$`. Emit the inner text as one centred paragraph whose single run is italic, after applying the
   step-7 cleanup. Append the raw inner text (unmodified) to a module-level list that the caller
   writes into the "Formulas (verbatim source)" appendix.
4. **Pipe table.** A run of two or more consecutive lines each of whose stripped form starts with
   `|` is a candidate table. The run is a table when a line at index 1 of the run consists only of
   the characters `|`, `-`, `:`, and whitespace (the Markdown alignment row). Split each remaining
   line on `|`, discard the leading and trailing empty fields produced by the outer pipes, and strip
   each cell. Normalise ragged rows to the width of the first row by padding with `""` or truncating
   the overflow. Apply step 6 to every cell's text (emphasis markers removed, since cell runs are
   styled by `set_cell_text`). Render with
   `add_styled_table(doc, rows, widths=None, header=True, font_size=8.7)` from
   `src/pdd_agent/export/table_helpers.py`. If the candidate run has no alignment row, fall through
   and render each line as a plain paragraph.
5. **List item.** A line matching `^\s*[-*+]\s+(.*)$` emits a paragraph with style `List Bullet`;
   a line matching `^\s*\d+[.)]\s+(.*)$` emits a paragraph with style `List Number`. Apply
   `_safe_paragraph_style` so a template missing the style degrades to a plain paragraph rather than
   raising.
6. **Paragraph with inline emphasis.** Any other non-blank line emits one paragraph, built run by
   run: `**text**` and `__text__` produce a bold run; `*text*` and `_text_` produce an italic run;
   `` `text` `` produces a monospace run; `$…$` produces an italic run after step-7 cleanup;
   everything else produces a plain run. Emphasis markers themselves are never written into the
   document. Nested emphasis is not supported — the outermost match wins.
7. **Math text cleanup**, applied to display-math bodies and inline `$…$` spans:
   - Remove the surrounding `$` or `$$` delimiters.
   - Replace `\left` and `\right` with the empty string.
   - Replace `\times` with `×`, `\sum` with `Σ`, `\ge` with `≥`, `\le` with `≤`, `\neq` with `≠`,
     `\alpha` with `α`, `\beta` with `β`, `\Delta` with `Δ`.
   - Replace `_{x}` with `_x` and `^{x}` with `^x` for any single-token `x`.
   - Remove any remaining single backslash that is immediately followed by an ASCII letter, keeping
     the letters (so `\phi` becomes `phi`).
   - Collapse runs of two or more spaces into one, and strip.
8. **Blank line.** Skipped; it does not emit an empty paragraph.
9. Rendering never raises. Any unexpected structure falls through to rule 6.

### S-2. Per-section character budgets (the PHASE-02 change)

Budget tiers, keyed on the subsection's existing `content_class` value:

| `content_class` | budget (characters) |
|---|---|
| `OPTIONAL` | 2,000 |
| `FACTUAL` | 3,000 |
| `BOILERPLATE` | 4,000 |
| `NARRATIVE` | 8,000 |
| `EVIDENCE_BASED` | 8,000 |
| `METHODOLOGY_DEPENDENT` | 12,000 |
| `QUANTITATIVE` | 20,000 |

Applied to the 36 subsections in `schemas/pdd_section_schema.yaml`, this yields:

| Subsections | `content_class` | budget | count |
|---|---|---|---|
| 1.18 | OPTIONAL | 2,000 | 1 |
| 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.12, 3.1 | FACTUAL | 3,000 | 9 |
| 1.1, 1.17, 2.1, 2.4, 2.5 | BOILERPLATE | 4,000 | 5 |
| 1.11, 5.3 | NARRATIVE | 8,000 | 2 |
| 1.13, 1.14, 1.15, 1.16, 2.2, 2.3, 5.1 | EVIDENCE_BASED | 8,000 | 7 |
| 1.3, 3.2, 3.3, 3.4, 3.5, 3.6, 4.3, 5.2 | METHODOLOGY_DEPENDENT | 12,000 | 8 |
| 1.10, 4.1, 4.2, 4.4 | QUANTITATIVE | 20,000 | 4 |

Total across all 36 subsections: **297,000 characters** (the registered Soc Son PDD is 183,731
characters, so this is a ceiling with headroom, not a target).

Resolution order for the effective budget of one subsection:

1. `max_chars` declared on the subsection in `schemas/pdd_section_schema.yaml`, if present.
2. Otherwise, the tier value for the subsection's `content_class` from the table above.
3. Otherwise (unknown `content_class`), `4000`.
4. The result is then capped: `effective = min(result, project_input.generation_controls.max_tokens_per_section)`.

Truncation reporting: if a provider's returned text is longer than the effective budget, the stored
`DraftSection.text` is the truncated text and `DraftSection.issues` gains exactly one entry:

```
TRUNCATED: section {section_key} output was cut from {original_len} to {budget} characters; the final sentence is incomplete.
```

and `DraftSection.confidence` is downgraded one step along `HIGH -> MEDIUM -> LOW` (`LOW` and
`UNSUPPORTED` are left unchanged).

### S-3. Export-gate tiering (the PHASE-03 change)

Replace the single `[MISSING]`-is-a-hard-block rule with three tiers.

1. **HARD BLOCK** (export refused unless `--force`), unchanged from today:
   - `CRITICAL`-severity flags from `check_quantitative_consistency`.
   - Evidence citations to `[E###]` IDs absent from the evidence registry.
2. **REQUIRED INPUT** (export proceeds, no `--force`, no override watermark): a `[MISSING]` marker
   anywhere in any section. Each occurrence produces one entry
   `{"section_key": str, "context": str}` where `context` is the 200 characters of section text
   centred on the marker, whitespace-collapsed. These entries are rendered as a
   "Appendix — Required Inputs" table at the end of the document.
3. **ADVISORY** (export proceeds, listed in the reviewer-issues appendix), unchanged from today:
   `HIGH`-severity consistency flags.

`ExportGateResult` gains one field, `required_inputs: list[dict[str, str]]`, defaulting to an empty
list. `blocked` continues to mean `bool(hard_blocks)` and therefore becomes `False` for a run whose
only finding is `[MISSING]` markers. The DRAFT watermark is still applied to every export; the
`(EXPORT GATE OVERRIDE)` suffix is applied only when `force=True` **and** `hard_blocks` is non-empty.

### S-4. Approve-all transition walk (the PHASE-04 change)

For each section in the store, compute the shortest path from its current state to `approved` using
the existing `_TRANSITIONS` graph, then apply every hop in order. The graph is small and fixed, so
the paths are enumerable:

| From | Path applied |
|---|---|
| `approved` | (none — already approved) |
| `ready-for-human-edit` | → `approved` |
| `needs-domain-review` | → `ready-for-human-edit` → `approved` |
| `drafted` | → `ready-for-human-edit` → `approved` |
| `needs-input` | **not walked** — a section awaiting operator input must not be bulk-approved |

Every hop is applied through `ReviewStateStore.set_state(...)` with `updated_by="approve_all"` so
the transition validation still runs and the note trail is preserved. The endpoint's response body
becomes:

```json
{
  "run_id": "...",
  "sections_approved": 34,
  "sections_skipped": [{"section_key": "4.4", "state": "needs-input",
                        "reason": "sections awaiting operator input are not bulk-approved"}],
  "all_approved": false
}
```

When `sections_skipped` is non-empty the endpoint returns HTTP **409 Conflict** with that body,
rather than HTTP 200 — a partial bulk approval is never reported as success.

### S-5. ACM0022 incineration project emissions and the registered oracle (the PHASE-05 change)

#### S-5a. The measured discrepancies

The registered Soc Son PDD (`data/corpus/normalized/VCS_Soc_Son_Project-Description.norm.json`)
publishes a full year-by-year schedule. Table 9 gives baseline methane from the solid waste disposal
site; Section 1.10 gives the estimated emission reductions:

| Crediting year | Registered `BE_CH4,y` (tCO2e) | Registered `ER_y` (tCO2e) | `BE_CH4,y − ER_y` |
|---|---|---|---|
| 1 (24/07/2022–23/07/2023) | 277,866 | 195,589 | 82,277 |
| 2 (24/07/2023–23/07/2024) | 466,829 | 384,553 | 82,276 |
| 3 (24/07/2024–23/07/2025) | 596,016 | 513,739 | 82,277 |
| 4 (24/07/2025–23/07/2026) | 684,963 | 602,687 | 82,276 |
| 5 (24/07/2026–23/07/2027) | 746,778 | 664,502 | 82,276 |
| 6 (24/07/2027–23/07/2028) | 790,258 | 707,981 | 82,277 |
| 7 (24/07/2028–23/07/2029) | 821,308 | 739,032 | 82,276 |
| **Sum** | **4,384,018** | **3,808,083** | — |

The registered total ERs line reads `3,808,082` (one tCO2e below the column sum, a rounding
artifact in the source document).

Two facts follow arithmetically and are the targets of this phase:

- **D-1 (baseline methane too low).** The engine's 7-year `BE_CH4` sum is
  `5,397,730 − 7 × 357,006 = 2,898,688 tCO2e` against the registered `4,384,018 tCO2e` — the engine
  is **33.9% low** on avoided landfill methane.
- **D-2 (everything else has the wrong sign).** In the registered document,
  `ER_y = BE_CH4,y − 82,276.5` for every one of the seven years, so the registered net effect of
  (baseline electricity − project emissions − leakage) is a **constant charge of −82,276.5
  tCO2e/year**. The engine computes that same quantity as `+357,006 tCO2e/year` (all of it
  `BE_EC`, with `PE_y = 0` and `LE_y = 0`). The discrepancy is **439,282.5 tCO2e/year**, or
  **0.301 tCO2e per tonne** of the 1,460,000 t/year throughput.

D-2 is the dominant term and is where the missing `PE_INC` lives. This phase implements `PE_INC` and
`capacity_ramp`, then **measures** both discrepancies again and records whatever remains. It does not
promise to close them.

#### S-5b. `PE_INC` — incineration project emissions

Two terms, both in tCO2e per year.

**Fossil carbon dioxide from combustion** (IPCC 2006 Volume 5 Chapter 5, Equation 5.1, per-stream
form):

```
PE_INC_CO2,y = Σ_j ( MSW_j,y × dm_j × CF_j × FCF_j × OF ) × 44/12
```

| Symbol | Meaning | Unit |
|---|---|---|
| `MSW_j,y` | wet mass of waste stream *j* incinerated in crediting year *y* | tonnes/year |
| `dm_j` | dry matter content of stream *j*, as a fraction of wet weight | dimensionless, 0–1 |
| `CF_j` | total carbon content of stream *j*, as a fraction of **dry** matter | dimensionless, 0–1 |
| `FCF_j` | fraction of that carbon which is **fossil** in origin | dimensionless, 0–1 |
| `OF` | oxidation factor — fraction of carbon actually oxidised | dimensionless, 0–1, default 1.0 |
| `44/12` | molecular mass ratio of CO2 to C, i.e. 3.666667 | dimensionless |

**Nitrous oxide from combustion** (IPCC 2006 Volume 5 Chapter 5, Equation 5.4):

```
PE_INC_N2O,y = ( Σ_j MSW_j,y ) × EF_N2O × 0.001 × GWP_N2O
```

| Symbol | Meaning | Unit |
|---|---|---|
| `EF_N2O` | nitrous oxide emission factor per tonne of wet waste incinerated | kg N2O/tonne, default 0.05 |
| `0.001` | converts kilograms of N2O to tonnes | dimensionless |
| `GWP_N2O` | global warming potential of N2O, IPCC AR5 | tCO2e/tN2O, 265.0 |

**Total:** `PE_INC,y = PE_INC_CO2,y + PE_INC_N2O,y`, and the project total becomes
`PE_y = PE_EC + PE_FC + PE_CH4 + PE_FLARE + PE_INC`.

Per-waste-type defaults (ASM-005), to be added to `src/pdd_agent/calc/constants.py`:

| waste type key | `dm` | `CF` | `FCF` |
|---|---|---|---|
| `food_waste` | 0.40 | 0.38 | 0.00 |
| `garden_waste` | 0.40 | 0.49 | 0.00 |
| `paper_cardboard` | 0.90 | 0.46 | 0.01 |
| `wood` | 0.85 | 0.50 | 0.00 |
| `textiles` | 0.80 | 0.50 | 0.20 |
| `nappies` | 0.40 | 0.70 | 0.10 |
| `rubber_leather` | 0.84 | 0.67 | 0.20 |
| `plastics` | 1.00 | 0.75 | 1.00 |
| `inert` | 0.90 | 0.03 | 1.00 |
| `municipal_solid_waste` | 0.60 | 0.40 | 0.30 |

`PE_INC` is computed **only** when `ACM0022CalcInput.incineration_streams` is non-empty. When it is
empty (every existing config), `PE_INC = 0.0` and behaviour is byte-identical to today.

#### S-5c. `capacity_ramp`

In `compute_for()` (`src/pdd_agent/calc/dispatch.py`, the `for y in range(1, cpy + 1)` loop), before
constructing each year's `ACM0022CalcInput`, scale every waste mass by that year's ramp factor:

```
factor(y) = 1.0                       if capacity_ramp is None or empty
          = capacity_ramp[y - 1]      if 1 <= y <= len(capacity_ramp)
          = capacity_ramp[-1]         if y > len(capacity_ramp)
```

Apply `factor(y)` to every `annual_tonnes` in `year_inputs["waste_streams"]`, to every
`annual_tonnes` in `year_inputs["incineration_streams"]`, and to
`year_inputs["electricity_exported_mwh_per_year"]` when it is not `None`. Do not apply it to the
year-1 scalars on `PddCalcResult` (`baseline_emissions_tco2e` and friends), which continue to
describe an unramped nameplate year — only the `annual_schedule` and the
`crediting_period_total_tco2e` derived from it change.

#### S-5d. Soc Son composition provenance

The repo config `configs/projects/vietnam_socson_from_sheet.yaml` currently declares six
`waste_composition` entries summing to 0.575, all citing "VCS Soc Son registered PDD, Table 8 —
Components of solid waste". Table 8 in that document actually reads:

| Type of waste (j) | Fraction (p_j,x) |
|---|---|
| Wood and wood products | 0.0% |
| Pulp, paper and cardboard | 2.7% |
| Food, food waste, beverages and tobacco | 51.9% |
| Textiles | 1.6% |
| Garden, yard and park waste | 0.0% |
| Glass, plastic, metal, other inert waste | 43.8% |

Table 8 has **no rubber or leather row**. The config's `rubber_leather: 0.013` entry is not in the
cited source, and including it makes the declared composition sum to 1.013 against Table 8's exact
1.000. It must be removed. Separately, the same PDD's applicability discussion states that "the
waste received for incineration contains non-biodegradable materials (i.e. 0.5% of glass, 0.9% of
metal, 3% of plastic)", which splits the 43.8% inert bucket into 3.0% plastics and 40.8%
glass/metal/other inert — the numbers `PE_INC` needs.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Render Markdown model output faithfully in DOCX | None | `export/markdown_docx.py`, wired into `_add_section_prose`, formulas appendix, `tests/test_markdown_docx.py` |
| PHASE-02 | Per-section character budgets and honest truncation reporting | None (independent of PHASE-01) | `max_chars` in the section schema, budget resolution in the orchestrator, truncation issues, `tests/test_section_budgets.py` |
| PHASE-03 | Split the export gate's two meanings | PHASE-01 (reuses the appendix rendering pattern) | `required_inputs` on `ExportGateResult`, "Appendix — Required Inputs", unforced export of honest output |
| PHASE-04 | Repair the review UI and product surface | None | Working `approve-all`, populated family map, paginated run listing, `claude-code` reachable, docs resynced |
| PHASE-05 | Charge the emissions an incinerator causes, and measure against the registered year-by-year oracle | None (independent; sequenced last because it carries the most risk) | `PE_INC` in the ACM0022 engine, `capacity_ramp` consumed, seven-row oracle test, re-measured residuals |

## Detailed Phases

### PHASE-01 - Render Markdown Model Output Faithfully

**Goal**
Make a DOCX exported from real model output contain zero literal Markdown or LaTeX artifacts:
headings become Word headings, pipe tables become Word tables, emphasis becomes bold/italic runs,
lists become Word lists, and math becomes legible italic text with its verbatim source preserved in
an appendix.

**Tasks**
- [x] TASK-01-01: Create `src/pdd_agent/export/markdown_docx.py` implementing the S-1 block scanner.
- [x] TASK-01-02: Implement inline-emphasis run splitting (S-1 step 6) as `_split_inline_runs`.
- [x] TASK-01-03: Implement math text cleanup (S-1 step 7) as `clean_math_text`.
- [x] TASK-01-04: Rewrite `_add_section_prose` in `src/pdd_agent/export/docx_export.py` to call
      `render_markdown_body()` instead of `_split_paragraphs`, preserving the existing LOW/UNSUPPORTED
      yellow highlighting and the `[No content drafted yet]` placeholder behaviour.
- [x] TASK-01-05: Collect display-math sources across the whole document and render an
      "Appendix — Formulas (verbatim source)" section when at least one was captured.
- [x] TASK-01-06: Keep `_split_paragraphs` in place, unused by the section path, for the other
      call sites that render short single-purpose strings; add a docstring note saying it is
      deliberately Markdown-naive.
- [x] TASK-01-07: Add `tests/test_markdown_docx.py` with the Test Specs below.
- [x] TASK-01-08: Add one end-to-end regression test in `tests/test_docx_export.py` that builds a run
      dict containing the real Markdown shapes and asserts the exported document has no literal
      artifacts.
- [x] TASK-01-09: Update the "Known Gaps" list in `README.md` to remove any claim that the exporter
      handles model output, and state that Markdown and pipe tables now render natively while LaTeX
      renders as cleaned italic text with a verbatim-source appendix.

**File Changes**
- `src/pdd_agent/export/markdown_docx.py` (create): the S-1 scanner, the inline splitter, and the
  math cleaner. Uses the same lazy `_docx_attr(module_name, attr_name)` import helper as the rest of
  the export package (import it from `pdd_agent.export.table_helpers`). Imports
  `add_styled_table` from `pdd_agent.export.table_helpers` for pipe tables. No new third-party
  dependency.
- `src/pdd_agent/export/docx_export.py` (modify): change the body of `_add_section_prose` (currently
  at line 1000) to call `render_markdown_body(doc, text, on_display_math=…)`; add a module-level
  `_add_formulas_appendix(doc, formulas)` helper and call it from `export_run_to_docx` immediately
  after `_add_calc_audit_appendix(doc, calc_result_dict)` (currently line 287). Leave the export
  gate, the cover tables, the 11 `_TABLE_RENDERERS`, the assumption appendix, and the reviewer-issues
  appendix untouched.
- `tests/test_markdown_docx.py` (create): unit tests for the scanner.
- `tests/test_docx_export.py` (modify): add one class `TestMarkdownRendering` with the end-to-end
  regression test. Do not change existing tests.
- `README.md` (modify): the "Known Gaps" bullet list only.

**Function Signatures**
- `render_markdown_body(doc: Any, text: str, on_display_math: Callable[[str], None] | None = None) -> None`
  — renders `text` into `doc` following S-1; calls `on_display_math` once with the raw inner source
  of each display-math block; returns nothing and never raises.
- `_split_inline_runs(line: str) -> list[tuple[str, str]]` — returns an ordered list of
  `(style, text)` pairs where `style` is one of `"plain"`, `"bold"`, `"italic"`, `"code"`; emphasis
  delimiters are absent from every returned `text`.
- `clean_math_text(raw: str) -> str` — returns the LaTeX source with delimiters, `\left`/`\right`,
  and stray command backslashes removed and common symbols substituted per S-1 step 7.
- `parse_pipe_table(lines: list[str]) -> list[list[str]] | None` — returns the normalised
  rectangular cell grid for a Markdown pipe table, or `None` when `lines` is not a valid table
  (no alignment row at index 1, or fewer than two lines).
- `_add_formulas_appendix(doc: Any, formulas: list[str]) -> None` — appends an
  "Appendix — Formulas (verbatim source)" heading and one monospace paragraph per captured formula;
  a no-op when `formulas` is empty.

**Test Specs**
- `parse_pipe_table(["| A | B |", "|---|---|", "| 1 | 2 |"])` → `[["A", "B"], ["1", "2"]]`.
- `parse_pipe_table(["| A | B |", "| 1 | 2 |"])` → `None` (no alignment row).
- `parse_pipe_table(["| A | B | C |", "|---|---:|---|", "| 1 | 2 |"])` → `[["A","B","C"], ["1","2",""]]`
  (ragged row padded).
- `parse_pipe_table(["| A |", "|---|", "| 1 | 2 | 3 |"])` → `[["A"], ["1"]]` (overflow truncated).
- `clean_math_text("$$BE_y = \\sum_t \\left( X \\right) \\times 2$$")` → `"BE_y = Σ_t ( X ) × 2"`.
- `clean_math_text("$BE_{CH4,t,y}$")` → `"BE_CH4,t,y"`.
- `_split_inline_runs("Total is **487,710.99** tCO2e")` →
  `[("plain", "Total is "), ("bold", "487,710.99"), ("plain", " tCO2e")]`.
- `_split_inline_runs("plain text")` → `[("plain", "plain text")]`.
- `_split_inline_runs("`code` and *em*")` →
  `[("code", "code"), ("plain", " and "), ("italic", "em")]`.
- `_split_inline_runs("unbalanced ** marker")` → `[("plain", "unbalanced ** marker")]`
  (an unpaired delimiter is left alone rather than swallowing the rest of the line).
- `render_markdown_body(doc, "# Baseline Emissions")` → `doc` gains exactly one paragraph whose
  style name starts with `"Heading 3"` and whose text is `"Baseline Emissions"` (no `#`).
- `render_markdown_body(doc, "### Deep")` → heading level 4 (capped by `min(count + 2, 4)`).
- `render_markdown_body(doc, "| A | B |\n|---|---|\n| 1 | 2 |")` → `len(doc.tables) == 1`, that
  table has 2 rows and 2 columns, `doc.tables[0].cell(0,0).text == "A"`, and no paragraph in `doc`
  contains the character `|`.
- `render_markdown_body(doc, "- one\n- two")` → two paragraphs with style `List Bullet` and texts
  `"one"` and `"two"` (no `-`).
- `render_markdown_body(doc, "1. first\n2. second")` → two paragraphs with style `List Number`.
- `render_markdown_body(doc, "```\nraw | text\n```")` → one paragraph with text `"raw | text"`
  whose run font name is `"Consolas"`; the pipe is **not** interpreted as a table.
- `render_markdown_body(doc, "$$X = 1$$", on_display_math=collector)` → `collector` was called
  exactly once with `"X = 1"`, and `doc` gained one centred paragraph whose single run is italic.
- `render_markdown_body(doc, "")` → `doc` gains no paragraphs and no exception is raised.
- `render_markdown_body(doc, "| broken\n| still broken")` → two plain paragraphs; no table; no
  exception.
- End-to-end in `tests/test_docx_export.py`: export a run dict whose single section text is
  `"# H\n\n## H2\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n**bold** and $x$\n\n$$y = 2x$$"`, then assert
  that the concatenation of all paragraph texts contains no `"|---"`, no `"# "`, no `"**"`, and no
  `"$$"`, that `len(doc.tables) >= 1`, and that some paragraph contains `"y = 2x"`.

**Dependencies**
- None. Uses only `python-docx`, already a hard dependency in `pyproject.toml`.

**Exit Criteria**
- [ ] `python -m pytest tests/test_markdown_docx.py tests/test_docx_export.py tests/test_docx_export_tables.py -v` passes with 0 failures.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both exit 0.
- [ ] Exporting the real run on disk produces a document with no literal Markdown table rows:
      ```bash
      python -c "
      from pathlib import Path
      from pdd_agent.export.docx_export import export_run_to_docx
      from docx import Document
      p = export_run_to_docx(run_id='smoke-4-1', output_path=Path('smoke-check.docx'), force=True)
      d = Document(str(p))
      txt = chr(10).join(par.text for par in d.paragraphs)
      assert '|---' not in txt, 'literal markdown table survived'
      assert chr(36)*2 not in txt, 'literal display math survived'
      assert len(d.tables) >= 4, 'expected rendered tables, got ' + str(len(d.tables))
      print('OK', len(d.paragraphs), 'paragraphs,', len(d.tables), 'tables')
      "
      ```
      → prints `OK` with a table count of at least 4 and raises no assertion.
- [ ] `README.md` Known Gaps no longer implies the exporter is Markdown-blind.

**Phase Risks**
- **RISK-01-01:** The `smoke-4-1` run may not exist in a fresh clone (`data/runs/` is gitignored).
  Mitigation: the exit-criteria command above is a local convenience check; the binding automated
  proof is the end-to-end test in `tests/test_docx_export.py`, which builds its run dict inline and
  requires no on-disk artifact.
- **RISK-01-02:** The VCS template `templates/VCS-Project-Description-Template-v4.4-FINAL2.docx` may
  not define the `List Bullet` or `List Number` styles, which would make `paragraph.style = …` raise.
  Mitigation: route every style assignment through the existing `_safe_paragraph_style` helper in
  `docx_export.py`, which already swallows `KeyError` and leaves the paragraph unstyled.
- **RISK-01-03:** A pathological table (hundreds of columns) could produce an unreadable Word table.
  Mitigation: cap the rendered column count at 12. When the first row of a candidate table has more
  than 12 cells, do not build a table — emit a plain paragraph reading
  `[Table with {n} columns rendered as text]` and then render the table's lines as plain paragraphs.

### PHASE-02 - Per-Section Character Budgets and Honest Truncation

**Goal**
Replace the uniform 4,000-character cut with a per-subsection budget resolved from the canonical
schema, plumb it through every provider, and make truncation a reported event rather than a silent
amputation.

**Tasks**
- [x] TASK-02-01: Add a `max_chars` key to each of the 36 subsections in
      `schemas/pdd_section_schema.yaml` using the values in Specification S-2.
- [x] TASK-02-02: Add `_CONTENT_CLASS_BUDGETS` and `section_budget_chars()` to
      `src/pdd_agent/agent/section_orchestrator.py` implementing the S-2 resolution order.
- [x] TASK-02-03: Pass `max_chars=` from `SectionOrchestrator.draft_section` into both
      `self._provider.draft_section(...)` call sites (the initial draft near line 744 and the
      judge-redraft near line 934).
- [x] TASK-02-04: Raise the `le=` bound on `GenerationControls.max_tokens_per_section` from 16000 to
      40000 and rewrite its `description` to state that the value is a **global ceiling in
      characters** applied on top of the per-section schema budget.
- [x] TASK-02-05: Add truncation detection and reporting in `_enrich_draft` (or immediately after the
      provider call, whichever keeps the provider modules untouched) per Specification S-2: append the
      `TRUNCATED: …` issue and downgrade confidence one step.
- [x] TASK-02-06: Emit `logger.warning("section_truncated", section_key=..., original_chars=...,
      budget_chars=...)` when truncation occurs.
- [x] TASK-02-07: Add `tests/test_section_budgets.py` with the Test Specs below.
- [x] TASK-02-08: Document the budget mechanism in `README.md` under a new "Section length budgets"
      subsection placed immediately after "Quantification precedence".

**File Changes**
- `schemas/pdd_section_schema.yaml` (modify): add exactly one `max_chars: <int>` line to each of the
  36 `sub_sections` entries, placed immediately after that entry's `review_sensitivity` line. Change
  nothing else — the `aliases`, `evidence_required`, `guidance`, `content_class`, and
  `boilerplate_level` keys stay as they are.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): add the budget table and resolver; pass
  `max_chars` at both provider call sites; add truncation detection. Leave retrieval, prompt
  assembly, calc injection, `_build_structured_content`, and the review gate untouched.
- `schemas/project_input.py` (modify): the `max_tokens_per_section` field only.
- `tests/test_section_budgets.py` (create).
- `README.md` (modify): add the "Section length budgets" subsection.

**Function Signatures**
- `section_budget_chars(self, section_id: str, sub_section_id: str | None = None) -> int` — returns
  the effective character budget for one subsection following S-2 steps 1–4.
- `_apply_truncation_report(self, draft: DraftSection, budget: int, original_len: int) -> DraftSection`
  — returns the draft with a `TRUNCATED: …` issue appended and confidence downgraded one step when
  `original_len > budget`; returns the draft unchanged otherwise.

**Test Specs**
- `section_budget_chars("4", "4.4")` → `20000` (QUANTITATIVE).
- `section_budget_chars("1", "1.2")` → `3000` (FACTUAL).
- `section_budget_chars("1", "1.18")` → `2000` (OPTIONAL).
- `section_budget_chars("3", "3.5")` → `12000` (METHODOLOGY_DEPENDENT).
- `section_budget_chars("9", "9.9")` → `4000` (unknown subsection falls back to the default).
- With `generation_controls.max_tokens_per_section = 5000`, `section_budget_chars("4", "4.4")` →
  `5000` (the global ceiling caps the schema budget).
- With `generation_controls.max_tokens_per_section = 40000`, `section_budget_chars("4", "4.4")` →
  `20000` (the schema budget is the binding constraint).
- Sum of `section_budget_chars` over all 36 subsections → `297000`.
- A provider returning 25,000 characters for section 4.4 (budget 20,000) → stored
  `len(draft.text) == 20000`; `draft.issues` contains exactly one entry starting with `"TRUNCATED: "`
  and naming both `25000` and `20000`; `draft.confidence` is `"MEDIUM"` when the provider reported
  `"HIGH"`.
- A provider returning 25,000 characters with reported confidence `"LOW"` → confidence stays `"LOW"`.
- A provider returning 1,000 characters for section 4.4 → no `TRUNCATED:` issue, confidence
  unchanged, `len(draft.text) == 1000`.
- Every one of the 36 subsections in `schemas/pdd_section_schema.yaml` has a `max_chars` key, and
  every value is an `int` in the closed range `[2000, 20000]`.

**Dependencies**
- None. Independent of PHASE-01.

**Exit Criteria**
- [ ] `python -m pytest tests/test_section_budgets.py tests/test_section_orchestrator.py tests/test_input_schema.py -v` passes with 0 failures.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both exit 0.
- [ ] The following prints `297000`:
      ```bash
      python -c "
      import yaml
      d = yaml.safe_load(open('schemas/pdd_section_schema.yaml', encoding='utf-8'))
      subs = [ss for s in d['sections'] for ss in s.get('sub_sections', [])]
      assert len(subs) == 36, len(subs)
      assert all('max_chars' in ss for ss in subs), 'a subsection is missing max_chars'
      print(sum(ss['max_chars'] for ss in subs))
      "
      ```
- [ ] A full `demo`-provider draft still completes and stores 36 sections:
      ```bash
      pdd-agent draft --input configs/projects/demo_socson_like.yaml --provider demo --run-id budget-check
      python -c "
      import json; d = json.load(open('data/runs/budget-check.json', encoding='utf-8'))
      print(len(d['sections']), 'sections')
      assert len(d['sections']) == 36
      "
      ```
      → prints `36 sections`.

**Phase Risks**
- **RISK-02-01:** `DemoProvider` and `NoopProvider` produce short text, so raising the cap changes no
  committed artifact — but the `reports/demo-packages/` DOCX files must still not be regenerated
  (CON-003). Mitigation: no task writes to `reports/demo-packages/`; verify with
  `git status --short reports/` before committing.
- **RISK-02-02:** Raising the per-section budget to 20,000 characters raises the cost of a future
  real run roughly proportionally for the four QUANTITATIVE sections. Mitigation: the budget is a
  ceiling, not a target; `PDD_MAX_COST_USD` remains the hard spend control and no task in this plan
  runs a paid provider.
- **RISK-02-03:** `max_tokens_per_section` is named in tokens but now documented as characters.
  Mitigation: renaming the field would break the six committed configs; the description change plus
  the README subsection is the agreed compromise (ASM-004).

### PHASE-03 - Split the Export Gate's Two Meanings

**Goal**
Stop hard-blocking export on the `[MISSING]` markers the drafting prompt explicitly asks the model to
emit. Turn them into a first-class "Required Inputs" appendix that exports without `--force`.

**Tasks**
- [x] TASK-03-01: Add `required_inputs: list[dict[str, str]] = field(default_factory=list)` to
      `ExportGateResult` in `src/pdd_agent/export/docx_export.py`.
- [x] TASK-03-02: Rewrite `_check_missing_markers` as `_collect_required_inputs`, which appends to
      `required_inputs` instead of `hard_blocks`, records every occurrence in every section (not only
      Sections 3 and 4), and captures 200 characters of whitespace-collapsed surrounding context.
- [x] TASK-03-03: Update `check_export_gate` to call `_collect_required_inputs` and pass its output
      into `ExportGateResult`. Leave the consistency-flag and evidence-registry hard blocks exactly
      as they are.
- [x] TASK-03-04: Add `_add_required_inputs_appendix(doc, required_inputs)` rendering an
      "Appendix — Required Inputs" heading and a two-column table (`Section`, `What is missing`) via
      `add_styled_table`; call it from `export_run_to_docx` immediately before
      `_add_reviewer_issues_appendix`.
- [x] TASK-03-05: Change `_add_draft_watermark` so the `(EXPORT GATE OVERRIDE)` suffix appears only
      when `force=True` **and** the gate actually had hard blocks; pass the gate result into it.
- [x] TASK-03-06: Update the `check_export_gate` docstring so its "Hard-blocks" list no longer
      mentions `[MISSING]` markers, and add a "Required inputs" paragraph describing the new tier.
- [x] TASK-03-07: Update the tests in `tests/test_docx_export.py` that currently assert
      `[MISSING]` is a hard block, so they assert the new required-input behaviour instead.
- [x] TASK-03-08: Update the export-gate description in `README.md`.

**File Changes**
- `src/pdd_agent/export/docx_export.py` (modify): `ExportGateResult` dataclass (line 45),
  `check_export_gate` (line 54), `_check_missing_markers` (line 130, renamed), `_add_draft_watermark`
  (line 403), `export_run_to_docx` appendix ordering (line 286-289), plus the new appendix helper.
  Leave `_check_evidence_registry`, the consistency-flag handling, and every table renderer untouched.
- `tests/test_docx_export.py` (modify): the existing `[MISSING]`-hard-block assertions only.
- `README.md` (modify): the export-gate paragraph only.

**Function Signatures**
- `_collect_required_inputs(sections: list[Any], required_inputs: list[dict[str, str]]) -> None` —
  appends one `{"section_key": str, "context": str}` entry per `[MISSING]` occurrence; mutates in
  place and returns nothing.
- `_add_required_inputs_appendix(doc: Any, required_inputs: list[dict[str, str]]) -> None` —
  appends the appendix heading and table; a no-op when `required_inputs` is empty.
- `_add_draft_watermark(doc: Any, force: bool = False, had_hard_blocks: bool = False) -> None` —
  adds the DRAFT stamp, appending `" (EXPORT GATE OVERRIDE)"` only when both flags are true.

**Test Specs**
- A run whose section `4.1` text is `"Value is [MISSING] pending the grid EF."` →
  `check_export_gate(run).blocked is False`, `hard_blocks == []`, and `len(required_inputs) == 1`
  with `required_inputs[0]["section_key"] == "4.1"` and `"grid EF"` present in
  `required_inputs[0]["context"]`.
- A run whose section `1.1` text contains `[MISSING]` → also collected (Sections 1, 2, and 5 are no
  longer exempt); `blocked is False`.
- A run with a `[MISSING]` marker **and** a `CRITICAL` consistency flag → `blocked is True`,
  `len(hard_blocks) == 1`, `len(required_inputs) == 1`.
- A run with two `[MISSING]` markers in the same section → `len(required_inputs) == 2`.
- A run with no markers → `required_inputs == []` and no "Appendix — Required Inputs" heading appears
  in the exported document.
- Exporting a run whose only finding is `[MISSING]` markers **without** `force=True` → the export
  succeeds, the exported document contains a paragraph whose text is exactly
  `"Appendix — Required Inputs"`, and no paragraph text contains `"EXPORT GATE OVERRIDE"`.
- Exporting a run with a `CRITICAL` consistency flag and `force=True` → some paragraph contains
  `"EXPORT GATE OVERRIDE"`.

**Dependencies**
- PHASE-01, for the `add_styled_table`-based appendix pattern and to avoid two concurrent edits to
  `export_run_to_docx`'s appendix ordering.

**Exit Criteria**
- [ ] `python -m pytest tests/test_docx_export.py tests/test_docx_export_tables.py tests/test_review_checks.py -v` passes with 0 failures.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both exit 0.
- [ ] Exporting the real run without `--force` succeeds:
      ```bash
      pdd-agent export --run-id smoke-4-1
      ```
      → exits 0, logs no `export_gate_forced` event, and writes `data/runs/smoke-4-1.docx`.
      (Skip this check if `data/runs/smoke-4-1.json` is absent in your clone; the automated tests
      above are the binding proof.)

**Phase Risks**
- **RISK-03-01:** Widening `[MISSING]` collection to all five sections could produce a very long
  appendix for a `noop`-provider run whose placeholder bodies are full of markers. Mitigation: cap
  the rendered table at the first 100 entries and add a final row reading
  `"… and {n} more required inputs (see the run JSON)"` when there are more.
- **RISK-03-02:** Some existing test may depend on `blocked is True` for a `[MISSING]` fixture in a
  way that is not obvious from a grep. Mitigation: run
  `grep -rn "MISSING" tests/ --include=*.py` before editing and update every hit deliberately.

### PHASE-04 - Repair the Review UI and Product Surface

**Goal**
Make the human-facing surfaces work: bulk approval actually approves, a non-WTE project's borrowed
grounding is visible in the document, the run list does not degrade with the run count, and the one
keyless real provider is reachable and documented.

**Tasks**
- [x] TASK-04-01: Add `path_to_approved()` to `src/pdd_agent/review/states.py` returning the ordered
      list of hops from a given state to `approved` per Specification S-4.
- [x] TASK-04-02: Rewrite `api_approve_all` in `src/pdd_agent/service/main.py` to walk the path,
      collect skipped sections with reasons, and return HTTP 409 with the body in S-4 when
      `sections_skipped` is non-empty.
- [x] TASK-04-03: Populate `configs/corpus_families.yaml`'s `documents:` map with an explicit
      `wte` entry for each of the 17 stems in `data/corpus/normalized/` (listed in the File Changes
      below), so the mapping is declared rather than defaulted.
- [x] TASK-04-04: In `src/pdd_agent/retrieval/search.py`, keep the cross-family fallback (DEC-003)
      but have `get_examples_for_section` return results tagged so the caller can tell they came from
      the fallback: add a `from_fallback_family: bool` attribute to `RetrievalResult`, default
      `False`, set `True` on every result produced by the unfiltered re-fetch.
- [x] TASK-04-05: In `src/pdd_agent/agent/section_orchestrator.py`, when any retrieved example has
      `from_fallback_family is True`, append the issue
      `GROUNDING: no {family} corpus available; this section is grounded in {other_family} precedent and must be reviewed before use.`
      to the drafted section's `issues`.
- [x] TASK-04-06: Add `limit` (default 50, maximum 200) and `offset` (default 0) query parameters to
      `GET /api/runs` and to `GET /dashboard`, applying them to the sorted path list **before** any
      `_run_status()` call so the per-request `stat()` and JSON-parse cost is bounded. Include
      `"total"`, `"limit"`, and `"offset"` in the `/api/runs` response body.
- [x] TASK-04-07: Add `claude-code` to `_get_provider` in `src/pdd_agent/service/main.py`, resolving
      it via `configure_provider_from_env("claude-code")` exactly as `ollama` is resolved, with no
      API key and no `PDD_MAX_COST_USD` requirement.
- [x] TASK-04-08: Add `claude-code` to the `--provider` help strings in `src/pdd_agent/cli.py`
      (the `draft` parser at line 97 and the `benchmark` parser at line 272) and to the
      `pdd-agent draft` row of the CLI table in `README.md`.
- [x] TASK-04-09: Rename `get_active_index_doc_count()` in `src/pdd_agent/retrieval/index.py` to
      `get_active_index_row_count()`, keep a thin deprecated alias under the old name so existing
      callers keep working, and update the scorecard label in
      `src/pdd_agent/phase05/provider_scorecard.py` from "Corpus documents" to "Indexed section rows".
- [x] TASK-04-10: Add `reachable_rows` (rows with a non-empty `section_id`) and
      `reachable_documents` (distinct `document_name` among those rows) to the dict returned by
      `index_health()`, and print both from `_run_index_report` in `src/pdd_agent/cli.py`.
- [x] TASK-04-11: Add the `ingest` extra to the CI install step in `.github/workflows/ci.yml`.
- [x] TASK-04-12: Update the `**Status:**` line in `README.md` to the test count produced by the
      final green run of this plan.

**File Changes**
- `src/pdd_agent/review/states.py` (modify): add `path_to_approved`. Do not change `_TRANSITIONS`,
  `_VALID_STATES`, or `set_state`'s validation.
- `src/pdd_agent/service/main.py` (modify): `api_approve_all` (line 659), `_get_provider` (line 99),
  `dashboard` (line 385), `api_list_runs` (line 565). Leave the per-section approve endpoint,
  `_run_status`, and the edit endpoint untouched.
- `configs/corpus_families.yaml` (modify): replace `documents: {}` with an explicit mapping of these
  17 stems to `wte` — `Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2.norm`,
  `DraftProjectDescription.norm`, `EB111_repan07_ACM0022_v03.0.norm`,
  `VCS-Project-Description-HEREKO-v4.1_2022-10-24.norm`, `VCS_Bergama_Project-Description.norm`,
  `VCS_DRAFT_Yanjiang_Project-Description.norm`, `VCS_Guangzhou_Project-Description.norm`,
  `VCS_Guanxi_Zhuang_Project_Description.norm`, `VCS_Inegol_Project-Description.norm`,
  `VCS_Linfen_Project-Description.norm`, `VCS_Lizuhou_Project-Description.norm`,
  `VCS_Mahindra_Project-Description.norm`, `VCS_Shunping_Project-Description.norm`,
  `VCS_Soc_Son_Project-Description.norm`, `VCS_Tamil_Nadu_Project-Description.norm`,
  `VCS_Yingoku_Project-Description.norm`, and the stem for the Ödemiş document, which must be copied
  **byte for byte** from the output of
  `python -c "import pathlib;[print(p.stem) for p in pathlib.Path('data/corpus/normalized').glob('*.norm.json')]"`
  because its filename carries a mis-encoded character (see Gotchas). Keep `default_family: wte`.
- `src/pdd_agent/retrieval/search.py` (modify): `RetrievalResult` and the fallback branch at line 200.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): add the grounding issue after the retrieval
  block near line 728. Do not touch the budget code added in PHASE-02 beyond coexisting with it.
- `src/pdd_agent/retrieval/index.py` (modify): rename the row-count helper, add the alias, add the two
  reachability metrics to `index_health`.
- `src/pdd_agent/phase05/provider_scorecard.py` (modify): the label string only.
- `src/pdd_agent/cli.py` (modify): two `--provider` help strings and the `_run_index_report` printer.
- `.github/workflows/ci.yml` (modify): the `pip install -e` line in the `test` job.
- `README.md` (modify): status line, CLI table `draft` row.
- `tests/test_service.py` (modify): add approve-all and pagination cases.
- `tests/test_retrieval_search.py` (modify): add the fallback-tagging and reachability-metric cases.

**Function Signatures**
- `path_to_approved(state: ReviewState) -> list[ReviewState]` — returns the ordered hops that take
  `state` to `ReviewState.APPROVED`; returns `[]` for `APPROVED` itself and for `NEEDS_INPUT`
  (which is never bulk-approved).
- `get_active_index_row_count() -> int` — returns `COUNT(*)` of `sections_fts` in the active index,
  or `0` when the index is missing or unreadable.
- `index_health(db_path: Path | None = None, corpus_dir: Path | None = None) -> dict[str, Any]` —
  unchanged signature; the returned dict gains `"reachable_rows": int` and
  `"reachable_documents": int`.

**Test Specs**
- `path_to_approved(ReviewState.DRAFTED)` →
  `[ReviewState.READY_FOR_HUMAN_EDIT, ReviewState.APPROVED]`.
- `path_to_approved(ReviewState.NEEDS_DOMAIN_REVIEW)` →
  `[ReviewState.READY_FOR_HUMAN_EDIT, ReviewState.APPROVED]`.
- `path_to_approved(ReviewState.READY_FOR_HUMAN_EDIT)` → `[ReviewState.APPROVED]`.
- `path_to_approved(ReviewState.APPROVED)` → `[]`.
- `path_to_approved(ReviewState.NEEDS_INPUT)` → `[]`.
- `POST /api/runs/{id}/approve-all` on a fresh run whose 36 sections are all `drafted` → HTTP 200,
  `sections_approved == 36`, `sections_skipped == []`, `all_approved is True`.
- The same call on a run with 35 `drafted` sections and 1 `needs-input` section → HTTP **409**,
  `sections_approved == 35`, `len(sections_skipped) == 1`, that entry's `state` is `"needs-input"`,
  `all_approved is False`.
- The same call twice in a row on an all-`drafted` run → the second call returns HTTP 200 with
  `sections_approved == 0` and `all_approved is True` (already-approved sections are not skips).
- `GET /api/runs?limit=2` with 5 runs present → the response has `len(runs) == 2`, `total == 5`,
  `limit == 2`, `offset == 0`, and the two entries are the two most recently modified.
- `GET /api/runs?limit=2&offset=4` with 5 runs present → `len(runs) == 1`.
- `GET /api/runs?limit=9999` → `limit` is clamped to `200` in the response body.
- `_get_provider("claude-code")` → the returned provider's `name` is `"claude-code"` and
  `provider_status()["reason"]` is `None` (no `unknown_provider` fallback).
- A retrieval call for `document_family="rice"` against a WTE-only index → the returned results all
  have `from_fallback_family is True`, and the drafted section's `issues` contains an entry starting
  with `"GROUNDING: no rice corpus available"`.
- A retrieval call for `document_family="wte"` against the same index → every result has
  `from_fallback_family is False` and no `GROUNDING:` issue is added.
- `index_health()` over a synthetic in-memory index with 3 rows of which 2 have a non-empty
  `section_id` spread over 2 documents → `reachable_rows == 2` and `reachable_documents == 2`.

**Dependencies**
- None. Independent of PHASE-01, PHASE-02, and PHASE-03.

**Exit Criteria**
- [ ] `python -m pytest tests/test_service.py tests/test_retrieval_search.py -v` passes with 0 failures.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both exit 0.
- [ ] `configs/corpus_families.yaml` maps every normalized document explicitly:
      ```bash
      python -c "
      import pathlib, yaml
      cfg = yaml.safe_load(open('configs/corpus_families.yaml', encoding='utf-8'))
      stems = {p.name[:-len('.json')] for p in pathlib.Path('data/corpus/normalized').glob('*.norm.json')}
      missing = sorted(stems - set(cfg['documents']))
      assert not missing, f'unmapped: {missing}'
      print('mapped', len(cfg['documents']), 'documents')
      "
      ```
      → prints `mapped 17 documents`. (Skip if `data/corpus/normalized/` is absent in your clone;
      it is gitignored.)
- [ ] `pdd-agent index-report` prints both a `Reachable rows:` line and a `Reachable documents:` line.
- [ ] `grep -c "claude-code" README.md` returns a value of at least 1.

**Phase Risks**
- **RISK-04-01:** Changing `approve-all` from HTTP 200 to HTTP 409 on partial application is a
  breaking API change for any existing client. Mitigation: the only in-repo caller is the dashboard
  template; grep for `approve-all` across `src/` and `templates` and update every call site.
  Document the change in the `README.md` service section.
- **RISK-04-02:** The Ödemiş document's filename contains a mis-encoded character, so a hand-typed
  YAML key will silently fail to match. Mitigation: TASK-04-03 mandates copying the stem from the
  `pathlib` listing output rather than typing it, and the exit-criteria command asserts a complete
  mapping.
- **RISK-04-03:** Adding `from_fallback_family` to `RetrievalResult` may break constructors that pass
  positional arguments. Mitigation: add the field last with a default of `False`, and grep for
  `RetrievalResult(` across `src/` and `tests/` to confirm every construction is keyword-based.

### PHASE-05 - Charge the Emissions an Incinerator Causes

**Goal**
Give the ACM0022 engine an incineration project-emission term and a working capacity ramp, correct
the Soc Son composition to what the registered PDD actually publishes, and measure the result against
a seven-row year-by-year oracle read out of that same document — recording whatever residual remains
rather than forcing a pass.

**Tasks**
- [x] TASK-05-01: Add `GWP_N2O`, `EF_N2O_INCINERATION_KG_PER_TONNE`, `OXIDATION_FACTOR_INCINERATION`,
      `CO2_PER_C_RATIO`, and `INCINERATION_CARBON_BY_WASTE_TYPE` to
      `src/pdd_agent/calc/constants.py` with the values in Specification S-5b and an IPCC citation in
      the module docstring.
- [x] TASK-05-02: Add an `IncinerationStream` model and an `incineration_streams: list[IncinerationStream] = []`
      field (plus `oxidation_factor_incineration: float = 1.0` and
      `ef_n2o_kg_per_tonne: float = 0.05`) to `ACM0022CalcInput` in `src/pdd_agent/calc/models.py`,
      and the matching `project_incineration_tco2e: float` output field on `ACM0022CalcResult`.
- [x] TASK-05-03: Implement `incineration_emissions(...)` in a new
      `src/pdd_agent/calc/incineration.py` module following Specification S-5b.
- [x] TASK-05-04: Wire `PE_INC` into `ACM0022Calculator.calculate()` as a fifth project-emission
      component named `"PE_INC (waste incineration)"` with `formula_ref="ACM0022 Eq.17 + IPCC 2006 V5 Eq.5.1/5.4"`,
      add it to `project_total`, and update `compute_project()`'s `formula` string to
      `"PE_y = PE_EC + PE_FC + PE_CH4 + PE_FLARE + PE_INC"`.
- [x] TASK-05-05: Add `plastics` and `inert` handling in `_map_acm0022`
      (`src/pdd_agent/calc/dispatch.py`): every `waste_composition` entry — including those absent
      from `DOC_BY_WASTE_TYPE` — produces an `incineration_streams` entry when
      `technology.technology_type == "incineration_with_energy_recovery"`, while only the mapped
      types continue to produce `waste_streams`. Add one warning line per unmapped type explaining
      that it contributes `PE_INC` but no `BE_CH4`.
- [x] TASK-05-06: Implement `capacity_ramp` consumption in the year loop of `compute_for()` per
      Specification S-5c, and delete the "validated but not yet consumed by the calc engine" clause
      from the field's description in `schemas/project_input.py`.
- [x] TASK-05-07: Correct `configs/projects/vietnam_socson_from_sheet.yaml` per Specification S-5d:
      remove the `rubber_leather` entry (not in the cited Table 8), keep the five Table 8 degradable
      rows, and add `plastics: 0.030` and `inert: 0.408` entries whose `source` string is
      `"VCS Soc Son registered PDD, Section 3.2 applicability — 0.5% glass, 0.9% metal, 3% plastic of the 43.8% inert bucket in Table 8"`.
- [x] TASK-05-08: Add the seven-row registered schedule from Specification S-5a to
      `tests/test_registered_pdd_oracle.py` as module constants
      `SOC_SON_REGISTERED_BE_CH4_BY_YEAR` and `SOC_SON_REGISTERED_ER_BY_YEAR`, and add a
      `TestSocSonAnnualSchedule` class asserting the two discrepancies D-1 and D-2 are measured.
- [x] TASK-05-09: Re-measure all three existing oracle `xfail`s. Update each `reason` string with the
      date `2026-08-21` and the newly measured numbers. Flip an `xfail` to a plain test **only** if
      it genuinely passes. Do not touch `TOLERANCE`.
- [x] TASK-05-10: Add unit tests for `incineration_emissions` and `capacity_ramp` in
      `tests/test_calc_dispatch.py` and a new `tests/test_incineration.py`.
- [x] TASK-05-11: Record the measured before/after numbers for both discrepancies in the commit
      message body, following the precedent set by commit `e14c107`.
- [x] TASK-05-12: Update the "Quantification precedence" section of `README.md` to describe `PE_INC`
      and the capacity ramp.

**File Changes**
- `src/pdd_agent/calc/constants.py` (modify): append the new constants after `FOSSIL_FUEL_NCV`.
  Do not change `GWP_CH4`, `DOC_BY_WASTE_TYPE`, or `DECAY_RATE_BY_WASTE_TYPE`.
- `src/pdd_agent/calc/incineration.py` (create): the two IPCC equations and nothing else.
- `src/pdd_agent/calc/models.py` (modify): add `IncinerationStream`, three `ACM0022CalcInput` fields,
  and one `ACM0022CalcResult` field. All new fields default so existing configs still validate.
- `src/pdd_agent/calc/acm0022.py` (modify): the project-emissions block (lines 106–166), the
  `project_total` sum (line 166), the `ACM0022CalcResult(...)` construction, and the
  `compute_project()` formula string (line 269). Leave the baseline and leakage blocks untouched.
- `src/pdd_agent/calc/dispatch.py` (modify): `_map_acm0022`'s composition branch (lines 168–196) and
  the year loop in `compute_for` (lines 357–374).
- `schemas/project_input.py` (modify): the `capacity_ramp` field description only.
- `configs/projects/vietnam_socson_from_sheet.yaml` (modify): the `waste_composition` list only.
  Leave `waste_type`, `annual_waste_throughput`, and every other key untouched.
- `tests/test_registered_pdd_oracle.py` (modify): add the two schedule constants and the new test
  class; update the three `xfail` reasons. **Do not change `TOLERANCE`.**
- `tests/test_incineration.py` (create).
- `tests/test_calc_dispatch.py` (modify): add capacity-ramp and unmapped-type cases.
- `README.md` (modify): the "Quantification precedence" section only.

**Function Signatures**
- `incineration_co2(streams: list[dict[str, Any]], oxidation_factor: float = 1.0) -> float` —
  returns fossil CO2 from combustion in tCO2/year; each stream dict carries `waste_type` and
  `annual_tonnes` and may carry `dm_override`, `cf_override`, and `fcf_override`.
- `incineration_n2o(total_tonnes: float, ef_kg_per_tonne: float = 0.05, gwp_n2o: float = 265.0) -> float`
  — returns N2O emissions expressed in tCO2e/year.
- `incineration_emissions(streams: list[dict[str, Any]], oxidation_factor: float = 1.0, ef_n2o_kg_per_tonne: float = 0.05) -> float`
  — returns `incineration_co2(...) + incineration_n2o(...)` in tCO2e/year; returns `0.0` for an
  empty stream list.
- `_ramp_factor(capacity_ramp: list[float] | None, year: int) -> float` — returns the year's
  utilisation factor per Specification S-5c; returns `1.0` when `capacity_ramp` is `None` or empty.

**Test Specs**
- `incineration_emissions([], ...)` → `0.0`.
- `incineration_co2([{"waste_type": "plastics", "annual_tonnes": 1000.0}])` →
  `1000.0 × 1.00 × 0.75 × 1.00 × 1.0 × (44/12)` = `2750.0` (±0.01).
- `incineration_co2([{"waste_type": "food_waste", "annual_tonnes": 1000.0}])` → `0.0`
  (`FCF = 0.00`, so biogenic carbon is correctly excluded).
- `incineration_co2([{"waste_type": "textiles", "annual_tonnes": 1000.0}])` →
  `1000.0 × 0.80 × 0.50 × 0.20 × 1.0 × (44/12)` = `293.3333` (±0.01).
- `incineration_co2([{"waste_type": "plastics", "annual_tonnes": 1000.0}], oxidation_factor=0.98)` →
  `2695.0` (±0.01).
- `incineration_co2([{"waste_type": "unknown_type", "annual_tonnes": 1000.0}])` → `0.0`, and a
  `structlog` warning event `incineration_waste_type_unknown` is emitted.
- `incineration_n2o(1_460_000.0)` → `1_460_000 × 0.05 × 0.001 × 265.0` = `19_345.0` (±0.01).
- `_ramp_factor(None, 1)` → `1.0`; `_ramp_factor([], 3)` → `1.0`.
- `_ramp_factor([0.5, 0.8, 1.0], 1)` → `0.5`; `_ramp_factor([0.5, 0.8, 1.0], 3)` → `1.0`;
  `_ramp_factor([0.5, 0.8, 1.0], 7)` → `1.0` (last value carried forward).
- A `ProjectInput` with `capacity_ramp = [0.5, 1.0]` and `crediting_period_years = 2` →
  `compute_for(pi).annual_schedule[0].baseline_tco2e` is strictly less than the same value computed
  with `capacity_ramp = None`, and `annual_schedule[1]` is unchanged from the no-ramp case.
- An existing config with no `capacity_ramp` and no `incineration_streams` → `compute_for(pi)`
  returns exactly the same `crediting_period_total_tco2e` as before this phase (regression guard;
  assert against the literal `5_397_729.87` for Soc Son **before** TASK-05-07 changes its composition,
  in a test that constructs the pre-change composition inline rather than reading the YAML).
- Soc Son after TASK-05-07 → `compute_for(pi).project_emissions_tco2e > 0.0` (the engine no longer
  reports zero project emissions for an incinerator).
- `TestSocSonAnnualSchedule`: `sum(SOC_SON_REGISTERED_BE_CH4_BY_YEAR) == 4_384_018` and
  `sum(SOC_SON_REGISTERED_ER_BY_YEAR) == 3_808_083`.
- `TestSocSonAnnualSchedule`: for every year index `i`, `abs((SOC_SON_REGISTERED_BE_CH4_BY_YEAR[i] -
  SOC_SON_REGISTERED_ER_BY_YEAR[i]) - 82_276.5) <= 0.5` (the registered constant-charge identity).
- `TestSocSonAnnualSchedule` (D-1, expected to `xfail` until baseline methane is corrected): the
  engine's 7-year `BE_CH4` sum is within `TOLERANCE` of `4_384_018`.
- `TestSocSonAnnualSchedule` (D-2): the engine's per-year value of
  `(baseline_tco2e − BE_CH4,y) − project_tco2e − leakage_tco2e` is within `TOLERANCE` of
  `−82_276.5`. Mark `xfail(strict=True)` with a reason recording the measured value if it does not
  pass.

**Dependencies**
- None. Independent of PHASE-01 through PHASE-04; sequenced last because it carries the highest risk
  of not fully closing.

**Exit Criteria**
- [ ] `python -m pytest tests/test_incineration.py tests/test_calc_dispatch.py tests/test_acm0022_calc.py tests/test_registered_pdd_oracle.py -v` passes with 0 failures (`xfail`s are not failures).
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failed.
- [ ] `ruff check . && ruff format --check .` both exit 0.
- [ ] Project emissions are no longer zero for Soc Son:
      ```bash
      pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml
      ```
      → the `Project emissions:` line reports a value strictly greater than `0.00 tCO2e/year`, and a
      `PE_INC (waste incineration)` component appears in the component list.
- [ ] `grep -n "TOLERANCE = 0.20" tests/test_registered_pdd_oracle.py` still matches (the tolerance
      was not widened).
- [ ] Every `xfail` reason in `tests/test_registered_pdd_oracle.py` contains the string `2026-08-21`
      and the newly measured numbers.
- [ ] `python -c "import yaml; c=yaml.safe_load(open('configs/projects/vietnam_socson_from_sheet.yaml',encoding='utf-8')); wc=c['technology']['waste_composition']; print(round(sum(e['mass_fraction'] for e in wc), 4))"`
      → prints `1.0`.

**Phase Risks**
- **RISK-05-01:** Adding `PE_INC` will reduce net emission reductions and may push the Soc Son
  crediting total from `+41.7%` through the true value and out the other side, turning an
  overstatement into an understatement. Mitigation: the year-by-year oracle in TASK-05-08 measures
  both directions per year; report the signed residual and leave the `xfail` in place if it does not
  land inside `TOLERANCE`.
- **RISK-05-02:** The 43.8% "Glass, plastic, metal, other inert" bucket is split into 3.0% plastics
  and 40.8% inert on the strength of one sentence in the registered PDD's applicability discussion.
  Mitigation: both new composition entries carry that exact provenance string, which surfaces as a
  `waste_composition:` calc warning and reaches the DOCX reviewer-issues appendix — the assumption is
  visible to a reviewer rather than buried.
- **RISK-05-03:** D-1 (baseline methane 33.9% low) is not addressed by this phase and may not be
  closable without changing the first-order-decay parameters, which risks regressing the ACM0022
  golden tests. Mitigation: D-1 is measured and recorded, not fixed. Any FOD parameter change is
  explicitly out of scope for this plan.
- **RISK-05-04:** Removing `rubber_leather` from the Soc Son composition changes `BE_CH4` and
  therefore every downstream number in the committed `docs/vietnam-pdd-*.md` reports. Mitigation:
  those documents are regenerated by `pdd-agent run-vietnam-pdd`; do not hand-edit them, and note in
  the commit message that they are stale until the workflow is re-run.

## Gotchas

- **`_split_paragraphs` has more than one caller.** Grep before changing it. PHASE-01 changes only
  `_add_section_prose`; other callers render short single-purpose strings and must keep the naive
  behaviour.
- **python-docx must stay lazily imported.** Every python-docx symbol in the export package is
  fetched through `_docx_attr(module_name, attr_name)` so that `import pdd_agent.export.docx_export`
  works in an environment without `python-docx` installed. A module-level `from docx import Document`
  will break `pdd-agent doctor` and several tests.
- **`add_styled_table` appends a trailing empty paragraph.** It calls `doc.add_paragraph()` before
  returning. Any test that counts paragraphs after rendering a table must account for it.
- **`add_styled_table` shades the first column when a row has exactly 2 cells.** A two-column
  Markdown table will therefore render with a shaded left column. This is intended styling, not a bug.
- **One corpus filename is mis-encoded.** The Ödemiş document's stem contains a replacement/mojibake
  character. Never type it by hand into YAML or a test — read it from the filesystem. The corpus also
  contains 2,677 U+FFFD characters overall, concentrated in the Chinese-project PDDs; do not "fix"
  them in this plan, and do not let a test assert on exact corpus text.
- **`max_chars` is characters, not tokens, everywhere in this codebase.** The provider parameter is
  `max_chars` and the truncation is `text[:max_chars]`. `GenerationControls.max_tokens_per_section`
  is the odd one out and is being redefined as a character ceiling (ASM-004); do not "correct" it
  into a token count.
- **Emission signs.** In this codebase `BE_*` components are credits (they increase net emission
  reductions), `PE_*` and `LE_*` are charges (they decrease it), and `net = baseline − project −
  leakage`. `PE_INC` must be **added** to `project_total`, which **reduces** the net. Getting this
  backwards will make the oracle gap worse in a way that looks superficially like progress.
- **`dm`, `CF`, and `FCF` multiply in that order and the result is carbon, not CO2.** Multiply by
  `44/12` exactly once, at the end. A missing `44/12` understates by 3.67×; a doubled one overstates
  by the same factor.
- **`CF` is a fraction of dry matter, not of wet weight.** `dm` must be applied first. Skipping `dm`
  overstates plastics by 0% (its `dm` is 1.00) but overstates food waste by 2.5×.
- **Do not widen `TOLERANCE`.** It is `0.20` in `tests/test_registered_pdd_oracle.py` and stays there
  (DEC-004). The `xfail` reasons are the deliverable when a gap does not close.
- **The registered totals do not self-consistently sum.** The Soc Son PDD's "Total estimated ERs
  3,808,082" is one tCO2e below its own column sum of 3,808,083. Use the per-year values for
  per-year assertions and the published total for total assertions; do not try to reconcile them.
- **`reports/demo-packages/` is committed.** Run `git status --short reports/` before every commit in
  this plan and confirm it is empty.
- **`data/index/`, `data/runs/`, and `data/corpus/` are gitignored.** Any exit-criteria command that
  reads them is a local convenience check, not a CI gate. Every binding proof in this plan is a test
  that constructs its own fixtures.
- **`api_approve_all` changing to HTTP 409 is a breaking API change.** Update the dashboard template
  and any other in-repo caller in the same commit.

## Verification Strategy

- **TEST-001:** `python -m pytest -m "not corpus" -q` → `0 failed`. The pre-plan baseline is
  `841 passed, 7 deselected, 3 xfailed`; the post-plan run must have a passed count strictly greater
  than 841 and a failed count of 0.
- **TEST-002:** `ruff check .` → exit code 0, no findings.
- **TEST-003:** `ruff format --check .` → exit code 0.
- **TEST-004:** `uv lock --check` → exit code 0 (no dependency was added by this plan, so the
  lockfile must be unchanged).
- **TEST-005:** `python -m pytest tests/test_markdown_docx.py -v` → all pass; verifies S-1.
- **TEST-006:**
  ```bash
  python -c "
  import yaml
  d = yaml.safe_load(open('schemas/pdd_section_schema.yaml', encoding='utf-8'))
  subs = [ss for s in d['sections'] for ss in s.get('sub_sections', [])]
  print(len(subs), sum(ss['max_chars'] for ss in subs))
  "
  ```
  → prints `36 297000`; verifies S-2.
- **TEST-007:** `python -m pytest tests/test_docx_export.py -k required_input -v` → all pass;
  verifies S-3.
- **TEST-008:** `python -m pytest tests/test_service.py -k approve_all -v` → all pass; verifies S-4.
- **TEST-009:** `python -m pytest tests/test_registered_pdd_oracle.py -v` → 0 failed; verifies S-5.
- **TEST-010:** `grep -n "TOLERANCE = 0.20" tests/test_registered_pdd_oracle.py` → exactly one match.
- **MANUAL-001:** Run `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` and
  confirm the output now lists a `PE_INC (waste incineration)` component with a value strictly
  greater than zero and a `Project emissions:` line strictly greater than `0.00`.
- **MANUAL-002:** Run
  `pdd-agent draft --input configs/projects/demo_socson_like.yaml --provider demo --run-id verify-demo`
  followed by `pdd-agent export --run-id verify-demo`, open the resulting
  `data/runs/verify-demo.docx`, and confirm the document opens in Word without a repair prompt and
  contains no literal `|`-delimited rows.
- **MANUAL-003:** Start the service with
  `uvicorn pdd_agent.service.main:app --port 8000`, open `http://localhost:8000/dashboard`, and
  confirm the page renders within a second and lists at most 50 runs.
- **MANUAL-004:** With the service running, `curl -X POST http://localhost:8000/api/runs/verify-demo/approve-all`
  → HTTP 200 and `"sections_approved": 36`.
- **OBS-001:** Confirm the new structlog events appear with the expected keys and never as f-strings:
  `section_truncated` (keys `section_key`, `original_chars`, `budget_chars`) and
  `incineration_waste_type_unknown` (key `waste_type`). Verify with
  `grep -rn "section_truncated\|incineration_waste_type_unknown" src/`.
- **OBS-002:** `pdd-agent index-report` prints `Reachable rows:` and `Reachable documents:` lines.
  With the current index these should read `889` and `13` respectively — a much more honest pair of
  numbers than the existing `Total rows: 3026` / `Documents: 17`.
- **OBS-003:** `git status --short reports/` → empty output, confirming CON-003 was respected.

## Risks and Alternatives

- **RISK-001:** PHASE-01 and PHASE-03 both edit the appendix ordering inside `export_run_to_docx`.
  Mitigation: PHASE-03 depends on PHASE-01 and must be executed after it; do not parallelise them.
- **RISK-002:** PHASE-02 and PHASE-04 both edit `src/pdd_agent/agent/section_orchestrator.py` — the
  budget resolver and the grounding issue respectively. Mitigation: the two edits are in different
  methods (`draft_section`'s provider-call region versus its retrieval region); execute PHASE-02
  first and re-run `python -m pytest tests/test_section_orchestrator.py -v` after each.
- **RISK-003:** The plan raises the effective per-section output ceiling from 4,000 to as much as
  20,000 characters, which raises the cost of a future real-model run. Mitigation: budgets are
  ceilings; `PDD_MAX_COST_USD` remains the hard spend control; no task here spends money.
- **RISK-004:** PHASE-05 may leave both discrepancies open. Mitigation: this is an accepted outcome
  (ASM-008). The phase's value is the year-by-year oracle and the non-zero project-emission term;
  the residual is recorded, not hidden.
- **ALT-001:** Prompt models to emit plain prose instead of Markdown. Rejected — Verra PDDs contain
  tables and equations, and suppressing them to protect the renderer degrades the deliverable
  (DEC-001).
- **ALT-002:** Adopt a third-party Markdown library (`markdown`, `mistune`, `pandoc`) and convert to
  DOCX through it. Rejected — it adds a dependency (or an external binary) to a pipeline whose
  selling point is that it needs neither, and the model output uses a small, predictable subset that
  a 200-line scanner handles. Revisit if the subset grows.
- **ALT-003:** Generate OOXML Math (OMML) for LaTeX. Rejected for this pass as high-effort and
  high-risk; the cleaned-italic rendering plus a verbatim-source appendix preserves all information
  (ASM-002). Revisit once a full real run shows how much math actually appears.
- **ALT-004:** Delete the cross-family retrieval fallback outright so a rice project produces
  `[MISSING]` rather than WTE citations. Rejected for this pass — it reverses a deliberate prior
  decision. Escalating the fallback to a document-visible section issue (TASK-04-05) captures most of
  the benefit without the reversal (DEC-003).
- **ALT-005:** Add run-store retention (delete runs older than N days) alongside pagination.
  Rejected — deleting a user's artifacts is not reversible and pagination alone fixes the
  performance problem (ASM-009).

## Suggested Next Step

Execute PHASE-01. It is self-contained, adds no dependency, is provable entirely offline, and every
later phase renders into the document it fixes. Verify PHASE-01's exit criteria in full — in
particular that `python -m pytest -m "not corpus" -q` still reports 0 failed — before starting
PHASE-02.
