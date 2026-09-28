"""LLM client for OpenRouter chat completions."""

import logging

import httpx

from .config import MODEL_TIMEOUT, OPENROUTER_API_KEY, OPENROUTER_API_URL

logger = logging.getLogger(__name__)


async def query_model(
    model: str,
    prompt: str,
    *,
    timeout: float = MODEL_TIMEOUT,
) -> str | None:
    """
    Send a single-message prompt to a model.

    Args:
        model: OpenRouter model identifier (e.g. "openai/gpt-5.1")
        prompt: The user message to send
        timeout: Request timeout in seconds

    Returns:
        The response text, or None if the request failed
    """
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"].get("content") or ""
    except Exception as e:
        logger.warning("Error querying model %s: %s", model, e)
        return None
