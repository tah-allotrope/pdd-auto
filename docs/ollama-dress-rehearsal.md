# Ollama Small-Model Dress Rehearsal — Runbook

PHASE-06 of `plans/2026-07-16-trust-layer-keyless-frontier-proof-plan.md`. Purpose:
complete the first full 36-section local-model run (prior attempts on an 8B model
timed out on CPU-only hardware) using a ~3B model, to shake out nondeterministic-
output bugs — marker parsing, redraft-loop convergence, budget accounting — on free
tokens before any real-model (frontier or subscription-billed) run.

## Prerequisites

- Ollama installed: https://ollama.com/download
- Repo synced: `uv sync --all-extras` (or `pip install -e ".[dev,service,export,llm]"`)
- ~2 GB free disk for the model

## Commands

```bash
# Prerequisites: Ollama installed (https://ollama.com/download), repo synced (uv sync --all-extras)
ollama pull llama3.2:3b
ollama serve   # if not already running as a service

# WTE rehearsal (Inegol)
OLLAMA_MODEL=llama3.2:3b pdd-agent prove --project inegol --providers ollama \
  --output reports/prove-inegol-ollama.md

# Non-WTE rehearsal (rice VM0051)
OLLAMA_MODEL=llama3.2:3b pdd-agent prove --project rice --providers ollama \
  --output reports/prove-rice-ollama.md
```

PowerShell variant:

```powershell
$env:OLLAMA_MODEL = "llama3.2:3b"
pdd-agent prove --project inegol --providers ollama --output reports/prove-inegol-ollama.md
pdd-agent prove --project rice --providers ollama --output reports/prove-rice-ollama.md
```

## Expected duration

On CPU-only hardware (e.g. Intel i5-8250U, no GPU), a 36-section run on a 3B model
can take several hours. Run overnight; do not expect completion within a single
working session. Disable machine sleep for the duration — a multi-hour run
interrupted by sleep/reboot must be restarted (each `prove` run is idempotent: it
always starts a fresh run ID, so a rerun is safe but starts from section 1 again).

Prefer running the two projects (Inegol, rice) as two separate invocations rather
than one combined command, so an interruption only costs one project's progress,
not both.

## Completion bar

The rehearsal counts as complete only when **`Sections failed` = 0** in both
`reports/prove-inegol-ollama.md` and `reports/prove-rice-ollama.md` — i.e. the
model actually produced 36 real drafted sections per project, not
`[OLLAMA ERROR ...]` placeholders. A nonzero `Sections failed` means Ollama
wasn't reachable or crashed mid-run; fix that and rerun before treating the
rehearsal as done.

## Where results land

- `reports/prove-inegol-ollama.md` — WTE family scorecard
- `reports/prove-rice-ollama.md` — rice family scorecard
- `docs/<run-date>-ollama-dress-rehearsal-findings.md` — findings write-up (sections
  drafted/failed, redraft counts, marker-parsing anomalies, wall-clock, and any bugs
  found — each bug gets its own fix + regression test in the same change) and a
  go/no-go statement for proceeding to a real-model run.

## Status as of 2026-07-17

**Blocked, per this plan's own external-dependency contingency.** Ollama is not
installed on the primary dev machine used for this push (a stale `PATH` entry
pointed at `AppData/Local/Programs/Ollama`, but that directory does not exist —
confirmed via `ollama --version` failing with "command not found" and the target
directory not existing on disk). Per the plan: *"External: a machine with Ollama
installed and ~2 GB free disk for the model. If unavailable, this phase blocks
WITHOUT blocking PHASE-05's exit criteria (they are independent)."*

Installing new system software and then running a multi-hour, unattended process
is a consequential enough action (disk space, background CPU load for hours,
potential interruption of other work on the machine) that it should be a
deliberate, confirmed choice by whoever runs the rehearsal, not something done
silently as a side effect of implementing this runbook. This document is ready to
execute the moment a suitable machine (this one, with Ollama installed, or another)
is available — the exact commands above are copy-paste runnable.
