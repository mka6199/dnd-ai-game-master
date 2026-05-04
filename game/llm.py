"""LLM wrapper around the OpenAI Chat Completions API.

Centralizes model calls so we can swap providers later. Handles tool/function
calling and parameter selection per scenario.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from game.prompts import PARAMETERS

load_dotenv()

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Lazy singleton OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


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
    """Generate an image using DALL-E 3 and return the URL."""
    client = get_client()
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
    )
    return response.data[0].url
