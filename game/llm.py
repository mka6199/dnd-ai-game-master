"""LLM wrapper supporting both OpenAI (cloud) and Ollama (local).

Set LLM_PROVIDER=openai (default) or LLM_PROVIDER=ollama in .env.

Ollama is used via its OpenAI-compatible /v1 endpoint so the same OpenAI
Python SDK code path handles both providers, including tool/function calling.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from game.prompts import PARAMETERS

load_dotenv()

_client: OpenAI | None = None


def get_provider() -> str:
    """Return 'openai' or 'ollama' (lowercased)."""
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


def get_model() -> str:
    """Return the chat model name for the active provider."""
    if get_provider() == "ollama":
        return os.getenv("OLLAMA_MODEL", "llama3.1")
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client() -> OpenAI:
    """Lazy singleton client. Routed to OpenAI or to a local Ollama server."""
    global _client
    if _client is None:
        provider = get_provider()
        if provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            # Ollama ignores the API key but the SDK requires a non-empty value.
            _client = OpenAI(api_key="ollama", base_url=base_url)
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key == "your-openai-api-key-here":
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key, "
                    "or set LLM_PROVIDER=ollama to use a local model."
                )
            _client = OpenAI(api_key=api_key)
    return _client


def reset_client() -> None:
    """Drop the cached client (useful if the user switches providers at runtime)."""
    global _client
    _client = None


def chat(
    messages: list[dict],
    scenario: str = "narration",
    tools: list[dict] | None = None,
    tool_choice: str | dict = "auto",
) -> Any:
    """Send a chat completion request.

    Args:
        messages: OpenAI-style message list.
        scenario: Key into prompts.PARAMETERS to select temperature/max_tokens.
        tools: Optional list of tool/function schemas.
        tool_choice: 'auto', 'none', or a specific tool selection dict.

    Returns:
        The OpenAI response message object (with .content and .tool_calls).
    """
    params = PARAMETERS.get(scenario, PARAMETERS["narration"])
    client = get_client()

    request = {
        "model": get_model(),
        "messages": messages,
        "temperature": params["temperature"],
        "max_tokens": params["max_tokens"],
    }
    if tools:
        request["tools"] = tools
        request["tool_choice"] = tool_choice

    response = client.chat.completions.create(**request)
    return response.choices[0].message


def generate_image(prompt: str, size: str = "1024x1024") -> str:
    """Generate an image. Only supported on the OpenAI provider (DALL-E 3).

    Raises RuntimeError if the active provider is Ollama (no local image model
    is shipped with this project).
    """
    if get_provider() != "openai":
        raise RuntimeError(
            "Image generation requires LLM_PROVIDER=openai. "
            "Ollama mode does not include an image model."
        )
    client = get_client()
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
    )
    return response.data[0].url
