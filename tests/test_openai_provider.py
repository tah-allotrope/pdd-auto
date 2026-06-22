"""Tests for the OpenAI provider (mocked API — no real API calls)."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pdd_agent.llm.openai_provider import OpenAIProvider, OpenAIProviderError
from pdd_agent.llm.provider import ModelConfig, DraftSection
from pdd_agent.llm.budget import TokenBudget


def _make_config(**overrides):
    defaults = {
        "provider_name": "openai",
        "model_name": "gpt-4o",
        "api_key": "test-key-123",
        "max_tokens": 4000,
        "temperature": 0.1,
    }
    defaults.update(overrides)
    return ModelConfig(**defaults)


def _mock_response(text="Test response", input_tokens=100, output_tokens=50):
    """Build a mock OpenAI ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = text
    choice.finish_reason = "stop"

    usage = MagicMock()
    usage.prompt_tokens = input_tokens
    usage.completion_tokens = output_tokens

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    response.model = "gpt-4o"
    response.id = "chatcmpl-test123"

    return response


class TestOpenAIProviderInit:
    def test_name(self):
        provider = OpenAIProvider(_make_config())
        assert provider.name == "openai"

    def test_no_api_key_raises(self):
        provider = OpenAIProvider(_make_config(api_key=None))
        with pytest.raises(OpenAIProviderError, match="API key"):
            provider._get_client()

    def test_missing_openai_package(self):
        provider = OpenAIProvider(_make_config())
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(OpenAIProviderError, match="not installed"):
                provider._get_client()


class TestOpenAIProviderDraftSection:
    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._get_client")
    def test_successful_draft(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.return_value = _mock_response(
            text="## Section 1.1\nProject description [CORPUS: doc, heading]"
        )
        mock_get_client.return_value = client

        provider = OpenAIProvider(_make_config())
        result = provider.draft_section(
            section_id="1",
            sub_section_id="1.1",
            prompt="Draft section 1.1",
            provenance=["[CORPUS: test_doc, test_heading]"],
        )

        assert isinstance(result, DraftSection)
        assert result.section_id == "1"
        assert result.sub_section_id == "1.1"
        assert result.provider == "openai"
        assert "[CORPUS:" in result.text
        assert result.confidence == "HIGH"

    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._get_client")
    def test_draft_with_review_markers(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.return_value = _mock_response(
            text="Some content [REVIEW REQUIRED: need evidence] and more [MISSING] data"
        )
        mock_get_client.return_value = client

        provider = OpenAIProvider(_make_config())
        result = provider.draft_section(
            section_id="3",
            sub_section_id="3.4",
            prompt="Draft section 3.4",
            provenance=[],
        )

        assert result.confidence == "LOW"
        assert any("REVIEW REQUIRED" in issue for issue in result.issues)
        assert any("MISSING" in issue for issue in result.issues)

    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._get_client")
    def test_draft_with_inference_markers(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.return_value = _mock_response(
            text="Based on the data [INFERENCE] the project will reduce emissions [CORPUS: doc, sec]"
        )
        mock_get_client.return_value = client

        provider = OpenAIProvider(_make_config())
        result = provider.draft_section(
            section_id="3",
            sub_section_id="3.5",
            prompt="Draft section 3.5",
            provenance=["[CORPUS: doc, sec]"],
        )

        assert result.confidence == "MEDIUM"
        assert any("INFERENCE" in issue for issue in result.issues)

    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._call_api")
    def test_api_error_returns_error_draft(self, mock_call):
        mock_call.side_effect = OpenAIProviderError("Connection failed")

        provider = OpenAIProvider(_make_config())
        result = provider.draft_section(
            section_id="1",
            sub_section_id="1.1",
            prompt="Draft section 1.1",
            provenance=[],
        )

        assert result.confidence == "UNSUPPORTED"
        assert "OPENAI ERROR" in result.text
        assert any("OPENAI ERROR" in issue for issue in result.issues)

    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._get_client")
    def test_max_chars_truncation(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.return_value = _mock_response(text="x" * 5000)
        mock_get_client.return_value = client

        provider = OpenAIProvider(_make_config())
        result = provider.draft_section(
            section_id="1",
            sub_section_id="1.1",
            prompt="Draft section 1.1",
            provenance=[],
            max_chars=100,
        )

        assert len(result.text) <= 100


class TestOpenAIProviderBudgetTracking:
    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._get_client")
    def test_records_to_budget(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.return_value = _mock_response(
            input_tokens=500, output_tokens=200
        )
        mock_get_client.return_value = client

        budget = TokenBudget(max_tokens=100000)
        provider = OpenAIProvider(_make_config())
        provider.set_budget(budget)

        provider.draft_section(
            section_id="1",
            sub_section_id="1.1",
            prompt="Draft",
            provenance=[],
        )

        assert budget.total_tokens == 700
        assert len(budget.calls) == 1
        assert budget.calls[0].section_id == "1.1.1"

    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._get_client")
    def test_budget_exhaustion_prevents_call(self, mock_get_client):
        budget = TokenBudget(max_tokens=100)
        budget.record("0.0", input_tokens=80, output_tokens=30)

        provider = OpenAIProvider(_make_config())
        provider.set_budget(budget)

        result = provider.draft_section(
            section_id="1",
            sub_section_id="1.1",
            prompt="Draft",
            provenance=[],
        )

        assert result.confidence == "UNSUPPORTED"
        assert "OPENAI ERROR" in result.text


class TestOpenAIProviderClose:
    def test_close_without_client(self):
        provider = OpenAIProvider(_make_config())
        provider.close()

    @patch("pdd_agent.llm.openai_provider.OpenAIProvider._get_client")
    def test_close_with_client(self, mock_get_client):
        client = MagicMock()
        mock_get_client.return_value = client
        provider = OpenAIProvider(_make_config())
        provider._client = client
        provider.close()
        client.close.assert_called_once()
        assert provider._client is None
