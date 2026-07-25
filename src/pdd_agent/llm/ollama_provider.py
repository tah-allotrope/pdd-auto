"""Ollama local-model provider.

Talks to a local Ollama instance's ``/api/chat`` endpoint via stdlib
``urllib.request`` (no ``ollama`` pip package — the service must stay
dependency-light and keyless-runnable). Mirrors ``openai_provider.py``'s
retry, marker-detection, and confidence-assignment structure so the drafting
pipeline behaves identically regardless of provider.

Install Ollama from https://ollama.com/download, then:
    ollama pull llama3.1:8b
    ollama serve   # usually started automatically by the installer

Configure via ``configure_provider_from_env("ollama")``
(``pdd_agent.llm.env_config``) or directly with a ``ModelConfig``.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import structlog

from pdd_agent.llm.budget import BudgetExhaustedError
from pdd_agent.llm.output_normalize import strip_assistant_preamble
from pdd_agent.llm.provider import BaseProvider, DraftSection, LLMResponse, ModelConfig

logger = structlog.get_logger()

_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0
_REQUEST_TIMEOUT_SECONDS = 120

_DEFAULT_SYSTEM_PROMPT = (
    "You are a technical writing assistant specializing in Verra VCS "
    "carbon credit Project Design Documents for waste-to-energy projects. "
    "Follow the prompt instructions exactly. Cite all sources using the "
    "required citation format. Never fabricate data."
)


class OllamaProviderError(Exception):
    """Raised when the Ollama provider encounters a non-retryable error."""


class OllamaProvider(BaseProvider):
    """Local-model provider using a running Ollama instance."""

    name = "ollama"

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._model = config.model_name or "llama3.1:8b"
        self._base_url = (config.base_url or "http://localhost:11434").rstrip("/")
        self._budget = None
        self._system_prompt = _DEFAULT_SYSTEM_PROMPT

    def set_budget(self, budget) -> None:
        """Attach a TokenBudget instance for per-run tracking."""
        self._budget = budget

    def set_system_prompt(self, text: str) -> None:
        """Override the system message used on every subsequent draft call."""
        self._system_prompt = text

    def _call_api(self, prompt: str, max_tokens: int) -> LLMResponse:
        """Call Ollama's /api/chat endpoint with retry logic."""
        body = json.dumps(
            {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": self._config.temperature,
                    "num_predict": max_tokens,
                },
            }
        ).encode("utf-8")

        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                if self._budget:
                    self._budget.check_budget()

                request = urllib.request.Request(
                    f"{self._base_url}/api/chat",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
                    payload = json.loads(response.read().decode("utf-8"))

                text = payload.get("message", {}).get("content", "")
                model = payload.get("model") or self._model
                input_tokens = payload.get("prompt_eval_count", 0) or 0
                output_tokens = payload.get("eval_count", 0) or 0

                return LLMResponse(
                    text=text,
                    provider=self.name,
                    model=model,
                    tokens_used=input_tokens + output_tokens,
                    cost_usd=0.0,
                    raw={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                )
            except BudgetExhaustedError:
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                wait = _RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "ollama_connection_error",
                    attempt=attempt,
                    wait_seconds=wait,
                    error=str(exc),
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(wait)
            except (json.JSONDecodeError, KeyError) as exc:
                last_error = exc
                logger.warning("ollama_bad_response", attempt=attempt, error=str(exc))
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_BACKOFF_BASE**attempt)

        raise OllamaProviderError(
            f"Ollama API call failed after {_MAX_RETRIES} retries: {last_error}"
        )

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list[str],
        max_chars: int = 4000,
    ) -> DraftSection:
        max_tokens = min(self._config.max_tokens, max_chars)

        try:
            response = self._call_api(prompt, max_tokens)
        except (OllamaProviderError, BudgetExhaustedError) as exc:
            logger.error(
                "ollama_draft_failed",
                section_id=section_id,
                sub_section_id=sub_section_id,
                error=str(exc),
            )
            return DraftSection(
                section_id=section_id,
                sub_section_id=sub_section_id,
                text=f"[OLLAMA ERROR — {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}]\n"
                f"Provider error: {exc}\n"
                f"This section requires manual drafting or retry. Is `ollama serve` "
                f"running at {self._base_url}?",
                confidence="UNSUPPORTED",
                provenance=provenance,
                issues=[f"OLLAMA ERROR: {exc}"],
                provider=self.name,
                output_references=[{"type": "section_body", "description": "ollama error output"}],
            )

        if self._budget and response.raw:
            self._budget.record(
                section_id=f"{section_id}.{sub_section_id}" if sub_section_id else section_id,
                input_tokens=response.raw.get("input_tokens", 0),
                output_tokens=response.raw.get("output_tokens", 0),
                model=response.model or self._model,
                provider=self.name,
            )

        text = strip_assistant_preamble(response.text)[:max_chars]
        confidence = self._assess_confidence(text, provenance)

        return DraftSection(
            section_id=section_id,
            sub_section_id=sub_section_id,
            text=text,
            confidence=confidence,
            provenance=provenance,
            issues=self._extract_issues(text, section_id, sub_section_id),
            provider=self.name,
            output_references=[{"type": "section_body", "description": "ollama generated output"}],
        )

    def _assess_confidence(self, text: str, provenance: list[str]) -> str:
        has_review_markers = "[REVIEW REQUIRED" in text or "[MISSING]" in text
        has_inference = "[INFERENCE]" in text
        has_citations = any(
            marker in text for marker in ("[CORPUS:", "[METHODOLOGY:", "[E0", "[USER INPUT:")
        )

        if has_review_markers and not has_citations:
            return "LOW"
        if has_review_markers or has_inference:
            return "MEDIUM"
        if has_citations and provenance:
            return "HIGH"
        return "MEDIUM"

    def _extract_issues(self, text: str, section_id: str, sub_section_id: str) -> list[str]:
        issues = []
        if "[REVIEW REQUIRED" in text:
            issues.append(
                f"Contains [REVIEW REQUIRED] markers in {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}"
            )
        if "[MISSING]" in text:
            issues.append(
                f"Contains [MISSING] markers — evidence gaps in {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}"
            )
        if "[INFERENCE]" in text:
            issues.append(
                f"Contains [INFERENCE] markers — model-inferred content in {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}"
            )
        return issues

    def close(self) -> None:
        pass
