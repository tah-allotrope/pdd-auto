"""Configure LLM providers from environment variables.

Shared by the CLI and the FastAPI service so both use identical provider
resolution logic (env var names, defaults, key requirements).
"""

from __future__ import annotations

import os

from pdd_agent.llm.provider import ModelConfig, configure_provider


def configure_provider_from_env(provider_name: str) -> None:
    """Configure a provider from environment variables if applicable.

    - ``openai`` / ``anthropic``: requires ``{PROVIDER}_API_KEY``; a no-op
      (provider left unconfigured / falls back to registry default) when the
      key is absent, matching prior CLI behavior.
    - ``ollama``: always configures — local inference needs no API key.
      Reads ``OLLAMA_MODEL`` (default ``llama3.1:8b``) and
      ``OLLAMA_BASE_URL`` (default ``http://localhost:11434``).
    - ``claude-code``: always configures — shells out to the local Claude
      Code CLI, no API key needed. Reads ``CLAUDE_CODE_MODEL`` (default
      ``sonnet``) and ``CLAUDE_CODE_MAX_TOKENS`` (default ``4000``).
    - Any other provider name: no-op.
    """
    if provider_name == "ollama":
        config = ModelConfig(
            provider_name="ollama",
            model_name=os.environ.get("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            max_tokens=int(os.environ.get("OLLAMA_MAX_TOKENS", "4000")),
            temperature=float(os.environ.get("OLLAMA_TEMPERATURE", "0.1")),
        )
        configure_provider(config)
        return

    if provider_name == "claude-code":
        config = ModelConfig(
            provider_name="claude-code",
            model_name=os.environ.get("CLAUDE_CODE_MODEL", "sonnet"),
            max_tokens=int(os.environ.get("CLAUDE_CODE_MAX_TOKENS", "4000")),
            temperature=0.1,
        )
        configure_provider(config)
        return

    if provider_name not in {"openai", "anthropic"}:
        return

    api_key = os.environ.get(f"{provider_name.upper()}_API_KEY")
    if not api_key:
        return

    config = ModelConfig(
        provider_name=provider_name,
        model_name=os.environ.get(f"{provider_name.upper()}_MODEL"),
        api_key=api_key,
        base_url=os.environ.get(f"{provider_name.upper()}_BASE_URL"),
        max_tokens=int(os.environ.get(f"{provider_name.upper()}_MAX_TOKENS", "4000")),
        temperature=float(os.environ.get(f"{provider_name.upper()}_TEMPERATURE", "0.1")),
    )
    configure_provider(config)
