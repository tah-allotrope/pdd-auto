"""Environment diagnostics for pdd-agent.

Run via ``pdd-agent doctor``. Prints one ``[OK]``/``[WARN]``/``[FAIL]`` line
per check and exits non-zero only when a check reports ``FAIL``. Optional
tooling (LLM SDKs, LibreOffice, gws, a running Ollama instance, a built
retrieval index) is always ``WARN`` on absence, never ``FAIL`` — the pipeline
must keep degrading gracefully without them.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from pdd_agent.llm.budget import _DEFAULT_PRICING

_OPTIONAL_PACKAGES = ["openai", "anthropic", "fastapi", "docx", "dotenv"]
_API_KEY_ENV_VARS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
_MODEL_ENV_VARS = ["OPENAI_MODEL", "ANTHROPIC_MODEL", "PDD_JUDGE_MODEL"]
_TEST_DEPS = ["pytest", "python_multipart", "uvicorn", "jinja2"]
_INSTALL_HINT = (
    "install with 'uv sync --all-extras' or 'pip install -e \".[dev,service,export,llm]\"'"
)


def check_python_version() -> tuple[str, str]:
    """Return ("OK", ...) when running on Python 3.11+, else ("FAIL", ...)."""
    if sys.version_info >= (3, 11):
        return ("OK", f"Python {sys.version.split()[0]}")
    return ("FAIL", f"Python {sys.version.split()[0]} — requires >=3.11")


def check_package_imports() -> list[tuple[str, str]]:
    """Return one (status, message) per optional package; WARN when missing."""
    results = []
    for package_name in _OPTIONAL_PACKAGES:
        try:
            importlib.import_module(package_name)
            results.append(("OK", f"{package_name} importable"))
        except ImportError:
            results.append(("WARN", f"{package_name} not installed"))
    return results


def check_test_deps() -> list[tuple[str, str]]:
    """Return one (status, message) per fresh-install dev/service dependency.

    Unlike check_package_imports (LLM/export extras), these are the
    dependencies a fresh `uv sync --all-extras`/`pip install -e .` must
    provide for the test suite and service to even collect/import — a gap
    here is exactly the class of bug that left CI red for 3 days (an
    undeclared python-multipart dependency broke test collection on every
    fresh install while the dev machine's already-provisioned venv masked it
    locally).
    """
    results = []
    for name in _TEST_DEPS:
        if name == "python_multipart":
            found = False
            for candidate in ("python_multipart", "multipart"):
                try:
                    importlib.import_module(candidate)
                    found = True
                    break
                except ImportError:
                    continue
            if found:
                results.append(("OK", f"{name} importable"))
            else:
                results.append(("WARN", f"{name} not installed — {_INSTALL_HINT}"))
            continue
        try:
            importlib.import_module(name)
            results.append(("OK", f"{name} importable"))
        except ImportError:
            results.append(("WARN", f"{name} not installed — {_INSTALL_HINT}"))
    return results


def check_pythonpath() -> tuple[str, str]:
    """Return ("WARN", ...) if PYTHONPATH is set, else ("OK", ...).

    A foreign PYTHONPATH injected by other tooling on the machine can shadow
    this project's venv (symptom: `No module named pytest` or a mismatched
    pydantic_core binary) even though the project's own dependencies are
    correctly installed.
    """
    import os

    value = os.environ.get("PYTHONPATH")
    if not value:
        return ("OK", "PYTHONPATH not set")
    return (
        "WARN",
        f"PYTHONPATH is set ({value}) — may shadow the project venv; run with PYTHONPATH cleared",
    )


def check_uv_lock(repo_root: Path | None = None) -> tuple[str, str]:
    """Return ("OK", ...) if uv.lock is current or not applicable, else ("WARN", ...).

    A stale uv.lock silently drifts from pyproject.toml (missing dependencies,
    outdated versions) until someone runs a fresh `uv sync` and discovers it —
    exactly what happened before the CI lock-reproducibility job was added.
    """
    root = repo_root or Path.cwd()
    if shutil.which("uv") is None:
        return ("OK", "uv not on PATH; lock check skipped")
    lock_path = root / "uv.lock"
    if not lock_path.exists():
        return ("OK", "uv.lock not present")
    try:
        proc = subprocess.run(
            ["uv", "lock", "--check"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return ("WARN", f"uv lock --check failed to run: {exc}")
    if proc.returncode == 0:
        return ("OK", "uv.lock is current")
    return ("WARN", "uv.lock is stale relative to pyproject.toml — run 'uv lock' and commit")


def check_api_keys() -> list[tuple[str, str]]:
    """Return one (status, message) per known API key env var; keys are masked."""
    import os

    results = []
    for var_name in _API_KEY_ENV_VARS:
        value = os.environ.get(var_name)
        if value:
            masked = value[:8] + "…" if len(value) > 8 else value[:4] + "…"
            results.append(("OK", f"{var_name} set ({masked})"))
        else:
            results.append(("WARN", f"{var_name} not set"))
    return results


def check_ollama(base_url: str = "http://localhost:11434") -> tuple[str, str]:
    """Return ("OK", model list) if Ollama responds, else ("WARN", ...)."""
    try:
        request = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(request, timeout=2) as response:
            import json

            payload = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "?") for m in payload.get("models", [])]
            return (
                "OK",
                f"Ollama reachable at {base_url} — models: {', '.join(models) or 'none pulled'}",
            )
    except (urllib.error.URLError, OSError, TimeoutError):
        return ("WARN", f"Ollama not reachable at {base_url}")


def check_external_tools() -> list[tuple[str, str]]:
    """Return one (status, message) per optional external CLI tool."""
    results = []
    for tool_name, version_args in (("soffice", ["--version"]), ("gws", ["--version"])):
        path = shutil.which(tool_name)
        if not path:
            results.append(("WARN", f"{tool_name} not found on PATH"))
            continue
        try:
            proc = subprocess.run(
                [tool_name, *version_args], capture_output=True, text=True, timeout=5
            )
            first_line = (
                (proc.stdout or proc.stderr or "").splitlines()[0]
                if (proc.stdout or proc.stderr)
                else path
            )
            results.append(("OK", f"{tool_name}: {first_line.strip()}"))
        except (OSError, subprocess.TimeoutExpired, IndexError):
            results.append(("WARN", f"{tool_name} found at {path} but version check failed"))
    return results


def check_claude_cli() -> tuple[str, str]:
    """Return ("OK", version) if the Claude Code CLI is installed, else ("WARN", ...).

    The claude-code provider (keyless frontier drafting) needs this CLI on
    PATH; its absence is never fatal since demo/noop/other providers remain
    available.
    """
    path = shutil.which("claude")
    if not path:
        return ("WARN", "claude CLI not found on PATH — claude-code provider unavailable")
    try:
        proc = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
        first_line = (
            (proc.stdout or proc.stderr or "").splitlines()[0]
            if (proc.stdout or proc.stderr)
            else path
        )
        return ("OK", f"claude CLI: {first_line.strip()}")
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return ("WARN", f"claude CLI found at {path} but version check failed")


def check_retrieval_index(db_path: Path | None = None) -> tuple[str, str]:
    """Return ("OK", doc count) if the FTS5 index DB exists and is queryable."""
    import sqlite3

    path = db_path or Path("data/index/corpus.fts.db")
    if not path.exists():
        return ("WARN", f"No retrieval index at {path}")
    try:
        conn = sqlite3.connect(str(path))
        try:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            fts_tables = [t for t in tables if "fts" in t.lower() or t == "documents"]
            if not fts_tables:
                return ("WARN", f"{path} exists but has no recognizable FTS table")
            count_table = fts_tables[0]
            count = conn.execute(f"SELECT COUNT(*) FROM {count_table}").fetchone()[0]
            return ("OK", f"{path} — {count} rows in {count_table}")
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return ("WARN", f"{path} exists but is not a valid SQLite DB: {exc}")


def check_model_pricing() -> tuple[str, str]:
    """Return ("WARN", ...) if a configured model has no pricing entry, else ("OK", ...)."""
    import os

    unknown = []
    for var_name in _MODEL_ENV_VARS:
        model_name = os.environ.get(var_name)
        if model_name and model_name not in _DEFAULT_PRICING:
            unknown.append(f"{var_name}={model_name}")
    if unknown:
        return ("WARN", f"No pricing entry for: {', '.join(unknown)}")
    return ("OK", "All configured models have pricing entries")


def run_doctor() -> int:
    """Run all checks, print results, and return the process exit code."""
    all_results: list[tuple[str, str]] = []

    all_results.append(check_python_version())
    all_results.extend(check_package_imports())
    all_results.extend(check_test_deps())
    all_results.append(check_pythonpath())
    all_results.append(check_uv_lock())
    all_results.extend(check_api_keys())
    all_results.append(check_ollama())
    all_results.extend(check_external_tools())
    all_results.append(check_claude_cli())
    all_results.append(check_retrieval_index())
    all_results.append(check_model_pricing())

    for status, message in all_results:
        print(f"[{status}] {message}")

    if any(status == "FAIL" for status, _ in all_results):
        return 1
    return 0
