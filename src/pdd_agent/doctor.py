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
    all_results.extend(check_api_keys())
    all_results.append(check_ollama())
    all_results.extend(check_external_tools())
    all_results.append(check_retrieval_index())
    all_results.append(check_model_pricing())

    for status, message in all_results:
        print(f"[{status}] {message}")

    if any(status == "FAIL" for status, _ in all_results):
        return 1
    return 0
