import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.openai_service import OpenAIService
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
    service = OpenAIService()
    service._client = None
    return service


@pytest.mark.asyncio
async def test_openai_tool_calling_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    tool_call = _mock_tool_call("lookup_order_status", '{"order_id": "ORD1001"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(
        content="Order ORD1001 has been shipped and arrives 2026-11-20.",
        usage=_mock_usage(prompt_tokens=50, completion_tokens=60, total_tokens=110),
    )

    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, model, latency_ms, usage = await service.generate_with_tools(
            "What is the status of order ORD1001?",
            TOOL_DEFINITIONS,
        )

    assert text == "Order ORD1001 has been shipped and arrives 2026-11-20."
    assert model == "gpt-4o-mini"
    assert latency_ms >= 0
    assert usage == {"input_tokens": 50, "output_tokens": 60, "total_tokens": 110}


@pytest.mark.asyncio
async def test_openai_tool_calling_no_tool_call(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    first = _mock_response(
        content="I can help with that!",
        usage=_mock_usage(),
    )

    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=first)
        mock_cls.return_value = mock_client

        service = _make_service()
        text, model, _latency_ms, usage = await service.generate_with_tools(
            "Hello", TOOL_DEFINITIONS
        )

    assert text == "I can help with that!"
    assert model == "gpt-4o-mini"
    assert usage == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}


@pytest.mark.asyncio
async def test_openai_tool_calling_unknown_order(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    tool_call = _mock_tool_call("lookup_order_status", '{"order_id": "ORD9999"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(
        content="I could not find that order.",
        usage=_mock_usage(),
    )

    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[first, second])
        mock_cls.return_value = mock_client

        service = _make_service()
        text, _model, _latency, _usage = await service.generate_with_tools(
            "Status of ORD9999?", TOOL_DEFINITIONS
        )

    assert text == "I could not find that order."

    second_call_kwargs = mock_client.chat.completions.create.await_args_list[1].kwargs
    follow_up_messages = second_call_kwargs["messages"]
    tool_msg = follow_up_messages[-1]
    assert tool_msg["role"] == "tool"
    payload = json.loads(tool_msg["content"])
    assert payload == {"error": "Order not found"}


@pytest.mark.asyncio
async def test_openai_tool_calling_malformed_arguments(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    tool_call = _mock_tool_call("lookup_order_status", "this is not valid json")
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(
        content="Sorry, I could not understand the request.",
        usage=_mock_usage(),
    )

    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
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
async def test_openai_tool_calling_unknown_tool(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    tool_call = _mock_tool_call("some_random_tool", '{"order_id": "ORD1001"}')
    first = _mock_response(tool_calls=[tool_call], usage=_mock_usage())
    second = _mock_response(content="That tool is not available.", usage=_mock_usage())

    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
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
async def test_openai_tool_calling_provider_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    from openai import APIError

    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
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
async def test_openai_tool_calling_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = _make_service()

    from app.services.llm_errors import MissingAPIKeyError

    with pytest.raises(MissingAPIKeyError):
        await service.generate_with_tools("Hello", TOOL_DEFINITIONS)
