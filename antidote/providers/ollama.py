"""Ollama provider via LiteLLM.

Local LLM fallback. Zero cost, full privacy. Uses LiteLLM's acompletion()
with the "ollama/" prefix to route requests to a local Ollama instance.
"""

from __future__ import annotations

import json
import logging

import litellm

from antidote.config import Config
from antidote.providers.base import (
    BaseProvider,
    LLMResponse,
    Message,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Local Ollama LLM provider via LiteLLM."""

    def __init__(self) -> None:
        self._config = Config()
        self._default_model = self._config.providers.ollama.model
        self._base_url = self._config.providers.ollama.base_url

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

    def _build_tool_prompt(self, tools: list[ToolDefinition]) -> str:
        """Build a text-based tool description for models without native tool calling."""
        lines = [
            "You have access to the following tools. To use a tool, respond with "
            "a JSON block like: {\"tool\": \"tool_name\", \"arguments\": {...}}\n"
        ]
        for tool in tools:
            lines.append(f"- **{tool.name}**: {tool.description}")
            if tool.parameters.get("properties"):
                params = ", ".join(tool.parameters["properties"].keys())
                lines.append(f"  Parameters: {params}")
        return "\n".join(lines)

    def _parse_text_tool_calls(self, content: str) -> list[dict] | None:
        """Try to extract tool calls from plain-text responses (fallback mode)."""
        # Look for JSON blocks that look like tool calls
        try:
            # Try to find a JSON object in the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end <= start:
                return None
            candidate = content[start:end]
            data = json.loads(candidate)
            if "tool" in data and "arguments" in data:
                return [{
                    "id": f"text_call_0",
                    "name": data["tool"],
                    "arguments": json.dumps(data["arguments"])
                    if isinstance(data["arguments"], dict)
                    else data["arguments"],
                }]
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send messages to local Ollama via LiteLLM. Gracefully handles Ollama being down."""
        model_name = f"ollama/{model or self._default_model}"
        formatted_messages = self._format_messages(messages)

        kwargs: dict = {
            "model": model_name,
            "messages": formatted_messages,
            "temperature": temperature,
            "api_base": self._base_url,
        }

        # Try native tool calling first; fall back to prompt-based
        use_native_tools = tools is not None
        if use_native_tools:
            kwargs["tools"] = self._format_tools(tools)

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            error_str = str(exc).lower()

            # If native tools failed, retry without tools (prompt-based fallback)
            if use_native_tools and ("tool" in error_str or "function" in error_str):
                logger.warning(
                    "Model %s doesn't support native tools, falling back to prompt-based",
                    model_name,
                )
                del kwargs["tools"]
                # Inject tool descriptions into the system prompt
                tool_prompt = self._build_tool_prompt(tools)
                formatted_messages.insert(0, {
                    "role": "system",
                    "content": tool_prompt,
                })
                kwargs["messages"] = formatted_messages
                try:
                    response = await litellm.acompletion(**kwargs)
                except Exception as inner_exc:
                    return self._handle_connection_error(inner_exc)
            else:
                return self._handle_connection_error(exc)

        choice = response.choices[0]
        message = choice.message

        # Parse tool calls -- native or text-based fallback
        tool_calls = None
        if message.tool_calls:
            tool_calls = self._parse_tool_calls(message.tool_calls)
        elif tools and message.content:
            tool_calls = self._parse_text_tool_calls(message.content)

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

    @staticmethod
    def _handle_connection_error(exc: Exception) -> LLMResponse:
        """Return a friendly error response when Ollama is unreachable."""
        error_str = str(exc).lower()
        if "connection" in error_str or "refused" in error_str or "timeout" in error_str:
            logger.error("Ollama is not reachable: %s", exc)
            return LLMResponse(
                content=(
                    "I couldn't reach the local Ollama server. "
                    "Make sure Ollama is running (`ollama serve`) and try again."
                ),
                tool_calls=None,
                usage=None,
            )
        logger.error("Ollama request failed: %s", exc)
        return LLMResponse(
            content=f"Ollama error: {exc}",
            tool_calls=None,
            usage=None,
        )
