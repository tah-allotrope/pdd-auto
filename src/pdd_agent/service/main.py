"""FastAPI service wrapping the PDD drafting pipeline.

Uses only the ``demo`` provider by default so the service can run without
API keys. Execution happens in FastAPI ``BackgroundTasks``; state is persisted
in ``data/runs/{run_id}.json`` and ``data/runs/review-state-{run_id}.json``.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml
from dotenv import find_dotenv, load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv(find_dotenv(usecwd=True))

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.export.docx_export import export_run_to_docx
from pdd_agent.ingest.extract import extract_project_input
from pdd_agent.llm.env_config import configure_provider_from_env
from pdd_agent.llm.provider import get_provider_registry
from pdd_agent.phase06.spreadsheet_mapper import generate_project_artifacts
from pdd_agent.review.states import ReviewState, ReviewStateStore, init_review_state
from schemas.project_input import ProjectInput

logger = structlog.get_logger()

REPO_ROOT = Path(__file__).resolve().parents[3]


def _service_runs_dir() -> Path:
    return Path(os.environ.get("PDD_SERVICE_RUNS_DIR", REPO_ROOT / "data" / "runs"))


RUNS_DIR = REPO_ROOT / "data" / "runs"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    sweep_orphaned_runs()
    yield


app = FastAPI(title="PDD Agent Service", version="0.1.0", lifespan=_lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _provider_name() -> str:
    """Return the provider to use for drafting.

    Defaults to ``demo`` so no API keys are required.
    """
    return os.environ.get("PDD_SERVICE_PROVIDER", "demo").lower()


_last_provider_status: dict[str, str | None] = {
    "requested": "demo",
    "effective": "demo",
    "reason": None,
}


def provider_status() -> dict[str, str | None]:
    """Return the most recent _get_provider() resolution for UI display."""
    return dict(_last_provider_status)


def _parse_positive_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _get_provider(provider_name: str | None = None):
    """Resolve the drafting provider for a run.

    - ``demo`` / ``noop``: always allowed, no key or cost ceiling required.
    - ``ollama``: always allowed (local inference, no key required).
    - ``openai`` / ``anthropic``: requires both ``{PROVIDER}_API_KEY`` and a
      positive ``PDD_MAX_COST_USD``; falls back to ``demo`` with a logged
      reason otherwise.
    - anything else: falls back to ``demo`` with reason ``unknown_provider``.

    Never raises for a bad name — the service must stay usable even when
    misconfigured.
    """
    global _last_provider_status
    name = (provider_name or _provider_name()).lower()
    registry = get_provider_registry()
    reason: str | None = None
    effective = name

    if name in ("demo", "noop"):
        pass
    elif name == "ollama":
        configure_provider_from_env("ollama")
    elif name in ("openai", "anthropic"):
        if not os.environ.get(f"{name.upper()}_API_KEY"):
            reason = "missing_api_key"
            effective = "demo"
        elif _parse_positive_float(os.environ.get("PDD_MAX_COST_USD")) is None:
            reason = "missing_cost_ceiling"
            effective = "demo"
        else:
            configure_provider_from_env(name)
    else:
        reason = "unknown_provider"
        effective = "demo"

    if reason:
        logger.warning("service_provider_fallback", requested=name, reason=reason)

    _last_provider_status = {"requested": name, "effective": effective, "reason": reason}
    return registry.get(effective)


def _runs_dir() -> Path:
    return Path(os.environ.get("PDD_SERVICE_RUNS_DIR", RUNS_DIR))


def _run_json_path(run_id: str) -> Path:
    return _runs_dir() / f"{run_id}.json"


def _review_state_path(run_id: str) -> Path:
    return _runs_dir() / f"review-state-{run_id}.json"


def _pending_marker_path(run_id: str) -> Path:
    return _runs_dir() / f".pending-{run_id}"


def _generate_run_id() -> str:
    return f"run-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"


def _parse_section_key(section_key: str) -> tuple[str, str]:
    """Parse ``section_id/sub_section_id`` into components."""
    parts = section_key.split("/", 1)
    section_id = parts[0]
    sub_section_id = parts[1] if len(parts) > 1 and parts[1] else ""
    return section_id, sub_section_id


def _format_section_key(section_id: str, sub_section_id: str) -> str:
    return f"{section_id}/{sub_section_id or ''}"


def _load_run_json(run_id: str) -> dict[str, Any]:
    path = _run_json_path(run_id)
    if not path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_run_json(run_id: str, data: dict[str, Any]) -> None:
    path = _run_json_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_review_state(run_id: str) -> ReviewStateStore:
    return ReviewStateStore.load(run_id, output_dir=_runs_dir())


def _save_review_state(store: ReviewStateStore) -> None:
    store.save(output_dir=_runs_dir())


def _load_project_input(path: Path) -> ProjectInput:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ProjectInput.model_validate(data)


def _run_status(run_id: str) -> dict[str, Any]:
    run_path = _run_json_path(run_id)
    review_path = _review_state_path(run_id)
    pending_path = _pending_marker_path(run_id)
    status_payload = _read_status(run_id)

    if not run_path.exists() and pending_path.exists():
        return {"run_id": run_id, "status": "pending", "sections_total": 0, "sections_approved": 0}
    if not run_path.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # The durable status file is authoritative for "failed" — a background
    # task that died mid-run leaves no review state to infer from, and a
    # process restart (sweep_orphaned_runs) can only mark this via the file.
    if status_payload and status_payload.get("status") == "failed":
        return {
            "run_id": run_id,
            "status": "failed",
            "sections_total": 0,
            "sections_approved": 0,
            "error": status_payload.get("error"),
        }

    status = "running"
    sections_total = 0
    sections_approved = 0

    if review_path.exists():
        try:
            store = _load_review_state(run_id)
            sections_total = len(store.sections)
            sections_approved = sum(
                1 for s in store.sections.values() if s.state == ReviewState.APPROVED
            )
            if store.is_all_approved():
                status = "approved"
            else:
                status = "review"
        except Exception:
            status = "running"

    return {
        "run_id": run_id,
        "status": status,
        "sections_total": sections_total,
        "sections_approved": sections_approved,
    }


def _section_summary(run_data: dict[str, Any], section_key: str) -> dict[str, Any]:
    section_id, sub_section_id = _parse_section_key(section_key)
    for s in run_data.get("sections", []):
        if s.get("section_id") == section_id and s.get("sub_section_id") == sub_section_id:
            return s
    raise HTTPException(status_code=404, detail=f"Section {section_key} not found")


def _ensure_review_state_for_run(run_id: str, run_data: dict[str, Any]) -> ReviewStateStore:
    """Load or reconstruct a ReviewStateStore for a run."""
    try:
        return _load_review_state(run_id)
    except FileNotFoundError:
        section_ids = [
            (str(s.get("section_id", "")), str(s.get("sub_section_id", "")))
            for s in run_data.get("sections", [])
        ]
        store = init_review_state(
            run_id=run_id,
            project_name=run_data.get("project_name", "unknown"),
            section_ids=section_ids,
        )
        _save_review_state(store)
        return store


# ─────────────────────────────────────────────
# Background execution
# ─────────────────────────────────────────────


def _status_path(run_id: str) -> Path:
    return _runs_dir() / f"{run_id}.status.json"


def _write_status(run_id: str, status: str, error: str | None = None) -> None:
    path = _status_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"status": status, "error": error}
    if status == "running":
        payload["started_at"] = datetime.now(timezone.utc).isoformat()
    else:
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_status(run_id: str) -> dict[str, Any] | None:
    path = _status_path(run_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def sweep_orphaned_runs() -> None:
    """Rewrite any "running" status file as failed on service startup.

    A run whose status file still says "running" after a fresh process start
    can only mean the previous process died mid-run — there is no other way
    for that status to persist across restarts.
    """
    runs_dir = _runs_dir()
    if not runs_dir.exists():
        return
    for path in runs_dir.glob("*.status.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("status") == "running":
            run_id = path.name[: -len(".status.json")]
            logger.warning("service_run_orphaned_by_restart", run_id=run_id)
            _write_status(run_id, "failed", error="orphaned by service restart")


def _execute_run(run_id: str, project_input_path: Path, provider_name: str) -> None:
    """Run the full drafting + review pipeline in a background task."""
    pending_path = _pending_marker_path(run_id)
    _write_status(run_id, "running")
    try:
        logger.info("service_run_start", run_id=run_id, provider=provider_name)
        project_input = _load_project_input(project_input_path)

        provider = _get_provider(provider_name)
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project_input,
            run_id=run_id,
            assumption_burden_path=_service_runs_dir() / f"assumption-burden-{run_id}.md",
            runs_dir=_service_runs_dir(),
        )
        orchestrator.run()
        orchestrator.run_review()
        logger.info("service_run_complete", run_id=run_id)
        _write_status(run_id, "complete")
    except Exception as exc:
        logger.error("service_run_failed", run_id=run_id, error=str(exc))
        # Persist a minimal failure record so the UI can surface it.
        failure = {
            "run_id": run_id,
            "project_name": "unknown",
            "provider": provider_name,
            "sections": [],
            "notes": [f"RUN FAILED: {exc}"],
            "assumption_register": None,
        }
        _save_run_json(run_id, failure)
        _write_status(run_id, "failed", error=str(exc))
    finally:
        if pending_path.exists():
            pending_path.unlink()


# ─────────────────────────────────────────────
# Web UI routes
# ─────────────────────────────────────────────


@app.get("/", response_class=RedirectResponse)
def root():
    return "/dashboard"


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    runs: list[dict[str, Any]] = []
    runs_dir = _runs_dir()
    if runs_dir.exists():
        for path in sorted(
            runs_dir.glob("run-*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            run_id = path.stem
            try:
                status = _run_status(run_id)
                runs.append(status)
            except HTTPException:
                continue
    # Refresh provider_status() to reflect the currently configured
    # PDD_SERVICE_PROVIDER so the banner is accurate even before any run
    # has been created in this process.
    _get_provider()
    return templates.TemplateResponse(
        request, "dashboard.html", {"runs": runs, "provider_status": provider_status()}
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str):
    run_data = _load_run_json(run_id)
    store = _ensure_review_state_for_run(run_id, run_data)

    sections: list[dict[str, Any]] = []
    for s in run_data.get("sections", []):
        key = _format_section_key(s.get("section_id", ""), s.get("sub_section_id", ""))
        state_obj = store.sections.get(key)
        sections.append(
            {
                "key": key,
                "section_id": s.get("section_id"),
                "sub_section_id": s.get("sub_section_id"),
                "heading": s.get("sub_section_id") or s.get("section_id"),
                "state": state_obj.state.value if state_obj else "drafted",
                "state_label": state_obj.state.label() if state_obj else "Drafted (auto)",
                "confidence": s.get("confidence", "UNKNOWN"),
                "issue_count": len(s.get("issues", [])),
            }
        )

    return templates.TemplateResponse(
        request,
        "run_detail.html",
        {
            "run_id": run_id,
            "project_name": run_data.get("project_name", "Unknown Project"),
            "provider": run_data.get("provider", "unknown"),
            "sections": sections,
            "all_approved": store.is_all_approved(),
        },
    )


@app.get("/runs/{run_id}/sections/{section_key:path}", response_class=HTMLResponse)
def section_review_page(request: Request, run_id: str, section_key: str):
    run_data = _load_run_json(run_id)
    section = _section_summary(run_data, section_key)
    store = _ensure_review_state_for_run(run_id, run_data)
    state_obj = store.sections.get(section_key)

    return templates.TemplateResponse(
        request,
        "section_review.html",
        {
            "run_id": run_id,
            "section_key": section_key,
            "section": section,
            "state": state_obj.state if state_obj else ReviewState.DRAFTED,
            "state_label": state_obj.state.label() if state_obj else "Drafted (auto)",
            "reviewer_notes": state_obj.reviewer_notes if state_obj else [],
        },
    )


# ─────────────────────────────────────────────
# API routes
# ─────────────────────────────────────────────


@app.post("/api/intake/document")
def api_intake_document(
    file: UploadFile = File(...),
    provider_name: str = Form("demo"),
):
    """Upload a DOCX/PDF/text file and extract a ProjectInput YAML."""
    suffix = Path(file.filename or "upload.txt").suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(file.file, tmp)

    try:
        provider = _get_provider(provider_name)
        project_input = extract_project_input(tmp_path, provider)
        yaml_text = yaml.safe_dump(project_input.model_dump(mode="json"), sort_keys=False)
        return {
            "project_input": project_input.model_dump(mode="json"),
            "yaml": yaml_text,
            "provider": provider_name,
            "source": file.filename,
        }
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/api/intake/spreadsheet")
def api_intake_spreadsheet(
    file: UploadFile | None = File(None),
    candidate_key: str = Form("soc-son"),
    mapping_config: str | None = Form(None),
):
    """Upload a spreadsheet or use the cached workbook and map it to ProjectInput."""
    if file is not None and file.filename:
        suffix = Path(file.filename).suffix or ".xlsx"
        cache_dir = REPO_ROOT / "data" / "source_inputs" / "spreadsheets"
        cache_dir.mkdir(parents=True, exist_ok=True)
        workbook_path = cache_dir / f"uploaded{suffix}"
        with open(workbook_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    else:
        from pdd_agent.phase06.spreadsheet_mapper import DEFAULT_SPREADSHEET_CACHE_DIR

        cache_dir = Path(DEFAULT_SPREADSHEET_CACHE_DIR)
        workbooks = sorted(cache_dir.glob("*.xlsx"))
        if not workbooks:
            raise HTTPException(
                status_code=400,
                detail="No spreadsheet uploaded and no cached workbook found",
            )
        workbook_path = workbooks[0]

    output_dir = REPO_ROOT / "data" / "source_inputs" / "spreadsheet_service"
    output_dir.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {
        "workbook_path": workbook_path,
        "candidate_key": candidate_key,
        "output_dir": output_dir,
    }
    if mapping_config:
        kwargs["mapping_config_path"] = Path(mapping_config)
    artifacts = generate_project_artifacts(**kwargs)
    return {
        "project_yaml_path": str(artifacts.project_yaml_path),
        "assumptions_yaml_path": str(artifacts.assumptions_yaml_path),
        "workbook_path": str(artifacts.workbook_path),
        "candidate_key": candidate_key,
    }


@app.post("/api/runs")
def api_create_run(
    background_tasks: BackgroundTasks,
    project_input_yaml: UploadFile = File(...),
    run_id: str | None = Form(None),
    provider_name: str | None = Form(None),
):
    """Create a new draft run from a ProjectInput YAML file.

    Execution happens in the background; the endpoint returns immediately
    with the run_id and status.
    """
    actual_provider = provider_name or _provider_name()

    new_run_id = run_id or _generate_run_id()
    suffix = Path(project_input_yaml.filename or "project.yaml").suffix or ".yaml"
    project_input_dir = REPO_ROOT / "data" / "source_inputs" / "service_uploads"
    project_input_dir.mkdir(parents=True, exist_ok=True)
    project_input_path = project_input_dir / f"{new_run_id}{suffix}"
    with open(project_input_path, "wb") as f:
        shutil.copyfileobj(project_input_yaml.file, f)

    _pending_marker_path(new_run_id).touch()
    background_tasks.add_task(_execute_run, new_run_id, project_input_path, actual_provider)

    return {"run_id": new_run_id, "status": "pending", "provider": actual_provider}


@app.get("/api/runs")
def api_list_runs():
    """List all runs with status summaries."""
    runs: list[dict[str, Any]] = []
    runs_dir = _runs_dir()
    if runs_dir.exists():
        for path in sorted(
            runs_dir.glob("run-*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                runs.append(_run_status(path.stem))
            except HTTPException:
                continue
    return {"runs": runs}


@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str):
    """Get run details plus a sections summary."""
    run_data = _load_run_json(run_id)
    store = _ensure_review_state_for_run(run_id, run_data)

    sections: list[dict[str, Any]] = []
    for s in run_data.get("sections", []):
        key = _format_section_key(s.get("section_id", ""), s.get("sub_section_id", ""))
        state_obj = store.sections.get(key)
        sections.append(
            {
                "key": key,
                "section_id": s.get("section_id"),
                "sub_section_id": s.get("sub_section_id"),
                "heading": s.get("sub_section_id") or s.get("section_id"),
                "state": state_obj.state.value if state_obj else "drafted",
                "state_label": state_obj.state.label() if state_obj else "Drafted (auto)",
                "confidence": s.get("confidence", "UNKNOWN"),
                "issue_count": len(s.get("issues", [])),
            }
        )

    return {
        "run_id": run_id,
        "project_name": run_data.get("project_name", "Unknown Project"),
        "provider": run_data.get("provider", "unknown"),
        "status": _run_status(run_id)["status"],
        "sections": sections,
        "notes": run_data.get("notes", []),
        "all_approved": store.is_all_approved(),
    }


@app.get("/api/runs/{run_id}/sections/{section_key:path}")
def api_get_section(run_id: str, section_key: str):
    """Get section detail: state, judge findings, provenance, text."""
    run_data = _load_run_json(run_id)
    section = _section_summary(run_data, section_key)
    store = _ensure_review_state_for_run(run_id, run_data)
    state_obj = store.sections.get(section_key)

    return {
        "run_id": run_id,
        "section_key": section_key,
        "section_id": section.get("section_id"),
        "sub_section_id": section.get("sub_section_id"),
        "text": section.get("text", ""),
        "confidence": section.get("confidence", "UNKNOWN"),
        "provenance": section.get("provenance", []),
        "issues": section.get("issues", []),
        "synthetic_uses": section.get("synthetic_uses", []),
        "state": state_obj.state.value if state_obj else "drafted",
        "state_label": state_obj.state.label() if state_obj else "Drafted (auto)",
        "reviewer_notes": state_obj.reviewer_notes if state_obj else [],
    }


@app.post("/api/runs/{run_id}/sections/{section_key:path}/approve")
def api_approve_section(run_id: str, section_key: str):
    """Approve a section."""
    run_data = _load_run_json(run_id)
    _section_summary(run_data, section_key)  # validate section exists
    store = _ensure_review_state_for_run(run_id, run_data)

    ok, msg = store.set_state(
        *_parse_section_key(section_key),
        ReviewState.APPROVED,
        reviewer_notes="Approved via web UI",
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    _save_review_state(store)
    return {"run_id": run_id, "section_key": section_key, "state": "approved"}


@app.post("/api/runs/{run_id}/sections/{section_key:path}/edit")
def api_edit_section(
    run_id: str,
    section_key: str,
    text: str = Form(...),
    approve: bool = Form(False),
):
    """Inline edit section text and persist as human-edit provenance."""
    run_data = _load_run_json(run_id)
    section = _section_summary(run_data, section_key)
    store = _ensure_review_state_for_run(run_id, run_data)

    previous_text = section.get("text", "")
    now = datetime.now(timezone.utc).isoformat()

    # Update the section text in the DraftRun JSON.
    section_id, sub_section_id = _parse_section_key(section_key)
    for s in run_data.get("sections", []):
        if s.get("section_id") == section_id and s.get("sub_section_id") == sub_section_id:
            s["text"] = text
            provenance_entry = (
                f"[HUMAN EDIT at {now}] Inline edit via service. "
                f"Previous text length: {len(previous_text)} chars."
            )
            s.setdefault("provenance", []).append(provenance_entry)
            break
    else:
        raise HTTPException(status_code=404, detail=f"Section {section_key} not found")

    _save_run_json(run_id, run_data)

    target_state = ReviewState.APPROVED if approve else ReviewState.READY_FOR_HUMAN_EDIT
    note = "Edited via web UI" + (" and approved" if approve else "")
    state_obj = store.get_or_create(section_id, sub_section_id)
    if state_obj.state != target_state:
        ok, msg = store.set_state(section_id, sub_section_id, target_state, reviewer_notes=note)
        if not ok:
            # Still persist text even if state transition failed.
            raise HTTPException(status_code=400, detail=msg)
    else:
        store.add_note(section_id, sub_section_id, note)
    _save_review_state(store)

    return {
        "run_id": run_id,
        "section_key": section_key,
        "state": target_state.value,
        "edited": True,
        "approved": approve,
    }


@app.post("/api/runs/{run_id}/sections/{section_key:path}/redraft")
def api_redraft_section(
    run_id: str,
    section_key: str,
    background_tasks: BackgroundTasks,
):
    """Re-invoke drafting for a single section.

    Because ``SectionOrchestrator`` does not expose a redraft method, this
    rebuilds the orchestrator for the run and regenerates the requested
    section with ``force_regenerate=True``.
    """
    run_data = _load_run_json(run_id)
    section = _section_summary(run_data, section_key)
    project_input_dir = REPO_ROOT / "data" / "source_inputs" / "service_uploads"
    project_input_path = _find_project_input_path(run_id, project_input_dir)

    if not project_input_path:
        raise HTTPException(
            status_code=400,
            detail="Original ProjectInput YAML not found; cannot redraft section",
        )

    background_tasks.add_task(
        _redraft_section_task,
        run_id,
        project_input_path,
        section.get("section_id", ""),
        section.get("sub_section_id", ""),
        run_data.get("provider", _provider_name()),
    )

    return {"run_id": run_id, "section_key": section_key, "status": "redrafting"}


def _find_project_input_path(run_id: str, project_input_dir: Path) -> Path | None:
    for suffix in (".yaml", ".yml"):
        candidate = project_input_dir / f"{run_id}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _redraft_section_task(
    run_id: str,
    project_input_path: Path,
    section_id: str,
    sub_section_id: str,
    provider_name: str,
) -> None:
    try:
        project_input = _load_project_input(project_input_path)
        provider = _get_provider(provider_name)
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project_input,
            run_id=run_id,
            assumption_burden_path=_service_runs_dir() / f"assumption-burden-{run_id}.md",
            runs_dir=_service_runs_dir(),
        )
        draft = orchestrator.draft_section(
            section_id=section_id,
            sub_section_id=sub_section_id or None,
            force_regenerate=True,
        )

        run_data = _load_run_json(run_id)
        for s in run_data.get("sections", []):
            if s.get("section_id") == section_id and s.get("sub_section_id") == sub_section_id:
                s["text"] = draft.text
                s["confidence"] = draft.confidence
                s["provider"] = draft.provider
                s.setdefault("provenance", []).append(
                    f"[REDRAFT at {datetime.now(timezone.utc).isoformat()}] Regenerated via service."
                )
                break
        else:
            run_data["sections"].append(
                {
                    "section_id": draft.section_id,
                    "sub_section_id": draft.sub_section_id,
                    "text": draft.text,
                    "confidence": draft.confidence,
                    "provenance": [
                        f"[REDRAFT at {datetime.now(timezone.utc).isoformat()}] Regenerated via service."
                    ],
                    "issues": list(draft.issues),
                    "provider": draft.provider,
                    "fact_provenance": [dict(item) for item in draft.fact_provenance],
                    "synthetic_uses": [dict(item) for item in draft.synthetic_uses],
                    "output_references": [dict(item) for item in draft.output_references],
                    "review_sensitivity": draft.review_sensitivity,
                    "content_class": draft.content_class,
                }
            )
        _save_run_json(run_id, run_data)

        store = _ensure_review_state_for_run(run_id, run_data)
        store.set_state(
            section_id,
            sub_section_id,
            ReviewState.DRAFTED,
            reviewer_notes="Redrafted via service",
        )
        _save_review_state(store)
        logger.info(
            "service_redraft_complete", run_id=run_id, section_key=f"{section_id}/{sub_section_id}"
        )
    except Exception as exc:
        logger.error(
            "service_redraft_failed",
            run_id=run_id,
            section_key=f"{section_id}/{sub_section_id}",
            error=str(exc),
        )


@app.get("/api/runs/{run_id}/docx")
def api_download_docx(run_id: str, force: int = 0):
    """Download gated DOCX export.

    By default the export is blocked if sections are not all approved or if
    the review state has blocking issues. Pass ``?force=1`` to override.
    """
    run_data = _load_run_json(run_id)
    store = _ensure_review_state_for_run(run_id, run_data)

    if not force and not store.is_all_approved():
        blocking = store.blocking_states()
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Export gate: not all sections are approved",
                "blocking_states": blocking,
                "hint": "Use ?force=1 to override",
            },
        )

    output_path = _runs_dir() / f"{run_id}.docx"
    export_run_to_docx(
        run_id=run_id,
        output_path=output_path,
        project_name=run_data.get("project_name", "Unknown Project"),
        force=bool(force),
        runs_dir=_runs_dir(),
    )
    return FileResponse(
        path=str(output_path),
        filename=f"{run_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
