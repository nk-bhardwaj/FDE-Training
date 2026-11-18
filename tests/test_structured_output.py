import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "category": "billing",
    "sentiment": "negative",
    "summary": "Customer was overcharged.",
    "suggested_resolution": "Issue a refund.",
    "requires_human": False,
}
VALID_JSON = json.dumps(VALID_PAYLOAD)


def _openai_style_response(content: str) -> MagicMock:
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=32, total_tokens=42)
    return mock_response


def _anthropic_style_response(content: str) -> MagicMock:
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = content
    mock_response.content = [mock_content]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=20, total_tokens=None)
    return mock_response


def _reset_openai_client():
    from app.api.routes.llm import structured_output_service

    structured_output_service.llm_service.openai._client = None


def _reset_anthropic_client():
    from app.api.routes.llm import structured_output_service

    structured_output_service.llm_service.anthropic._client = None


def _reset_groq_client():
    from app.api.routes.llm import structured_output_service

    structured_output_service.llm_service.groq._client = None


def test_structured_openai_valid_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_openai_style_response(VALID_JSON)
        )
        mock_client_cls.return_value = mock_client
        _reset_openai_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "openai", "message": "I was overcharged"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["analysis"] == VALID_PAYLOAD
    assert data["model"] == "gpt-4o-mini"
    assert data["latency_ms"] >= 0
    assert data["usage"] == {"input_tokens": 10, "output_tokens": 32, "total_tokens": 42}
    assert data["attempts"] == 1


def test_structured_openai_retry_after_invalid_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _openai_style_response("not json"),
                _openai_style_response(VALID_JSON),
            ]
        )
        mock_client_cls.return_value = mock_client
        _reset_openai_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "openai", "message": "I was overcharged"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["analysis"] == VALID_PAYLOAD
    assert data["attempts"] == 2
    # Token usage and latency account for both attempts
    assert data["usage"] == {"input_tokens": 20, "output_tokens": 64, "total_tokens": 84}
    assert data["latency_ms"] >= 0
    assert mock_client.chat.completions.create.await_count == 2
    second_call = mock_client.chat.completions.create.await_args_list[1]
    user_messages = [
        m["content"] for m in second_call.kwargs["messages"] if m.get("role") == "user"
    ]
    assert any("Validation error" in content for content in user_messages)


def test_structured_openai_invalid_json_both_attempts(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _openai_style_response("not json"),
                _openai_style_response("still bad"),
            ]
        )
        mock_client_cls.return_value = mock_client
        _reset_openai_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "openai", "message": "I was overcharged"},
        )

    assert response.status_code == 400
    assert "Failed to produce valid structured output" in response.json()["detail"]


def test_structured_openai_validation_failure_both_attempts(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _openai_style_response("{}"),
                _openai_style_response("{}"),
            ]
        )
        mock_client_cls.return_value = mock_client
        _reset_openai_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "openai", "message": "I was overcharged"},
        )

    assert response.status_code == 400
    assert "Failed to produce valid structured output" in response.json()["detail"]


def test_structured_openai_missing_key_returns_503(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post(
        "/api/chat/structured",
        json={"provider": "openai", "message": "hello"},
    )
    assert response.status_code == 503


def test_structured_openai_auth_error_no_retry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from openai import AuthenticationError

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError(
                "invalid",
                response=MagicMock(status_code=401),
                body=None,
            )
        )
        mock_client_cls.return_value = mock_client
        _reset_openai_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "openai", "message": "hello"},
        )

    assert response.status_code == 502
    assert mock_client.chat.completions.create.await_count == 1


def test_structured_anthropic_valid_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_anthropic_style_response(VALID_JSON))
        mock_client_cls.return_value = mock_client
        _reset_anthropic_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "anthropic", "message": "I was overcharged"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "anthropic"
    assert data["analysis"] == VALID_PAYLOAD
    assert data["model"] == "claude-sonnet-4-5"
    assert data["attempts"] == 1


def test_structured_groq_valid_json(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    with patch("app.services.groq_service.AsyncGroq") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_openai_style_response(VALID_JSON)
        )
        mock_client_cls.return_value = mock_client
        _reset_groq_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "groq", "message": "I was overcharged"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq"
    assert data["analysis"] == VALID_PAYLOAD
    assert data["attempts"] == 1


def test_structured_unsupported_provider_rejected():
    response = client.post(
        "/api/chat/structured",
        json={"provider": "invalid", "message": "hello"},
    )
    assert response.status_code == 422


def test_structured_empty_message_rejected():
    response = client.post(
        "/api/chat/structured",
        json={"provider": "openai", "message": ""},
    )
    assert response.status_code == 422


async def test_service_accumulates_latency_and_usage_on_retry():
    from app.services.structured_output_service import StructuredOutputService

    class _FakeLLMService:
        def __init__(self, responses):
            self.responses = list(responses)
            self.calls = []

        async def generate_response(self, provider, prompt, system_prompt=None):
            self.calls.append(prompt)
            return self.responses.pop(0)

    fake = _FakeLLMService(
        [
            (
                "not json",
                "model-1",
                5.0,
                {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            ),
            (
                VALID_JSON,
                "model-2",
                7.0,
                {"input_tokens": 11, "output_tokens": 21, "total_tokens": 32},
            ),
        ]
    )
    service = StructuredOutputService(llm_service=fake)
    result = await service.analyze_support("openai", "hi")
    assert result.attempts == 2
    assert result.latency_ms == 12.0
    assert result.usage == {"input_tokens": 21, "output_tokens": 41, "total_tokens": 62}


def test_structured_invalid_sentiment_validation_triggers_retry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    bad_payload = json.dumps({**VALID_PAYLOAD, "sentiment": "angry"})
    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _openai_style_response(bad_payload),
                _openai_style_response(bad_payload),
            ]
        )
        mock_client_cls.return_value = mock_client
        _reset_openai_client()

        response = client.post(
            "/api/chat/structured",
            json={"provider": "openai", "message": "I was overcharged"},
        )

    assert response.status_code == 400
    assert mock_client.chat.completions.create.await_count == 2
    # Proves it was SupportAnalysis validation (not just JSON parse) that triggered retry:
    # the payload is valid JSON, so a JSON-only parser would not have retried.
    assert "Failed to produce valid structured output" in response.json()["detail"]


def test_existing_chat_endpoint_backward_compatible(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "mocked openai response"
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=32, total_tokens=42)

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from app.api.routes.llm import llm_service

        llm_service.openai._client = None

        response = client.post(
            "/api/chat",
            json={"provider": "openai", "prompt": "hello"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["response"] == "mocked openai response"
    assert data["model"] == "gpt-4o-mini"
    assert data["latency_ms"] >= 0
    assert data["usage"] == {"input_tokens": 10, "output_tokens": 32, "total_tokens": 42}
