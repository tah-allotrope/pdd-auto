# PDD Agent Local Service

A minimal FastAPI service that wraps the PDD drafting pipeline and exposes a
server-rendered web UI for section review.

## Features

- Upload DOCX/PDF/text documents to extract a `ProjectInput` YAML.
- Upload spreadsheets (or use the cached workbook) to generate a `ProjectInput`.
- Create draft runs that execute in FastAPI `BackgroundTasks`.
- Review sections: approve, inline edit (with human-edit provenance), or request redraft.
- Download gated DOCX exports; override with `?force=1`.
- Demo/noop providers only — no API keys required by default.

## Setup

From the repository root:

```bash
python scripts/setup_service.py
```

This script:

- checks Python >=3.11,
- installs the package with `[dev,service,export]` extras,
- checks optional tooling (LibreOffice, `gws` CLI),
- optionally validates API keys only if you opt in,
- prints the launch command.

## Run

```bash
uvicorn pdd_agent.service.main:app --reload
```

Then open http://localhost:8000/dashboard.

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Redirect to dashboard |
| GET | `/dashboard` | Run list + intake forms |
| GET | `/runs/{run_id}` | Run detail page |
| GET | `/runs/{run_id}/sections/{section_key}` | Section review page |
| POST | `/api/intake/document` | Upload document → ProjectInput YAML |
| POST | `/api/intake/spreadsheet` | Map spreadsheet → ProjectInput YAML |
| POST | `/api/runs` | Create run from ProjectInput YAML |
| GET | `/api/runs` | List runs with status |
| GET | `/api/runs/{run_id}` | Run details + sections summary |
| GET | `/api/runs/{run_id}/sections/{section_key}` | Section detail |
| POST | `/api/runs/{run_id}/sections/{section_key}/approve` | Approve section |
| POST | `/api/runs/{run_id}/sections/{section_key}/edit` | Edit section text |
| POST | `/api/runs/{run_id}/sections/{section_key}/redraft` | Redraft section |
| GET | `/api/runs/{run_id}/docx` | Download gated DOCX |

## Environment Variables

- `PDD_SERVICE_PROVIDER` — provider used by the service (`demo` or `noop`; default `demo`).
- `PDD_SERVICE_RUNS_DIR` — override the run persistence directory (default `data/runs`).

## Notes

- The service persists state to `data/runs/{run_id}.json` and
  `data/runs/review-state-{run_id}.json`, matching the CLI.
- Optional dependencies (`gws`, LibreOffice) are not required; the service
  degrades gracefully when they are absent.
