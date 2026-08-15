# Grounding Rebuild + Calc Inputs — PHASE-01/02/03 Push

**Plan:** `plans/2026-08-13-grounding-rebuild-and-calc-inputs-plan.md`
**Scope decision (user, 2026-08-15):** implement PHASE-01, PHASE-02, PHASE-03 only.
PHASE-04 (real $1-capped `claude-code` spend) and everything gated behind it (PHASE-05
calc-composition fix, PHASE-06 table-aware ingestion) are explicitly **out of scope** for
this push — user chose "skip PHASE-04 and PHASE-05/06 gate" when asked.

## Environment notes

- `PYTHONPATH` is polluted by a hermes venv in the user profile
  (`C:\Users\tukum\AppData\Local\hermes\hermes-agent\...`). Must `unset PYTHONPATH` before
  `uv run --no-sync python -m pytest ...` or imports resolve to the wrong site-packages.
- `claude` CLI present (v2.1.233), not used this push (PHASE-04 skipped).
- `data/corpus/normalized/` present locally: 17 documents.

## Checklist

### PHASE-01 — Make Corpus Health Measurable — DONE (commit `8b77742`)
- [x] TASK-01-01/02: `rows_by_document` / `docs_with_zero_sections` in `RetrievalIndex.build()` + WARNING log
- [x] TASK-01-03: `index_health()`
- [x] TASK-01-04: `pdd-agent index-report` subcommand
- [x] TASK-01-05: zero-yield doc list printed by `build-index`
- [x] TASK-01-06: tests in `tests/test_retrieval_search.py`
- [x] README updated (CLI table row + test count)
- [x] Exit criteria: tests green (16/16 new), `index-report` run against current index (1015/270/0.734/13, matches plan), ruff clean

### PHASE-02 — Rebuild Index on Real Section Spans — DONE (commit `d595e31`)
- [x] TASK-02-01/02/03: `section_spans` + `_chunk_block` (S-1) in `section_parser.py`, `_find_content_page` fallback kept
- [x] TASK-02-04: `document_family`/`chunk_index` columns, bump `_SCHEMA_VERSION` to `"2"`
- [x] TASK-02-05: populate `content_class`/`review_sensitivity`
- [x] TASK-02-06: `configs/corpus_families.yaml` + `load_corpus_families`
- [x] TASK-02-07: family filter through `search()`/`get_examples_for_section()` with ASM-004 fallback
- [x] TASK-02-08: orchestrator passes `document_family`
- [x] TASK-02-09: rebuild local index, before/after `index-report` recorded below
- [x] Exit criteria: **partially met** — duplication_rate 0.027 (≤0.15 ✓), mean_text_chars 1068.1 (≥800 ✓),
      4.4 retrieval non-degenerate (5 distinct texts/5 distinct docs ✓, after an orchestrator-added fix — see below),
      tests green, ruff clean. **`documents` stays at 13, not ≥16; ACM0022 methodology text still not retrievable** —
      honest gap, root-caused, not forced. See Review section.

### PHASE-03 — Render Prose *and* Tables — DONE (commit `fdc32f5`)
- [x] TASK-03-01/02: `_add_section_prose`, prose-then-table dispatch
- [x] TASK-03-03: audit-history front matter
- [x] TASK-03-04: S-3 `ghg_boundary` rows in `wte_methodology_rules.yaml` + accessor
- [x] TASK-03-05: `_build_structured_content` (proponent/applicability/ghg_boundary/monitoring_fixed_params)
- [x] TASK-03-06: split 5.1 (fixed) / 5.2 (tracked) monitoring params
- [x] TASK-03-07: README Known Gaps update
- [x] Exit criteria: docx export tests green (70/70), 4.4 has prose+table (manually verified), tests green, ruff clean

## Final steps
- [x] Full suite `python -m pytest -m "not corpus" -q` green: **823 passed, 7 deselected, 3 xfailed, 0 failed**
      (baseline was 798 passed; +25 net new tests across the three phases)
- [x] `ruff check .` / `ruff format --check .` clean
- [x] Update this file's review section
- [ ] Run `/report final` against the plan
- [ ] git commit + push (user pre-authorized)

## Review / Results

**Delivered:** PHASE-01, PHASE-02, PHASE-03 of the 2026-08-13 grounding-rebuild plan, each
implemented in an isolated git worktree by a separate agent, merged into `main` sequentially
(PHASE-01 → PHASE-02, which depends on it; PHASE-03 ran independently in parallel), each
verified against the full suite and ruff before its own commit.

- `8b77742` — PHASE-01: `pdd-agent index-report`, `index_health()`, zero-yield document warnings.
- `fdc32f5` — PHASE-03: prose no longer deleted by a table; 8 of 11 Verra table types now have a
  producer (was 3); audit-history front matter; S-3 GHG boundary rows.
- `d595e31` — PHASE-02: real section-span chunking (S-1) replaces 500-char page-fragment
  indexing; `document_family`/`chunk_index` columns; family-scoped retrieval with fallback;
  `content_class`/`review_sensitivity` finally populated (they were always `""` before).

**Measured before/after (PHASE-02, local `data/index/`, gitignored):**

| Metric | Before | After | Plan threshold | Met |
|---|---|---|---|---|
| total_rows | 1015 | 2660 | — | — |
| distinct_texts | 270 | 2588 | — | — |
| duplication_rate | 0.734 | **0.027** | ≤0.15 | ✅ |
| documents | 13 | 13 | ≥16 | ❌ |
| mean_text_chars | 498.0 | **1068.1** | ≥800 | ✅ |
| 4.4 example retrieval: distinct texts / docs | 2 / 1 | **5 / 5** | ≥4 / ≥3 | ✅ |

**Orchestrator-level fix beyond the PHASE-02 agent's own diff:** the agent flagged (rather than
silently resolving) a genuine tension in the plan — `get_section_examples()`'s
`ORDER BY document_name LIMIT k` was written when each document contributed ~1 row per
sub-section; after S-1 chunking a document can contribute many, so the alphabetically-first
document(s) could exhaust `k` before other documents were reached (2 distinct docs measured,
below the plan's ≥3 threshold). Fixed in `main` directly: rank rows per-document by
`chunk_index` (`ROW_NUMBER() OVER (PARTITION BY document_name ORDER BY chunk_index)`) before
slicing to `k`, so the top-k spans documents first. Re-measured after the fix: 5 distinct
docs. Included in the `d595e31` commit.

**Known, honest gap (not fixed, out of scope):** 4 of 17 documents — including
`EB111_repan07_ACM0022_v03.0`, the methodology text itself — still yield zero indexable
sections, so `documents` stays at 13 (plan wanted ≥16) and the ACM0022-retrievability smoke
check still fails. Root cause, confirmed directly: these four `.norm.json` files have
`text_blocks: 1` (a single collapsed preamble — `_build_headings_and_blocks()` found no real
headings) alongside an unrelated 50-entry `headings` list from an older extraction path. S-1's
alignment check correctly detects this mismatch and falls back to the legacy
`_find_content_page` path (per DEC-003), which also can't match these headings against the
canonical WTE schema. This is a defect in `ingest/normalize.py`'s heading extraction for these
four specific PDFs — explicitly out of scope for PHASE-02 (anticipated by the plan's own
RISK-02-03, whose mitigation is "record which and why... rather than forcing it"). Fixing it is
a separate, evidence-driven `normalize.py` change.

**Not built (explicit user scope cut):** PHASE-04 (real $1-capped `claude-code` single-section
smoke draft), PHASE-05 (waste-composition-weighted calc mapping, mass-conservation fix, oracle
xfail re-measurement), PHASE-06 (pdfplumber table-aware ingestion). The plan file still carries
these as open phases if picked up later; PHASE-05 in particular no longer strictly depends on
PHASE-04 having run (PHASE-04 was a spend-bounded smoke check, not a code dependency) if a
future session wants to pull it forward independently — re-read PHASE-05's own Dependencies
note before doing so.

**Suite state:** 823 passed, 7 deselected, 3 xfailed, 0 failed. `ruff check .` / `ruff format --check .` clean.
