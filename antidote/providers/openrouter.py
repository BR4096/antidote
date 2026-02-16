"""OpenRouter provider via LiteLLM.

Primary cloud provider supporting 100+ models through a single API key.
Uses LiteLLM's acompletion() for async calls with the "openrouter/" prefix.
"""

from __future__ import annotations

import asyncio
import logging
import os

import litellm

from antidote.config import Config
from antidote.providers.base import (
    BaseProvider,
    LLMResponse,
    Message,
    ToolDefinition,
)

logger = logging.getLogger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True


class OpenRouterProvider(BaseProvider):
    """OpenRouter LLM provider via LiteLLM."""

    def __init__(self) -> None:
        self._config = Config()
        self._api_key = self._resolve_api_key()
        self._default_model = self._config.providers.openrouter.model

    def _resolve_api_key(self) -> str:
        """Get API key from secrets store, fall back to env var."""
        key = self._config.get_secret("OPENROUTER_API_KEY")
        if not key:
            raise ValueError(
                "OPENROUTER_API_KEY not found. Run the setup wizard or set "
                "the OPENROUTER_API_KEY environment variable."
            )
        return key

    def _format_messages(self, messages: list[Message]) -> list[dict]:
        """Convert Message dataclasses to LiteLLM dict format."""
        formatted = []
        for msg in messages:
            entry: dict = {"role": msg.role, "content": msg.content or ""}
            if msg.tool_calls is not None:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id is not None:
                entry["tool_call_id"] = msg.tool_call_id
            formatted.append(entry)
        return formatted

    def _format_tools(self, tools: list[ToolDefinition]) -> list[dict]:
        """Convert ToolDefinition dataclasses to OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    def _parse_tool_calls(self, raw_calls: list) -> list[dict]:
        """Extract tool call data from LiteLLM response."""
        parsed = []
        for call in raw_calls:
            parsed.append({
                "id": call.id,
                "name": call.function.name,
                "arguments": call.function.arguments,
            })
        return parsed

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send messages to OpenRouter via LiteLLM. Retries on 429/5xx."""
        model_name = f"openrouter/{model or self._default_model}"
        formatted_messages = self._format_messages(messages)

        kwargs: dict = {
            "model": model_name,
            "messages": formatted_messages,
            "temperature": temperature,
            "timeout": 120,
            "api_key": self._api_key,
        }

        if tools:
            kwargs["tools"] = self._format_tools(tools)

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await litellm.acompletion(**kwargs)
                break
            except Exception as exc:
                last_error = exc
                error_str = str(exc).lower()
                retryable = (
                    "429" in error_str
                    or "rate" in error_str
                    or "500" in error_str
                    or "502" in error_str
                    or "503" in error_str
                    or "504" in error_str
                )
                if not retryable or attempt == 2:
                    logger.error("OpenRouter request failed: %s", exc)
                    raise
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "OpenRouter error (attempt %d/3), retrying in %ds: %s",
                    attempt + 1,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
        else:
            raise last_error  # type: ignore[misc]

        choice = response.choices[0]
        message = choice.message

        # Parse tool calls if present
        tool_calls = None
        if message.tool_calls:
            tool_calls = self._parse_tool_calls(message.tool_calls)

        # Extract usage
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
            logger.info(
                "Token usage — prompt: %d, completion: %d, model: %s",
                usage["prompt_tokens"],
                usage["completion_tokens"],
                model_name,
            )

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage=usage,
        )
