"""Tests for the Ollama provider (mocked HTTP — never a live call)."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from pdd_agent.llm.budget import TokenBudget
from pdd_agent.llm.env_config import configure_provider_from_env
from pdd_agent.llm.ollama_provider import OllamaProvider, OllamaProviderError
from pdd_agent.llm.provider import ModelConfig, get_provider_registry


def _make_config(**overrides):
    defaults = {
        "provider_name": "ollama",
        "model_name": "llama3.1:8b",
        "max_tokens": 4000,
        "temperature": 0.1,
    }
    defaults.update(overrides)
    return ModelConfig(**defaults)


def _mock_urlopen_response(payload: dict) -> MagicMock:
    body = json.dumps(payload).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = BytesIO(body)
    cm.__exit__.return_value = False
    return cm


class TestOllamaProviderInit:
    def test_name(self):
        provider = OllamaProvider(_make_config())
        assert provider.name == "ollama"

    def test_default_base_url(self):
        provider = OllamaProvider(_make_config(base_url=None))
        assert provider._base_url == "http://localhost:11434"

    def test_default_model(self):
        provider = OllamaProvider(_make_config(model_name=None))
        assert provider._model == "llama3.1:8b"


class TestOllamaProviderDraftSection:
    @patch("pdd_agent.llm.ollama_provider.urllib.request.urlopen")
    def test_successful_draft(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_response(
            {
                "message": {"content": "Section text here."},
                "model": "llama3.1:8b",
                "prompt_eval_count": 120,
                "eval_count": 300,
            }
        )
        budget = TokenBudget(max_tokens=500_000)
        provider = OllamaProvider(_make_config())
        provider.set_budget(budget)

        result = provider.draft_section("1", "1.1", "prompt text", provenance=[])

        assert result.text == "Section text here."
        assert result.provider == "ollama"
        assert not any("REVIEW REQUIRED" in issue for issue in result.issues)
        assert budget.total_tokens == 420
        assert budget.estimated_cost_usd == 0.0

    @patch("pdd_agent.llm.ollama_provider.urllib.request.urlopen")
    def test_inference_marker_detected(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_response(
            {
                "message": {"content": "[INFERENCE] the plant likely operates at capacity."},
                "model": "llama3.1:8b",
                "prompt_eval_count": 10,
                "eval_count": 10,
            }
        )
        provider = OllamaProvider(_make_config())
        result = provider.draft_section("1", "1.1", "prompt text", provenance=[])

        assert any("[INFERENCE]" in issue for issue in result.issues)

    @patch("pdd_agent.llm.ollama_provider.time.sleep", return_value=None)
    @patch("pdd_agent.llm.ollama_provider.urllib.request.urlopen")
    def test_all_attempts_fail_raises_after_retries(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        provider = OllamaProvider(_make_config())

        with pytest.raises(OllamaProviderError, match="failed after 3 retries"):
            provider._call_api("prompt", max_tokens=100)

        assert mock_urlopen.call_count == 3

    @patch("pdd_agent.llm.ollama_provider.time.sleep", return_value=None)
    @patch("pdd_agent.llm.ollama_provider.urllib.request.urlopen")
    def test_recovers_after_transient_failures(self, mock_urlopen, _mock_sleep):
        success = _mock_urlopen_response(
            {
                "message": {"content": "ok"},
                "model": "llama3.1:8b",
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )
        mock_urlopen.side_effect = [
            urllib.error.URLError("timeout"),
            urllib.error.URLError("timeout"),
            success,
        ]
        provider = OllamaProvider(_make_config())

        response = provider._call_api("prompt", max_tokens=100)

        assert response.text == "ok"
        assert mock_urlopen.call_count == 3

    @patch("pdd_agent.llm.ollama_provider.urllib.request.urlopen")
    def test_draft_failure_returns_error_section_not_exception(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        provider = OllamaProvider(_make_config())

        result = provider.draft_section("1", "1.1", "prompt text", provenance=[])

        assert result.confidence == "UNSUPPORTED"
        assert "OLLAMA ERROR" in result.issues[0]


class TestConfigureProviderFromEnv:
    def test_ollama_configures_without_key(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

        configure_provider_from_env("ollama")

        provider = get_provider_registry().get("ollama")
        assert provider.name == "ollama"
        assert provider._model == "llama3.1:8b"

    def test_ollama_respects_env_overrides(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9999")

        configure_provider_from_env("ollama")

        provider = get_provider_registry().get("ollama")
        assert provider._model == "qwen2.5:7b"
        assert provider._base_url == "http://127.0.0.1:9999"

    def test_openai_without_key_is_noop(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Should not raise even though no key is present.
        configure_provider_from_env("openai")

    def test_unknown_provider_is_noop(self):
        configure_provider_from_env("totally-unknown-provider")


class TestBudgetOllamaFallback:
    def test_unknown_model_on_ollama_costs_zero(self):
        budget = TokenBudget(max_tokens=500_000)
        record = budget.record(
            section_id="1.1",
            input_tokens=100,
            output_tokens=100,
            model="mystery",
            provider="ollama",
        )
        assert record.cost_usd == 0.0

    def test_known_ollama_model_costs_zero(self):
        budget = TokenBudget(max_tokens=500_000)
        record = budget.record(
            section_id="1.1",
            input_tokens=100,
            output_tokens=100,
            model="llama3.1:8b",
            provider="ollama",
        )
        assert record.cost_usd == 0.0

    def test_unknown_model_without_provider_still_falls_back_to_gpt4o_pricing(self):
        # Non-ollama callers keep prior behavior (openai/anthropic pricing lookup).
        budget = TokenBudget(max_tokens=500_000)
        record = budget.record(
            section_id="1.1",
            input_tokens=1_000_000,
            output_tokens=0,
            model="some-unknown-model",
        )
        assert record.cost_usd == pytest.approx(2.50)
