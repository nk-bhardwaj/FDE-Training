from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_tools_openai_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from app.api.routes.llm import llm_service

    monkeypatch.setattr(
        llm_service.openai,
        "generate_with_tools",
        AsyncMock(
            return_value=(
                "Order ORD1001 has been shipped.",
                "gpt-4o-mini",
                12.34,
                {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            )
        ),
    )

    response = client.post(
        "/api/chat/tools",
        json={"provider": "openai", "prompt": "Status of ORD1001?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"
    assert data["response"] == "Order ORD1001 has been shipped."
    assert data["model"] == "gpt-4o-mini"
    assert data["latency_ms"] == 12.34
    assert data["usage"] == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}


def test_chat_tools_groq_success(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from app.api.routes.llm import llm_service

    monkeypatch.setattr(
        llm_service.groq,
        "generate_with_tools",
        AsyncMock(
            return_value=(
                "Order ORD1001 has been shipped.",
                "openai/gpt-oss-120b",
                45.67,
                {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            )
        ),
    )

    response = client.post(
        "/api/chat/tools",
        json={"provider": "groq", "prompt": "Status of ORD1001?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq"
    assert data["response"] == "Order ORD1001 has been shipped."
    assert data["model"] == "openai/gpt-oss-120b"
    assert data["latency_ms"] == 45.67
    assert data["usage"] == {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7}


def test_chat_tools_anthropic_success(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.api.routes.llm import llm_service

    monkeypatch.setattr(
        llm_service.anthropic,
        "generate_with_tools",
        AsyncMock(
            return_value=(
                "Order ORD1001 has been shipped.",
                "claude-sonnet-4-5",
                23.45,
                {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            )
        ),
    )

    response = client.post(
        "/api/chat/tools",
        json={"provider": "anthropic", "prompt": "Status of ORD1001?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "anthropic"
    assert data["response"] == "Order ORD1001 has been shipped."
    assert data["model"] == "claude-sonnet-4-5"
    assert data["latency_ms"] == 23.45
    assert data["usage"] == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}


def test_chat_tools_invalid_provider_returns_422(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    response = client.post(
        "/api/chat/tools",
        json={"provider": "invalid-provider", "prompt": "hello"},
    )
    assert response.status_code == 422


def test_chat_tools_missing_key_returns_503(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.api.routes.llm import llm_service

    llm_service.openai._client = None

    response = client.post(
        "/api/chat/tools",
        json={"provider": "openai", "prompt": "hello"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_chat_tools_provider_error_returns_502(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from app.api.routes.llm import llm_service
    from app.services.llm_errors import LLMProviderError

    monkeypatch.setattr(
        llm_service.openai,
        "generate_with_tools",
        AsyncMock(side_effect=LLMProviderError("OpenAI request failed", status_code=502)),
    )

    response = client.post(
        "/api/chat/tools",
        json={"provider": "openai", "prompt": "hello"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "OpenAI request failed"


def test_chat_tools_timeout_returns_504(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from app.api.routes.llm import llm_service
    from app.services.llm_errors import LLMTimeoutError

    monkeypatch.setattr(
        llm_service.openai,
        "generate_with_tools",
        AsyncMock(side_effect=LLMTimeoutError("OpenAI request timed out")),
    )

    response = client.post(
        "/api/chat/tools",
        json={"provider": "openai", "prompt": "hello"},
    )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()
