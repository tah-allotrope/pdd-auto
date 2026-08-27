---
title: "Defensible Numbers and Document Assembly: reproduce the registered PDD's arithmetic, then own the document it goes into"
date: "2026-08-28"
status: "draft"
request: "Implement the 2026-08-27 brainstorm: close both ACM0022 oracle discrepancies together (climate-zone-aware FOD decay rates plus a methodology-faithful project-emission model sourced from the registered PDD's own parameter tables, with corpus re-normalization so extracted tables exist), own the assembled DOCX (canonical subsection numbering, no title echo, a real section length contract, document-level coherence checks), and make the first real full model run survivable (pre-flight cost estimate, per-section checkpointing, --resume, bounded concurrency, CLI budget flags)."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-08-27-pdd-assembly-and-defensible-numbers-brainstorm.md"
  - "research/2026-08-21-pdd-real-output-gap-brainstorm.md"
---

# Plan: Defensible Numbers and Document Assembly

## Objective

Make the ACM0022 calculation engine reproduce the arithmetic of a registered, validated Verra PDD
(Soc Son waste-to-power, Hanoi) using that PDD's own published parameters and the methodology's own
equations — then make the Word document the pipeline emits look like a PDD rather than 36 stapled
model replies, and make a full 36-section real-model run something that can be started, estimated,
interrupted, and resumed without losing paid work.

This matters now because the engine is the product's only falsifiable claim. Everything else the
repository asserts is checked against itself; the registered PDD is the one external referee
available, and the gap to it is currently explained, decomposed, and closable.

## Context Snapshot

- **Current state:**
  - `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` reports project
    emissions of 187,895 tCO2e/year and a 7-year crediting total of 4,010,142 tCO2e against the
    registered 3,808,082 (+5.3%). Two oracle tests in `tests/test_registered_pdd_oracle.py` are
    `xfail` with measured residuals: baseline methane 7-year sum 2,826,368 vs registered 4,384,018
    (−35.5%), and a per-year non-methane net charge of +169,110.6 vs the registered −82,276.5.
  - `src/pdd_agent/calc/constants.py` line 87 declares `DECAY_RATE_BY_WASTE_TYPE` with the comment
    "IPCC 2006 Table 3.3, wet tropical", but the values (`food_waste: 0.185`, `paper_cardboard: 0.06`,
    `wood: 0.03`, bulk `municipal_solid_waste: 0.09`) are the **boreal/temperate wet** column. The
    project site is Hanoi (latitude 21.261), which is tropical wet.
  - `src/pdd_agent/calc/incineration.py` computes project emissions from waste combustion with the
    IPCC 2006 Vol.5 Eq. 5.1 dry-matter form (`dm × CF × FCF`). ACM0022 v03.0 Equation 22 — the
    equation the registered PDD actually applies — uses a **wet-basis** fraction of total carbon
    (`FCC`) times a fossil fraction of that carbon (`FFC`), with no dry-matter term.
  - The engine has **no wastewater project-emission term** (ACM0022 Eq. 28) and
    `src/pdd_agent/calc/dispatch.py::_map_acm0022` never populates `fossil_fuels`, so `PE_FC` is
    always zero. Together those two omissions are 124,074 tCO2e/year of the registered project's
    420,336 tCO2e/year.
  - All 17 files in `data/corpus/normalized/` predate the pdfplumber table extraction added to
    `src/pdd_agent/ingest/normalize.py`: none of them has a `tables` key. Four of them
    (`EB111_repan07_ACM0022_v03.0.norm.json`, `DraftProjectDescription.norm.json`,
    `Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2.norm.json`,
    `VCS-Project-Description-HEREKO-v4.1_2022-10-24.norm.json`) were ingested from pre-extracted
    `.txt` files (`mime_type: text/plain`), which `_extract_text` does not handle: they contain one
    text block and a 50-entry heading list produced by an unrelated pipeline.
  - A real-model export (`data/runs/smoke-4-1.json`, provider `claude-code`) renders as
    `Heading 2 "Baseline Emissions"` immediately followed by `Heading 3 "4.4.1 Baseline Emissions"`:
    the exporter writes the canonical heading unnumbered and the model writes its own, misnumbered.
  - Per-subsection character budgets (2,000–20,000) exist in `schemas/pdd_section_schema.yaml`, but
    the prompt built by `SectionOrchestrator._build_prompt` never states a target length, and
    `src/pdd_agent/llm/openai_provider.py:158` / `src/pdd_agent/llm/ollama_provider.py:147` pass
    characters where the API expects tokens (`max_tokens = min(self._config.max_tokens, max_chars)`,
    with `ModelConfig.max_tokens` defaulting to 4000).
  - Drafting is serial, nothing is persisted until `draft_all_sections()` returns, the default token
    budget is 500,000 (about ten sections at the measured `claude-code` rate of ~47,500 tokens per
    section), and there are no CLI flags for budget, workers, or resume.
  - Test suite: `909 passed, 7 deselected, 4 xfailed` in about 72 seconds.
- **Desired state:**
  - The engine models ACM0022 project emissions the way the methodology defines them (Eq. 20/22/27/28)
    and resolves landfill decay rates from an IPCC climate zone derived from the project's latitude.
  - Every parameter used for Soc Son is traceable to the registered PDD or to a cited IPCC table, and
    the residual against the registered numbers is measured and recorded — not tuned.
  - The normalized corpus carries extracted tables, so registered parameter tables can be re-read
    mechanically instead of re-typed.
  - A real export has canonical `1.1`-style subsection numbering, no echoed section titles, and a
    document-level coherence report covering cross-section number agreement.
  - Sections are drafted against a stated length budget, with output token limits derived from that
    budget rather than from a character count misread as tokens.
  - A 36-section run prints a cost estimate before its first call, saves after every section, can be
    resumed, and can run several sections concurrently.
- **Key repo surfaces:** `src/pdd_agent/calc/constants.py`, `src/pdd_agent/calc/cdm_tool_04.py`,
  `src/pdd_agent/calc/incineration.py`, `src/pdd_agent/calc/acm0022.py`,
  `src/pdd_agent/calc/models.py`, `src/pdd_agent/calc/dispatch.py`, `schemas/project_input.py`,
  `configs/projects/vietnam_socson_from_sheet.yaml`, `tests/test_registered_pdd_oracle.py`,
  `src/pdd_agent/ingest/normalize.py`, `src/pdd_agent/export/docx_export.py`,
  `src/pdd_agent/export/markdown_docx.py`, `src/pdd_agent/agent/section_orchestrator.py`,
  `src/pdd_agent/llm/provider.py`, `src/pdd_agent/llm/budget.py`, `src/pdd_agent/cli.py`.
- **Out of scope:**
  - Re-ingesting the four `text/plain` corpus documents from their source PDFs in `ref/`, adding a
    normative (methodology-text) retrieval channel, resolving `[CORPUS: …]` citations against the
    index, and repairing the mojibake document stem `VCS_Ã_demis_Project-Description.norm`. These are
    real and are the next push; this plan only adds a `text/plain` extraction branch so that
    re-normalization does not destroy the records that exist.
  - Spending money on a real-model run. No task in this plan calls a paid provider. The run itself
    stays gated on explicit human authorization.
  - Regenerating the committed client-demo packages under `reports/demo-packages/`.
  - Widening `TOLERANCE` in `tests/test_registered_pdd_oracle.py`. It stays at `0.20`.
  - Leave-one-out retrieval exclusion and any diff-against-registered evaluation harness.

## Environment & Conventions

- **Stack:** Python 3.11+ (CI matrix: 3.11 and 3.12; local development has run on 3.13). Pydantic v2,
  structlog, python-docx, FastAPI, SQLite FTS5, pypdf, pdfplumber. Both `pip` and `uv` are supported;
  a committed `uv.lock` is checked in CI.
- **Setup:**
  ```bash
  pip install -e ".[dev,service,export,llm,ingest]"
  ```
  or, with uv:
  ```bash
  uv sync --locked --all-extras
  ```
  The `ingest` extra (pdfplumber) is required by PHASE-01 and is installed by CI.
- **Build / Run:** No build step. CLI entry point is `pdd-agent` (`src/pdd_agent/cli.py::main`).
  Environment diagnosis:
  ```bash
  pdd-agent doctor
  ```
- **Test:** full suite:
  ```bash
  python -m pytest -m "not corpus" -q
  ```
  single file:
  ```bash
  python -m pytest tests/test_registered_pdd_oracle.py -v
  ```
  single test:
  ```bash
  python -m pytest tests/test_registered_pdd_oracle.py::TestSocSonOracle::test_crediting_period_total_within_tolerance -v
  ```
  Tests marked `corpus` require `data/corpus/normalized/` and are excluded by `-m "not corpus"`.
  Tests must never require API keys, network access, or a running Ollama instance.
- **Lint / format gates** (both must pass; CI runs them):
  ```bash
  ruff check .
  ruff format --check .
  uv lock --check
  ```
- **Conventions & traps:**
  - Ruff, line length 100. structlog event-style logging: `logger.warning("event_name", key=value)`.
  - Pydantic v2 models for `ProjectInput` (`schemas/project_input.py`, a top-level package **outside**
    `src/`) and for the calc engine inputs (`src/pdd_agent/calc/models.py`); dataclasses elsewhere.
  - Units: waste masses in **tonnes per year (wet basis)**; emissions in **tCO2e per year**;
    electricity in **MWh per year**; grid emission factor in **tCO2/MWh**; decay rate `k` in
    **1/year**; currency USD. Mass fractions are dimensionless 0–1, never percentages.
  - Backward compatibility: six committed project configs must keep validating. Every new
    `ProjectInput` field is optional with a default that preserves today's behavior.
  - On Windows, set `PYTHONIOENCODING=utf-8` before running CLI commands whose output is piped;
    several help strings and log lines contain non-ASCII characters.
  - `data/corpus/`, `data/index/`, and `data/runs/` are gitignored. Do not commit their contents.
- **Repo map:**
  ```
  src/pdd_agent/calc/        ACM0022 + CDM tool engines, constants, dispatch to ProjectInput
  src/pdd_agent/ingest/      Drive inventory, download, normalize (PDF/DOCX -> .norm.json), bucket
  src/pdd_agent/retrieval/   FTS5 index build + search
  src/pdd_agent/agent/       SectionOrchestrator: retrieval, prompt assembly, provider calls, judging
  src/pdd_agent/llm/         Provider implementations, TokenBudget, output normalization
  src/pdd_agent/export/      DOCX export, Markdown renderer, Verra table renderers
  src/pdd_agent/review/      Rule checks, consistency checks, LLM judge, review state machine
  src/pdd_agent/service/     FastAPI section-review UI and API
  schemas/                   project_input.py (Pydantic) + pdd_section_schema.yaml (36 subsections)
  configs/projects/          Committed ProjectInput YAML files
  tests/                     pytest suite (61 files)
  ```

## Research Inputs

- From `research/2026-08-27-pdd-assembly-and-defensible-numbers-brainstorm.md`:
  - The FOD decay-rate table in `calc/constants.py` is the IPCC temperate-wet column labelled
    "wet tropical". Substituting the tropical-wet column moves the 7-year baseline methane sum from
    2,826,368 (−35.5% vs the registered 4,384,018) to about 4,126,000 (−6%), and the year-by-year
    curve then tracks the registered schedule within about 6% in every year.
  - Fixing baseline methane **alone** breaks a currently passing test: the 7-year crediting total
    moves from 4,010,142 (+5.3%) to 5,309,908 (+39.4%). The two known errors have been cancelling, so
    the baseline fix and the project-emission fix must be adopted in the same change.
  - The brainstorm hypothesised that the missing project emissions were a plastics fraction near 9%.
    **That hypothesis is refuted by the registered document** (see the next bullet block). The
    registered plastics fraction is 3.0%, exactly what the config already carries. Do not pursue it.
  - No `.norm.json` in `data/corpus/normalized/` has a `tables` key, so the registered parameter
    tables have never been machine-read; the extraction code exists and has never been run.
  - A real export echoes the section title as a misnumbered sub-heading, and the exporter's own
    subsection headings carry no number at all.
  - Section budgets are enforced only by truncating generated text; the prompt states no target
    length, and two providers pass a character count into an API parameter that counts tokens.
  - The default token budget (500,000) covers roughly ten of 36 sections at the measured rate, and
    nothing is written to disk until the whole drafting loop finishes.
- From the registered Soc Son PDD (`data/corpus/normalized/VCS_Soc_Son_Project-Description.norm.json`
  and `data/corpus/raw/verra/VCS_Soc_Son_Project-Description.pdf`), read during planning — these are
  the numbers this plan is built on:
  - Registered totals over the 7-year crediting period: baseline 6,750,431 tCO2e, project 2,942,349
    tCO2e, leakage 0, emission reductions 3,808,082 tCO2e. Per year: project emissions 420,336 tCO2e,
    baseline electricity displacement 338,059 tCO2e.
  - Registered project emissions decompose exactly as: `PE_COM,CO2 = 272,843` (Eq. 22, combustion
    efficiency 100%, 74,411.82 tonnes of fossil carbon × 44/12) + `PE_COM,CH4,N2O = 23,418` (Eq. 27)
    + `PE_FC = 3,887` (1,200 t/year of diesel) + `PE_EC = 0` (all on-site electricity is self-supplied)
    + `PE_WW = 120,187` (Eq. 28, run-off wastewater) = **420,335 tCO2e/year**.
  - Registered grid emission factor `EF_grid,CM = 0.84585 tCO2/MWh` with a 3% transmission and
    distribution loss factor; 388,050 MWh/year exported → 338,059 tCO2e/year of baseline electricity
    displacement. The committed config currently uses 0.92 tCO2/MWh and no loss factor.
  - Registered waste composition (monitoring parameter `Pn,j`, page 78 of the PDF): Paper and
    Cardboard 2.7%, Textiles 1.6%, Food waste 51.9%, Wood 0%, Garden and park waste 0%, Nappies 0%,
    Rubber and leather 1.3%, Plastic 3.0%, Metal 0.9%, Glass 0.5%, Other inert waste 38.1% — summing
    to 100.0%. The committed config omits rubber and leather and splits the residue as
    plastics 3.0% + inert 40.8%.

## Assumptions and Constraints

- **ASM-001:** IPCC climate zone is derived from `ProjectInput.location.latitude` rather than from
  measured temperature and precipitation, which the schema does not carry. — **BINDING DEFAULT:**
  `abs(latitude) <= 23.5` → tropical, otherwise temperate; wet is assumed in both cases. An explicit
  `location.climate_zone` value always wins over the derived value.
- **ASM-002:** The IPCC 2006 Volume 5 Chapter 3 Table 3.3 decay-rate values written into
  `constants.py` in PHASE-02 must be checked against the published table by the executor before the
  phase is closed. — **BINDING DEFAULT:** use the values printed in Specification S-1b; if the
  published table differs, use the published table, record the difference in the commit message, and
  re-measure every number this plan predicts.
- **ASM-003:** `PE_WW` (ACM0022 Eq. 28) is modelled as an optional declared input, not a required
  one. — **BINDING DEFAULT:** when `technology.runoff_wastewater` is absent, `PE_WW = 0` and a
  warning `runoff_wastewater absent; PE_WW assumed zero` is appended to the calc warnings.
- **ASM-004:** The ACM0022 Eq. 22 carbon table replaces the IPCC Eq. 5.1 dry-matter table for
  ACM0022 project emissions. — **BINDING DEFAULT:** keep `INCINERATION_CARBON_BY_WASTE_TYPE` and the
  functions in `calc/incineration.py` in place and still exported (other engines and existing tests
  use them), and add the Eq. 22 path alongside; ACM0022 uses the Eq. 22 path.
- **ASM-005:** Concurrency defaults to off. — **BINDING DEFAULT:** `--workers` defaults to `1`, which
  preserves today's strictly serial ordering; values above 1 are opt-in.
- **ASM-006:** Pre-flight estimation must never block a run interactively. — **BINDING DEFAULT:**
  print the estimate, and abort with a non-zero exit code and an explanatory message only when the
  estimate exceeds the configured token or cost budget; `--force-budget` overrides the abort.
- **ASM-007:** Re-normalizing the corpus changes the FTS index, and therefore changes which corpus
  excerpts future drafting runs retrieve. — **BINDING DEFAULT:** accept the change, back the previous
  normalized directory up first, and verify no document loses text blocks.
- **CON-001:** Tests must never require API keys, network access, or a running Ollama instance. All
  HTTP is mocked.
- **CON-002:** Every new `ProjectInput` field is optional with a behavior-preserving default; the six
  committed configs in `configs/projects/` and `configs/demo/` must keep validating unchanged.
- **CON-003:** Do not commit anything under `data/` (gitignored) or regenerate
  `reports/demo-packages/`.
- **DEC-001:** `TOLERANCE` in `tests/test_registered_pdd_oracle.py` stays `0.20` and is never
  widened. Residuals are recorded in `xfail` reasons with the date they were measured.
- **DEC-002:** Parameters come from a cited source — the registered PDD, ACM0022 v03.0, or a named
  IPCC table — never from fitting the engine to the oracle. If a sourced parameter produces a worse
  residual than an unsourced one, the sourced parameter wins and the residual is recorded.
- **DEC-003:** Baseline methane (climate zone) and project emissions (Eq. 22/27/28) are adopted for
  Soc Son in the **same** phase (PHASE-04), because adopting either alone moves the crediting total
  outside tolerance.
- **DEC-004:** Inegol (`configs/demo/inegol_project_input.yaml`, latitude 40.1505) resolves to the
  temperate-wet zone, whose values are exactly today's constants, so its numbers must not move.

## Specification

### S-1. Baseline methane with an explicit climate zone

**S-1a. The model (unchanged, CDM Tool 04 v08.0 Equation 2, Application B)**

```
BE_CH4,y = φ × (1 − f) × GWP_CH4 × (1 − OX) × (16/12) × F × DOC_f × MCF
           × Σ_j Σ_{x=1..y} [ W_j,x × DOC_j × e^(−k_j (y − x)) × (1 − e^(−k_j)) ]
```

- `BE_CH4,y` — baseline methane from the solid waste disposal site in crediting year `y`, tCO2e/year.
- `φ` — model correction factor, dimensionless, default 0.9.
- `f` — fraction of methane captured at the baseline site, dimensionless 0–1, default 0.0.
- `GWP_CH4` — global warming potential of methane, tCO2e per tCH4 (repo constant).
- `OX` — oxidation factor in cover material, dimensionless, default 0.0.
- `16/12` — molecular weight ratio, tCH4 per tC.
- `F` — volume fraction of methane in landfill gas, dimensionless, default 0.5.
- `DOC_f` — fraction of degradable organic carbon that decomposes, dimensionless, default 0.5.
- `MCF` — methane correction factor for the site type, dimensionless, default 1.0.
- `W_j,x` — tonnes of waste type `j` diverted from the site in year `x`, wet basis.
- `DOC_j` — degradable organic carbon fraction of waste type `j`, wet basis, dimensionless.
- `k_j` — decay rate of waste type `j`, 1/year. **This is the only quantity this plan changes.**
- `y`, `x` — 1-based crediting-period years.

**S-1b. Decay rates by IPCC climate zone (IPCC 2006 Vol.5 Ch.3 Table 3.3, 1/year)**

| waste type key | `boreal_temperate_dry` | `boreal_temperate_wet` | `tropical_dry` | `tropical_wet` |
|---|---|---|---|---|
| `paper_cardboard` | 0.04 | 0.06 | 0.045 | 0.07 |
| `textiles` | 0.04 | 0.06 | 0.045 | 0.07 |
| `wood` | 0.02 | 0.03 | 0.025 | 0.035 |
| `garden_waste` | 0.05 | 0.10 | 0.065 | 0.17 |
| `nappies` | 0.05 | 0.10 | 0.065 | 0.17 |
| `rubber_leather` | 0.04 | 0.06 | 0.045 | 0.07 |
| `food_waste` | 0.06 | 0.185 | 0.085 | 0.40 |
| `municipal_solid_waste` (bulk) | 0.05 | 0.09 | 0.065 | 0.17 |

The `boreal_temperate_wet` column is byte-identical to today's `DECAY_RATE_BY_WASTE_TYPE`, which is
why Inegol's numbers must not move (DEC-004). Per ASM-002 the executor verifies this table against
the published source before closing PHASE-02.

**S-1c. Zone resolution order (first match wins)**

1. `WasteStream.decay_rate_override` (already exists) — per stream.
2. `ACM0022CalcInput.climate_zone`, when not `None` — looked up in the S-1b table.
3. `DECAY_RATE_BY_WASTE_TYPE` — the legacy table, retained as an alias of `boreal_temperate_wet`.

**S-1d. Deriving the zone from a project (applied in PHASE-04, not PHASE-02)**

1. If `ProjectInput.location.climate_zone` is set, use it verbatim.
2. Else if `abs(ProjectInput.location.latitude) <= 23.5`, use `tropical_wet`.
3. Else use `boreal_temperate_wet`.

`DOC_j` values are climate-independent and are **not** changed by this plan.

### S-2. Project emissions the way ACM0022 defines them

**S-2a. Structure (ACM0022 v03.0 Equations 17 and 20)**

```
PE_y   = PE_COMP,y + PE_AD,y + PE_GAS,y + PE_RDF_SB,y + PE_INC,y            [Eq. 17]
PE_INC,y = PE_COM,INC,y + PE_EC,INC,y + PE_FC,INC,y + PE_WW,INC,y            [Eq. 20]
```

- `PE_COM` — CO2, CH4 and N2O from combusting the waste itself.
- `PE_EC` — grid electricity consumed by the project (already modelled; zero when self-supplied).
- `PE_FC` — fossil fuel combusted by the project (already modelled; currently never populated).
- `PE_WW` — run-off wastewater treated anaerobically (**not modelled today**).

**S-2b. Fossil CO2 from combustion (Equation 22)**

```
PE_COM,CO2,y = EFF_COM,y × (44/12) × Σ_j ( Q_j,y × FCC_j × FFC_j )
```

- `PE_COM,CO2,y` — tCO2/year.
- `EFF_COM,y` — combustion efficiency of the combustor, dimensionless 0–1; registered value 1.00.
- `44/12` — tCO2 per tC.
- `Q_j,y` — tonnes of fresh waste type `j` fed to the combustor in year `y`, wet basis, equal to
  `annual_waste_throughput × mass_fraction_j`.
- `FCC_j` — fraction of total carbon in waste type `j`, **tC per tonne of wet waste**.
- `FFC_j` — fraction of that carbon which is fossil, dimensionless 0–1.

Note the difference from the IPCC Eq. 5.1 form currently implemented in `calc/incineration.py`:
Eq. 22 has **no dry-matter term**, and its `FCC` is expressed per tonne of wet waste.

**S-2c. The Equation 22 carbon table (ACM0022 v03.0 pages 42–43, as applied by the registered PDD)**

| waste type key | `FCC` (tC/t wet waste) | `FFC` (fossil share of carbon) |
|---|---|---|
| `paper_cardboard` | 0.50 | 0.05 |
| `textiles` | 0.50 | 0.50 |
| `food_waste` | 0.50 | 0.00 |
| `wood` | 0.54 | 0.00 |
| `garden_waste` | 0.55 | 0.00 |
| `nappies` | 0.90 | 0.10 |
| `rubber_leather` | 0.67 | 0.20 |
| `plastics` | 0.85 | 1.00 |
| `metal` | 0.00 | 0.00 |
| `glass` | 0.00 | 0.00 |
| `inert` (other, inert waste) | 0.05 | 1.00 |
| `municipal_solid_waste` (bulk fallback) | 0.20 | 0.30 |

The bulk `municipal_solid_waste` row has no registered counterpart (the registered PDD always sorts
into types); it is a documented fallback so that projects declaring only a bulk waste type still get
a non-zero, conservative `PE_COM,CO2`. Mark it as such in a code comment.

Worked check with the registered composition and 1,460,000 t/year:
`Σ Q_j × FCC_j × FFC_j` = 985.50 (paper) + 5,840.00 (textiles) + 2,543.32 (rubber and leather)
+ 37,230.00 (plastic) + 27,813.00 (other inert) = **74,411.82 tC fossil**, and
`74,411.82 × 44/12 × 1.00` = **272,843 tCO2/year**.

**S-2d. CH4 and N2O from combustion (Equation 27, Option 2)**

```
PE_COM,CH4,N2O,y = Q_waste,y × ( EF_N2O × GWP_N2O + EF_CH4 × GWP_CH4 )
```

- `Q_waste,y` — total tonnes of fresh waste combusted in year `y`.
- `EF_N2O` — tN2O per tonne of waste; registered value `1.21 × 50 × 10^-6 = 6.05e-5`.
- `EF_CH4` — tCH4 per tonne of waste; registered value `1.21 × 0.2 × 10^-6 = 2.42e-7`
  (continuous stoker incinerator).
- `GWP_N2O` — 265 tCO2e per tN2O (AR5; already in `constants.py`).
- `GWP_CH4` — 28 tCO2e per tCH4 (AR5; already in `constants.py`).

Worked check: `1,460,000 × (6.05e-5 × 265 + 2.42e-7 × 28) = 23,418 tCO2e/year`.

**S-2e. Run-off wastewater (Equation 28)**

```
PE_WW,y = Q_ww,y × P_COD,y × B_o × MCF_ww × GWP_CH4
```

- `Q_ww,y` — cubic metres of run-off wastewater treated anaerobically or released untreated per year.
- `P_COD,y` — chemical oxygen demand, **tCOD per m3**.
- `B_o` — maximum methane producing capacity, tCH4 per tCOD; default 0.25.
- `MCF_ww` — methane conversion factor of the treatment system, dimensionless 0–1; default 0.8.
- `GWP_CH4` — 28 tCO2e per tCH4.

Worked check: `613,200 × 0.035 × 0.25 × 0.8 × 28 = 120,187 tCO2e/year`.

**S-2f. Composition of the new PE_INC**

```
PE_INC,y = PE_COM,CO2,y + PE_COM,CH4,N2O,y + PE_EC,y + PE_FC,y + PE_WW,y
```

`PE_EC` and `PE_FC` already exist as separate components in `ACM0022Calculator.calculate()`; keep
them as their own components and do **not** double count them inside `PE_INC`. The engine reports
each term as its own `EmissionComponent`, and `project_emissions_tco2e` remains their sum.

### S-3. Document assembly rules

Applied in the exporter, in this order, per subsection:

1. The exporter writes the subsection heading as `"{sub_section_id} {heading}"` at Word Heading
   level 2 — for example `4.1 Baseline Emissions`, `1.10 Project Scale and Estimated GHG Emission
   Reductions or Removals`. Section-level (level 1) headings keep their existing format
   (`"{section_id} {CANONICAL HEADING}"`).
2. Before rendering a section body, strip a **leading title-echo heading**: the first non-blank line
   of the body is removed when it is an ATX heading (`^#{1,6}\s+`) whose text, after removing any
   leading numeric label matching `^\d+(\.\d+)*\.?\s*` and lowercasing and collapsing whitespace,
   equals the canonical subsection heading treated the same way. Only the first heading line is ever
   removed, and only when it matches; nothing else is touched.
3. Remaining Markdown headings in the body continue to be demoted by the existing renderer
   (`markdown_docx._render_blocks` maps `#` → Word Heading 3, capped at Heading 4).

### S-4. Section length contract

1. `SectionOrchestrator._build_prompt` appends a `## Length Budget` block stating the resolved budget
   in characters and the instruction: aim for 60–90% of the budget, never pad to reach it, and never
   exceed it.
2. Providers convert the character budget into an output-token ceiling:
   ```
   max_tokens = min( config.max_tokens, ceil( max_chars / 3.5 × 1.15 ) )
   ```
   - `3.5` — assumed characters per token for English technical prose.
   - `1.15` — 15% headroom so a section that lands slightly long is not cut mid-sentence.
   - `config.max_tokens` — the provider-level hard ceiling, raised from 4,000 to 16,000.
3. Post-generation truncation at `max_chars` stays exactly as it is, including the `TRUNCATED:` issue
   and the one-step confidence downgrade.

### S-5. Document-level coherence checks

Run over the assembled run record, not over one section:

1. **NUMBER_DISAGREEMENT** — for each distinct quantity expressed in tCO2e that appears in two or
   more sections, flag when the largest and smallest differ by more than 1% of the largest. Compare
   only numbers followed within 30 characters by `tCO2e`, `tCO2-e`, or `tCO2`.
2. **CALC_DISAGREEMENT** — flag any tCO2e number in a section that is within 30 characters of the
   words `baseline`, `project emissions`, or `net`, and that differs by more than 5% from the
   corresponding value in the run's stored `calc_result`.
3. **DUPLICATE_BODY** — flag any pair of sections whose normalized bodies (lowercased, whitespace
   collapsed) have a `difflib.SequenceMatcher` ratio of 0.90 or higher.
4. **DANGLING_CROSS_REFERENCE** — flag any `Section N.M` reference whose `N.M` is not a
   `sub_section_id` in `schemas/pdd_section_schema.yaml`.
5. **TITLE_ECHO** — flag any section body still starting with a heading that restates its canonical
   title (the S-3 step 2 predicate), which indicates the assembly pass was bypassed.

Severity: `CALC_DISAGREEMENT` and `NUMBER_DISAGREEMENT` are `HIGH`; the rest are `ADVISORY`. None of
them hard-blocks export.

### S-6. Run survivability

1. **Pre-flight estimate.** Before the first provider call:
   ```
   estimated_input_tokens  = sections × avg_prompt_chars / 3.5
   estimated_output_tokens = Σ_sections ( section_budget_chars / 3.5 )
   estimated_cost_usd      = price(model, provider) applied to the two totals
   ```
   `avg_prompt_chars` is measured by building the prompt for every section that will be drafted, so
   the estimate costs nothing. Add a `provider_overhead_tokens_per_section` term, default 25,000 for
   the `claude-code` provider and 0 for every other provider, to account for CLI harness overhead.
2. **Checkpointing.** After every section completes (including judge and redraft), write the whole
   run record to `data/runs/{run_id}.json` via a temporary file in the same directory followed by
   `os.replace`, so a partially written file is never observable.
3. **Resume.** With `--resume`, load `data/runs/{run_id}.json` if it exists and skip any section
   whose stored text is non-empty and does not start with `[PLACEHOLDER` or `[BUDGET EXHAUSTED`.
4. **Concurrency.** With `--workers N` (N > 1), draft sections through a
   `concurrent.futures.ThreadPoolExecutor` with `max_workers=N`, preserving canonical schema order in
   the stored run record regardless of completion order. `TokenBudget.record`, `check_budget`, and
   the checkpoint write are serialized with a single `threading.Lock`.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Re-normalize the corpus so extracted tables exist, without destroying the four text-sourced documents | None | `text/plain` extraction branch, `tables` in every `.norm.json`, table lookup helper |
| PHASE-02 | Climate-zone decay rates as a mechanism, with today's behavior unchanged by default | None | Zone table + resolver in `calc/`, `climate_zone` on the calc input and on `ProjectLocation` |
| PHASE-03 | Model ACM0022 project emissions the way the methodology defines them | None | Eq. 22 / Eq. 27 / Eq. 28 implementations, new optional `ProjectInput` fields, dispatch mapping |
| PHASE-04 | Adopt the registered parameters for Soc Son and re-measure both oracles together | PHASE-01, PHASE-02, PHASE-03 | Corrected config, derived zone in dispatch, re-measured oracle tests |
| PHASE-05 | Own the assembled document: numbering, title echo, length contract, coherence checks | None | `export/assembly.py`, `review/document_coherence.py`, prompt length block, token conversion |
| PHASE-06 | Make a real 36-section run survivable | PHASE-05 (prompt changes affect the estimate) | Pre-flight estimate, checkpointing, `--resume`, `--workers`, CLI budget flags |

## Detailed Phases

### PHASE-01 - Re-normalize the Corpus So Extracted Tables Exist

**Goal**
Give every normalized corpus document a `tables` key produced by the existing pdfplumber path, add a
`text/plain` extraction branch so re-normalization cannot destroy the four documents that were
ingested from pre-extracted text, and provide a small helper for reading a registered parameter table
out of a normalized record.

**Tasks**
- [ ] TASK-01-01: Install the `ingest` extra and confirm pdfplumber imports:
      `python -c "import pdfplumber; print(pdfplumber.__version__)"`.
- [ ] TASK-01-02: Back up the current normalized corpus before touching it:
      `python -c "import shutil; shutil.copytree('data/corpus/normalized','data/corpus/normalized.bak')"`
      (the directory is gitignored; this form works on Windows, macOS and Linux alike).
- [ ] TASK-01-03: Add `_extract_plain_text(path: Path, dry_run: bool = False) -> dict[str, Any]` to
      `src/pdd_agent/ingest/normalize.py`, reading the file as UTF-8 with `errors="replace"`, splitting
      on lines, and reusing `_build_headings_and_blocks(lines)` for headings and text blocks. It
      returns the same shape as `_extract_pdf` with `"tables": []` and `"page_count": 1`.
- [ ] TASK-01-04: Wire a `text/plain` branch into `_extract_text` alongside the PDF and DOCX branches.
      Leave the "Unsupported MIME type" fallback in place for every other MIME type.
- [ ] TASK-01-05: Re-normalize the corpus:
      `PYTHONIOENCODING=utf-8 pdd-agent normalize --manifest data/corpus/manifest.jsonl`.
- [ ] TASK-01-06: Rebuild the retrieval index:
      `pdd-agent build-index --corpus-dir data/corpus/normalized --index-db data/index/corpus.fts.db`,
      then record `pdd-agent index-report` output in the commit message.
- [ ] TASK-01-07: Create `src/pdd_agent/ingest/table_lookup.py` with `find_tables()` and
      `table_rows_as_pairs()` per the Function Signatures below.
- [ ] TASK-01-08: Add `tests/test_table_lookup.py` covering the specs below, using an inline fixture
      dict written to `tmp_path` — the tests must not require the real corpus and must not carry the
      `corpus` marker.
- [ ] TASK-01-09: Add a `corpus`-marked test in `tests/test_normalize.py` asserting that every file in
      `data/corpus/normalized/*.norm.json` has a `tables` key and at least 2 text blocks.

**File Changes**
- `src/pdd_agent/ingest/normalize.py` (modify): add `_extract_plain_text` and the `text/plain` branch
  in `_extract_text`. Do not change `_extract_pdf`, `_extract_tables`, `_build_headings_and_blocks`,
  `_sanitize_for_json`, or the manifest rewrite logic.
- `src/pdd_agent/ingest/table_lookup.py` (create): table lookup helpers, no third-party imports beyond
  the standard library and structlog.
- `tests/test_table_lookup.py` (create): unit tests against a temporary normalized record.
- `tests/test_normalize.py` (modify): append the `corpus`-marked corpus-shape test; leave existing
  tests unchanged.

**Function Signatures**
- `_extract_plain_text(path: Path, dry_run: bool = False) -> dict[str, Any]` — returns
  `{"parseable", "pages", "text", "headings", "text_blocks", "tables", "page_count"}` for a UTF-8 text
  file, with `tables` always `[]`.
- `find_tables(document_stem: str, must_contain: Sequence[str], normalized_dir: Path | None = None) -> list[dict[str, Any]]`
  — returns every extracted table of that document whose flattened cell text contains **all** of the
  `must_contain` strings, case-insensitively; each entry is `{"page": int, "table_index": int, "rows": list[list[str]]}`.
  Returns `[]` when the document, its file, or its `tables` key is missing.
- `table_rows_as_pairs(table: dict[str, Any], key_column: int = 0, value_column: int = 1) -> list[tuple[str, str]]`
  — returns `(key, value)` pairs of stripped cell text for rows that have non-empty cells in both
  columns, skipping rows whose key cell is empty.

**Test Specs**
- `find_tables("doc_a", ["Paper", "%"], normalized_dir=tmp)` where `tmp/doc_a.norm.json` has
  `tables: [{"page": 3, "table_index": 0, "rows": [["Waste type", "Pn,j"], ["Paper and Cardboard", "2.7 %"]]}]`
  → a one-element list whose `["rows"][1][1] == "2.7 %"`.
- `find_tables("doc_a", ["Textiles"], normalized_dir=tmp)` with the same fixture → `[]`.
- `find_tables("missing_doc", ["x"], normalized_dir=tmp)` → `[]` and no exception raised.
- `table_rows_as_pairs({"rows": [["Waste type", "Pn,j"], ["Food waste", "51.9 %"], ["", ""]]})` →
  `[("Waste type", "Pn,j"), ("Food waste", "51.9 %")]`.
- `_extract_plain_text(tmp_path / "a.txt")` where the file contains
  `"1. INTRODUCTION\nbody text\n2. SCOPE\nmore text\n"` → `heading` count 2 and `text_blocks` length 3
  (the leading empty block plus one per heading), `tables == []`.

**Dependencies**
- pdfplumber (the `ingest` extra) must be installed for TASK-01-05 to populate `tables`.

**Exit Criteria**
- [ ] `python -c "import json,glob; print(sum('tables' in json.load(open(p,encoding='utf-8')) for p in glob.glob('data/corpus/normalized/*.norm.json')))"`
      prints `17`.
- [ ] `python -c "import json; d=json.load(open('data/corpus/normalized/VCS_Soc_Son_Project-Description.norm.json',encoding='utf-8')); print(len(d['tables']))"`
      prints a number greater than 50.
- [ ] `python -c "import json,glob; print(min(len(json.load(open(p,encoding='utf-8'))['text_blocks']) for p in glob.glob('data/corpus/normalized/*.norm.json')))"`
      prints a number greater than 1 (the four text-sourced documents no longer collapse to a single
      block).
- [ ] `pdd-agent index-report` prints `Reachable rows:` at least 889 and `Reachable documents:` at
      least 13.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failures.

**Phase Risks**
- **RISK-01-01:** Re-normalization overwrites `data/corpus/normalized/` in place. Mitigation:
  TASK-01-02's backup, plus the text-block exit criterion, which fails loudly if any document
  regresses.
- **RISK-01-02:** pdfplumber table extraction is slow on large PDFs (measured at roughly 0.12 seconds
  per page; the 17-document corpus is a few minutes). Mitigation: none needed — run it once and
  record the wall-clock time in the commit message.

### PHASE-02 - Climate-Zone Decay Rates as a Mechanism

**Goal**
Make the FOD decay rate resolvable from an IPCC climate zone, with a resolution order that leaves
every existing project's numbers untouched until a zone is explicitly declared.

**Tasks**
- [ ] TASK-02-01: Add `DECAY_RATE_BY_CLIMATE_ZONE: dict[str, dict[str, float]]` to
      `src/pdd_agent/calc/constants.py` with the four zones and eight waste-type keys from
      Specification S-1b, each entry cited in a comment as IPCC 2006 Vol.5 Ch.3 Table 3.3.
- [ ] TASK-02-02: Redefine `DECAY_RATE_BY_WASTE_TYPE` as
      `DECAY_RATE_BY_CLIMATE_ZONE["boreal_temperate_wet"]` and correct its misleading
      "wet tropical" comment to say it is the boreal/temperate wet column retained as the default.
- [ ] TASK-02-03: Add `climate_zone: str | None = None` to `methane_from_swds()` in
      `src/pdd_agent/calc/cdm_tool_04.py` and implement the S-1c resolution order. An unknown zone
      name raises `ValueError` naming the four valid zones.
- [ ] TASK-02-04: Add `climate_zone: str | None` to `ACM0022CalcInput` in
      `src/pdd_agent/calc/models.py`, with a description naming the four valid values and stating that
      `None` means the legacy default table.
- [ ] TASK-02-05: Pass `climate_zone=self._inp.climate_zone` from the `methane_from_swds` call in
      `ACM0022Calculator.calculate()` (`src/pdd_agent/calc/acm0022.py`). Change nothing else in that
      method.
- [ ] TASK-02-06: Add `climate_zone` as an optional `Literal` field on `ProjectLocation` in
      `schemas/project_input.py`, defaulting to `None`.
- [ ] TASK-02-07: Add `climate_zone_for(latitude: float, declared: str | None = None) -> str` to
      `src/pdd_agent/calc/constants.py` implementing S-1d. Do **not** call it from `dispatch.py` yet —
      PHASE-04 wires it in.
- [ ] TASK-02-08: In `src/pdd_agent/calc/dispatch.py::_map_acm0022`, pass
      `pi.location.climate_zone` through to `mapped["climate_zone"]` only when it is not `None`.
- [ ] TASK-02-09: Add `tests/test_climate_zone.py` with the specs below.
- [ ] TASK-02-10: Document the zone mechanism in the "Quantification precedence" subsection of
      `README.md`: what the zones are, how one is chosen, and that an undeclared zone keeps the
      boreal/temperate wet defaults.

**File Changes**
- `src/pdd_agent/calc/constants.py` (modify): add `DECAY_RATE_BY_CLIMATE_ZONE` and
  `climate_zone_for`; redefine `DECAY_RATE_BY_WASTE_TYPE` as an alias. Leave `DOC_BY_WASTE_TYPE`,
  `INCINERATION_CARBON_BY_WASTE_TYPE`, and every other constant unchanged.
- `src/pdd_agent/calc/cdm_tool_04.py` (modify): add the `climate_zone` parameter and the resolution
  order in `methane_from_swds`. Leave `methane_from_swds_simplified` unchanged.
- `src/pdd_agent/calc/models.py` (modify): add `climate_zone` to `ACM0022CalcInput`.
- `src/pdd_agent/calc/acm0022.py` (modify): forward `climate_zone` into the `methane_from_swds` call.
- `src/pdd_agent/calc/dispatch.py` (modify): forward a declared `location.climate_zone` into the
  mapped engine inputs.
- `schemas/project_input.py` (modify): add `climate_zone` to `ProjectLocation`.
- `tests/test_climate_zone.py` (create): unit tests for the table, the resolver, and the no-op default.
- `README.md` (modify): extend "Quantification precedence".

**Function Signatures**
- `climate_zone_for(latitude: float, declared: str | None = None) -> str` — returns one of
  `"tropical_wet"`, `"tropical_dry"`, `"boreal_temperate_wet"`, `"boreal_temperate_dry"`; returns
  `declared` unchanged when it is a valid zone name.
- `methane_from_swds(waste_type: str, annual_waste_tonnes: float, year: int, crediting_start_year: int = 1, doc_override: float | None = None, decay_rate_override: float | None = None, model_correction_factor: float = MODEL_CORRECTION_FACTOR_DEFAULT, baseline_capture_fraction: float = 0.0, mcf: float = MCF_DEFAULT, oxidation_factor: float = OX_DEFAULT, doc_f: float = DOC_F_DEFAULT, f_ch4: float = F_CH4_DEFAULT, climate_zone: str | None = None) -> float`
  — unchanged return: baseline methane for one waste stream in one crediting year, tCO2e.

**Test Specs**
- `climate_zone_for(21.261)` → `"tropical_wet"`; `climate_zone_for(40.1505)` → `"boreal_temperate_wet"`;
  `climate_zone_for(40.1505, declared="tropical_dry")` → `"tropical_dry"`;
  `climate_zone_for(-23.4)` → `"tropical_wet"`; `climate_zone_for(23.6)` → `"boreal_temperate_wet"`.
- `DECAY_RATE_BY_CLIMATE_ZONE["boreal_temperate_wet"] == DECAY_RATE_BY_WASTE_TYPE` → `True`.
- `DECAY_RATE_BY_CLIMATE_ZONE["tropical_wet"]["food_waste"]` → `0.40`.
- `methane_from_swds("food_waste", 1000.0, 1, climate_zone="tropical_wet")` is greater than
  `methane_from_swds("food_waste", 1000.0, 1)` by a factor between 2.0 and 2.5.
- `methane_from_swds("food_waste", 1000.0, 1, decay_rate_override=0.1, climate_zone="tropical_wet")`
  equals `methane_from_swds("food_waste", 1000.0, 1, decay_rate_override=0.1)` — the per-stream
  override wins over the zone.
- `methane_from_swds("food_waste", 1000.0, 1, climate_zone="atlantis")` raises `ValueError` whose
  message contains all four valid zone names.
- `compute_for(ProjectInput)` for `configs/projects/vietnam_socson_from_sheet.yaml` and
  `configs/demo/inegol_project_input.yaml` returns the same `crediting_period_total_tco2e` as before
  this phase (no config declares a zone yet).

**Dependencies**
- None.

**Exit Criteria**
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failures and the same 4 xfails as before.
- [ ] `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` still prints a
      crediting-period total of 4,010,142 tCO2e (behavior is unchanged in this phase).
- [ ] `ruff check . && ruff format --check .` pass.

**Phase Risks**
- **RISK-02-01:** Redefining `DECAY_RATE_BY_WASTE_TYPE` as an alias makes it mutable shared state; a
  test that mutates it would silently corrupt the zone table. Mitigation: build the alias with
  `dict(DECAY_RATE_BY_CLIMATE_ZONE["boreal_temperate_wet"])` so it is a copy, and assert equality (not
  identity) in the test spec above.
- **RISK-02-02:** ASM-002 — the published table may differ from S-1b. Mitigation: verify before
  closing the phase; if it differs, use the published values and re-measure PHASE-04's predictions.

### PHASE-03 - Model ACM0022 Project Emissions the Way the Methodology Defines Them

**Goal**
Implement Equations 22, 27 and 28 with parameters the methodology publishes, populate `PE_FC` from
`ProjectInput`, and leave the existing IPCC Eq. 5.1 helpers in place for other callers.

**Tasks**
- [ ] TASK-03-01: Add `ACM0022_CARBON_BY_WASTE_TYPE: dict[str, dict[str, float]]` to
      `src/pdd_agent/calc/constants.py` with the `FCC`/`FFC` pairs from Specification S-2c, each cited
      as ACM0022 v03.0 pages 42–43, and the bulk `municipal_solid_waste` row commented as a documented
      fallback with no registered counterpart.
- [ ] TASK-03-02: Add `EF_N2O_INCINERATION_T_PER_TONNE = 6.05e-5` and
      `EF_CH4_INCINERATION_T_PER_TONNE = 2.42e-7` and `B_O_DEFAULT_T_CH4_PER_T_COD = 0.25` and
      `MCF_WASTEWATER_DEFAULT = 0.8` to `src/pdd_agent/calc/constants.py`, each with its ACM0022 page
      citation. Leave `EF_N2O_INCINERATION_KG_PER_TONNE` in place for the existing Eq. 5.1 path.
- [ ] TASK-03-03: Add `combustion_co2_eq22()`, `combustion_ch4_n2o_eq27()`, and `wastewater_ch4_eq28()`
      to `src/pdd_agent/calc/incineration.py` per the Function Signatures below. Do not modify
      `incineration_co2`, `incineration_n2o`, or `incineration_emissions`.
- [ ] TASK-03-04: Add to `ACM0022CalcInput` (`src/pdd_agent/calc/models.py`):
      `combustion_efficiency: float = 1.0` (ge=0, le=1),
      `runoff_wastewater_m3_per_year: float = 0.0` (ge=0),
      `runoff_wastewater_cod_t_per_m3: float = 0.0` (ge=0),
      `wastewater_bo_t_ch4_per_t_cod: float = 0.25` (gt=0),
      `wastewater_mcf: float = 0.8` (ge=0, le=1).
- [ ] TASK-03-05: In `ACM0022Calculator.calculate()` (`src/pdd_agent/calc/acm0022.py`), replace the
      `PE_INC` component with three components computed from `incineration_streams` **plus the
      degradable `waste_streams`** (Eq. 22 charges every combusted waste type, not only the unmapped
      ones): `PE_COM_CO2 (fossil carbon in combusted waste)`, `PE_COM_CH4_N2O (combustion CH4 + N2O)`,
      and `PE_WW (run-off wastewater)`. Keep the existing `PE_EC`, `PE_FC`, `PE_CH4` and `PE_FLARE`
      components untouched, and keep `project_emissions_tco2e` as the sum of all project components.
- [ ] TASK-03-06: Add `AuxiliaryFuel` and `RunoffWastewater` models to `schemas/project_input.py` and
      optional fields `technology.auxiliary_fossil_fuel: list[AuxiliaryFuel]` (default empty) and
      `technology.runoff_wastewater: RunoffWastewater | None` (default `None`).
- [ ] TASK-03-07: Add `quantification.grid_tdl_factor: float | None` (ge=0, le=0.3, default `None`) to
      `schemas/project_input.py`.
- [ ] TASK-03-08: In `src/pdd_agent/calc/dispatch.py::_map_acm0022`, map the new inputs:
      `fossil_fuels` from `technology.auxiliary_fossil_fuel`, the four wastewater scalars from
      `technology.runoff_wastewater`, and `tdl_factor` from `quantification.grid_tdl_factor`. Append a
      warning `runoff_wastewater absent; PE_WW assumed zero` when the wastewater block is missing and
      `technology_type == "incineration_with_energy_recovery"`.
- [ ] TASK-03-09: In the same function, stop treating unmapped composition entries as the *only*
      incineration streams: emit an incineration stream for **every** composition entry when
      `technology_type == "incineration_with_energy_recovery"`, keeping the existing behavior that
      only `DOC_BY_WASTE_TYPE` entries also become `waste_streams`. Preserve the existing per-entry
      warnings.
- [ ] TASK-03-10: Extend `tests/test_incineration.py` with the Eq. 22 / 27 / 28 specs below and add
      dispatch-mapping specs to `tests/test_calc_dispatch.py`.
- [ ] TASK-03-11: Update the "Quantification precedence" subsection of `README.md` to describe the
      three new project-emission terms and the new optional input blocks.

**File Changes**
- `src/pdd_agent/calc/constants.py` (modify): add the Eq. 22 carbon table, the Eq. 27 emission
  factors, and the Eq. 28 defaults.
- `src/pdd_agent/calc/incineration.py` (modify): add three functions; leave the existing three intact
  and exported.
- `src/pdd_agent/calc/models.py` (modify): add five fields to `ACM0022CalcInput`.
- `src/pdd_agent/calc/acm0022.py` (modify): replace the single `PE_INC` component with the three new
  components; update the module docstring's equation list to name Eq. 20/22/27/28.
- `schemas/project_input.py` (modify): add `AuxiliaryFuel`, `RunoffWastewater`, two technology fields,
  one quantification field. Leave every existing field and validator unchanged.
- `src/pdd_agent/calc/dispatch.py` (modify): map the new fields; broaden incineration-stream mapping.
- `tests/test_incineration.py`, `tests/test_calc_dispatch.py` (modify): add the new specs.
- `README.md` (modify): extend "Quantification precedence".

**Function Signatures**
- `combustion_co2_eq22(streams: list[dict[str, object]], combustion_efficiency: float = 1.0) -> float`
  — fossil CO2 in tCO2/year from `Σ Q_j × FCC_j × FFC_j × EFF × 44/12`; unknown waste types
  contribute 0 and log `acm0022_carbon_waste_type_unknown`.
- `combustion_ch4_n2o_eq27(total_tonnes: float, ef_n2o_t_per_tonne: float = EF_N2O_INCINERATION_T_PER_TONNE, ef_ch4_t_per_tonne: float = EF_CH4_INCINERATION_T_PER_TONNE) -> float`
  — combustion CH4 and N2O in tCO2e/year.
- `wastewater_ch4_eq28(volume_m3_per_year: float, cod_t_per_m3: float, bo_t_ch4_per_t_cod: float = B_O_DEFAULT_T_CH4_PER_T_COD, mcf: float = MCF_WASTEWATER_DEFAULT) -> float`
  — run-off wastewater methane in tCO2e/year; returns `0.0` when volume or COD is zero.
- `AuxiliaryFuel` — Pydantic model with `fuel_type: str`, `annual_tonnes: float` (ge=0),
  `ncv_gj_per_tonne: float | None`, `ef_tco2_per_gj: float | None`, `source: str`.
- `RunoffWastewater` — Pydantic model with `annual_volume_m3: float` (ge=0),
  `cod_t_per_m3: float` (ge=0), `bo_t_ch4_per_t_cod: float = 0.25`, `mcf: float = 0.8`,
  `source: str`.

**Test Specs**
- `combustion_co2_eq22([{ "waste_type": "plastics", "annual_tonnes": 43800.0 }])` → `136,510.0`
  tCO2 ± 1.0 (`43,800 × 0.85 × 1.00 × 44/12`).
- `combustion_co2_eq22` over the full registered composition at 1,460,000 t/year — paper 39,420 t,
  textiles 23,360 t, food 757,740 t, rubber and leather 18,980 t, plastics 43,800 t, metal 13,140 t,
  glass 7,300 t, inert 556,260 t — → `272,843` tCO2 ± 50 (matching the registered PDD).
- `combustion_co2_eq22([{"waste_type": "food_waste", "annual_tonnes": 1000.0}])` → `0.0` (FFC is zero).
- `combustion_co2_eq22([{"waste_type": "unobtainium", "annual_tonnes": 1000.0}])` → `0.0`, no raise.
- `combustion_ch4_n2o_eq27(1_460_000.0)` → `23,418` tCO2e ± 5.
- `wastewater_ch4_eq28(613_200.0, 0.035)` → `120,187` tCO2e ± 5.
- `wastewater_ch4_eq28(0.0, 0.035)` → `0.0`.
- `ACM0022CalcInput` built with no wastewater fields → the calc result contains a `PE_WW` component
  with `value_tco2e == 0.0`.
- `_map_acm0022` for a config with `technology_type == "incineration_with_energy_recovery"` and no
  `runoff_wastewater` → warnings contain `runoff_wastewater absent; PE_WW assumed zero`.
- `_map_acm0022` for `configs/demo/inegol_project_input.yaml` (no composition declared) → produces no
  incineration streams, and `compute_for` returns the same `crediting_period_total_tco2e` as before
  this phase.

**Dependencies**
- None. This phase changes ACM0022's project-emission arithmetic for any project that declares a waste
  composition; today that is only `configs/projects/vietnam_socson_from_sheet.yaml`.

**Exit Criteria**
- [ ] `python -m pytest tests/test_incineration.py tests/test_calc_dispatch.py -q` reports 0 failures.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failures; the Soc Son oracle tests may change
      status in this phase and their `xfail` reasons are updated in PHASE-04, not here.
- [ ] `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` lists `PE_COM_CO2`,
      `PE_COM_CH4_N2O`, and `PE_WW` as separate components.
- [ ] `ruff check . && ruff format --check .` pass.

**Phase Risks**
- **RISK-03-01:** TASK-03-09 broadens which streams are charged for combustion, which increases
  project emissions for any composition-declaring project. That is the intended correction (the
  methodology charges fossil carbon in *all* combusted waste), but it must not silently double count:
  assert in a test that a waste type appearing in both `waste_streams` and `incineration_streams`
  contributes to `BE_CH4` and to `PE_COM_CO2` exactly once each.
- **RISK-03-02:** If the Soc Son oracle's currently passing crediting-total test fails at the end of
  this phase, that is expected (DEC-003) and is resolved in PHASE-04. Do not tune anything here; if
  the phase must be committed separately, mark that one test `xfail` with the measured value and the
  note `resolved in PHASE-04`.

### PHASE-04 - Adopt the Registered Parameters and Re-Measure Both Oracles

**Goal**
Apply the registered PDD's own published inputs to the Soc Son config, wire latitude-derived climate
zones into dispatch, and re-measure every oracle number in one change.

**Tasks**
- [ ] TASK-04-01: Re-read the registered composition table mechanically and record the result in the
      commit message:
      `python -c "from pdd_agent.ingest.table_lookup import find_tables, table_rows_as_pairs; t=find_tables('VCS_Soc_Son_Project-Description', ['Food waste','%']); print(table_rows_as_pairs(t[0]) if t else 'NOT FOUND')"`.
      The expected pairs are Paper and Cardboard 2.7%, Textiles 1.6%, Food waste 51.9%, Wood 0%,
      Garden and park waste 0%, Nappies 0%, Rubber and leather 1.3%, Plastic 3.0%, Metal 0.9%,
      Glass 0.5%, Others 38.1%.
- [ ] TASK-04-02: Rewrite `technology.waste_composition` in
      `configs/projects/vietnam_socson_from_sheet.yaml` to exactly:
      `food_waste 0.519`, `paper_cardboard 0.027`, `textiles 0.016`, `rubber_leather 0.013`,
      `plastics 0.030`, `inert 0.395` (metal 0.9% + glass 0.5% + others 38.1%), each with
      `source: "VCS Soc Son registered PDD, monitoring parameter Pn,j (page 78) — waste composition on wet basis"`.
      The fractions must sum to 1.000.
- [ ] TASK-04-03: Set `location.climate_zone: tropical_wet` in the same config, with a YAML comment
      citing the site latitude (21.261) and the IPCC zone definition.
- [ ] TASK-04-04: Set `quantification.grid_emission_factor: 0.84585`,
      `quantification.grid_emission_factor_source: "VCS Soc Son registered PDD, Section 4.1 — EF_grid,CM,y (combined margin)"`,
      and `quantification.grid_tdl_factor: 0.03` in the same config.
- [ ] TASK-04-05: Add to the same config
      `technology.auxiliary_fossil_fuel: [{fuel_type: diesel, annual_tonnes: 1200.0, ncv_gj_per_tonne: 43.3, ef_tco2_per_gj: 0.0748, source: "VCS Soc Son registered PDD, Section 4.2 (2) — FSR diesel consumption"}]`
      and
      `technology.runoff_wastewater: {annual_volume_m3: 613200.0, cod_t_per_m3: 0.035, bo_t_ch4_per_t_cod: 0.25, mcf: 0.8, source: "VCS Soc Son registered PDD, Section 4.2 (4) — EIA pages 248 and 252"}`.
- [ ] TASK-04-06: In `src/pdd_agent/calc/dispatch.py::_map_acm0022`, set
      `mapped["climate_zone"] = climate_zone_for(pi.location.latitude, pi.location.climate_zone)` so
      the zone is derived when not declared (S-1d). Add a warning naming the resolved zone and whether
      it was declared or derived.
- [ ] TASK-04-07: Update `configs/projects/vietnam_socson_from_sheet.assumptions.yaml` so any entry
      that described the old composition split, the old grid factor, or the removed rubber-and-leather
      fraction now points at the registered-PDD source instead of a synthetic assumption.
- [ ] TASK-04-08: Re-measure and record: run
      `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` and
      `pdd-agent calc --input configs/demo/inegol_project_input.yaml`, and paste both outputs into the
      commit message.
- [ ] TASK-04-09: Update `tests/test_registered_pdd_oracle.py`: add the registered per-year project
      emissions (420,336) and baseline electricity (338,059) as module constants with their source
      comment; convert each existing `xfail` whose residual now falls inside `TOLERANCE` into a
      passing assertion; for any that remain outside, update the `reason` string with the newly
      measured residual and the date `2026-08-28`. `TOLERANCE` stays `0.20`.
- [ ] TASK-04-10: Add three new oracle assertions: engine `PE_y` within `TOLERANCE` of 420,336;
      engine `BE_EC` within `TOLERANCE` of 338,059; engine 7-year `BE_CH4` sum within `TOLERANCE` of
      4,384,018.
- [ ] TASK-04-11: Add a guard test asserting `sum(mass_fraction) == 1.000 ± 0.001` for the Soc Son
      composition and that every entry's `source` string contains `registered PDD`.
- [ ] TASK-04-12: Update the `**Status:**` line and the "Quantification precedence" subsection of
      `README.md` with the new test count and a one-paragraph statement of what the engine now
      reproduces and what residual remains.

**File Changes**
- `configs/projects/vietnam_socson_from_sheet.yaml` (modify): composition, climate zone, grid factor
  and loss factor, auxiliary fuel, wastewater. Leave project identity, dates, and every other block
  unchanged.
- `configs/projects/vietnam_socson_from_sheet.assumptions.yaml` (modify): re-point provenance entries.
- `src/pdd_agent/calc/dispatch.py` (modify): derive the climate zone.
- `tests/test_registered_pdd_oracle.py` (modify): new constants, new assertions, re-measured xfail
  reasons. Do not change `TOLERANCE`.
- `README.md` (modify): status line and quantification paragraph.

**Function Signatures**
- None — no new code interfaces; this phase wires existing ones and changes data.

**Test Specs**
Values below were measured during planning against the current code with the registered parameters
applied. Treat them as **expected within ±2%**; record whatever the engine actually produces.
- Soc Son `BE_CH4` year 1 → about `264,884` tCO2e (registered 277,866, residual about −4.7%).
- Soc Son `BE_CH4` 7-year sum → about `4,208,584` tCO2e (registered 4,384,018, residual about −4.0%),
  inside `TOLERANCE`.
- Soc Son `BE_EC` → `338,059` tCO2e/year ± 500 (`388,050 MWh × 0.84585 × 1.03`).
- Soc Son `PE_y` → about `420,000` tCO2e/year (registered 420,336): `PE_COM_CO2` about 272,843,
  `PE_COM_CH4_N2O` about 23,418, `PE_FC` about 3,887, `PE_WW` about 120,187, `PE_EC` 0.
- Soc Son 7-year crediting total → about `3,632,645` tCO2e (registered 3,808,082, residual about
  −4.6%), inside `TOLERANCE`.
- Inegol crediting-period total and year-1 values → unchanged from before this phase (no composition,
  no wastewater, no auxiliary fuel declared; latitude 40.1505 derives `boreal_temperate_wet`).
- `ProjectInput.model_validate` succeeds for all six committed configs.

**Dependencies**
- PHASE-01 (table lookup for TASK-04-01), PHASE-02 (zone mechanism), PHASE-03 (Eq. 22/27/28 terms).

**Exit Criteria**
- [ ] `python -m pytest tests/test_registered_pdd_oracle.py -v` reports 0 failures, and every
      remaining `xfail` carries a reason containing a measured residual and the date `2026-08-28`.
- [ ] `grep -n "TOLERANCE = " tests/test_registered_pdd_oracle.py` prints exactly one line reading
      `TOLERANCE = 0.20`.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failures.
- [ ] `pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml` prints a project
      emissions figure between 380,000 and 460,000 tCO2e/year.
- [ ] The commit message contains the before and after numbers for baseline methane, project
      emissions, baseline electricity, and the crediting-period total, for both Soc Son and Inegol.

**Phase Risks**
- **RISK-04-01:** A sourced parameter may make a residual worse. Per DEC-002 the sourced parameter
  stays and the residual is recorded; do not adjust a parameter to move a number.
- **RISK-04-02:** `technology.waste_type` in the Soc Son config lists only three types while the
  composition now names six. `_map_acm0022` reads the composition when present, so this is cosmetic —
  but update `waste_type` to list the same six keys so a reader is not misled.
- **RISK-04-03:** The registered PDD also states an exported capacity of 75 MW where the config says
  `installed_capacity_mw: 52.115`. That inconsistency is **out of scope** for this plan (it does not
  enter the calculation, which uses `energy_generation_mwh_year: 388050`). Note it in the commit
  message and leave it alone.

### PHASE-05 - Own the Assembled Document

**Goal**
Make the exported DOCX read as one numbered document, give the drafting prompt a real length
contract, and add a document-level coherence report that no section-scoped check can produce.

**Tasks**
- [ ] TASK-05-01: Create `src/pdd_agent/export/assembly.py` with `canonical_subsection_title()`,
      `strip_leading_title_heading()`, and `is_title_echo()` per the Function Signatures below,
      implementing Specification S-3.
- [ ] TASK-05-02: In `src/pdd_agent/export/docx_export.py`, replace
      `doc.add_heading(subsection_heading, level=2)` with
      `doc.add_heading(canonical_subsection_title(ssid, subsection_heading), level=2)`.
- [ ] TASK-05-03: In the same file, pass each section's body through `strip_leading_title_heading()`
      before `_add_section_prose` renders it. Do not mutate the stored run record — strip a copy.
- [ ] TASK-05-04: In `src/pdd_agent/agent/section_orchestrator.py::_build_prompt`, append a
      `## Length Budget` block per Specification S-4 step 1, stating the resolved budget from
      `self.section_budget_chars(section_id, sub_section_id)`.
- [ ] TASK-05-05: Add `chars_to_max_tokens(max_chars: int, chars_per_token: float = 3.5, headroom: float = 1.15) -> int`
      to `src/pdd_agent/llm/provider.py` and raise `ModelConfig.max_tokens`'s default from 4000 to
      16000, documenting it as a provider-level hard ceiling on output tokens.
- [ ] TASK-05-06: Use `min(self._config.max_tokens, chars_to_max_tokens(max_chars))` in
      `src/pdd_agent/llm/openai_provider.py`, `src/pdd_agent/llm/anthropic_provider.py`, and
      `src/pdd_agent/llm/ollama_provider.py` wherever `max_tokens` is currently derived from
      `max_chars`. `src/pdd_agent/llm/claude_code_provider.py` needs no change (the CLI takes no output
      cap) — leave its post-generation truncation as it is.
- [ ] TASK-05-07: Delete `prompts/section_draft.md` and `prompts/section_draft_v2.md`. No module reads
      them (the live prompt is assembled in `_build_prompt`), and their "keep sections under 2000
      characters" rule contradicts the shipped budgets. Leave `prompts/methodologies/*.md` and
      `prompts/extract_project_input.md` untouched.
- [ ] TASK-05-08: Create `src/pdd_agent/review/document_coherence.py` implementing the five checks in
      Specification S-5.
- [ ] TASK-05-09: Call `check_document_coherence()` from `SectionOrchestrator.run_review()` and include
      its findings in the returned dict under the key `document_coherence`.
- [ ] TASK-05-10: Render the coherence findings in the DOCX reviewer-issues appendix
      (`_add_reviewer_issues_appendix` in `src/pdd_agent/export/docx_export.py`) under a
      `Document-level findings` sub-heading, only when `is_demo` is false.
- [ ] TASK-05-11: Add `tests/test_assembly.py`, `tests/test_document_coherence.py`, and extend
      `tests/test_prompt_assembly.py` and `tests/test_docx_export.py` with the specs below.
- [ ] TASK-05-12: Update `README.md`: the export-gate/export description gains the numbering and
      title-echo rules, and the "Section length budgets" subsection gains the prompt contract and the
      character-to-token conversion.

**File Changes**
- `src/pdd_agent/export/assembly.py` (create): three pure functions, no python-docx import.
- `src/pdd_agent/export/docx_export.py` (modify): numbered subsection headings, title-echo stripping,
  coherence findings in the reviewer appendix. Leave the export gate, required-inputs appendix, calc
  appendix, and formulas appendix unchanged.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): `## Length Budget` block in `_build_prompt`;
  `document_coherence` in `run_review()`.
- `src/pdd_agent/llm/provider.py` (modify): add `chars_to_max_tokens`, raise `ModelConfig.max_tokens`
  default.
- `src/pdd_agent/llm/openai_provider.py`, `src/pdd_agent/llm/anthropic_provider.py`,
  `src/pdd_agent/llm/ollama_provider.py` (modify): one line each, the `max_tokens` derivation.
- `src/pdd_agent/review/document_coherence.py` (create): the five checks and a report dataclass.
- `prompts/section_draft.md`, `prompts/section_draft_v2.md` (delete).
- `tests/test_assembly.py`, `tests/test_document_coherence.py` (create);
  `tests/test_prompt_assembly.py`, `tests/test_docx_export.py` (modify).
- `README.md` (modify).

**Function Signatures**
- `canonical_subsection_title(sub_section_id: str, heading: str) -> str` — returns
  `f"{sub_section_id} {heading}"`, or just `heading` when `sub_section_id` is empty.
- `is_title_echo(line: str, heading: str) -> bool` — True when `line` is an ATX heading whose text,
  with a leading numeric label stripped, matches `heading` case-insensitively after whitespace
  collapsing.
- `strip_leading_title_heading(text: str, heading: str) -> str` — returns `text` with its first
  non-blank line removed when `is_title_echo` holds for that line, otherwise `text` unchanged.
- `chars_to_max_tokens(max_chars: int, chars_per_token: float = 3.5, headroom: float = 1.15) -> int`
  — returns the output-token ceiling for a character budget, minimum 256.
- `check_document_coherence(run_data: dict[str, Any], schema_path: Path | None = None) -> list[dict[str, Any]]`
  — returns findings, each `{"check": str, "severity": "HIGH"|"ADVISORY", "sections": list[str], "detail": str}`.

**Test Specs**
- `canonical_subsection_title("4.1", "Baseline Emissions")` → `"4.1 Baseline Emissions"`.
- `is_title_echo("# 4.4.1 Baseline Emissions", "Baseline Emissions")` → `True`.
- `is_title_echo("## Baseline Emissions", "Baseline Emissions")` → `True`.
- `is_title_echo("## Methodology Basis", "Baseline Emissions")` → `False`.
- `strip_leading_title_heading("# 4.4.1 Baseline Emissions\n\nUnder ACM0022...", "Baseline Emissions")`
  → `"Under ACM0022..."` (leading blank lines collapsed).
- `strip_leading_title_heading("Under ACM0022...", "Baseline Emissions")` → unchanged.
- Exporting `data/runs/smoke-4-1.json` produces a Word heading tree containing
  `("Heading 2", "4.1 Baseline Emissions")` and **no** heading whose text is `"4.4.1 Baseline Emissions"`.
- `chars_to_max_tokens(20000)` → `6572`; `chars_to_max_tokens(2000)` → `658`;
  `chars_to_max_tokens(100)` → `256` (the floor).
- The prompt built for section `4.1` contains the literal string `## Length Budget` and the resolved
  budget `20000`.
- `check_document_coherence` on a run whose section `4.1` says `1,234,567 tCO2e` and whose section
  `4.4` says `1,300,000 tCO2e` → one `NUMBER_DISAGREEMENT` finding naming both sections.
- `check_document_coherence` on a run whose two sections have identical bodies → one `DUPLICATE_BODY`
  finding.
- `check_document_coherence` on a run containing `see Section 9.9` → one
  `DANGLING_CROSS_REFERENCE` finding.
- `check_document_coherence` on a run with no issues → `[]`.

**Dependencies**
- None. `data/runs/smoke-4-1.json` must be present for the export regression test; skip that test with
  `pytest.mark.skipif` when the file is absent so CI stays green.

**Exit Criteria**
- [ ] `python -m pytest tests/test_assembly.py tests/test_document_coherence.py tests/test_docx_export.py tests/test_prompt_assembly.py -q`
      reports 0 failures.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failures.
- [ ] `grep -rn "section_draft_v2" src/ tests/` returns no matches.
- [ ] `ruff check . && ruff format --check .` pass.

**Phase Risks**
- **RISK-05-01:** Over-aggressive title-echo stripping could delete real content. Mitigation: the
  predicate matches only the **first** non-blank line, only when it is an ATX heading, and only on an
  exact normalized title match; the negative test specs above lock that down.
- **RISK-05-02:** Raising `ModelConfig.max_tokens` to 16000 raises the ceiling for every provider,
  including in tests that assert on request payloads. Mitigation: run
  `python -m pytest tests/test_openai_provider.py tests/test_anthropic_provider.py tests/test_ollama_provider.py -q`
  first and update any payload assertion to the computed value.

### PHASE-06 - Make a Real 36-Section Run Survivable

**Goal**
Let an operator see the cost before spending it, keep every completed section on disk, resume an
interrupted run, and optionally draft several sections at once — without changing default behavior.

**Tasks**
- [ ] TASK-06-01: Add `estimate_run(section_budgets: dict[str, int], avg_prompt_chars: float, model: str, provider: str, overhead_tokens_per_section: int = 0) -> dict[str, float]`
      to `src/pdd_agent/llm/budget.py` implementing Specification S-6 step 1, reusing the existing
      `_DEFAULT_PRICING` lookup.
- [ ] TASK-06-02: Add `SectionOrchestrator.preflight_estimate() -> dict[str, float]` that builds every
      prompt it would send (retrieval included, no provider call), measures their mean length, and
      returns `estimate_run(...)` with `overhead_tokens_per_section=25000` for the `claude-code`
      provider and 0 otherwise.
- [ ] TASK-06-03: Make `TokenBudget` thread-safe: add a `threading.Lock` guarding `record()` and
      `check_budget()`.
- [ ] TASK-06-04: Fix `SectionOrchestrator._store_draft` so re-drafting a section replaces its entry in
      `self._run.sections` instead of appending a second one (match on
      `(section_id, sub_section_id)`).
- [ ] TASK-06-05: Add `SectionOrchestrator.checkpoint()` that writes the run record atomically
      (temporary file in the target directory plus `os.replace`) and call it after every section in
      `draft_all_sections()`.
- [ ] TASK-06-06: Add a `resume: bool = False` constructor parameter. When true and
      `data/runs/{run_id}.json` exists, pre-populate `self._drafted` and `self._run.sections` from it,
      and skip any section whose stored text is non-empty and starts with neither `[PLACEHOLDER` nor
      `[BUDGET EXHAUSTED`. Log `run_resumed` with the number of sections skipped.
- [ ] TASK-06-07: Add a `max_workers: int = 1` constructor parameter and use a
      `ThreadPoolExecutor` in `draft_all_sections()` when it exceeds 1, submitting sections in
      canonical schema order and sorting results back into that order before storing.
- [ ] TASK-06-08: Add CLI flags to the `draft` sub-parser in `src/pdd_agent/cli.py`:
      `--max-tokens` (int), `--max-cost-usd` (float), `--workers` (int, default 1),
      `--resume` (flag), `--estimate-only` (flag), `--force-budget` (flag).
- [ ] TASK-06-09: In `_run_draft`, build the `TokenBudget` from the flags (falling back to the
      `PDD_MAX_TOKENS` / `PDD_MAX_COST_USD` environment variables, then to the existing defaults),
      print the pre-flight estimate before drafting, exit with code 0 after printing when
      `--estimate-only` is set, and exit with code 2 and an explanatory message when the estimate
      exceeds the budget unless `--force-budget` is set.
- [ ] TASK-06-10: Raise the default `TokenBudget.max_tokens` for real providers only: when the provider
      is not `demo` or `noop` and no explicit budget was given, default to
      `60_000 × number_of_sections_to_draft`. Keep 500,000 for `demo` and `noop`.
- [ ] TASK-06-11: Add `tests/test_run_survivability.py` with the specs below, using the `noop`
      provider and `tmp_path` for `runs_dir` — no network, no API keys.
- [ ] TASK-06-12: Document the new flags in the CLI table in `README.md` and add a short
      "Running a real drafting run" subsection covering estimate, resume, and workers.

**File Changes**
- `src/pdd_agent/llm/budget.py` (modify): `estimate_run()` and the lock. Leave `_estimate_cost`,
  `record`, and `summary` semantics otherwise unchanged.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): `preflight_estimate`, `checkpoint`,
  `resume`, `max_workers`, and the `_store_draft` replace-not-append fix.
- `src/pdd_agent/cli.py` (modify): six new flags on the `draft` sub-parser and the corresponding
  handling in `_run_draft`.
- `tests/test_run_survivability.py` (create).
- `README.md` (modify): CLI table and the new subsection.

**Function Signatures**
- `estimate_run(section_budgets: dict[str, int], avg_prompt_chars: float, model: str, provider: str, overhead_tokens_per_section: int = 0) -> dict[str, float]`
  — returns `{"sections", "input_tokens", "output_tokens", "total_tokens", "estimated_cost_usd"}`.
- `SectionOrchestrator.preflight_estimate() -> dict[str, float]` — same shape, for the sections this
  run would actually draft (honouring `only_sections`).
- `SectionOrchestrator.checkpoint(self) -> Path` — writes the run record atomically and returns the
  path written.
- `SectionOrchestrator.__init__(..., resume: bool = False, max_workers: int = 1)` — additive
  parameters, defaults preserve current behavior.

**Test Specs**
- `estimate_run({"1.1": 4000, "4.1": 20000}, avg_prompt_chars=9000, model="gpt-4o", provider="openai")`
  → `input_tokens == 5143` (`round(2 × 9000 / 3.5)`), `output_tokens == 6857`
  (`round((4000 + 20000) / 3.5)`), `estimated_cost_usd` greater than 0.
- The same call with `provider="claude-code", overhead_tokens_per_section=25000` → `total_tokens`
  exactly 50,000 higher than without the overhead.
- Drafting two sections with the `noop` provider and `runs_dir=tmp_path` leaves
  `tmp_path/{run_id}.json` on disk containing 1 section after the first section completes (checkpoint
  written mid-run, verified by reading the file from a `checkpoint()` call inside a loop of one).
- Re-running the same orchestrator with `resume=True` over a run file whose `1.1` section has real
  text and whose `1.2` section text starts with `[PLACEHOLDER` → `1.1` is skipped and `1.2` is
  re-drafted; the resulting run record still has exactly one entry per section id.
- `draft_all_sections()` with `max_workers=4` and the `noop` provider over the full 36-section schema
  → the stored `sections` list is in canonical schema order (`1.1, 1.2, …, 5.3`) and has length 36.
- `_store_draft` called twice for `("4", "4.1")` → `run.sections` has exactly one entry for that key,
  holding the second draft.
- CLI: `pdd-agent draft --input configs/projects/demo_socson_like.yaml --provider noop --estimate-only`
  exits 0 and prints a line containing `estimated_cost_usd`.

**Dependencies**
- PHASE-05, because the `## Length Budget` block changes prompt length and therefore the estimate.

**Exit Criteria**
- [ ] `python -m pytest tests/test_run_survivability.py -q` reports 0 failures.
- [ ] `python -m pytest -m "not corpus" -q` reports 0 failures.
- [ ] `PYTHONIOENCODING=utf-8 pdd-agent draft --input configs/projects/demo_socson_like.yaml --provider noop --estimate-only`
      exits 0 and prints an estimate without creating a run JSON.
- [ ] `PYTHONIOENCODING=utf-8 pdd-agent draft --input configs/projects/demo_socson_like.yaml --provider noop --workers 4`
      produces a run JSON with 36 sections in canonical order.
- [ ] `ruff check . && ruff format --check .` pass.

**Phase Risks**
- **RISK-06-01:** Thread-pool drafting shares one `RetrievalIndex` and one provider instance.
  `tests/test_retrieval_threading.py` already covers index thread safety; providers are stateless per
  call except for the budget, which TASK-06-03 locks. Mitigation: keep `--workers 1` the default
  (ASM-005) and add the ordering test spec above.
- **RISK-06-02:** Checkpointing after every section multiplies writes of a file that reaches roughly
  250 KB for a 36-section run. That is 36 writes of 250 KB per run — negligible, but use the atomic
  temp-plus-replace pattern so an interrupted write never leaves a truncated JSON.

## Gotchas

- **Two decay-rate tables must agree.** `DECAY_RATE_BY_WASTE_TYPE` is imported directly by
  `cdm_tool_04.py` and possibly by tests. After PHASE-02 it is a copy of the `boreal_temperate_wet`
  zone; assert equality, never identity, and never mutate either table at runtime.
- **`FCC` is wet-basis; `dm × CF` is dry-basis.** Do not multiply ACM0022's `FCC` by a dry-matter
  fraction. Mixing the two conventions understates fossil carbon by roughly the dry-matter factor —
  that is precisely the bug PHASE-03 fixes.
- **Mass fractions are 0–1, not percentages.** The registered table prints `51.9 %`; the config field
  is `0.519`. `ProjectTechnology.validate_waste_composition` rejects a sum above 1.0.
- **Emission factors have two unit conventions in this repo.** The existing
  `EF_N2O_INCINERATION_KG_PER_TONNE` is in **kilograms** per tonne; the new Eq. 27 factors are in
  **tonnes** per tonne. Keep the unit in the constant name, as both do.
- **Grid emission factor and loss factor multiply.** `BE_EC = MWh × EF_grid × (1 + TDL)`. A 3% loss
  factor is `0.03`, not `1.03`.
- **The crediting-period total is a sum over the annual schedule**, not the year-1 value times seven —
  `BE_CH4` grows every year under the FOD model while `PE` is constant.
- **Do not tune to the oracle.** Every parameter must cite the registered PDD, ACM0022 v03.0, or a
  named IPCC table (DEC-002). A residual that is measured and recorded is a success; a residual that
  was fitted away is a regression in the only quality signal this repository has.
- **`data/corpus/normalized/` is gitignored and is regenerated in PHASE-01.** Nothing there may be
  committed, and the backup taken in TASK-01-02 is the only way back.
- **Windows console encoding.** Prefix CLI invocations with `PYTHONIOENCODING=utf-8` when piping
  output; several help strings and log lines contain non-ASCII characters and will otherwise raise
  `UnicodeEncodeError` under the cp1252 code page.
- **The test suite writes into `data/runs/`.** A full run leaves several `run-*.json` files there.
  That is pre-existing behavior; do not "fix" it as part of this plan, and do not be surprised by new
  files after running the suite.
- **`prompts/section_draft*.md` are not loaded by any module.** Deleting them in PHASE-05 changes no
  behavior; the live prompt is assembled in `SectionOrchestrator._build_prompt`.

## Verification Strategy

- **TEST-001:** `python -m pytest -m "not corpus" -q` → `0 failed`; the passed count is at least 909
  plus the new tests, and every remaining `xfail` carries a measured residual dated `2026-08-28`.
- **TEST-002:** `python -m pytest tests/test_registered_pdd_oracle.py -v` → 0 failures; the Soc Son
  crediting-period total, baseline methane 7-year sum, project emissions, and baseline electricity
  assertions all pass inside `TOLERANCE = 0.20`.
- **TEST-003:** `grep -c "TOLERANCE = 0.20" tests/test_registered_pdd_oracle.py` → `1`.
- **TEST-004:** `python -m pytest tests/test_incineration.py -q` → 0 failures, including the
  `272,843` / `23,418` / `120,187` worked checks from Specification S-2.
- **TEST-005:** `python -m pytest tests/test_assembly.py tests/test_document_coherence.py -q` →
  0 failures.
- **TEST-006:** `python -m pytest tests/test_run_survivability.py -q` → 0 failures.
- **TEST-007:** `ruff check . && ruff format --check . && uv lock --check` → all three exit 0.
- **MANUAL-001:** `PYTHONIOENCODING=utf-8 pdd-agent calc --input configs/projects/vietnam_socson_from_sheet.yaml`
  → components list contains `BE_CH4`, `BE_EC`, `PE_COM_CO2`, `PE_COM_CH4_N2O`, `PE_FC`, `PE_WW`;
  project emissions between 380,000 and 460,000 tCO2e/year; crediting-period total between 3,400,000
  and 3,900,000 tCO2e.
- **MANUAL-002:** `PYTHONIOENCODING=utf-8 pdd-agent calc --input configs/demo/inegol_project_input.yaml`
  → identical output to the same command run before PHASE-04 (capture it beforehand by redirecting
  to `inegol-before.txt` in the repo root, then diff the two captures and delete the files).
- **MANUAL-003:** `PYTHONIOENCODING=utf-8 pdd-agent export --run-id smoke-4-1` then open the DOCX →
  section 4 shows `4.1 Baseline Emissions` as a single Heading 2 with no `4.4.1 Baseline Emissions`
  sub-heading beneath it, and the body's own sub-headings (`Methodology Basis` and the rest) survive.
- **MANUAL-004:** `PYTHONIOENCODING=utf-8 pdd-agent index-report` → `Reachable rows` at least 889 and
  `Reachable documents` at least 13, both no lower than before PHASE-01.
- **OBS-001:** Confirm the new structlog events appear with their keys during a `noop` drafting run:
  `run_resumed` (sections_skipped), `preflight_estimate` (total_tokens, estimated_cost_usd),
  `calc_climate_zone_resolved` (zone, derived), and `runoff_wastewater absent; PE_WW assumed zero` in
  the calc warnings for a config without a wastewater block.

## Risks and Alternatives

- **RISK-001:** The plan's predicted post-fix residuals (baseline methane about −4%, crediting total
  about −4.6%) were measured with a monkey-patched decay table and a reconstructed composition, not
  with the finished implementation. The real numbers will differ slightly. Mitigation: every exit
  criterion is expressed as a range or as "record what you measure", and DEC-002 forbids adjusting
  parameters to hit a target.
- **RISK-002:** PHASE-03 changes project emissions for any project declaring a waste composition. Only
  Soc Son does today, so the blast radius is one config — but a future config would silently inherit
  the new arithmetic. Mitigation: the README paragraph from TASK-03-11 documents the change, and the
  dispatch warnings name every stream that contributes to `PE_COM_CO2`.
- **RISK-003:** Re-normalization in PHASE-01 changes retrieval results for every future drafting run,
  so section text produced after it will not be byte-comparable with runs produced before it.
  Mitigation: accept (ASM-007); no committed artifact depends on retrieval byte-stability.
- **RISK-004:** The `claude-code` overhead constant (25,000 tokens per section) comes from a single
  measured section. Mitigation: it is a named default parameter of `estimate_run`, overridable, and
  the estimate is advisory unless it exceeds the budget.
- **ALT-001:** Keep the IPCC Eq. 5.1 dry-matter model and calibrate its `CF`/`FCF` values until the
  totals match. Rejected: it reproduces the answer without reproducing the method, and a validator
  checks the method.
- **ALT-002:** Fix baseline methane now and project emissions in a later push. Rejected: measured to
  move the crediting total to +39.4% and break a currently passing oracle test (DEC-003).
- **ALT-003:** Derive the climate zone from a bundled climate dataset rather than from latitude.
  Rejected: a new data dependency for a decision that latitude resolves correctly for both oracle
  projects, and an explicit `location.climate_zone` override exists for anything ambiguous.
- **ALT-004:** Add a document-level LLM coherence pass instead of the deterministic checks in
  Specification S-5. Rejected for this plan: the deterministic checks catch the defects actually
  observed (title echo, calc disagreement) at zero cost; an LLM pass can be layered on later behind a
  flag.

## Suggested Next Step

Execute PHASE-01. It is independent of every other phase, it is the only phase that touches
ingestion, and its output (extracted tables in `data/corpus/normalized/`) is what lets PHASE-04
re-read the registered parameter table mechanically instead of trusting the values transcribed into
this plan. Verify its exit criteria — in particular that no document loses text blocks — before
starting PHASE-02.
