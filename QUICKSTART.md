# Demo Quickstart

Get from zero to a working PDD DOCX in under 5 minutes. **No API keys, no Google Drive, no Node.js required.**

## Prerequisites

- **Python 3.11+**
- **pip**
- **git**

That's it. The demo path does not need `gws`, Node.js, LLM API keys, or Drive access.

## Setup

```bash
# Clone the repo
git clone https://github.com/anomalyco/pdd-agent.git
cd pdd-agent

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install the package
pip install -e ".[dev]"
```

## Run the Soc Son Demo

```bash
python scripts/run_demo.py
```

This runs the deterministic `DemoProvider` against a synthetic Soc Son-like waste-to-energy project and publishes a client-demo package under `reports/demo-packages/`.

Add `--open` to automatically open the generated DOCX:

```bash
python scripts/run_demo.py --open
```

## Run the Inegol Demo

```bash
python scripts/run_inegol_demo.py
```

This runs the same demo provider against a reverse-engineered Inegol (Türkiye) project input with VCS v4.4 table structures.

Add `--open` to automatically open the generated DOCX:

```bash
python scripts/run_inegol_demo.py --open
```

## What You Get

After either demo script finishes, you'll find:

| Artifact | Path |
|---|---|
| **DOCX (Soc Son)** | `output/latest-demo.docx` |
| **DOCX (Inegol)** | `output/latest-inegol-demo.docx` |
| **Full package** | `reports/demo-packages/<project-slug>/` |
| **Scorecard** | `reports/demo-scorecard.md` |
| **Section diff** | `reports/section-diff.md` |
| **Comparison report** | `docs/2026-05-21-codex-vs-pipeline-comparison.md` |

Each DOCX contains **36 sections** with readable synthetic prose, zero `[PLACEHOLDER]` markers, and aligned quantification numbers. The cover page carries a bold synthetic-use disclosure.

## Preview Without Running

To see what the tool produces without installing or running anything, open one of the pre-built example files:

- `examples/example-soc-son-demo.docx` — Synthetic Soc Son-like WTE project
- `examples/example-inegol-demo.docx` — Synthetic İnegol facility (VCS-3908)

Both carry a bold synthetic-use disclaimer on the cover page. See [examples/README.md](examples/README.md) for details.

## Run Tests

```bash
pytest
```

Expected result: **204 passed, ~7 skipped, 0 failed**.

The 6-7 skipped tests are corpus-dependent (they require an FTS5 index built from real Verra documents) and skip gracefully on fresh clones. This is expected behavior.

## Next Steps

For production workflows (corpus ingestion from Drive, spreadsheet mapping, LLM provider integration), see the full [README.md](README.md).
