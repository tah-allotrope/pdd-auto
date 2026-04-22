# Research Brief: Agentic Low-Cost Waste-to-Energy PDD Creation

**Date:** 2026-04-22
**Modes run:** domain, codebase, literature
**Depth:** standard
**Invocation context:** Produce a compact research brief for "agentic low-cost waste-to-energy carbon credit PDD creation using Verra-style project documents and Google Workspace CLI for corpus ingestion", incorporating local workspace inputs and external evidence from `gws`/Drive docs.

---

## Synthesis
The strongest near-term path is not generic "carbon document generation" but a narrow, methodology-bucketed pipeline for waste-to-energy PDD drafting: Verra-style project documents are public, structurally repetitive, and explicitly tied to methodologies, while your local sample PDF shows a machine-readable section hierarchy suitable for section-level parsing and retrieval (`template/VCS_Soc Son_Project-Description.pdf`; `research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt`; https://verra.org/programs/verified-carbon-standard/). The internal workflow note is directionally sound on template-first generation, but its solar-focused corpus assumptions should be replaced with a waste-to-energy bucket keyed by methodology, template/version, project structure, and geography before any automation quality claims are made (`research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt`).

Google Workspace CLI is credible for low-cost corpus ingestion because its Drive surface is dynamically generated from Google Discovery docs, exposes `drive files list/get`, and returns structured JSON rather than HTML scraping output (https://github.com/googleworkspace/cli/blob/main/README.md; local `gws --help`; local `gws schema drive.files.list`). In this workspace, `gws drive files list` and `gws drive files get` already work against an accessible Drive corpus and returned a live DOCX plus parent folder metadata, which is enough to support inventorying, bucketing, and later download/export workflows (observed local command results on 2026-04-22).

The main planning risk is not ingestion cost but evidence integrity: Verra requires methodology-specific eligibility, additionality, baseline, safeguards, validation, and public-comment handling, so an agentic system should draft by section with citations and explicit human-review gates rather than produce monolithic "complete" PDDs (https://verra.org/programs/verified-carbon-standard/). [NOTE] For Google Docs-native sources, ingestion must distinguish metadata retrieval (`files.get`) from content retrieval/export (`files.export` or browser `exportLinks`), while blob files can use `files.get?alt=media`; this affects how a Drive corpus is normalized and cached (https://developers.google.com/workspace/drive/api/guides/manage-downloads).

## Domain
### Discovery
The key domain sources were the local waste-to-energy methodology map, the local POC workflow memo, Verra's VCS overview, and the sample Soc Son waste-to-power project description PDF (`research/Waste to Energy Carbon Credits.md`; `research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt`; `template/VCS_Soc Son_Project-Description.pdf`; https://verra.org/programs/verified-carbon-standard/).

### Verification
The local methodology map usefully distinguishes creditable activities across MBT sorting, anaerobic digestion, RDF production, and cement fuel substitution, and explicitly flags double-counting risk between landfill-diversion and fossil-fuel-substitution claims, which is central for any retrieval/generation schema (`research/Waste to Energy Carbon Credits.md`). Verra's public VCS description confirms that projects must follow the VCS Standard, apply approved accounting methodologies, undergo independent auditing, and publish registry information, so any automated drafting system has to be registry- and methodology-aware rather than template-only (https://verra.org/programs/verified-carbon-standard/).

### Comparison
Compared with the local solar-oriented POC memo, the waste-to-energy domain has more heterogeneous activity chains and credit ownership boundaries; a single project may combine diversion, digestion, energy generation, and industrial fuel substitution, which makes section logic and anti-double-counting checks more important than pure template filling (`research/Waste to Energy Carbon Credits.md`; `research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt`). The Soc Son sample appears closer to the target problem than the memo's recommended solar benchmark because it already reflects waste-to-power project structure and section ordering (`template/VCS_Soc Son_Project-Description.pdf`).

### Synthesis
Plan around homogeneous waste-to-energy buckets, not the whole VCM. The first useful bucket is likely "Verra-style waste-to-power / municipal solid waste projects in Vietnam or nearby markets using the same methodology family and template generation," because that minimizes section drift while preserving enough corpus size to retrieve examples (`research/Waste to Energy Carbon Credits.md`; `template/VCS_Soc Son_Project-Description.pdf`).

### Confidence
Medium - strong local evidence and official program evidence, but methodology/version details for the Soc Son sample were not fully verified from the registry page in this session.

## Codebase
### Discovery
The workspace currently contains two research notes and one sample project PDF; there is no local ingestion or generation code yet, so the practical "codebase" is the available artifact set plus the installed `gws` CLI surface (`research/Waste to Energy Carbon Credits.md`; `research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt`; `template/VCS_Soc Son_Project-Description.pdf`; local `gws --help`).

### Verification
`gws --help` documents a stable command pattern of `gws <service> <resource> <method>` with Drive support and JSON output, while `gws schema drive.files.list` and `gws schema drive.files.get` expose query parameters such as `q`, `driveId`, `corpora`, `supportsAllDrives`, and content-vs-metadata semantics (`alt=media` for blob downloads) that are directly relevant to corpus ingestion (local `gws --help`; local `gws schema drive.files.list`; local `gws schema drive.files.get`). A live `gws drive files list` returned a DOCX file and a live `gws drive files get` returned its metadata, parent folder ID, and `webViewLink`, so access is not hypothetical in this environment (observed local command results on 2026-04-22).

### Comparison
For corpus assembly, `gws` is better suited than browser scraping because it provides typed metadata, pagination, shared-drive parameters, and predictable JSON output (https://github.com/googleworkspace/cli/blob/main/README.md; local `gws --help`). However, metadata enumeration and content acquisition differ by file type: blob files can be downloaded with `files.get`/`alt=media`, but Google Docs/Sheets/Slides require export workflows, which means the ingestion pipeline needs MIME-aware branches from day one (https://developers.google.com/workspace/drive/api/guides/manage-downloads).

### Synthesis
The cheapest robust ingestion stack is: `gws drive files list` for inventory, bucketing, and metadata capture; `gws drive files get` for file-level enrichment and parent/folder lineage; MIME-aware download/export steps for normalization into local text/PDF/DOCX; then section extraction against the sample Verra-style heading tree. Because the workspace already proves Drive query access, the gating unknown is not authentication but folder targeting, MIME normalization, and bucket discipline (observed local command results on 2026-04-22; https://developers.google.com/workspace/drive/api/guides/search-files).

### Confidence
High - command surface and live local behavior were both directly observed.

## Literature
### Discovery
The most relevant external literature-level source found in-session was a recent RAG survey, supplemented by official Google Drive guidance on search and export/download behavior and Verra's program documentation (https://arxiv.org/abs/2312.10997; https://developers.google.com/workspace/drive/api/guides/search-files; https://developers.google.com/workspace/drive/api/guides/manage-downloads; https://verra.org/programs/verified-carbon-standard/).

### Verification
The RAG survey is credible for architectural guidance, not carbon-market specifics: it argues that retrieval improves accuracy, freshness, and traceability for knowledge-intensive generation, which maps well to PDD drafting where registry rules and methodology clauses must remain inspectable (https://arxiv.org/abs/2312.10997). Google's Drive docs are official and current enough to rely on for search/export behavior, including `fields`, `q`, corpora narrowing, and the distinction between listing metadata and exporting Workspace-native documents (https://developers.google.com/workspace/drive/api/guides/search-files; https://developers.google.com/workspace/drive/api/guides/manage-downloads).

### Comparison
The literature and docs together favor retrieval-backed section drafting over end-to-end free generation. RAG handles repetitive but high-stakes text better when the system can cite retrieved examples and standards, while Drive's official APIs make corpus freshness and provenance cheaper to maintain than a scraped registry dump (https://arxiv.org/abs/2312.10997; https://developers.google.com/workspace/drive/api/guides/search-files).

### Synthesis
Planning should assume an agentic RAG workflow with explicit provenance per section: retrieve methodology-aligned exemplars, template requirements, and source facts; draft one section; then run a compliance-oriented check against methodology and registry rules. The evidence does not support promising fully autonomous PDD completion without review, but it does support a low-cost, high-leverage drafting assistant that reduces blank-page work and preserves citations (https://arxiv.org/abs/2312.10997; https://verra.org/programs/verified-carbon-standard/).

### Confidence
Medium - strong architectural evidence, but sparse peer-reviewed literature specific to carbon-credit PDD automation was identified in this pass.

## Sources
- `research/Waste to Energy Carbon Credits.md` - local note; methodology map and double-counting pitfalls for waste-to-energy project chains
- `research/VCM_Document_Generation_POC_Workflow Updated April 2026.txt` - local internal memo; existing assumptions, cost thesis, and corpus-bucketing guidance
- `template/VCS_Soc Son_Project-Description.pdf` - local sample project document; real Verra-style section hierarchy for waste-to-power parsing
- https://verra.org/programs/verified-carbon-standard/ - official program page; VCS process, rules, public registry, validation, and project-development constraints
- https://github.com/googleworkspace/cli/blob/main/README.md - official project README; `gws` architecture, auth model, JSON-first output, and Drive coverage
- https://developers.google.com/workspace/drive/api/guides/search-files - official Google Drive doc; file search, `fields`, `q`, corpora, and incomplete-search behavior
- https://developers.google.com/workspace/drive/api/guides/manage-downloads - official Google Drive doc; metadata vs blob download vs Workspace export behavior
- https://arxiv.org/abs/2312.10997 - survey paper; RAG benefits and architectural patterns relevant to citation-preserving document drafting
