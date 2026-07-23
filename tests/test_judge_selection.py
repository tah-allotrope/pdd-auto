"""Tests for the shared never-self-judge provider-selection logic."""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

from pdd_agent.llm.judge_selection import (
    is_provider_available,
    resolve_judge_provider,
    select_judge_provider,
)


class TestIsProviderAvailable:
    def test_demo_always_available(self):
        assert is_provider_available("demo") == (True, None)

    def test_noop_always_available(self):
        assert is_provider_available("noop") == (True, None)

    def test_ollama_unreachable_is_unavailable(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            assert is_provider_available("ollama") == (False, "ollama_unreachable")

    def test_ollama_reachable_is_available(self):
        response = MagicMock()
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=response):
            assert is_provider_available("ollama") == (True, None)

    def test_openai_without_key_unavailable(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert is_provider_available("openai") == (False, "missing_api_key")

    def test_openai_with_key_but_no_cost_ceiling_unavailable(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)
        assert is_provider_available("openai") == (False, "missing_cost_ceiling")

    def test_openai_with_key_and_cost_ceiling_available(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("PDD_MAX_COST_USD", "5.0")
        assert is_provider_available("openai") == (True, None)

    def test_unknown_provider_unavailable(self):
        assert is_provider_available("mystery") == (False, "unknown_provider")

    def test_claude_code_unavailable_without_cli(self, monkeypatch):
        monkeypatch.setattr("pdd_agent.llm.judge_selection.shutil.which", lambda name: None)
        assert is_provider_available("claude-code") == (False, "claude_cli_not_found")

    def test_claude_code_available_with_cli_no_cost_ceiling_required(self, monkeypatch):
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)
        monkeypatch.setattr(
            "pdd_agent.llm.judge_selection.shutil.which",
            lambda name: "/usr/local/bin/claude",
        )
        assert is_provider_available("claude-code") == (True, None)


class TestSelectJudgeProvider:
    def test_no_other_candidate_falls_back_to_demo(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        assert select_judge_provider("ollama", ["demo", "ollama"]) == ("demo", False)

    def test_prefers_anthropic_over_drafting_provider(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        assert select_judge_provider("ollama", ["demo", "ollama", "anthropic"]) == (
            "anthropic",
            True,
        )

    def test_skips_self_and_picks_next_in_preference_order(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        assert select_judge_provider("anthropic", ["anthropic", "openai"]) == ("openai", True)

    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("PDD_JUDGE_PROVIDER", "demo")
        assert select_judge_provider("anthropic", ["anthropic", "openai"]) == ("demo", False)


class TestResolveJudgeProvider:
    def test_skips_drafting_provider_even_if_later_available(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        monkeypatch.setattr(
            "pdd_agent.llm.judge_selection.is_provider_available",
            lambda name: (True, None) if name == "anthropic" else (False, "unavailable"),
        )
        assert resolve_judge_provider("claude-code") == ("anthropic", True)

    def test_falls_back_to_demo_when_nothing_available(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        monkeypatch.setattr(
            "pdd_agent.llm.judge_selection.is_provider_available",
            lambda name: (False, "unavailable"),
        )
        assert resolve_judge_provider("ollama") == ("demo", False)

    def test_env_override_wins_over_probing(self, monkeypatch):
        monkeypatch.setenv("PDD_JUDGE_PROVIDER", "ollama")
        assert resolve_judge_provider("anthropic") == ("ollama", True)
