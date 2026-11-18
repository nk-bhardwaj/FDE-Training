"""Shared tool-calling orchestration for provider services.

This module owns the provider-agnostic tool-calling loop. Each provider
service keeps its own API communication, tool-call parsing, message
formatting, SDK exception handling, and usage extraction by implementing
the :class:`ToolCallingAdapter` protocol.
"""

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.logging import get_logger
from app.schemas.llm import LLMGeneration
from app.services.llm_errors import (
    LLMProviderError,
    ToolCallLimitError,
)
from app.tools.order_tools import get_tool

logger = get_logger(__name__)

MAX_TOOL_ITERATIONS = 5


@dataclass(frozen=True)
class ToolCall:
    """Provider-normalized tool call."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ToolTurn:
    """Provider-normalized result of a single provider request."""

    content: str
    tool_calls: list[ToolCall]
    usage: dict[str, int | None]


class ToolCallingAdapter(Protocol):
    """Provider-specific adapter consumed by :func:`run_tool_calling`.

    Implementations live inside each provider service and keep all
    provider-specific concerns (client calls, response parsing, message
    formatting, SDK exception translation, usage extraction) local.
    """

    provider_name: str

    def format_tools(self, tool_definitions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert registry definitions into the provider's tool schema."""
        ...

    async def send_tool_request(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
    ) -> ToolTurn:
        """Send one provider request and return a normalized turn."""
        ...

    def append_assistant_message(self, messages: list[dict[str, Any]], turn: ToolTurn) -> None:
        """Append the assistant turn (including tool calls) to ``messages``."""
        ...

    def append_tool_result(
        self, messages: list[dict[str, Any]], tool_call: ToolCall, content: str
    ) -> None:
        """Append a single tool result message to ``messages``."""
        ...


def _execute_tool_call(tool_call: ToolCall) -> str:
    """Resolve and run a registered tool, returning its JSON content.

    Only functions registered in the tool registry are ever executed.
    Arbitrary model-generated code is never executed.
    """
    try:
        arguments = json.loads(tool_call.arguments) if tool_call.arguments else {}
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object")
    except (json.JSONDecodeError, TypeError, ValueError):
        return json.dumps({"error": "Malformed tool arguments"})

    try:
        tool_fn = get_tool(tool_call.name)
    except ValueError:
        return json.dumps({"error": f"Unknown tool: {tool_call.name}"})

    try:
        result = tool_fn(**arguments)
    except (TypeError, ValueError):
        return json.dumps({"error": "Invalid arguments for tool"})

    if result is None:
        return json.dumps({"error": "Order not found"})
    return json.dumps(result)


async def run_tool_calling(
    adapter: ToolCallingAdapter,
    messages: list[dict[str, Any]],
    tool_definitions: dict[str, dict[str, Any]],
    model: str,
) -> LLMGeneration:
    """Run the shared tool-calling loop for ``adapter``.

    The loop performs at most :data:`MAX_TOOL_ITERATIONS` provider requests.
    Each request that returns tool calls appends the assistant message first,
    then the corresponding tool results, before the next request.

    Raises:
        ToolCallLimitError: If the model keeps requesting tools past
            :data:`MAX_TOOL_ITERATIONS` without producing a final answer.
        LLMProviderError: If a provider request or tool execution fails
            unexpectedly.
    """
    start = time.perf_counter()
    tools = adapter.format_tools(tool_definitions)

    content = ""
    usage: dict[str, int | None] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }

    for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
        turn = await adapter.send_tool_request(messages, tools, model)
        content = turn.content
        usage = turn.usage

        if not turn.tool_calls:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
                adapter.provider_name,
                model,
                latency_ms,
                usage["input_tokens"],
                usage["output_tokens"],
                usage["total_tokens"],
            )
            return content, model, latency_ms, usage

        if iteration >= MAX_TOOL_ITERATIONS:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s model=%s status=failure latency_ms=%.2f reason=tool_call_limit iterations=%d",
                adapter.provider_name,
                model,
                latency_ms,
                iteration,
            )
            raise ToolCallLimitError(
                f"Exceeded maximum of {MAX_TOOL_ITERATIONS} tool-calling iterations"
            )

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "provider=%s model=%s status=tool_call latency_ms=%.2f tool_calls=%d input_tokens=%s output_tokens=%s total_tokens=%s",
            adapter.provider_name,
            model,
            latency_ms,
            len(turn.tool_calls),
            usage["input_tokens"],
            usage["output_tokens"],
            usage["total_tokens"],
        )

        adapter.append_assistant_message(messages, turn)

        for tool_call in turn.tool_calls:
            try:
                tool_content = _execute_tool_call(tool_call)
            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                logger.exception(
                    "provider=%s model=%s status=failure latency_ms=%.2f reason=tool_execution",
                    adapter.provider_name,
                    model,
                    latency_ms,
                )
                raise LLMProviderError("Tool execution failed", status_code=502) from exc
            adapter.append_tool_result(messages, tool_call, tool_content)

    raise ToolCallLimitError(f"Exceeded maximum of {MAX_TOOL_ITERATIONS} tool-calling iterations")
