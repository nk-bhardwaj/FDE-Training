import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.anthropic_service import AnthropicService


def _mock_block(
    type="text",
    text="",
    id="",
    name="",
    input=None,
    cache_control=None,
):
    block = MagicMock()
    block.type = type
    block.text = text
    block.id = id
    block.name = name
    block.input = input if input is not None else {}
    return block


def _mock_usage(input_tokens=10, completion_tokens=20, total_tokens=30):
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = completion_tokens
    usage.total_tokens = total_tokens
    return usage


def _mock_response(blocks=None, usage=None):
    response = MagicMock()
    response.content = list(blocks or [])
    response.usage = usage
    return response


def _make_service():
    service = AnthropicService()
    service._client = None
    return service


@pytest.mark.asyncio
async def test_anthropic_tool_calling_success(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    tool_use = _mock_block(
        type="tool_use", id="call_1", name="lookup_order_status", input={"order_id": "ORD1001"}
    )
    first = _mock_response(blocks=[tool_use], usage=_mock_usage())
    second = _mock_response(
        blocks=[_mock_block(text="Order ORD1001 has been shipped.")],
        usage=_mock_usage(input_tokens=50, completion_tokens=60, total_tokens=110),
    )

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, model, latency_ms, usage = await service.generate_with_tools(
            "What is the status of order ORD1001?",
            {
                "lookup_order_status": {
                    "name": "lookup_order_status",
                    "description": "Look up an order",
                }
            },
        )

    assert text == "Order ORD1001 has been shipped."
    assert model == "claude-sonnet-4-5"
    assert latency_ms >= 0
    assert usage == {"input_tokens": 50, "output_tokens": 60, "total_tokens": 110}

    calls = mock_client.messages.create.await_args_list
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_anthropic_tool_calling_no_tool_call(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    first = _mock_response(
        blocks=[_mock_block(text="I can help with that!")],
        usage=_mock_usage(),
    )

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=first)
        mock_cls.return_value = mock_client

        service = _make_service()
        text, model, _latency_ms, usage = await service.generate_with_tools(
            "Hello",
            {
                "lookup_order_status": {
                    "name": "lookup_order_status",
                    "description": "Look up an order",
                }
            },
        )

    assert text == "I can help with that!"
    assert model == "claude-sonnet-4-5"
    assert usage == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    assert mock_client.messages.create.await_count == 1


@pytest.mark.asyncio
async def test_anthropic_tool_calling_multiple_tool_calls(monkeypatch):
    """Two tool_use blocks in one response should both be executed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    from app.tools.order_tools import TOOL_REGISTRY

    def dummy_tool(x: str) -> dict[str, str]:
        return {"echo": x}

    TOOL_REGISTRY["dummy_tool"] = dummy_tool
    try:
        tool_use_1 = _mock_block(
            type="tool_use", id="call_1", name="lookup_order_status", input={"order_id": "ORD1001"}
        )
        tool_use_2 = _mock_block(
            type="tool_use", id="call_2", name="dummy_tool", input={"x": "hello"}
        )
        first = _mock_response(blocks=[tool_use_1, tool_use_2], usage=_mock_usage())
        second = _mock_response(
            blocks=[_mock_block(text="Done both.")],
            usage=_mock_usage(input_tokens=50, completion_tokens=60, total_tokens=110),
        )

        with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(side_effect=[first, second])
            mock_cls.return_value = mock_client

            service = _make_service()
            text, _model, _latency, _usage = await service.generate_with_tools(
                "Do two things",
                {
                    "lookup_order_status": {
                        "name": "lookup_order_status",
                        "description": "Look up an order",
                    }
                },
            )

        assert text == "Done both."

        second_call_kwargs = mock_client.messages.create.await_args_list[1].kwargs
        follow_up_messages = second_call_kwargs["messages"]
        # Should contain a user message with two tool_result blocks.
        result_messages = [
            m
            for m in follow_up_messages
            if m["role"] == "user" and isinstance(m.get("content"), list)
        ]
        assert len(result_messages) == 1
        tool_results = [
            b
            for b in result_messages[0]["content"]
            if isinstance(b, dict) and b.get("type") == "tool_result"
        ]
        assert len(tool_results) == 2
    finally:
        TOOL_REGISTRY.pop("dummy_tool", None)


@pytest.mark.asyncio
async def test_anthropic_tool_calling_multiple_rounds(monkeypatch):
    """Model calls tools in round 1, another tool in round 2, then answers."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    from app.tools.order_tools import TOOL_REGISTRY

    def dummy_tool(x: str) -> dict[str, str]:
        return {"echo": x}

    TOOL_REGISTRY["dummy_tool"] = dummy_tool
    try:
        # Round 1: model calls lookup_order_status
        tool_call_1 = _mock_block(
            type="tool_use", id="call_1", name="lookup_order_status", input={"order_id": "ORD1001"}
        )
        r1 = _mock_response(
            blocks=[tool_call_1],
            usage=_mock_usage(input_tokens=10, completion_tokens=20, total_tokens=30),
        )
        # Round 2: model calls dummy_tool
        tool_call_2 = _mock_block(
            type="tool_use", id="call_2", name="dummy_tool", input={"x": "foo"}
        )
        r2 = _mock_response(
            blocks=[tool_call_2],
            usage=_mock_usage(input_tokens=40, completion_tokens=50, total_tokens=90),
        )
        # Round 3: final answer
        r3 = _mock_response(
            blocks=[_mock_block(text="Final answer.")],
            usage=_mock_usage(input_tokens=60, completion_tokens=70, total_tokens=130),
        )

        with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(side_effect=[r1, r2, r3])
            mock_cls.return_value = mock_client

            service = _make_service()
            text, _model, _latency, usage = await service.generate_with_tools(
                "Multi round",
                {
                    "lookup_order_status": {
                        "name": "lookup_order_status",
                        "description": "Look up an order",
                    }
                },
            )

        assert text == "Final answer."
        # Usage must be from final round only (not accumulated)
        assert usage == {"input_tokens": 60, "output_tokens": 70, "total_tokens": 130}
        assert mock_client.messages.create.await_count == 3
    finally:
        TOOL_REGISTRY.pop("dummy_tool", None)


@pytest.mark.asyncio
async def test_anthropic_tool_calling_unknown_tool(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    tool_use = _mock_block(
        type="tool_use", id="call_1", name="some_random_tool", input={"order_id": "ORD1001"}
    )
    first = _mock_response(blocks=[tool_use], usage=_mock_usage())
    second = _mock_response(
        blocks=[_mock_block(text="That tool is not available.")],
        usage=_mock_usage(),
    )

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, _model, _latency, _usage = await service.generate_with_tools(
            "Use some_random_tool",
            {
                "lookup_order_status": {
                    "name": "lookup_order_status",
                    "description": "Look up an order",
                }
            },
        )

    assert text == "That tool is not available."

    second_call_kwargs = mock_client.messages.create.await_args_list[1].kwargs
    follow_up_messages = second_call_kwargs["messages"]
    tool_result_messages = [
        m for m in follow_up_messages if m["role"] == "user" and isinstance(m.get("content"), list)
    ]
    tool_results = [
        b
        for b in tool_result_messages[0]["content"]
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    payload = json.loads(tool_results[0]["content"])
    assert payload == {"error": "Unknown tool: some_random_tool"}


@pytest.mark.asyncio
async def test_anthropic_tool_calling_malformed_arguments(monkeypatch):
    """Non-JSON input object from Anthropic should still route through tool execution (invalid args error path)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    # Anthropic passes input as a parsed dict; malformed arguments scenario
    # arises when required args are missing or wrong type, producing Invalid arguments error.
    tool_use = _mock_block(type="tool_use", id="call_1", name="lookup_order_status", input={})
    first = _mock_response(blocks=[tool_use], usage=_mock_usage())
    second = _mock_response(
        blocks=[_mock_block(text="Got invalid arguments.")],
        usage=_mock_usage(),
    )

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, _model, _latency, _usage = await service.generate_with_tools(
            "Test",
            {
                "lookup_order_status": {
                    "name": "lookup_order_status",
                    "description": "Look up an order",
                }
            },
        )

    assert text == "Got invalid arguments."
    second_call_kwargs = mock_client.messages.create.await_args_list[1].kwargs
    follow_up_messages = second_call_kwargs["messages"]
    tool_result_messages = [
        m for m in follow_up_messages if m["role"] == "user" and isinstance(m.get("content"), list)
    ]
    tool_results = [
        b
        for b in tool_result_messages[0]["content"]
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    payload = json.loads(tool_results[0]["content"])
    assert payload == {"error": "Invalid arguments for tool"}


@pytest.mark.asyncio
async def test_anthropic_tool_calling_provider_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    from anthropic import APIError

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=APIError("provider error", request=None, body=None)
        )
        mock_cls.return_value = mock_client

        service = _make_service()

        from app.services.llm_errors import LLMProviderError

        with pytest.raises(LLMProviderError) as exc_info:
            await service.generate_with_tools(
                "Hello", {"lookup_order_status": {"name": "lookup_order_status"}}
            )

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_anthropic_tool_calling_missing_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    service = _make_service()

    from app.services.llm_errors import MissingAPIKeyError

    with pytest.raises(MissingAPIKeyError):
        await service.generate_with_tools(
            "Hello", {"lookup_order_status": {"name": "lookup_order_status"}}
        )


@pytest.mark.asyncio
async def test_anthropic_tool_calling_max_iterations(monkeypatch):
    """After MAX_TOOL_ITERATIONS rounds with tool calls, raise ToolCallLimitError."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    tool_use = _mock_block(
        type="tool_use", id="call_1", name="lookup_order_status", input={"order_id": "ORD1001"}
    )
    rounds = [_mock_response(blocks=[tool_use], usage=_mock_usage()) for _ in range(6)]

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=rounds)
        mock_cls.return_value = mock_client

        service = _make_service()

        from app.services.llm_errors import ToolCallLimitError

        with pytest.raises(ToolCallLimitError) as exc_info:
            await service.generate_with_tools(
                "Loop forever", {"lookup_order_status": {"name": "lookup_order_status"}}
            )

        assert "Exceeded maximum of 5 tool-calling iterations" in str(exc_info.value)
        # Exactly 5 calls (iterations 1..5)
        assert mock_client.messages.create.await_count == 5


@pytest.mark.asyncio
async def test_anthropic_tool_calling_token_usage_preserved_final_round(monkeypatch):
    """Usage returned equals the final round's usage, not accumulated across rounds."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")

    from app.tools.order_tools import TOOL_REGISTRY

    def dummy_tool(x: str) -> dict[str, str]:
        return {"echo": x}

    TOOL_REGISTRY["dummy_tool"] = dummy_tool
    try:
        # Round 1 usage: 10+20=30
        tool_call_1 = _mock_block(
            type="tool_use", id="call_1", name="lookup_order_status", input={"order_id": "ORD1001"}
        )
        r1 = _mock_response(
            blocks=[tool_call_1],
            usage=_mock_usage(input_tokens=10, completion_tokens=20, total_tokens=30),
        )
        # Round 2 usage: 40+50=90
        tool_call_2 = _mock_block(
            type="tool_use", id="call_2", name="dummy_tool", input={"x": "foo"}
        )
        r2 = _mock_response(
            blocks=[tool_call_2],
            usage=_mock_usage(input_tokens=40, completion_tokens=50, total_tokens=90),
        )
        # Round 3 final usage: 60+70=130
        r3 = _mock_response(
            blocks=[_mock_block(text="Done.")],
            usage=_mock_usage(input_tokens=60, completion_tokens=70, total_tokens=130),
        )

        with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(side_effect=[r1, r2, r3])
            mock_cls.return_value = mock_client

            service = _make_service()
            _text, _model, _latency, usage = await service.generate_with_tools(
                "Test",
                {
                    "lookup_order_status": {
                        "name": "lookup_order_status",
                        "description": "Look up an order",
                    }
                },
            )

        assert usage == {"input_tokens": 60, "output_tokens": 70, "total_tokens": 130}
    finally:
        TOOL_REGISTRY.pop("dummy_tool", None)
