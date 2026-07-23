"""Tests for the Claude Code CLI provider (mocked subprocess — never a live call)."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from pdd_agent.llm.budget import BudgetExhaustedError, TokenBudget
from pdd_agent.llm.claude_code_provider import (
    ClaudeCodeProvider,
    ClaudeCodeProviderError,
    _DEFAULT_SYSTEM_PROMPT,
)
from pdd_agent.llm.provider import ModelConfig, configure_provider, get_provider_registry
from pdd_agent.phase05.provider_scorecard import _is_provider_available


def _make_config(**overrides):
    defaults = {
        "provider_name": "claude-code",
        "model_name": "sonnet",
        "max_tokens": 4000,
        "temperature": 0.1,
    }
    defaults.update(overrides)
    return ModelConfig(**defaults)


def _completed_process(payload: dict, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["claude"], returncode=returncode, stdout=json.dumps(payload), stderr=""
    )


class TestClaudeCodeProviderInit:
    def test_name(self):
        provider = ClaudeCodeProvider(_make_config())
        assert provider.name == "claude-code"

    def test_default_model(self):
        provider = ClaudeCodeProvider(_make_config(model_name=None))
        assert provider._model == "sonnet"

    def test_default_cli_binary(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_CODE_CLI", raising=False)
        provider = ClaudeCodeProvider(_make_config())
        assert provider._cli == "claude"

    def test_cli_binary_override(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_CODE_CLI", "claude-custom")
        provider = ClaudeCodeProvider(_make_config())
        assert provider._cli == "claude-custom"


class TestClaudeCodeProviderDraftSection:
    @patch("pdd_agent.llm.claude_code_provider.subprocess.run")
    def test_successful_draft_records_budget(self, mock_run):
        mock_run.return_value = _completed_process(
            {
                "result": "Drafted text [USER INPUT: name]",
                "is_error": False,
                "usage": {"input_tokens": 120, "output_tokens": 340},
                "total_cost_usd": 0.01,
            }
        )
        provider = ClaudeCodeProvider(_make_config())
        budget = TokenBudget()
        provider.set_budget(budget)

        section = provider.draft_section("1", "1.1", "p", ["[USER INPUT: name]"])

        assert section.provider == "claude-code"
        assert section.text.startswith("Drafted text")
        assert budget.total_tokens == 460

    @patch("pdd_agent.llm.claude_code_provider.subprocess.run")
    def test_cli_invocation_shape(self, mock_run):
        mock_run.return_value = _completed_process({"result": "ok", "is_error": False, "usage": {}})
        provider = ClaudeCodeProvider(_make_config())
        provider.draft_section("1", "1.1", "the prompt text", [])

        called_args, called_kwargs = mock_run.call_args
        argv = called_args[0]
        assert argv == [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--model",
            "sonnet",
            "--append-system-prompt",
            _DEFAULT_SYSTEM_PROMPT,
        ]
        assert called_kwargs["input"] == "the prompt text"

    @patch("pdd_agent.llm.claude_code_provider.subprocess.run")
    def test_is_error_result_retried_then_error_section(self, mock_run):
        mock_run.return_value = _completed_process({"result": "", "is_error": True})
        provider = ClaudeCodeProvider(_make_config())

        section = provider.draft_section("1", "1.1", "p", [])

        assert section.text.startswith("[CLAUDE-CODE ERROR")
        assert section.confidence == "UNSUPPORTED"
        assert mock_run.call_count == 2  # _MAX_RETRIES

    @patch("pdd_agent.llm.claude_code_provider.subprocess.run")
    def test_timeout_yields_error_section_without_raising(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)
        provider = ClaudeCodeProvider(_make_config())

        section = provider.draft_section("1", "1.1", "p", [])

        assert section.text.startswith("[CLAUDE-CODE ERROR")

    @patch("pdd_agent.llm.claude_code_provider.subprocess.run")
    def test_malformed_stdout_retried_then_error_section(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="not json", stderr=""
        )
        provider = ClaudeCodeProvider(_make_config())

        section = provider.draft_section("1", "1.1", "p", [])

        assert section.text.startswith("[CLAUDE-CODE ERROR")
        assert mock_run.call_count == 2

    @patch("pdd_agent.llm.claude_code_provider.subprocess.run")
    def test_budget_exhausted_before_call_never_invokes_subprocess(self, mock_run):
        provider = ClaudeCodeProvider(_make_config())
        budget = TokenBudget(max_tokens=1)
        budget.record(section_id="0", input_tokens=1, output_tokens=1)
        provider.set_budget(budget)

        section = provider.draft_section("1", "1.1", "p", [])

        assert section.text.startswith("[CLAUDE-CODE ERROR")
        mock_run.assert_not_called()

    def test_set_system_prompt_overrides_default(self):
        provider = ClaudeCodeProvider(_make_config())
        with patch("pdd_agent.llm.claude_code_provider.subprocess.run") as mock_run:
            mock_run.return_value = _completed_process(
                {"result": "ok", "is_error": False, "usage": {}}
            )
            provider.set_system_prompt("CUSTOM SYSTEM PROMPT")
            provider.draft_section("1", "1.1", "p", [])
            argv = mock_run.call_args[0][0]
            assert argv[-1] == "CUSTOM SYSTEM PROMPT"


class TestClaudeCodeProviderAvailability:
    def test_unavailable_when_cli_missing(self, monkeypatch):
        monkeypatch.setattr("pdd_agent.llm.judge_selection.shutil.which", lambda name: None)
        assert _is_provider_available("claude-code") == (False, "claude_cli_not_found")

    def test_available_when_cli_present(self, monkeypatch):
        monkeypatch.setattr(
            "pdd_agent.llm.judge_selection.shutil.which",
            lambda name: "/usr/local/bin/claude",
        )
        assert _is_provider_available("claude-code") == (True, None)


class TestClaudeCodeProviderRegistry:
    def test_registers_under_claude_code_name(self):
        configure_provider(_make_config())
        provider = get_provider_registry().get("claude-code")
        assert provider.name == "claude-code"


class TestClaudeCodeProviderErrorPropagation:
    def test_error_message_names_provider_error_class(self):
        assert issubclass(ClaudeCodeProviderError, Exception)

    def test_budget_exhausted_error_is_reraised_not_wrapped(self):
        provider = ClaudeCodeProvider(_make_config())
        exhausted_budget = MagicMock()
        exhausted_budget.check_budget.side_effect = BudgetExhaustedError("no tokens left")
        provider.set_budget(exhausted_budget)

        section = provider.draft_section("1", "1.1", "p", [])
        assert "no tokens left" in section.text
