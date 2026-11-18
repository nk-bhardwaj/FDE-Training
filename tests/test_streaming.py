import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.anthropic_service import AnthropicService
from app.services.groq_service import GroqService
from app.services.openai_service import OpenAIService

client = TestClient(app)


def _make_stream_mock(chunks, final_model):
    """Return an async generator function yielding text chunks then done."""

    async def _gen(prompt=None, model="test", system_prompt=None):
        for text, usage, mdl in chunks:
            yield text, usage, mdl
        yield "", {"input_tokens": None, "output_tokens": None, "total_tokens": None}, final_model

    return _gen


@pytest.fixture(autouse=True)
def reset_llm_service():
    """Reset the LLM service singleton so each test starts fresh."""
    from app.api.routes.llm import llm_service

    llm_service.openai._client = None
    llm_service.anthropic._client = None
    llm_service.groq._client = None


def _post_stream(provider: str, prompt: str = "hello", prompt_version: str | None = None):
    return client.post(
        "/api/chat/stream",
        json={"provider": provider, "prompt": prompt, "prompt_version": prompt_version},
    )


def _sse_events(response):
    lines = [line for line in response.text.strip().split("\n") if line.strip()]
    events = []
    for line in lines:
        assert line.startswith("data: "), f"Expected data: prefix, got: {line!r}"
        events.append(json.loads(line[len("data: ") :]))
    return events


# ---------- OpenAI streaming ----------


def test_stream_openai_chunks_and_done(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234567890abcdefgh")

    chunks = [
        ("Hello there!", None, "gpt-4o-mini"),
        (" How are you?", None, "gpt-4o-mini"),
        (" I'm doing well.", None, "gpt-4o-mini"),
    ]

    from app.api.routes.llm import llm_service as ls

    with patch.object(
        ls.openai, "generate_stream", new=_make_stream_mock(chunks, final_model="gpt-4o-mini")
    ):
        response = _post_stream("openai")
        assert response.status_code == 200

    events = _sse_events(response)
    assert len(events) == 4  # 3 chunk + 1 done
    assert [e["type"] for e in events[:3]] == ["chunk", "chunk", "chunk"]
    assert events[0]["text"] == "Hello there!"
    assert events[1]["text"] == " How are you?"
    assert events[2]["text"] == " I'm doing well."

    done = events[-1]
    assert done["type"] == "done"
    assert done["model"] == "gpt-4o-mini"
    assert "latency_ms" in done
    assert done["usage"] == {"input_tokens": None, "output_tokens": None, "total_tokens": None}


# ---------- Groq streaming ----------


def test_stream_groq_chunks_and_done(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test1234567890abcdefgh")

    chunks = [
        ("Hi!", None, "openai/gpt-oss-120b"),
        (" There!", None, "openai/gpt-oss-120b"),
    ]

    from app.api.routes.llm import llm_service as ls

    with patch.object(
        ls.groq, "generate_stream", new=_make_stream_mock(chunks, final_model="openai/gpt-oss-120b")
    ):
        response = _post_stream("groq")
        assert response.status_code == 200

    events = _sse_events(response)
    assert len(events) == 3  # 2 chunk + 1 done
    assert [e["type"] for e in events] == ["chunk", "chunk", "done"]
    assert events[0]["text"] == "Hi!"
    assert events[-1]["model"] == "openai/gpt-oss-120b"


# ---------- Anthropic streaming ----------


def test_stream_anthropic_chunks_and_done(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test1234567890abcdefgh")

    chunks = [
        ("Hey!", None, "claude-sonnet-4-5"),
        (" There!", None, "claude-sonnet-4-5"),
    ]

    from app.api.routes.llm import llm_service as ls

    with patch.object(
        ls.anthropic,
        "generate_stream",
        new=_make_stream_mock(chunks, final_model="claude-sonnet-4-5"),
    ):
        response = _post_stream("anthropic")
        assert response.status_code == 200

    events = _sse_events(response)
    assert len(events) == 3
    assert [e["type"] for e in events] == ["chunk", "chunk", "done"]
    assert events[-1]["model"] == "claude-sonnet-4-5"


# ---------- Prompt versioning ----------


def test_stream_with_prompt_version(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234567890abcdefgh")

    chunks = [
        ("User response.", None, "gpt-4o-mini"),
    ]

    from app.api.routes.llm import llm_service as ls

    with patch.object(
        ls.openai, "generate_stream", new=_make_stream_mock(chunks, final_model="gpt-4o-mini")
    ):
        response = _post_stream("openai", prompt_version="v1")
        assert response.status_code == 200

    events = _sse_events(response)
    assert len(events) == 2  # 1 chunk + 1 done
    assert events[0]["type"] == "chunk"
    assert events[-1]["type"] == "done"


# ---------- Provider error during streaming ----------


def test_stream_provider_error_yields_error_event(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234567890abcdefgh")

    from app.services.llm_errors import LLMProviderError

    async def _gen_err(prompt=None, model="gpt-4o-mini", system_prompt=None):
        yield "Partial text", None, "gpt-4o-mini"
        raise LLMProviderError("OpenAI request failed", status_code=502)

    from app.api.routes.llm import llm_service as ls

    with patch.object(ls.openai, "generate_stream", new=_gen_err):
        response = _post_stream("openai")
        assert response.status_code == 200

    events = _sse_events(response)
    assert len(events) == 2  # 1 chunk + 1 error
    assert events[0]["type"] == "chunk"
    assert events[-1]["type"] == "error"
    assert "OpenAI request failed" in events[-1]["message"]


# ---------- Missing API key (503 before streaming starts) ----------


def test_stream_missing_openai_key_returns_503(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = _post_stream("openai")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_stream_missing_anthropic_key_returns_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = _post_stream("anthropic")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_stream_missing_groq_key_returns_503(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = _post_stream("groq")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


# ---------- Client disconnection and upstream cleanup ----------


def test_stream_client_disconnection_no_done(monkeypatch):
    """When client disconnects, no 'done' event is emitted and upstream stream closes."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234567890abcdefgh")

    closed = []

    async def _gen_with_close(prompt=None, model="gpt-4o-mini", system_prompt=None):
        try:
            yield "Chunk 1", None, "gpt-4o-mini"
            yield "Chunk 2", None, "gpt-4o-mini"
        finally:
            closed.append(True)

    from app.api.routes.llm import llm_service as ls

    with (
        patch.object(ls.openai, "generate_stream", new=_gen_with_close),
        # is_disconnected: False before first chunk, True before second -> disconnect after 1st
        patch(
            "starlette.requests.Request.is_disconnected",
            new_callable=lambda: AsyncMock(side_effect=[False, True]),
        ),
    ):
        response = _post_stream("openai")
        assert response.status_code == 200

    events = _sse_events(response)
    # Only the first chunk yielded before disconnect; no 'done' event.
    assert events == [{"type": "chunk", "text": "Chunk 1"}]
    # Upstream stream was closed (finally block ran).
    assert closed == [True]


# ---------- Usage tracking ----------


class _AsyncIterable:
    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._items:
            return self._items.pop(0)
        raise StopAsyncIteration


class _AsyncContextManager:
    def __init__(self, obj):
        self._obj = obj

    async def __aenter__(self):
        return self._obj

    async def __aexit__(self, *args):
        return False


def _openai_chunk(content=None, usage=None):
    chunk = MagicMock()
    if content is not None:
        choice = MagicMock()
        choice.delta.content = content
        chunk.choices = [choice]
    else:
        chunk.choices = []
    chunk.usage = usage
    return chunk


def _openai_usage(prompt_tokens, completion_tokens, total_tokens):
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = total_tokens
    return usage


def _groq_chunk(content=None, usage=None, x_groq_present=True):
    chunk = MagicMock()
    if content is not None:
        choice = MagicMock()
        choice.delta.content = content
        chunk.choices = [choice]
    else:
        chunk.choices = []
    if x_groq_present:
        x_groq = MagicMock()
        x_groq.usage = usage
        chunk.x_groq = x_groq
    else:
        chunk.x_groq = None
    return chunk


def _groq_usage(prompt_tokens, completion_tokens, total_tokens):
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    usage.total_tokens = total_tokens
    return usage


@pytest.mark.asyncio
async def test_openai_stream_usage_reported(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    usage_obj = _openai_usage(10, 20, 30)
    chunks = [
        _openai_chunk(content="Hello"),
        _openai_chunk(content=" world"),
        _openai_chunk(usage=usage_obj),
    ]
    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_AsyncIterable(chunks))
        mock_cls.return_value = mock_client
        service = OpenAIService()
        service._client = None
        results = [item async for item in service.generate_stream("hello")]
    assert results[-1] == (
        "",
        {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        "gpt-4o-mini",
    )


@pytest.mark.asyncio
async def test_openai_stream_missing_usage_keeps_null(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    chunks = [
        _openai_chunk(content="Hello"),
        _openai_chunk(content=" world"),
        _openai_chunk(usage=None),
    ]
    with patch("app.services.openai_service.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_AsyncIterable(chunks))
        mock_cls.return_value = mock_client
        service = OpenAIService()
        service._client = None
        results = [item async for item in service.generate_stream("hello")]
    assert results[-1] == (
        "",
        {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "gpt-4o-mini",
    )


@pytest.mark.asyncio
async def test_groq_stream_usage_reported(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")
    usage_obj = _groq_usage(5, 7, 12)
    chunks = [
        _groq_chunk(content="Hi"),
        _groq_chunk(content=" there"),
        _groq_chunk(usage=usage_obj),
    ]
    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_AsyncIterable(chunks))
        mock_cls.return_value = mock_client
        service = GroqService()
        service._client = None
        results = [item async for item in service.generate_stream("hello")]
    assert results[-1] == (
        "",
        {"input_tokens": 5, "output_tokens": 7, "total_tokens": 12},
        "openai/gpt-oss-120b",
    )


@pytest.mark.asyncio
async def test_groq_stream_missing_usage_keeps_null(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")
    chunks = [
        _groq_chunk(content="Hi"),
        _groq_chunk(usage=None),
    ]
    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_AsyncIterable(chunks))
        mock_cls.return_value = mock_client
        service = GroqService()
        service._client = None
        results = [item async for item in service.generate_stream("hello")]
    assert results[-1] == (
        "",
        {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "openai/gpt-oss-120b",
    )


@pytest.mark.asyncio
async def test_groq_stream_missing_x_groq_keeps_null(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")
    chunks = [
        _groq_chunk(content="Hi", x_groq_present=False),
    ]
    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_AsyncIterable(chunks))
        mock_cls.return_value = mock_client
        service = GroqService()
        service._client = None
        results = [item async for item in service.generate_stream("hello")]
    assert results[-1] == (
        "",
        {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "openai/gpt-oss-120b",
    )


@pytest.mark.asyncio
async def test_groq_stream_does_not_pass_stream_options(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gs-test")
    chunk = _groq_chunk(content="Hi", usage=_groq_usage(5, 7, 12))

    with patch("app.services.groq_service.AsyncGroq") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_AsyncIterable([chunk]))
        mock_cls.return_value = mock_client
        service = GroqService()
        service._client = None
        [item async for item in service.generate_stream("hello")]

    assert mock_client.chat.completions.create.await_count == 1
    call_kwargs = mock_client.chat.completions.create.await_args.kwargs
    assert "stream_options" not in call_kwargs
    assert call_kwargs["stream"] is True


@pytest.mark.asyncio
async def test_anthropic_stream_usage_reported(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")
    usage_obj = MagicMock()
    usage_obj.input_tokens = 10
    usage_obj.output_tokens = 20
    usage_obj.total_tokens = None
    final_message = MagicMock()
    final_message.usage = usage_obj
    mock_stream = MagicMock()
    mock_stream.text_stream = _AsyncIterable(["Hello", " world"])
    mock_stream.get_final_message.return_value = final_message
    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.stream = MagicMock(return_value=_AsyncContextManager(mock_stream))
        mock_cls.return_value = mock_client
        service = AnthropicService()
        service._client = None
        results = [item async for item in service.generate_stream("hello")]
    assert results[-1] == (
        "",
        {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        "claude-sonnet-4-5",
    )


@pytest.mark.asyncio
async def test_anthropic_stream_missing_usage_keeps_null(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ac-test")
    final_message = MagicMock()
    final_message.usage = None
    mock_stream = MagicMock()
    mock_stream.text_stream = _AsyncIterable(["Hello"])
    mock_stream.get_final_message.return_value = final_message
    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.stream = MagicMock(return_value=_AsyncContextManager(mock_stream))
        mock_cls.return_value = mock_client
        service = AnthropicService()
        service._client = None
        results = [item async for item in service.generate_stream("hello")]
    assert results[-1] == (
        "",
        {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "claude-sonnet-4-5",
    )


def test_stream_done_event_carries_usage(monkeypatch):
    """The HTTP done event must report actual usage from the provider stream."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    from app.api.routes.llm import llm_service as ls

    async def _gen_with_usage(prompt=None, model="gpt-4o-mini", system_prompt=None):
        yield "Hello", None, model
        yield "", {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}, model

    with patch.object(ls.openai, "generate_stream", new=_gen_with_usage):
        response = _post_stream("openai")
        assert response.status_code == 200

    events = _sse_events(response)
    done = events[-1]
    assert done["type"] == "done"
    assert done["usage"] == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
