# Author: Bradley R. Kinnard — pay per token, cache per hash

"""
Async OpenAI client for all agents. Using native client instead of LangChain for better JSON mode support.
"""

import asyncio
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from src.backend.config import settings

log = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
_lock = asyncio.Lock()


@dataclass
class LLMResponse:
    """simple wrapper to match what agents expect"""
    content: str


async def get_llm() -> AsyncOpenAI:
    """
    Get or create the shared OpenAI client.
    """
    global _client
    if _client is not None:
        return _client

    async with _lock:
        if _client is not None:
            return _client

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set, can't create LLM client")

        log.info(f"creating AsyncOpenAI client, model={settings.openai_model}")
        _client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.llm_timeout,
        )
        return _client


async def chat_json(system: str, user: str) -> LLMResponse:
    """
    Send a chat request expecting JSON response.
    Returns LLMResponse with content string.
    """
    client = await get_llm()

    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    content = resp.choices[0].message.content or "{}"
    return LLMResponse(content=content)


def get_llm_sync() -> AsyncOpenAI | None:
    """For testing or sync contexts. Returns None if not initialized."""
    return _client


async def reset_llm() -> None:
    """For testing. Clears the singleton."""
    global _client
    async with _lock:
        _client = None


async def reset_llm() -> None:
    """For testing. Clears the singleton."""
    global _llm
    async with _lock:
        _llm = None
