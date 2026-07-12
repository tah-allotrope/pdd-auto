"""Tests for the pdd-agent doctor environment diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdd_agent.doctor import (
    check_api_keys,
    check_model_pricing,
    check_ollama,
    check_python_version,
    check_retrieval_index,
    run_doctor,
)


class TestCheckPythonVersion:
    def test_running_interpreter_is_ok(self):
        status, _ = check_python_version()
        assert status == "OK"


class TestCheckApiKeys:
    def test_key_present_is_masked(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234567890")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test1234567890")
        results = dict(
            (msg.split()[0], (status, msg)) for status, msg in check_api_keys()
        )
        status, message = results["OPENAI_API_KEY"]
        assert status == "OK"
        assert "sk-test1" in message
        assert "sk-test1234567890" not in message

    def test_key_absent_is_warn(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        results = {msg.split()[0]: status for status, msg in check_api_keys()}
        assert results["OPENAI_API_KEY"] == "WARN"


class TestCheckOllama:
    def test_nothing_listening_is_warn(self):
        status, _ = check_ollama(base_url="http://127.0.0.1:1")
        assert status == "WARN"


class TestCheckRetrievalIndex:
    def test_missing_db_is_warn(self, tmp_path: Path):
        status, _ = check_retrieval_index(db_path=tmp_path / "missing.db")
        assert status == "WARN"


class TestCheckModelPricing:
    def test_no_model_env_vars_is_ok(self, monkeypatch):
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        status, _ = check_model_pricing()
        assert status == "OK"

    def test_unknown_model_is_warn(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "totally-made-up-model")
        status, message = check_model_pricing()
        assert status == "WARN"
        assert "totally-made-up-model" in message


class TestRunDoctor:
    def test_exits_zero_with_only_warnings(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert run_doctor() == 0

    def test_exits_one_on_fail(self, monkeypatch):
        import pdd_agent.doctor as doctor_module

        monkeypatch.setattr(
            doctor_module, "check_python_version", lambda: ("FAIL", "forced failure")
        )
        assert run_doctor() == 1


class TestDotenvLoading:
    def test_env_file_is_picked_up(self, tmp_path: Path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("PDD_MAX_COST_USD=1.0\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)

        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv(usecwd=True))
        assert __import__("os").environ.get("PDD_MAX_COST_USD") == "1.0"
