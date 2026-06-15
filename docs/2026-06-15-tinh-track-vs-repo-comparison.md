# Tinh Ta's PDD Track vs. Current Repo — Comparison Report

**Date:** 2026-06-15
**Author:** Generated for Tung Ho (Aiden) via Claude Code
**Scope:** Compare colleague **Tinh Ta**'s PDD-automation work (last ~2 weeks, May 13 – Jun 11 2026) against the current `pdd-auto` repository (`PDD Agent`, through Sprint 3 / commit `314e827`).

> **How this was assembled.** Sources are (1) the Gmail thread *"Project Proposal Development [PDD] introduction"* (Tinh Ta, Hang Tran, Tung Ho, Aiden Roake) and (2) the shared Drive working folder *"Registered WTE PDD"* that Tinh's emails link to. Tinh's concrete artifacts (schema YAML, two prompts, findings doc, tracker) were retrieved and read directly. The repo side is grounded in `README.md`, `schemas/`, `src/pdd_agent/`, `rules/`, `prompts/`, and the prior `docs/2026-05-21-codex-vs-pipeline-comparison.md`. The Seraphin first-draft Word file itself was **not** opened directly — its status is taken from Hang Tran's Jun 11 review and from Tinh's `Schema_ver1.yaml` (see Limitations).

---

## 1. Executive summary

Two parallel tracks are building the same thing — machine-assisted drafting of Verra VCS Project Description documents (v4.4) for waste-to-energy / ACM0022 projects — from two different directions:

- **Tinh's track ("Codex track")** is a *prompt-engineering + Codex* approach: a single well-designed YAML intake schema, two carefully written LLM prompts (document → YAML extraction, and YAML → drafted PDD), plus design research and a manually-run Codex workflow that produces Word first drafts. It is **strong on prose depth, flexible document intake, methodology screening, and anti-hallucination discipline**, but is **manual, has no automation/tests/provenance code, and its quantification (emission calculations) does not yet produce results**.

- **The repo track ("Pipeline track", `pdd-auto`)** is an *engineered Python pipeline*: corpus RAG retrieval (FTS5/BM25), Pydantic schema, rule-based methodology + review engines, a 5-state review workflow, DOCX export against the Verra template, a Vietnam spreadsheet workflow, two demos (Soc Son, Inegol), and 204 passing tests. It is **strong on automation, structure, review rigor, provenance, reproducibility, and packaging**, but currently has **no real LLM provider wired** (so prose is shallow/deterministic), **rigid input intake** (spreadsheet-bound), and **no general methodology screening**.

**Net:** the two tracks are highly complementary. The repo is the more mature *product*; Tinh's recent work contains **three capabilities the repo does not yet have** (general document→YAML intake, methodology auto-screening against Verra's active lists, and a refined LLM drafting prompt with evidence/citation discipline) that are worth absorbing into the pipeline. Conversely, the prior comparison's conclusion that "the Codex script is hardcoded for Inegol only" is **now outdated** — Tinh's new schema + extraction prompt make his approach generalizable.

---

## 2. Timeline of Tinh's work (from the email thread)

| Date | Event |
|---|---|
| May 13 | Tinh introduces the PDD creation project: initial PDD from **VCS templates**, machine-assisted drafting via **Codex**, with a **working folder** and **plan tracker**. |
| May 26 | Hang reviews the working folder ("very impressed"); walkthrough scheduled. |
| May 28 | Tung shares the WtE financial model (`WtE plants carbon model early draft.xlsx`) — later the basis of the repo's Vietnam workbook intake. |
| Jun 9 | Hang supplies the **Seraphin** WTE project inputs (ACM0022, plus Vietnamese EIA) for model testing. |
| Jun 10 | Tinh delivers a **first-draft Word file + YAML** for Seraphin and asks for content review. |
| Jun 11 | Hang's review: content placement is good, **but calculations show no results for baseline or project emissions**; she proposes a **dedicated calculation input form**. |

## 3. Tinh's artifacts (Drive: *Registered WTE PDD*)

| Artifact | Type | What it is |
|---|---|---|
| `Schema_ver1.yaml` | YAML | Comprehensive VCS PD v4.4 intake schema: 15 top-level sections (`project_identity`, `parties`, `technical_design`, `location`, `methodology`, `eligibility_compliance`, `additionality`, `quantification_ex_ante`, `monitoring_plan`, `stakeholder_safeguards`, `sustainable_development`, `evidence_registry`) plus `generation_controls` (inferable vs non-inferable field lists, missing-info policy, citation policy) and `review_flags`. |
| `PDD creation prompt.txt` | Prompt | YAML → drafted PDD. Strict **authority order** (input YAML → evidence registry → template v4.4 → official VCS rules/methodology/tools → comparable projects → general logic); non-invention list; `[MISSING]`/`[INFERENCE]`/`[REVIEW REQUIRED]` markers; evidence-ID citations `[E001]`; Markdown output with per-section "SECTION REVIEW NOTE" sidecars and Missing/Inference/Review/Evidence registers. |
| `Create_YAML_From_Project_Summary_Prompt.txt` | Prompt | Arbitrary project summary (Word/PDF/text/OCR) → valid YAML. Includes **live methodology screening** against Verra active VCS/CDM methodology and tool lists, `suggested_methodologies` with confidence + `active_status_source`, a structured `review_flags` object schema, an `evidence_registry` schema, encoding-fix rules (mojibake/Turkish), and detailed non-invention rules. |
| `PDD intitial findings` | Doc | Design research: registry pattern analysis (PD vs Joint PD; v4.4 vs older section maps), corpus/template folder structure, required-inputs catalogue, and a field-by-field **"LLM-safe vs LLM+human-check"** risk classification. |
| `Trackers` | Sheet | "Project Tracker": 6 tasks — *Create demo, Check web service availability, Input file design, VCS methodologies filter (search logic), Prompt engineering, Pipeline assembly* — **with no progress/status filled in**. |
| Supporting folders | — | `VCS templates`, `PDD test`, `Active methodology`, `Verra registry` / `Verra_registry_download`. (The repo's `ref/PDD staff test-…` is a May-20 snapshot of the `PDD test` folder.) |

## 4. Current repo capabilities (`pdd-auto` / PDD Agent)

- **Corpus RAG, no API cost:** Drive ingest (`gws`) → normalize → WTE keyword bucketing → SQLite **FTS5 BM25** index (`src/pdd_agent/ingest/*`, `retrieval/*`).
- **Schema & domain rules:** Pydantic `ProjectInput` (`schemas/project_input.py`) with double-counting/net-emissions validators; canonical 5-section/30-subsection taxonomy (`schemas/pdd_section_schema.yaml`); **hard-coded** ACM0022/ACM0003 rules + WTE safeguards (`rules/verra/wte_methodology_rules.yaml`), with `run_pre_draft_checks()`/`run_post_draft_checks()`.
- **Drafting:** per-section retrieval → prompt assembly (`prompts/section_draft.md`) → provider call → review gate (`agent/section_orchestrator.py`). Provider abstraction with `NoopProvider`/`DemoProvider`; **OpenAI/Ollama stubs not wired**.
- **Review:** double-counting guards DC-01..04, cross-section numeric consistency, evidence requirements, auto-approval, and a **5-state review workflow** (`review/*`).
- **Export & delivery:** python-docx export against the **Verra VCS v4.4 template** with 11 structured table types, disclaimers, and assumption/reviewer appendices; Drive upload via `gws`.
- **Vietnam spreadsheet workflow:** `WtE plants carbon model early draft.xlsx` → profile → select Soc Son row → `ProjectInput` + assumptions → draft → review → DOCX → gap analysis (`phase06/*`).
- **Demos & tests:** Soc Son (synthetic) and Inegol (Türkiye, VCS-3908, 36 sections, 0 review flags) demos; **204 passing tests**; sprint/phase tracking in `activeContext.md`.

---

## 5. Side-by-side capability matrix

| Capability | Tinh (Codex track) | Repo (Pipeline track) |
|---|---|---|
| Target standard | VCS PD **v4.4** | VCS PD **v4.4** |
| Intake schema | `Schema_ver1.yaml` (flat YAML, generation_controls, review_flags) | Pydantic `ProjectInput` + section taxonomy YAML |
| **Document → structured input** | **Yes** — prompt extracts YAML from Word/PDF/text/OCR | **No** — intake is spreadsheet/`ProjectInput`-bound |
| **Methodology screening** | **Yes** — screens against Verra active VCS/CDM/tool lists, suggests w/ confidence | **No** — hard-coded ACM0022/ACM0003 rules only |
| Drafting engine | Real LLM via Codex (rich prose) | Pipeline w/ **NoopProvider/DemoProvider** (no real LLM wired → shallow prose) |
| Retrieval / corpus grounding | "comparable projects" pasted into prompt | **FTS5 BM25 RAG** with per-section corpus provenance |
| Anti-hallucination discipline | **Strong** — authority order, non-invention, MISSING/INFERENCE/REVIEW markers, evidence IDs | **Strong** — rule checks, assumption register, review gates, TBD tracking |
| Quantification / emissions calc | **Not working** (no baseline/project results — Hang, Jun 11) | Consistency **checks** on provided numbers; **no from-activity calc engine** |
| Automated review | Prompt-instructed registers (manual) | **Coded** consistency + compliance + 5-state workflow |
| Output format | Markdown / Word first draft | **DOCX** on Verra template, 11 table types, appendices |
| Reproducibility / tests | Manual Codex runs; **no tests**; tracker unmarked | **204 tests**, deterministic demos, sprint/phase docs |
| Packaging / CLI | Folder of prompts + schema | Installable `pdd-agent` CLI |

## 6. Where the two tracks agree (conceptual alignment)

Both independently converged on the same architecture:

1. **Schema-driven**: a structured intermediate (YAML / `ProjectInput`) between raw inputs and the drafted document.
2. **v4.4 template-conformant** output with the canonical VCS section order.
3. **Anti-hallucination first**: explicit "do not invent" rules, missing-info flagging, and human-review gates tied to evidence.
4. **First draft for expert review**, never a final validated document.
5. Same domain anchor: **WTE / ACM0022**, same test projects (Inegol earlier; Seraphin/Soc Son now).

This convergence is a strong signal the shared design is sound — and that the two schemas/prompts can be reconciled into one.

## 7. Divergences & gaps

### 7a. What Tinh has that the repo lacks (absorb these)
- **General document → YAML intake.** `Create_YAML_From_Project_Summary_Prompt.txt` ingests arbitrary Word/PDF/text/OCR. The repo's intake is bound to the Vietnam Excel workbook + `ProjectInput`. This is the single biggest capability the repo is missing for onboarding *new* projects quickly. (Confirmed: no `from_summary`/extraction path in `src/`.)
- **Methodology auto-screening.** Tinh screens project activity against Verra's *active* VCS/CDM/tool lists and emits ranked `suggested_methodologies` with confidence and source. The repo hard-codes ACM0022/ACM0003 only. (Confirmed: no methodology-suggestion logic in `src/` or `prompts/`.)
- **A production-grade LLM drafting prompt.** `PDD creation prompt.txt` is more complete than `prompts/section_draft.md` (authority order, evidence-ID citation policy, per-section review-note sidecars, end-of-doc registers) and is a ready upgrade once a real provider is wired.

### 7b. What the repo has that Tinh's track lacks
- **Everything operational:** RAG retrieval + provenance, coded review/consistency/compliance, 5-state workflow, DOCX export on the real template, CLI, 204 tests, reproducible demos, gap-analysis reports. Tinh's track is a set of prompts run by hand with an unmaintained tracker.
- **Provenance & reproducibility** are absent on Tinh's side (no citations to corpus, no run records).

### 7c. The shared gap: quantification / emissions calculations
Hang's Jun 11 review — *"calculations currently show no results for baseline or project emissions"* — is the **most important open item, and it affects both tracks**:
- Tinh's `Schema_ver1.yaml` has a full `quantification_ex_ante` block (formulas, annual_estimates, totals) but every value is `null`; his prompts explicitly **do not recalculate**.
- The repo **checks** numeric consistency (`review/consistency.py`) but does not contain an ACM0022 **calculation engine** that derives baseline/project/leakage emissions from activity data.
- Hang's proposed **dedicated calculation input form** is the right convergence point: a structured calc-input contract feeding a real ACM0022 calculator, consumed by both the YAML intake and the pipeline's quantification section. The repo's existing `assumptions` layer + the WtE Excel model are natural starting materials.

## 8. Relationship to the prior comparison (`2026-05-21-codex-vs-pipeline-comparison.md`)

That report compared the pipeline against Tinh's **earlier, Inegol-specific Codex DOCX** and concluded the pipeline exceeded Codex on provenance, review automation, appendices, and extensibility — with "the Codex script's sole advantage [being] project-specific narrative depth (hardcoded for Inegol)."

**What's changed since May 21:** Tinh's track is **no longer hardcoded for one project.** His `Schema_ver1.yaml` + `Create_YAML_From_Project_Summary_Prompt.txt` make the Codex approach **generalizable to any project and able to screen methodologies** — two things the pipeline still cannot do. So the extensibility gap has narrowed/reversed in those specific dimensions, even as the pipeline retains its decisive lead on automation, provenance, review code, and testing. The two efforts should now **merge** rather than be benchmarked against each other.

## 9. Recommendations

1. **Wire a real LLM provider** into the pipeline and adopt Tinh's `PDD creation prompt.txt` (authority order + citation/registers) as the `section_draft` prompt basis. Removes the pipeline's biggest current weakness (shallow demo prose).
2. **Add a document→`ProjectInput` intake path** based on `Create_YAML_From_Project_Summary_Prompt.txt`, mapped onto the Pydantic schema. Unlocks fast onboarding of new (non-spreadsheet) projects.
3. **Add methodology screening** (Verra active VCS/CDM/tool lists → `suggested_methodologies`) as a pre-draft step, generalizing beyond the hard-coded ACM0022/ACM0003 rules.
4. **Close the calculation gap jointly:** define Hang's "dedicated calculation input form" as a shared calc-input contract and build an ACM0022 baseline/project/leakage calculator that both tracks consume. Highest-priority item per Hang's review.
5. **Reconcile the two schemas** (`Schema_ver1.yaml` ↔ `ProjectInput` + section taxonomy) into one canonical schema with Tinh's `generation_controls`/`review_flags` semantics.
6. **Consolidate the tracker**: fold Tinh's 6 tasks into the repo's sprint/phase tracking (`activeContext.md`) so progress is maintained in one place.

## 10. Limitations of this comparison

- The **Seraphin first-draft Word document was not opened directly**; its status is inferred from Hang's Jun 11 review and Tinh's schema. A direct read would confirm prose quality and the exact calculation gap.
- Tinh's `PDD test`, `VCS templates`, and `Active methodology` Drive folders were inventoried but not exhaustively diffed against the repo corpus.
- The repo's quantification internals were assessed from `review/consistency.py` and method names; a deeper read could refine the "no calc engine" finding.

## Appendix — source references

**Email:** Gmail thread *"Project Proposal Development [PDD] introduction"* (May 13 – Jun 11, 2026). Participants: Tinh Ta `thdt@allotropevc.com`, Hang Tran `httt@allotropevc.com`, Tung Ho `tah@allotropevc.com`, Aiden Roake `atr@allotropevc.com`.

**Drive (working folder "Registered WTE PDD"):** `https://drive.google.com/drive/folders/1_2ethHHCfDk4pS8xIRKg2J_dlt5T5jaa`
**Plan tracker folder:** `https://drive.google.com/drive/folders/1s6Pm42dI6st_uqvadGJLb6hCY8v482K7`
**Tinh artifacts read:** `Schema_ver1.yaml`, `PDD creation prompt.txt`, `Create_YAML_From_Project_Summary_Prompt.txt`, `PDD intitial findings` (Doc), `Trackers` (Sheet).

**Repo:** `pdd-auto` @ `314e827` — `README.md`, `schemas/`, `src/pdd_agent/`, `rules/verra/`, `prompts/section_draft.md`, `docs/2026-05-21-codex-vs-pipeline-comparison.md`.
