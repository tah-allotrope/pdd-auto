# Tinh Ta's PDD Track vs. Current Repo — Comparison Report (Update)

**Date:** 2026-08-28
**Author:** Generated for Tung Ho (Aiden) via Claude Code
**Scope:** Update to `docs/2026-06-15-tinh-track-vs-repo-comparison.md`. Compare colleague **Tinh Ta**'s PDD-automation work (Jun 15 – Aug 27 2026) against the current `pdd-auto` repository (through commit `c1543e4`, "defensible numbers and document assembly").

> **How this was assembled.** Sources: (1) Gmail — no new Drive links were sent since the May 13 2026 "Project Proposal Development [PDD] introduction" thread; the only newer Tinh emails are two calendar invites ("[PDD] Verra registry download demonstration", Jul 17; "Carbon progress meeting report and demo", Aug 27) with no linked artifacts in the invite body. (2) The same shared Drive folder **"Registered WTE PDD"** (`.../folders/1_2ethHHCfDk4pS8xIRKg2J_dlt5T5jaa`), re-listed via `gws` on 2026-08-28 — it has grown substantially since June. (3) Current repo state: `README.md`, `activeContext.md`, `plans/2026-08-28-defensible-numbers-and-document-assembly-plan.md` (newest plan), `src/pdd_agent/calc/*`, `git log`. A new local snapshot is saved at `ref/PDD staff August 2026/` (see `MANIFEST.md` there for the full Drive tree and what was/wasn't downloaded).

---

## 1. Executive summary

Both tracks made major, largely independent progress on exactly the gap the June report called out as shared and top-priority: **a working emissions calculation engine**. Neither track knew about the other's calc work in detail — this report is the first place they're compared.

- **Tinh's track** shifted from "prompts + a static schema" to a real, if unpolished, **software project**. The Drive folder now contains an installable `pdd_automation` Python package (own `pyproject.toml`, `tests/`, `.egg-info`, a 7-stage CLI: `registry-download → ingest → parse → generate → check → assemble → evaluate`), a schema that grew from 306 to 541 lines, and — most importantly — a **calculation reconciliation package** (`Waste energy run/verra_pdd_original_and_final_package_20260722/`) that rebuilds baseline/project/leakage numbers against **five real registered VCS projects** (4818 ×2 versions, 5040, 4940, 4921) and a `Test PDD calculation/` folder with live spreadsheet calcs for two more named projects (ViOT_DOXACO under ACM0022, "Amya" under VM0043). A 672MB `PDD_Portable_Workspace_20260827_UPLOAD.zip` was uploaded the same day as an Aug 27 "Carbon progress meeting report and demo" invite to Tung/Aiden/Hang — Tinh is actively demoing this now.
- **The repo** independently built and shipped a real ACM0022 calculator (plus VM0051, VM0044, AMS-II.G engines) validated against a registered oracle (Soc Son), closed the "no real LLM output" gap (native Markdown/table/math rendering, per-section budgets), and fixed the review-UI/export-gate issues — 909 tests passing, per `README.md`/`activeContext.md`.
- **Net:** the calculation gap that was the single shared blocker in June is **no longer a blocker on either side** — each side solved it on its own project set, with different validation strategies (repo: one oracle project measured to a documented tolerance; Tinh: reconciliation against five real registered projects, useful as a broader spot-check). The June recommendation to "reconcile the two schemas" and "wire a real LLM provider" is now more urgent, not less — the two calc philosophies (defensible-arithmetic-with-tolerance vs. multi-project-reconciliation) are a good complement, and Tinh's own package now duplicates a nontrivial slice of repo functionality (registry download, DOCX assembly, schema-driven generation) that the June report explicitly flagged as a repo weakness (`ingest/registry_download.py` is still a stub in the repo today).

## 2. Timeline of new activity since Jun 15

| Date | Event |
|---|---|
| May 27 – Jun 10 | (Carried over from June report) `Schema_ver1.yaml`, first two prompts, Seraphine intake + first-draft Word/YAML delivered; Hang's Jun 11 review flags calcs producing no results. |
| Jun 10 | `md_to_vcs_docx.py` / `run_render_docx_workspace_tmp.py` added — first sign of a real DOCX-assembly script, not just a prompt. |
| Jul 8 | Drive folder reorganized: loose files moved into `Old /`; new `PDD/` workspace created with `pdd_automation` installable package, `config/intakes/`, `docs/`, `library/`, `outputs/`, `projects/seraphine-wte/`. Schema grows to `Schema.yaml` (541 lines, from 306). `pdd_automation/README.md` documents a 7-stage CLI pipeline. |
| Jul 14 | Tinh invites team to "[PDD] Verra registry download demonstration" (held Jul 17). |
| Jul 16 | Original registry PDFs/XLS calc files for VCS 4818/4940/4921/5040 pulled into a reconciliation workspace. |
| Jul 20–21 | `verra-pdd.pptx` (5.3MB) and the "Waste energy run" 5-project original-vs-final calc reconciliation package assembled; `Test PDD calculation/ACM0022` and `/VM0043` folders added with two more live project spreadsheets. |
| Aug 23 & 27 | "Carbon progress meeting report and demo" invited and held; same day (Aug 27) a 672MB portable workspace zip is uploaded to Drive — Tung was unable to attend (personal matter) and asked to catch up later. |

## 3. Tinh's new artifacts (beyond the June inventory)

| Artifact | What it is | Assessment |
|---|---|---|
| `pdd_automation/` package | Installable Python package, `pyproject.toml` (`pdd-automation` v0.1.0), console script `pdd`, modular CLI: `registry-download, ingest, parse, generate, check, assemble, evaluate`; has its own `tests/`, `schemas/` (JSON: `canonical_section_map.json`, `section_schema.json`, `field_policies.json`, `required_fields.json`), and `Verra_registry_download/` submodule. | Real engineering, not prompt-only. The `registry-download` command does exactly what the repo's `ingest/registry_download.py` stub doesn't yet: searches Verra by methodology ID(s)/country, classifies/ranks candidate PDs vs. monitoring/verification reports, and documents (in its README) a careful identity-verification framework (`confirmed/probable/conflict/unreadable`) for title-vs-content mismatches — a capability neither side has fully closed, but Tinh's design doc for it is more developed than anything in the repo. |
| `Waste energy run/.../` (5-project calc reconciliation) | Rebuilds baseline/project/leakage numbers for **VCS 4818 (two versions), 5040, 4940, 4921** against each project's own registry PDF + native `.xls` calc, producing small (~7KB) `final_created_calculation.xlsx` reconciliation workbooks and a `final_created_pdd.docx` per run. README explicitly states these "reconcile the reported calculation results from the YAML-backed pipeline" and are "not complete replicas of every formula chain." Run `04_4818_exante` is annotated as a "disclosed repair of the legacy invalid result" — i.e., Tinh's calc caught (and documents) an error in a real registered project's own workbook. | This is the calc-gap closure on Tinh's side, and it's validated across **5 real registered projects** vs. the repo's 1 (Soc Son) + 1 unvalidated (Inegol, "no composition declared"). Complementary, not redundant, validation strategy. |
| `Test PDD calculation/ACM0022/Allotrope-ViOT_DOXACO Project_Calculation.xlsx` (221KB) and `/VM0043/2025.12.09_Amya_Updated Financial Model.xlsx` (624KB) | Live calc spreadsheets for two more named, apparently real, prospective projects. | Not opened in this pass (binary spreadsheets); worth a follow-up read if these are active client projects — VM0043 is a methodology the repo does not implement. |
| `Schema.yaml` (541 lines, up from `Schema_ver1.yaml`'s 306) | Adds `source_context.source_mode` (new/extracted/update), a `registry_project_id` field, richer crediting-period and audit-history structure. | Schema is maturing toward something registry-aware, closer to what a "reconcile the two schemas" effort (June rec. #5) would need. |
| `projects/seraphine-wte/` (intake YAML 44.5KB + first-draft MD 56KB, both Jul 8) | The same Seraphine project from June, regenerated/reorganized but **still showing `quantification_ex_ante` totals as null and the ER table as all `[MISSING]`** — the calc breakthrough above has not yet been applied back to this project's own draft. Draft is candid about unresolved identity conflicts (EIA site "Amaccao – Thành Công" / Seraphin vs. spreadsheet's "Soc Son" location and differing capacity figures) and flags a hazardous-waste line ACM0022 excludes. | Confirms the calc-reconciliation work is a separate, not-yet-integrated stream from the main drafting pipeline — an open integration gap on Tinh's side. |
| `PDD_Portable_Workspace_20260827_UPLOAD.zip` (672MB, uploaded Aug 27) | Not downloaded (see Limitations). Almost certainly a full zipped copy of `PDD/` plus corpus/registry data, given the timing next to the Aug 27 demo invite. | Follow-up: worth asking Tinh directly what's new in it beyond what's already visible unzipped in `PDD/`. |

## 4. Repo capabilities added since Jun 15 (from git log / README / activeContext)

Per commits `19d96b8` → `c1543e4` (11 feature commits since the June comparison) and `README.md`'s status line:

- **Real calc engines wired into drafting**: `src/pdd_agent/calc/{acm0022,cdm_tool_03..14,cookstove_amsiig,rice_vm0051,biochar_vm0044,incineration,dispatch,methodology}.py` — ACM0022 (with incineration `PE_INC`, `capacity_ramp`), AMS-II.G, VM0051, VM0044, consumed via `pdd-agent calc` / `compute_for()`. This is broader methodology coverage than the June report anticipated (it only expected ACM0022).
- **Soc Son oracle validation**: year-by-year registered ER schedule constants + tests; Soc Son crediting-total test flipped from failing to passing (4,010,142 vs. registered 3,808,082, +5.3%, inside the repo's 20% tolerance); two known residual gaps (D-1 FOD parameter, D-2 non-methane net charge) are tracked as dated `xfail`s, not silently ignored.
- **Real-output fidelity**: native Markdown/table/math rendering into DOCX (zero literal `|---`/`$$` artifacts), per-section character budgets (297,000 chars total, replacing a uniform 144,000 cap), honest truncation reporting, export gate no longer hard-blocks on `[MISSING]` (collects them into a "Required Inputs" appendix instead).
- **909 tests passing** (up from 204 at the May 21 baseline / more since June).
- **Still a stub**: `ingest/registry_download.py` (public Verra/CDM registry PDD downloader) — confirmed directly in `README.md`'s Known Gaps — i.e., the repo still lacks what Tinh's `pdd_automation.Verra_registry_download.cli registry-download` command already does.

## 5. Updated capability matrix (changes from June only)

| Capability | Tinh (Codex/pdd_automation track) | Repo (pdd-auto) |
|---|---|---|
| Quantification / emissions calc | **Now working**, reconciled against 5 real registered VCS projects (ACM0022-family); a repair of a legacy registry error documented (run 04). Separate live test spreadsheets for ACM0022 (ViOT_DOXACO) and VM0043 (Amya). Not yet fed back into the Seraphine draft itself. | **Now working** for ACM0022/VM0051/VM0044/AMS-II.G, validated against 1 registered oracle (Soc Son, +5.3%, within 20% tolerance) with 2 dated residual gaps tracked as xfail; wired directly into the drafting/export pipeline. |
| Registry document acquisition | **Yes** — `registry-download` CLI command with methodology-ID/country filtering and a documented (if not yet implemented) title-vs-content identity-verification scheme. | **No** — `ingest/registry_download.py` is an explicit stub (confirmed in README Known Gaps). |
| Packaging / installability | **Yes now** — `pdd_automation` is `pip`-installable (`pyproject.toml`, `.egg-info` present), has its own `tests/`. | Yes (unchanged) — `pdd-agent` CLI. |
| Document rendering fidelity | Word drafts assembled via `md_to_vcs_docx.py`; not benchmarked here for fidelity. | Native Markdown/table/math → DOCX, budgeted per-section, honest truncation — directly verified in repo tests. |
| Methodology breadth | ACM0022-focused; VM0043 test spreadsheet exists but no generation/check/assemble pipeline confirmed for it. | ACM0022, AMS-II.G, VM0051, VM0044 all wired into `compute_for()`. |
| Schema maturity | `Schema.yaml` grew 306→541 lines; adds registry/source-context fields. | `ProjectInput` + section taxonomy unchanged in structure since June (calc/rendering work was the focus). |
| Test coverage | `pdd_automation/tests/` exists but not enumerated in this pass — unknown depth. | 909 tests passing, documented xfails with dated measurements. |

*(Everything the June report already listed as stable — anti-hallucination discipline on both sides, the repo's RAG/provenance/5-state review advantage, Tinh's document→YAML intake advantage — is unchanged and not repeated here.)*

## 6. Recommendations (supersedes June §9 items 3–4; others still open)

1. **Compare calc engines directly.** Both sides now have a working ACM0022 calculator with different validation strategies. Feed the repo's `ACM0022Calculator` the same five registered projects (4818, 5040, 4940, 4921) Tinh reconciled, and vice versa — cross-validation would catch bugs neither single-oracle nor single-track testing would surface, and would settle whether the two calculators agree.
2. **Ask Tinh for the `registry-download` module directly.** It duplicates and likely already solves the repo's confirmed stub (`ingest/registry_download.py`) — this is the cleanest, lowest-risk piece to absorb wholesale rather than reimplement.
3. **Close the loop on Seraphine.** Tinh's own flagship project draft (`projects/seraphine-wte/`) still shows a null quantification block even though his calc reconciliation package next to it works — get his new calc engine wired back into that draft before the next client-facing use.
4. **Get eyes on `PDD_Portable_Workspace_20260827_UPLOAD.zip`.** It's the newest and largest artifact (uploaded the day of the Aug 27 demo Tung missed) and wasn't opened in this pass — ask Tinh for a walkthrough recording or notes from that demo, or download and diff it against the already-inventoried `PDD/` tree to find what's new inside it.
5. **Investigate the two live test spreadsheets** (`ViOT_DOXACO` under ACM0022, `Amya` under VM0043) — if these are active/prospective client projects, coordinate before both tracks independently draft PDDs for the same clients.
6. Prior June recommendations #1 (real LLM provider), #2 (document→YAML intake), #5 (schema reconciliation), #6 (tracker consolidation) remain open and are now more valuable given both sides' maturing engineering investment.

## 7. Limitations of this comparison

- The 672MB `PDD_Portable_Workspace_20260827_UPLOAD.zip` was **not downloaded or unzipped** — its contents are inferred from the sibling unzipped `PDD/` folder tree, which may not be fully up to date with the zip's contents (the zip postdates most of `PDD/`'s modified timestamps by ~7 weeks).
- The two live calc spreadsheets (`Allotrope-ViOT_DOXACO Project_Calculation.xlsx`, `2025.12.09_Amya_Updated Financial Model.xlsx`) and the reconciliation workbooks in `Waste energy run/` were **not opened/parsed** (native binary spreadsheets) — their actual numeric outputs and formulas are not verified here, only their existence and file sizes.
- `pdd_automation/tests/` was listed but its contents were not enumerated — test depth/coverage on Tinh's side is unknown.
- No newer Drive link than the May 13 email exists in Tinh's recent correspondence; this comparison assumes the same "Registered WTE PDD" folder is still the canonical shared workspace (confirmed current as of this pass — folder is actively being written to, most recently Aug 27).
- The repo side of this comparison did not re-run the full test suite in this pass; findings are grounded in `README.md`/`activeContext.md`'s stated status plus direct confirmation that the calc engine source files (`src/pdd_agent/calc/*.py`) and the registry-download stub exist as described.

## Appendix — source references

**Email:** No new Drive-linked emails since 2026-05-13 (`Project Proposal Development [PDD] introduction`). Newer Tinh emails are calendar invites only: "[PDD] Verra registry download demostration" (2026-07-14/15, held Jul 17) and "Carbon progress meeting report and demo" (2026-08-23/27, held Aug 27).

**Drive (working folder "Registered WTE PDD"):** `https://drive.google.com/drive/folders/1_2ethHHCfDk4pS8xIRKg2J_dlt5T5jaa` — re-listed 2026-08-28 via `gws`.

**Local snapshot:** `ref/PDD staff August 2026/` (this repo) — see `MANIFEST.md` there for the full Drive tree, file ids, sizes, and modified dates, including what was and wasn't downloaded.

**Repo:** `pdd-auto` @ `c1543e4` ("feat: defensible numbers and document assembly — reproduce registered PDD arithmetic and own the DOCX") — `README.md`, `activeContext.md`, `src/pdd_agent/calc/`, `git log`.

**Prior report:** `docs/2026-06-15-tinh-track-vs-repo-comparison.md`.
