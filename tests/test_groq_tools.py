import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.groq_service import GroqService
from app.tools.order_tools import TOOL_DEFINITIONS


def _mock_usage(prompt_tokens=10, completion_tokens=20, total_tokens=30):
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = total_tokens
    return usage


def _mock_tool_call(name, arguments, call_id="call_1"):
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function = MagicMock()
    tool_call.function.name = name
    tool_call.function.arguments = arguments
    tool_call.model_dump.return_value = {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments,
        },
    }
    return tool_call


def _mock_response(content=None, tool_calls=None, usage=None):
    response = MagicMock()
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    response.choices = [MagicMock()]
    response.choices[0].message = message
    response.usage = usage
    return response


def _make_service():
    service = GroqService()
    service._client = None
    return service


@pytest.mark.asyncio
async def test_groq_tool_calling_success(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    tool_call = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(
        content="Order ORD1001 has been shipped and arrives 2026-11-20.",
        usage=_mock_usage(prompt_tokens=50, completion_tokens=60, total_tokens=110),
    )

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, model, latency_ms, usage = await service.generate_with_tools(
            "What is the status of order ORD1001?",
            TOOL_DEFINITIONS,
        )

    assert text == "Order ORD1001 has been shipped and arrives 2026-11-20."
    assert model == "openai/gpt-oss-120b"
    assert latency_ms >= 0
    assert usage == {"input_tokens": 50, "output_tokens": 60, "total_tokens": 110}

    calls = mock_client.chat.completions.create.await_args_list
    assert len(calls) == 2

    first_call = calls[0].args[0] if calls[0].args else calls[0].kwargs
    assert first_call.get("tools") or calls[0].kwargs.get("tools")


@pytest.mark.asyncio
async def test_groq_tool_calling_no_tool_call(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    first = _mock_response(
        content="I can help with that!",
        usage=_mock_usage(),
    )

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=first)
        mock_cls.return_value = mock_client

        service = _make_service()
        text, model, _latency_ms, usage = await service.generate_with_tools(
            "Hello", TOOL_DEFINITIONS
        )

    assert text == "I can help with that!"
    assert model == "openai/gpt-oss-120b"
    assert usage == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}

    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_groq_tool_calling_unknown_order(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    tool_call = _mock_tool_call("lookup_order_status", '{"order_id": "ORD9999"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(
        content="I could not find that order.",
        usage=_mock_usage(),
    )

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, _model, _latency, _usage = await service.generate_with_tools(
            "Status of ORD9999?", TOOL_DEFINITIONS
        )

    assert text == "I could not find that order."

    # The second call must include a tool result with not-found info.
    second_call_kwargs = mock_client.chat.completions.create.await_args_list[1].kwargs
    follow_up_messages = second_call_kwargs["messages"]
    tool_msg = follow_up_messages[-1]
    assert tool_msg["role"] == "tool"
    payload = json.loads(tool_msg["content"])
    assert payload == {"error": "Order not found"}


@pytest.mark.asyncio
async def test_groq_tool_calling_malformed_arguments(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    tool_call = _mock_tool_call("lookup_order_status", "this is not valid json")
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(
        content="Sorry, I could not understand the request.",
        usage=_mock_usage(),
    )

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, _model, _latency, _usage = await service.generate_with_tools(
            "Status?", TOOL_DEFINITIONS
        )

    assert text == "Sorry, I could not understand the request."

    second_call_kwargs = mock_client.chat.completions.create.await_args_list[1].kwargs
    follow_up_messages = second_call_kwargs["messages"]
    tool_msg = follow_up_messages[-1]
    payload = json.loads(tool_msg["content"])
    assert payload == {"error": "Malformed tool arguments"}


@pytest.mark.asyncio
async def test_groq_tool_calling_unknown_tool(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    tool_call = _mock_tool_call("some_random_tool", '{"order_id": "ORD1001"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(content="That tool is not available.", usage=_mock_usage())

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, _model, _latency, _usage = await service.generate_with_tools(
            "Use some_random_tool", TOOL_DEFINITIONS
        )

    assert text == "That tool is not available."

    second_call_kwargs = mock_client.chat.completions.create.await_args_list[1].kwargs
    tool_msg = second_call_kwargs["messages"][-1]
    payload = json.loads(tool_msg["content"])
    assert payload == {"error": "Unknown tool: some_random_tool"}


@pytest.mark.asyncio
async def test_groq_tool_calling_provider_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    from groq import APIError

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIError("provider error", request=None, body=None)
        )
        mock_cls.return_value = mock_client

        service = _make_service()

        from app.services.llm_errors import LLMProviderError

        with pytest.raises(LLMProviderError) as exc_info:
            await service.generate_with_tools("Hello", TOOL_DEFINITIONS)

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_groq_tool_calling_missing_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    service = _make_service()

    from app.services.llm_errors import MissingAPIKeyError

    with pytest.raises(MissingAPIKeyError):
        await service.generate_with_tools("Hello", TOOL_DEFINITIONS)


@pytest.mark.asyncio
async def test_groq_tool_calling_multiple_tools_one_round(monkeypatch):
    """Two tools called in the same provider response should both be executed."""
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    # Add a second tool to registry for this test
    from app.tools.order_tools import TOOL_REGISTRY

    def dummy_tool(x: str) -> dict[str, str]:
        return {"echo": x}

    TOOL_REGISTRY["dummy_tool"] = dummy_tool
    try:
        tool_call_1 = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
        tool_call_2 = _mock_tool_call("dummy_tool", '{"x": "hello"}')
        first = _mock_response(tool_calls=[tool_call_1, tool_call_2], usage=_mock_usage())
        second = _mock_response(
            content="Done both.",
            usage=_mock_usage(prompt_tokens=50, completion_tokens=60, total_tokens=110),
        )

        with patch("app.services.groq_service.AsyncGroq") as mock_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
            mock_cls.return_value = mock_client

            service = _make_service()
            text, _model, _latency, _usage = await service.generate_with_tools(
                "Do two things", TOOL_DEFINITIONS
            )

        assert text == "Done both."

        # Second call messages should contain two tool results
        second_call_kwargs = mock_client.chat.completions.create.await_args_list[1].kwargs
        follow_up_messages = second_call_kwargs["messages"]
        tool_messages = [m for m in follow_up_messages if m["role"] == "tool"]
        assert len(tool_messages) == 2
    finally:
        TOOL_REGISTRY.pop("dummy_tool", None)


@pytest.mark.asyncio
async def test_groq_tool_calling_multiple_rounds(monkeypatch):
    """Model calls tools in round 1, gets results, calls another tool in round 2, then answers."""
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    from app.tools.order_tools import TOOL_REGISTRY

    def dummy_tool(x: str) -> dict[str, str]:
        return {"echo": x}

    TOOL_REGISTRY["dummy_tool"] = dummy_tool
    try:
        # Round 1: model calls lookup_order_status
        tool_call_1 = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
        r1 = _mock_response(
            tool_calls=[tool_call_1],
            usage=_mock_usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        # Round 2: model calls dummy_tool
        tool_call_2 = _mock_tool_call("dummy_tool", '{"x": "foo"}')
        r2 = _mock_response(
            tool_calls=[tool_call_2],
            usage=_mock_usage(prompt_tokens=40, completion_tokens=50, total_tokens=90),
        )
        # Round 3: final answer
        r3 = _mock_response(
            content="Final answer.",
            usage=_mock_usage(prompt_tokens=60, completion_tokens=70, total_tokens=130),
        )

        with patch("app.services.groq_service.AsyncGroq") as mock_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=[r1, r2, r3])
            mock_cls.return_value = mock_client

            service = _make_service()
            text, _model, _latency, usage = await service.generate_with_tools(
                "Multi round", TOOL_DEFINITIONS
            )

        assert text == "Final answer."
        # Usage must be from final round only (not accumulated)
        assert usage == {"input_tokens": 60, "output_tokens": 70, "total_tokens": 130}
        assert mock_client.chat.completions.create.await_count == 3
    finally:
        TOOL_REGISTRY.pop("dummy_tool", None)


@pytest.mark.asyncio
async def test_groq_tool_calling_max_iterations(monkeypatch):
    """After MAX_TOOL_ITERATIONS rounds with tool calls, raise ToolCallLimitError."""
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    # Model returns a tool call on every round
    tool_call = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
    rounds = [_mock_response(tool_calls=[tool_call], usage=_mock_usage()) for _ in range(6)]

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=rounds)
        mock_cls.return_value = mock_client

        service = _make_service()

        from app.services.llm_errors import ToolCallLimitError

        with pytest.raises(ToolCallLimitError) as exc_info:
            await service.generate_with_tools("Loop forever", TOOL_DEFINITIONS)

        assert "Exceeded maximum of 5 tool-calling iterations" in str(exc_info.value)
        # Exactly 5 calls (iterations 1..5)
        assert mock_client.chat.completions.create.await_count == 5


@pytest.mark.asyncio
async def test_groq_tool_calling_malformed_json_arguments(monkeypatch):
    """Malformed JSON in tool arguments produces an error tool result."""
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    tool_call = _mock_tool_call("lookup_order_status", "not valid json")
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(content="Got malformed.", usage=_mock_usage())

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, _model, _latency, _usage = await service.generate_with_tools("Test", TOOL_DEFINITIONS)

    assert text == "Got malformed."
    second_call_kwargs = mock_client.chat.completions.create.await_args_list[1].kwargs
    tool_msg = second_call_kwargs["messages"][-1]
    assert tool_msg["role"] == "tool"
    payload = json.loads(tool_msg["content"])
    assert payload == {"error": "Malformed tool arguments"}


@pytest.mark.asyncio
async def test_groq_tool_calling_tool_execution_error(monkeypatch):
    """Unexpected exception during tool execution raises LLMProviderError."""
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    tool_call = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=first)
        mock_cls.return_value = mock_client

        # Monkeypatch the registry tool to raise an unexpected error
        from app.tools.order_tools import TOOL_REGISTRY

        original = TOOL_REGISTRY["lookup_order_status"]

        def bad_tool(**kwargs):
            raise RuntimeError("unexpected failure")

        TOOL_REGISTRY["lookup_order_status"] = bad_tool
        try:
            service = _make_service()

            from app.services.llm_errors import LLMProviderError

            with pytest.raises(LLMProviderError) as exc_info:
                await service.generate_with_tools("Test", TOOL_DEFINITIONS)

            assert exc_info.value.status_code == 502
            assert "Tool execution failed" in str(exc_info.value)
        finally:
            TOOL_REGISTRY["lookup_order_status"] = original


@pytest.mark.asyncio
async def test_groq_tool_calling_message_ordering(monkeypatch):
    """Assistant message with tool_calls comes BEFORE tool result messages."""
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    tool_call = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(content="Answer.", usage=_mock_usage())

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        await service.generate_with_tools("Test", TOOL_DEFINITIONS)

    second_call_kwargs = mock_client.chat.completions.create.await_args_list[1].kwargs
    follow_up_messages = second_call_kwargs["messages"]

    # Order should be: user, assistant(with tool_calls), tool result
    assistant_msg = follow_up_messages[1]
    tool_msg = follow_up_messages[2]

    assert assistant_msg["role"] == "assistant"
    assert "tool_calls" in assistant_msg
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == tool_call.id


@pytest.mark.asyncio
async def test_groq_tool_calling_token_usage_preserved_final_round(monkeypatch):
    """Usage returned equals the final round's usage, not accumulated across rounds."""
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")

    from app.tools.order_tools import TOOL_REGISTRY

    def dummy_tool(x: str) -> dict[str, str]:
        return {"echo": x}

    TOOL_REGISTRY["dummy_tool"] = dummy_tool
    try:
        # Round 1 usage: 10+20=30
        tool_call_1 = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
        r1 = _mock_response(
            tool_calls=[tool_call_1],
            usage=_mock_usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        # Round 2 usage: 40+50=90
        tool_call_2 = _mock_tool_call("dummy_tool", '{"x": "foo"}')
        r2 = _mock_response(
            tool_calls=[tool_call_2],
            usage=_mock_usage(prompt_tokens=40, completion_tokens=50, total_tokens=90),
        )
        # Round 3 final usage: 60+70=130
        r3 = _mock_response(
            content="Done.",
            usage=_mock_usage(prompt_tokens=60, completion_tokens=70, total_tokens=130),
        )

        with patch("app.services.groq_service.AsyncGroq") as mock_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=[r1, r2, r3])
            mock_cls.return_value = mock_client

            service = _make_service()
            _text, _model, _latency, usage = await service.generate_with_tools(
                "Test", TOOL_DEFINITIONS
            )

        # Must match final round only
        assert usage == {"input_tokens": 60, "output_tokens": 70, "total_tokens": 130}
    finally:
        TOOL_REGISTRY.pop("dummy_tool", None)
