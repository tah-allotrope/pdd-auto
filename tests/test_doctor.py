"""Tests for the pdd-agent doctor environment diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch


from pdd_agent.doctor import (
    check_api_keys,
    check_model_pricing,
    check_ollama,
    check_pythonpath,
    check_python_version,
    check_retrieval_index,
    check_test_deps,
    check_uv_lock,
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
        results = dict((msg.split()[0], (status, msg)) for status, msg in check_api_keys())
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


class TestCheckPythonpath:
    def test_not_set_is_ok(self, monkeypatch):
        monkeypatch.delenv("PYTHONPATH", raising=False)
        status, _ = check_pythonpath()
        assert status == "OK"

    def test_set_is_warn(self, monkeypatch):
        monkeypatch.setenv("PYTHONPATH", "C:/foreign/site-packages")
        status, message = check_pythonpath()
        assert status == "WARN"
        assert "C:/foreign/site-packages" in message


class TestCheckTestDeps:
    def test_all_present_is_ok(self):
        results = check_test_deps()
        assert all(status == "OK" for status, _ in results)

    def test_python_multipart_missing_is_warn(self):
        def fake_import(name):
            if name in ("python_multipart", "multipart"):
                raise ImportError(name)
            return object()

        with patch("pdd_agent.doctor.importlib.import_module", side_effect=fake_import):
            results = check_test_deps()

        warn_rows = [(status, msg) for status, msg in results if status == "WARN"]
        assert len(warn_rows) == 1
        assert "python_multipart" in warn_rows[0][1]
        ok_rows = [(status, msg) for status, msg in results if status == "OK"]
        assert len(ok_rows) == len(results) - 1


class TestCheckUvLock:
    def test_uv_not_on_path_is_ok(self):
        with patch("pdd_agent.doctor.shutil.which", return_value=None):
            status, message = check_uv_lock()
        assert status == "OK"
        assert "not on PATH" in message

    def test_lock_missing_is_ok(self, tmp_path: Path):
        with patch("pdd_agent.doctor.shutil.which", return_value="/usr/bin/uv"):
            status, message = check_uv_lock(repo_root=tmp_path)
        assert status == "OK"
        assert "not present" in message

    def test_stale_lock_is_warn(self, tmp_path: Path):
        (tmp_path / "uv.lock").write_text("stale", encoding="utf-8")
        with (
            patch("pdd_agent.doctor.shutil.which", return_value="/usr/bin/uv"),
            patch(
                "pdd_agent.doctor.subprocess.run",
                return_value=subprocess.CompletedProcess(args=[], returncode=2),
            ),
        ):
            status, message = check_uv_lock(repo_root=tmp_path)
        assert status == "WARN"
        assert "stale" in message

    def test_current_lock_is_ok(self, tmp_path: Path):
        (tmp_path / "uv.lock").write_text("current", encoding="utf-8")
        with (
            patch("pdd_agent.doctor.shutil.which", return_value="/usr/bin/uv"),
            patch(
                "pdd_agent.doctor.subprocess.run",
                return_value=subprocess.CompletedProcess(args=[], returncode=0),
            ),
        ):
            status, _ = check_uv_lock(repo_root=tmp_path)
        assert status == "OK"

    def test_timeout_is_warn(self, tmp_path: Path):
        (tmp_path / "uv.lock").write_text("current", encoding="utf-8")
        with (
            patch("pdd_agent.doctor.shutil.which", return_value="/usr/bin/uv"),
            patch(
                "pdd_agent.doctor.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="uv", timeout=30),
            ),
        ):
            status, message = check_uv_lock(repo_root=tmp_path)
        assert status == "WARN"
        assert "failed to run" in message


class TestCheckModelPricing:
    def test_no_model_env_vars_is_ok(self, monkeypatch):
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        monkeypatch.delenv("PDD_JUDGE_MODEL", raising=False)
        status, _ = check_model_pricing()
        assert status == "OK"

    def test_unknown_model_is_warn(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "totally-made-up-model")
        status, message = check_model_pricing()
        assert status == "WARN"
        assert "totally-made-up-model" in message

    def test_unknown_judge_model_is_warn(self, monkeypatch):
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        monkeypatch.setenv("PDD_JUDGE_MODEL", "totally-made-up-judge-model")
        status, message = check_model_pricing()
        assert status == "WARN"
        assert "PDD_JUDGE_MODEL" in message
        assert "totally-made-up-judge-model" in message


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

    def test_exits_zero_when_new_checks_all_warn(self, monkeypatch):
        import pdd_agent.doctor as doctor_module

        monkeypatch.setattr(doctor_module, "check_test_deps", lambda: [("WARN", "forced warn")])
        monkeypatch.setattr(doctor_module, "check_pythonpath", lambda: ("WARN", "forced warn"))
        monkeypatch.setattr(doctor_module, "check_uv_lock", lambda: ("WARN", "forced warn"))
        assert run_doctor() == 0


class TestDotenvLoading:
    def test_env_file_is_picked_up(self, tmp_path: Path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("PDD_MAX_COST_USD=1.0\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)

        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv(usecwd=True))
        assert __import__("os").environ.get("PDD_MAX_COST_USD") == "1.0"
