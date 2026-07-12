# PDD Agent Local Service

A minimal FastAPI service that wraps the PDD drafting pipeline and exposes a
server-rendered web UI for section review.

## Features

- Upload DOCX/PDF/text documents to extract a `ProjectInput` YAML.
- Upload spreadsheets (or use the cached workbook) to generate a `ProjectInput`.
- Create draft runs that execute in FastAPI `BackgroundTasks`, drafting with
  corpus retrieval enabled whenever a built retrieval index is present.
- Review sections: approve, inline edit (with human-edit provenance), or request redraft.
- Download gated DOCX exports; override with `?force=1`.
- Demo/noop by default — no API keys required. Real providers (Ollama,
  OpenAI, Anthropic) are opt-in; see the provider matrix below.

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

- `PDD_SERVICE_PROVIDER` — provider used by the service (default `demo`).
- `PDD_SERVICE_RUNS_DIR` — override the run persistence directory (default `data/runs`).

### Provider opt-in matrix

| `PDD_SERVICE_PROVIDER` | Requirements | Falls back to `demo` when... |
|---|---|---|
| `demo` / `noop` (default) | none | n/a |
| `ollama` | a local Ollama instance reachable at `OLLAMA_BASE_URL` (default `http://localhost:11434`) | never — local inference needs no key or cost ceiling |
| `openai` | `OPENAI_API_KEY` **and** a positive `PDD_MAX_COST_USD` | key missing (`missing_api_key`) or cost ceiling missing/non-positive (`missing_cost_ceiling`) |
| `anthropic` | `ANTHROPIC_API_KEY` **and** a positive `PDD_MAX_COST_USD` | same as above |
| anything else | — | always (`unknown_provider`) |

When a request falls back, the dashboard shows a banner naming the requested
provider, the effective provider, and the reason. The same resolution is
exposed programmatically via `provider_status()` in `main.py`.

## Notes

- The service persists state to `data/runs/{run_id}.json`,
  `data/runs/review-state-{run_id}.json`, and `data/runs/{run_id}.status.json`,
  matching the CLI's persistence layout (all overridable via
  `PDD_SERVICE_RUNS_DIR`). Persistence is dependency-injected through
  `SectionOrchestrator(runs_dir=...)` — importing this module does not alter
  `DraftRun`/`ReviewStateStore` behavior for any other code in the process.
- **Run status**: `{run_id}.status.json` is the source of truth for
  `running` / `complete` / `failed`. On service startup, any run still
  marked `running` is rewritten to `failed` with `"orphaned by service
  restart"` — this can only mean the previous process died mid-run.
- Optional dependencies (`gws`, LibreOffice) are not required; the service
  degrades gracefully when they are absent.
