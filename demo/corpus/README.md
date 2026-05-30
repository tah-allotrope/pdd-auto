# Demo Corpus Subset

This directory bundles a small, demo-only subset of the normalized PDD corpus so
that the one-command demo scripts (`scripts/run_demo.py`, `scripts/run_inegol_demo.py`)
can produce **corpus-backed provenance citations** out of the box — without a
colleague first having to ingest and index the full corpus.

## What these files are

Each `*.norm.json` file is the *normalized* (plain-text-extracted) form of a public
Verra VCS Project Description, produced by the `pdd-agent normalize` step. They contain
the document's extracted text and heading structure — not the original PDFs.

| File | Project | Why it's included |
|---|---|---|
| `VCS_Soc_Son_Project-Description.norm.json` | Soc Son waste-to-energy (Vietnam) | Direct reference for the Soc Son demo case |
| `VCS_Inegol_Project-Description.norm.json` | İnegöl WTE/AD (Türkiye) | Direct reference for the Inegol demo case |
| `VCS_Bergama_Project-Description.norm.json` | Bergama WTE (Türkiye) | Comparative context for both cases |

## Provenance and licensing

All three are **public Verra VCS registry documents**, published for stakeholder
review on the Verra registry (https://registry.verra.org/). Only the normalized
*extracted text* is committed here (for full-text indexing) — not the source PDFs.
This is a small, transformative subset intended solely for demonstrating the tool's
retrieval/provenance behaviour.

## Why only three?

The full corpus is 18 documents and is intentionally git-ignored
(`data/corpus/normalized/` — see the repo `.gitignore`). Bundling all 18 would bloat
the repository. Three documents are enough to show meaningful, corpus-backed
provenance for both demo cases. Total size of this subset is ~2.6 MB.

## How the demo uses these

The demo scripts auto-build a temporary FTS5 index from this directory
(`data/index/demo.fts.db`) the first time they run, via `pdd-agent demo-setup` /
`pdd_agent.demo_setup.build_demo_index()`. You can also build it explicitly:

```bash
pdd-agent demo-setup
```

## Building the full corpus instead

To work with the complete corpus rather than this demo subset:

```bash
pdd-agent ingest          # inventory + download + normalize + bucket
pdd-agent build-index     # build data/index/corpus.fts.db
```

The full `corpus.fts.db` index takes precedence over the demo index when present.
