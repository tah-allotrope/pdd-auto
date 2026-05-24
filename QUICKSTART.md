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

## Run the Inegol Demo

```bash
python scripts/run_inegol_demo.py
```

This runs the same demo provider against a reverse-engineered Inegol (Türkiye) project input with VCS v4.4 table structures.

## What You Get

After either demo script finishes, you'll find:

| Artifact | Path |
|---|---|
| **DOCX (Soc Son)** | `reports/demo-packages/soc-son-like-waste-to-power-demonstration-project/latest.docx` |
| **DOCX (Inegol)** | `data/runs/<run-id>.docx` |
| **Scorecard** | `reports/demo-scorecard.md` |
| **Section diff** | `reports/section-diff.md` |
| **Comparison report** | `reports/2026-05-21-codex-vs-pipeline-comparison.md` |

Each DOCX contains **36 sections** with readable synthetic prose, zero `[PLACEHOLDER]` markers, and aligned quantification numbers. The cover page carries a bold synthetic-use disclosure.

## Run Tests

```bash
pytest
```

Expected result: **204 passed, ~7 skipped, 0 failed**.

The 6-7 skipped tests are corpus-dependent (they require an FTS5 index built from real Verra documents) and skip gracefully on fresh clones. This is expected behavior.

## Next Steps

For production workflows (corpus ingestion from Drive, spreadsheet mapping, LLM provider integration), see the full [README.md](README.md).
