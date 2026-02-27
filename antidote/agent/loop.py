"""Core agent loop for Antidote.

Receives messages, retrieves relevant memories, calls the LLM with
available tools, executes tool calls in a loop (max 5 rounds), and
returns the final response. Maintains per-chat conversation history.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict

from antidote.agent.context import ContextBuilder
from antidote.channels.base import IncomingMessage
from antidote.config import Config
from antidote.memory.store import MemoryStore
from antidote.providers.base import BaseProvider, Message
from antidote.tools.base import ToolResult
from antidote.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Maximum tool call rounds per message
MAX_TOOL_ROUNDS = 5

# Maximum conversation history messages per chat
MAX_HISTORY = 50

# Trivial messages that should not be saved to memory
_TRIVIAL_PATTERNS = frozenset({
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay",
    "bye", "goodbye", "yes", "no", "sure", "yep", "nope",
    "cool", "great", "nice", "👍", "👋",
})


def _is_trivial(text: str) -> bool:
    """Check if a message is trivial and not worth saving to memory."""
    return text.strip().lower().rstrip("!.?") in _TRIVIAL_PATTERNS


# Keywords that signal a complex query requiring the full model
_COMPLEXITY_KEYWORDS = re.compile(
    r"\b(?:draft|write|analyze|compare|plan|strategy|review|create|build|design"
    r"|explain|outline|evaluate|summarize|refactor|debug|help me|what should)\b",
    re.IGNORECASE,
)


def _classify_query(text: str) -> str:
    """Classify a user query as 'fast' (Haiku) or 'full' (Sonnet).

    Routes to Haiku when the message is trivial or short without complexity
    signals. Routes to Sonnet for anything requiring real reasoning.
    """
    if _is_trivial(text):
        return "fast"

    # Code fences → full model
    if "```" in text:
        return "full"

    # Long messages → user invested effort → full model
    if len(text) > 200:
        return "full"

    # Multiple sentences → full model
    sentence_endings = len(re.findall(r"[.?!]", text))
    if sentence_endings >= 2:
        return "full"

    # Complexity keywords → full model
    if _COMPLEXITY_KEYWORDS.search(text):
        return "full"

    # Short, simple message without complexity signals → fast model
    if len(text) < 80:
        return "fast"

    return "full"


class AgentLoop:
    """The brain of Antidote. Processes messages through LLM with tool support.

    Usage:
        agent = AgentLoop(provider, context, memory, tools)
        response = await agent.process_message(incoming)
    """

    def __init__(
        self,
        provider: BaseProvider,
        context: ContextBuilder,
        memory: MemoryStore,
        tools: ToolRegistry,
    ) -> None:
        self._provider = provider
        self._context = context
        self._memory = memory
        self._tools = tools
        self._history: dict[str, list[Message]] = defaultdict(list)

        # Register built-in memory tools
        self._register_memory_tools()

    def _register_memory_tools(self) -> None:
        """Register save_memory, search_memory, and forget_memory as tools."""
        self._tools.register(_SaveMemoryTool(self._memory))
        self._tools.register(_SearchMemoryTool(self._memory))
        self._tools.register(_ForgetMemoryTool(self._memory))

    def _select_model(self, text: str) -> str | None:
        """Pick the right model tier based on query complexity.

        Returns a model string for the provider, or None to use the default.
        """
        config = Config()
        routing = config.get("routing")
        if routing is None or not routing.enabled:
            return None

        tier = _classify_query(text)
        if tier == "fast":
            model = routing.fast_model
        else:
            model = routing.full_model  # None means provider default

        logger.info("Routing → %s (model=%s)", tier, model or "provider-default")
        return model

    def _get_history(self, chat_id: str) -> list[Message]:
        """Get conversation history for a chat, capped at MAX_HISTORY."""
        return self._history[chat_id]

    def _append_history(self, chat_id: str, message: Message) -> None:
        """Append a message to the chat history, trimming if over limit."""
        history = self._history[chat_id]
        history.append(message)
        if len(history) > MAX_HISTORY:
            self._history[chat_id] = history[-MAX_HISTORY:]

    async def process_message(self, incoming: IncomingMessage) -> str:
        """Process an incoming message and return the response text.

        Flow:
        1. Load relevant memories via context builder
        2. Build message list (system prompt + history + new message)
        3. Call provider with messages + available tools
        4. If LLM returns tool calls, execute them and loop (max 5 rounds)
        5. Save conversation summary to memory (if substantive)
        6. Return final text response
        """
        chat_id = incoming.chat_id
        user_text = incoming.text

        # Get conversation history for this chat
        history = self._get_history(chat_id)

        # Build full context with system prompt, memories, and history
        tool_defs = self._tools.as_definitions()
        messages = await self._context.build_conversation_context(
            messages=history,
            query=user_text,
        )

        # Track user message in history
        self._append_history(chat_id, Message(role="user", content=user_text))

        # Select model tier based on query complexity
        selected_model = self._select_model(user_text)

        # LLM call loop with tool support
        response_text = await self._run_llm_loop(
            messages=messages,
            tool_defs=tool_defs,
            chat_id=chat_id,
            model=selected_model,
        )

        # Track assistant response in history
        self._append_history(chat_id, Message(role="assistant", content=response_text))

        # Save conversation summary to memory if substantive
        if not _is_trivial(user_text) and not _is_trivial(response_text):
            await self._save_conversation_summary(user_text, response_text)

        return response_text

    async def _run_llm_loop(
        self,
        messages: list[Message],
        tool_defs: list,
        chat_id: str,
        model: str | None = None,
    ) -> str:
        """Call the LLM, process tool calls, repeat until text response or max rounds."""
        current_messages = list(messages)
        current_model = model

        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                response = await self._provider.chat(
                    messages=current_messages,
                    tools=tool_defs if tool_defs else None,
                    model=current_model,
                )
            except Exception as e:
                logger.exception("LLM call failed (round %d)", round_num)
                return f"I encountered an error communicating with the AI provider: {e}"

            # If no tool calls, we have the final text response
            if not response.tool_calls:
                return response.content or "I'm not sure how to respond to that."

            # Upgrade: if Haiku returned tool calls, switch to Sonnet for
            # remaining rounds — Sonnet is better at synthesizing tool outputs
            if current_model and current_model != model:
                pass  # already upgraded
            elif current_model is not None:
                config = Config()
                full_model = config.get("routing", {}).get("full_model")
                if full_model is None:
                    full_model_resolved = None  # provider default (Sonnet)
                else:
                    full_model_resolved = full_model
                if current_model != full_model_resolved:
                    logger.info(
                        "Upgrading model for tool synthesis: %s → %s",
                        current_model,
                        full_model_resolved or "provider-default",
                    )
                    current_model = full_model_resolved

            # Process tool calls
            assistant_msg = Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            )
            current_messages.append(assistant_msg)

            for tool_call in response.tool_calls:
                tool_result = await self._execute_tool_call(tool_call)
                tool_msg = Message(
                    role="tool",
                    content=tool_result,
                    tool_call_id=tool_call.get("id", ""),
                )
                current_messages.append(tool_msg)

            logger.debug("Tool round %d/%d complete", round_num + 1, MAX_TOOL_ROUNDS)

        # Max rounds reached -- force a final text response without tools
        try:
            current_messages.append(
                Message(
                    role="user",
                    content="Please provide your final response based on the tool results above.",
                )
            )
            response = await self._provider.chat(
                messages=current_messages,
                tools=None,  # No tools -- force text response
                model=current_model,
            )
            return response.content or "I've completed the tool operations but couldn't formulate a response."
        except Exception as e:
            logger.exception("Final LLM call failed")
            return f"I encountered an error after processing tools: {e}"

    async def _execute_tool_call(self, tool_call: dict) -> str:
        """Execute a single tool call and return the result as a string."""
        tool_name = tool_call.get("name", "")
        arguments_raw = tool_call.get("arguments", "{}")

        # Parse arguments
        if isinstance(arguments_raw, str):
            try:
                arguments = json.loads(arguments_raw)
            except json.JSONDecodeError:
                return json.dumps({"error": f"Invalid JSON arguments: {arguments_raw}"})
        elif isinstance(arguments_raw, dict):
            arguments = arguments_raw
        else:
            arguments = {}

        # Look up tool
        tool = self._tools.get(tool_name)
        if tool is None:
            logger.warning("Unknown tool called: %s", tool_name)
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        # Execute
        try:
            result: ToolResult = await tool.execute(**arguments)
            return json.dumps({
                "success": result.success,
                "output": result.output,
                "error": result.error,
            })
        except Exception as e:
            logger.exception("Tool '%s' failed", tool_name)
            return json.dumps({"error": f"Tool execution failed: {e}"})

    async def _save_conversation_summary(self, user_text: str, response_text: str) -> None:
        """Save a brief conversation summary to memory."""
        # Keep the summary concise
        user_preview = user_text[:200]
        response_preview = response_text[:200]
        summary = f"User asked: {user_preview}\nAssistant responded: {response_preview}"
        try:
            await self._memory.save(summary, category="conversation")
        except Exception:
            logger.debug("Failed to save conversation summary", exc_info=True)


# --- Built-in memory tools ---


class _SaveMemoryTool:
    """Built-in tool: save something to long-term memory."""

    name = "save_memory"
    description = "Save a fact, preference, or piece of information to long-term memory for later recall."
    parameters = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The information to remember",
            },
            "category": {
                "type": "string",
                "description": "Category: 'fact', 'preference', 'conversation', or 'solution'",
                "enum": ["fact", "preference", "conversation", "solution"],
            },
        },
        "required": ["content"],
    }

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory

    async def execute(self, **kwargs) -> ToolResult:
        content = kwargs.get("content", "")
        category = kwargs.get("category", "fact")
        if not content:
            return ToolResult(success=False, output="", error="No content provided")
        try:
            mem_id = await self._memory.save(content, category=category)
            return ToolResult(success=True, output=f"Saved to memory (id={mem_id})")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class _SearchMemoryTool:
    """Built-in tool: search long-term memory."""

    name = "search_memory"
    description = "Search long-term memory for previously saved information."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (keywords)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, output="", error="No query provided")
        try:
            results = await self._memory.search(query, limit=10)
            if not results:
                return ToolResult(success=True, output="No memories found matching that query.")
            lines = []
            for mem in results:
                lines.append(f"[id={mem.id}, {mem.category}] {mem.content}")
            return ToolResult(success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class _ForgetMemoryTool:
    """Built-in tool: delete a memory by ID."""

    name = "forget_memory"
    description = "Delete a specific memory by its ID. Use search_memory first to find the ID."
    parameters = {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "description": "The memory ID to delete",
            },
        },
        "required": ["id"],
    }

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory

    async def execute(self, **kwargs) -> ToolResult:
        memory_id = kwargs.get("id")
        if memory_id is None:
            return ToolResult(success=False, output="", error="No memory ID provided")
        try:
            deleted = await self._memory.forget(int(memory_id))
            if deleted:
                return ToolResult(success=True, output=f"Memory {memory_id} deleted.")
            else:
                return ToolResult(success=True, output=f"Memory {memory_id} not found.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
