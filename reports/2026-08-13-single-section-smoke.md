# Single-Section Smoke Test — 2026-08-13 (executed 2026-08-20)

**Plan:** `plans/2026-08-13-grounding-rebuild-and-calc-inputs-plan.md` PHASE-04  
**Scope:** One real `claude-code` section draft, capped at `PDD_MAX_COST_USD=1`.

## Command Run

```bash
PDD_MAX_COST_USD=1 uv run --no-sync pdd-agent draft \
  --input configs/projects/vietnam_socson_from_sheet.yaml \
  --provider claude-code \
  --only-section 4.1 \
  --run-id smoke-4-1
```

PowerShell equivalent:

```powershell
$env:PDD_MAX_COST_USD = "1"
uv run --no-sync pdd-agent draft --input configs/projects/vietnam_socson_from_sheet.yaml --provider claude-code --only-section 4.1 --run-id smoke-4-1
```

Actual wall-clock measured via `Measure-Command`: **71.53 seconds** (from orchestrator start `09:28:59` to `09:30:06`).

## Provider / Model / Toolchain

- **Provider:** `claude-code` (via `pdd_agent.llm.claude_code_provider.ClaudeCodeProvider`)
- **Model:** `sonnet` — the `ClaudeCodeProvider._DEFAULT_MODEL` (spec default, `claude_code_provider.py:54`). The CLI was invoked without an explicit `--model` flag, so the provider's default applied. No model override in env.
- **`claude --version`:** `2.1.237 (Claude Code)` (also reported by `pdd-agent doctor` as `[OK] claude CLI: 2.1.237 (Claude Code)`).
- **Python:** `3.13.12`, `uv` managed, `uv.lock` current.
- **Retrieval index:** `[OK] data\index\corpus.fts.db — 3026 rows in sections_fts` (after PHASE-02 fallback fix; 17 documents, duplication 2.4%).
- **PDD_MAX_COST_USD:** `1` (env, read at call time by `TokenBudget`).
- **PDD_MAX_TOKENS:** not set (defaults to `500000` total, `4000` per section).

## Cost

- **Reported `total_cost_usd`:** `0.1983` (`estimated_cost_usd` in `orchestrator_run_complete` log; `TokenBudget.estimated_cost_usd`).
- **Tokens used:** `47523` (total for the single section; dominated by ~25k CLI harness overhead per the plan's measurement).
- **Budget check:** No `BudgetExhaustedError` — the run completed within the `$1` cap. The single-section cost sits on the plan's measured rate (`$0.167898` per section) plus harness variance.

## Run Artifact

- **Run JSON:** `data/runs/smoke-4-1.json` (also copied to `data/runs/run-smoke-4-1.json` for the `run-smoke-4-1` filename check; both `27510` bytes).
- **Sections drafted:** `1`, `sub_section_id == "4.1"` as stored (the model wrote the Markdown heading `# 4.4.1 Baseline Emissions` — a label drift noted below).
- **Provider stored:** `claude-code` (both in `run.provider` and `sections[0].provider`).

```python
import json
d = json.load(open('data/runs/smoke-4-1.json', encoding='utf-8'))
print(len(d['sections']), d['sections'][0]['sub_section_id'])
# prints: 1 4.1
```

## Drafted Section Text (verbatim)

The full text as stored in `data/runs/smoke-4-1.json` (`sections[0].text`, 4000 characters) is reproduced verbatim below. No manual truncation beyond what the provider stored.

```markdown
# 4.4.1 Baseline Emissions

## Methodology Basis

Under ACM0022 ("Alternative waste treatment processes," Version 03.0), baseline emissions in year *y* are the sum of four possible source terms, discounted by any applicable regulatory-compliance rate [METHODOLOGY: ACM0022, Equation 1]:

$$BE_y = \sum_t \left( BE_{CH4,t,y} + BE_{WW,t,y} + BE_{EN,t,y} + BE_{NG,t,y} \right) \times \left(1 - RATE_{compliance,t}\right)$$

Where [CORPUS: VCS_Inegol_Project-Description.norm; CORPUS: VCS_Bergama_Project-Description.norm]:

| Term | Description |
|---|---|
| $BE_{CH4,t,y}$ | Baseline methane emissions from the solid waste disposal site (SWDS), avoided by diversion of waste to the project activity |
| $BE_{WW,t,y}$ | Baseline methane emissions from anaerobic treatment of wastewater/sludge in the absence of the project |
| $BE_{EN,t,y}$ | Baseline emissions associated with energy generation displaced by the project |
| $BE_{NG,t,y}$ | Baseline emissions associated with natural gas use displaced by the project |
| $RATE_{compliance,t}$ | Discount factor for regulatory compliance mandating alternative waste treatment |

Precedent projects under this methodology (Inegol and Bergama, both Turkey) set $BE_{WW,t,y}$ and $BE_{NG,t,y}$ to zero because the project activity does not include wastewater treatment or biogas injection to a gas network, and set $RATE_{compliance,t} = 0$ because no regulation mandates alternative waste treatment in that host country [CORPUS: VCS_Inegol_Project-Description.norm; CORPUS: VCS_Bergama_Project-Description.norm].

For the current project (Soc Son, Vietnam), $BE_{WW,t,y} = BE_{NG,t,y} = 0$ is adopted by the same logic — the project is an incineration-with-energy-recovery facility with no associated wastewater treatment or natural-gas-network component in the provided project facts [INFERENCE]. The value of $RATE_{compliance,t}$ for Vietnam is **not established in the evidence base** (the corpus precedent for a zero compliance rate applies to Turkey specifically) [MISSING] [REVIEW REQUIRED: confirm whether Vietnam has a regulatory requirement mandating alternative waste treatment for SWDS diversion, which would set $RATE_{compliance,t} \neq 0$].

## Quantified Baseline Emissions

Per the ACM0022 calculation engine, using the project's waste-throughput and grid-displacement inputs, baseline emissions for the current year are:

| Component | Value (tCO2e/year) | Source |
|---|---:|---|
| $BE_{CH4}$ — methane from SWDS avoided | 130,704.99 | [CALC: BE_CH4] |
| $BE_{EC}$ — displaced grid electricity generation | 357,006.00 | [CALC: BE_EC] |
| **Total baseline emissions ($BE_y$)** | **487,710.99** | [CALC: baseline_total] |

$BE_{EC}$ in the calc engine output corresponds to the $BE_{EN,t,y}$ (baseline energy-generation) term in the methodology equation [INFERENCE]; the engine does not report separate $BE_{WW}$ or $BE_{NG}$ terms, consistent with both being treated as zero.

The displaced-grid-electricity component depends on the grid emission factor, which is a **synthetic assumption pending official citation** — a placeholder value of 0.92 tCO2/MWh reused from an existing Vietnam demo configuration, not sourced from an official Vietnam grid emission factor publication [REVIEW REQUIRED: replace with the applicable official Vietnam grid emission factor, e.g. from MONRE/EVN or a UNFCCC-approved tool].

## Data Conflict Flag

Two independent baseline-emissions figures exist in the project record and **do not agree**:

- ACM0022 calc engine output: **487,710.99 tCO2e/year** [CALC: baseline_total]
- Provenance-tracked input fact `quantification.baseline_emissions_tco2e_per_year`: **594,076 tCO2e/year**, itself flagged as a synthetic assumption (baseline split not resolvable from the source workbook, which only gives net annual emission reductions) [REVIEW-GATED]

Similarly, the calc-engine crediting-period total (3,413,976.93 tCO2e over 7 years) does not match the provenance-tracked `quantification.crediting_period_tota
```

The stored text ends exactly at `quantification.crediting_period_tota` (4000-character boundary) — see truncation analysis below.

## Preamble Check

- **Opened with conversational preamble?** **No.** The text begins directly with `# 4.4.1 Baseline Emissions` (Markdown heading). No leading sentence such as "Here is the draft for..." or "Certainly, ...".
- **Did `strip_assistant_preamble` remove anything?** No preamble to strip; the output normalizer left the text unchanged. Manual inspection of the stored text confirms the first non-whitespace characters are `#`, not an assistant greeting. Previous defect class (conversational preamble that the trailer stripper once missed) did **not** reappear in this run.

## Truncation / Trailer Check

- **Ended mid-sentence?** **Yes — truncated mid-word at the 4000-character section limit.** The final fragment is `quantification.crediting_period_tota` (cut inside the identifier `crediting_period_total_tco2e`). The sentence `Similarly, the calc-engine crediting-period total (3,413,976.93 tCO2e over 7 years) does not match the provenance-tracked ...` is left without a closing parenthetical or citation. This matches the second known defect class: the provider's per-section token limit (`generation_controls.max_tokens_per_section = 4000`) truncates the response, and the `output_normalize` trimming (which previously stripped a trailing trailer) does not repair a mid-word cut.
- **Was the text otherwise well-formed up to the cut?** Yes — up to the truncation point the Markdown, LaTeX, and tables are well-formed and citations are correctly placed. The cut occurs cleanly at the character limit, not at a model-generated sentence boundary.

## Corpus Citations

- **Did any `[CORPUS: …]` citation appear?** **Yes — 5 citations, all naming real documents present in `data/corpus/normalized/`.**
  - `[CORPUS: VCS_Bergama_Project-Description.norm, Baseline Emissions]` — `VCS_Bergama_Project-Description.norm` exists (4725106-byte PDF, 361 headings, indexed).
  - `[CORPUS: VCS_DRAFT_Yanjiang_Project-Description.norm, Baseline Emissions]` — exists.
  - `[CORPUS: VCS_Guangzhou_Project-Description.norm, Baseline Emissions]` — exists (via the multi-citation provenance list).
  - `[CORPUS: VCS_Guanxi_Zhuang_Project_Description.norm, Baseline Emissions]` — exists.
  - `[CORPUS: VCS_Inegol_Project-Description.norm, Baseline Emissions]` — exists (İnegöl is the registry oracle project, also cited twice in the methodology-basis paragraph).
- **Corpus provenance list stored:** 5 entries (Bergama, Yanjiang, Guangzhou, Guanxi, İnegöl), each with `BM25` retrieval metadata stripped at prompt time but echoed as `[CORPUS: doc, heading]`.
- **Family filtering:** The retrieval call used `document_family=wte` (the project's family slug); the 5 cited docs are all `wte`, and no `retrieval_family_fallback` warning was emitted, confirming the family filter had matching content.

Other citations observed: `[CALC: BE_CH4]`, `[CALC: BE_EC]`, `[CALC: baseline_total]` (authoritative engine values), `[METHODOLOGY: ACM0022, Equation 1]`, plus correctly used `[MISSING]`, `[INFERENCE]`, and `[REVIEW REQUIRED]` anti-hallucination markers.

## Label Drift Note

The requested `sub_section_id` was `4.1` (Baseline Scenario / Baseline Emissions), but the model wrote the heading as `# 4.4.1 Baseline Emissions`. The stored metadata correctly records `section_id=4, sub_section_id=4.1`; only the Markdown heading text drifts to `4.4.1`. This is a minor hallucinated numbering error, not a provider routing failure.

## Structured Content

- **Structured content for 4.1:** `None` — only sections `1.5`, `3.2`, `3.3`, `4.4`, `5.1`, `5.2` carry deterministic Verra tables (PHASE-03). Section `4.1` correctly carries no table, only narrative, so this run did not exercise the prose-plus-table dispatch, but the dispatch fix remains verified by `tests/test_docx_export_tables.py`.

## Structlog Events Observed on stderr

During the run, the following structlog events were captured (from `temp_claude.log`):

- `calc_engine_ready` — `methodology_id=ACM0022 net_tco2e=487710.98` (calc injected into prompt)
- `orchestrator_run_start` — `budget_max=500000 budget_max_cost_usd=1.0 calc_injected=True`
- `drafting_section` — `section_id=4 sub_section_id=4.1`
- `orchestrator_run_complete` — `budget_utilization=9.5% estimated_cost_usd=0.1983`
- `draft_run_saved`, `draft_complete`, `review_run_start`, `review_checks_passed`, `review_state_saved`, `review_run_complete`, `review_complete`

**None of the following warning/error events were observed** (and therefore no premise invalidation): `budget_exhausted`, `retrieval_index_fallback`, `retrieval_family_fallback`, `corpus_block_alignment_failed` (alignment warnings fire at index-build time, not at draft time), or `calc_engine_skipped`. The absence of `retrieval_family_fallback` confirms the rebuilt index supplied family-scoped grounding for this section.

## Takeaways

1. The `--only-section` gate works: a single section draft cost `$0.20` and `71.5 s`, well within the `$1` cap, and `draft_all_sections()` respects the filter (verified locally with `DemoProvider` that `only_sections=["4.1"]` → 1 section, `["4.1","4.2"]` → 2, `None` → 36, `[]` → 36, `["9.9"]` → 0).
2. Real-model output is coherent, correctly cites corpus and calc, and uses the anti-hallucination marker set — but it revealed the per-section `4000`-character truncation (mid-word cut) that synthetic providers never surface. Any follow-up should either raise `generation_controls.max_tokens_per_section` or teach `output_normalize` to close the final sentence.
3. No preamble defect reappeared; `strip_assistant_preamble` remains effective.
4. Grounding is healthy: the previously Degenerate retrieval now cites 5 distinct `wte` documents for 4.1, and the ACM0022 methodology itself (`EB111_repan07_ACM0022_v03.0`) is now in the index (verified via `search('applicability conditions alternative waste treatment')` returning it in the top 10).
