from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_missing_openai_key_returns_503(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post(
        "/api/chat",
        json={"provider": "openai", "prompt": "hello"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_generate_missing_anthropic_key_returns_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post(
        "/api/chat",
        json={"provider": "anthropic", "prompt": "hello"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_generate_openai_success_mocked(monkeypatch):
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

        # reset cached client
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


def test_generate_anthropic_success_mocked(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "mocked anthropic response"
    mock_response.content = [mock_content]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=20, total_tokens=None)

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from app.api.routes.llm import llm_service

        llm_service.anthropic._client = None

        response = client.post(
            "/api/chat",
            json={"provider": "anthropic", "prompt": "hello"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "anthropic"
    assert data["response"] == "mocked anthropic response"
    assert data["model"] == "claude-sonnet-4-5"
    assert data["latency_ms"] >= 0
    assert data["usage"] == {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}


def test_generate_openai_timeout_returns_504(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from openai import APITimeoutError

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )
        mock_client_cls.return_value = mock_client

        from app.api.routes.llm import llm_service

        llm_service.openai._client = None

        response = client.post(
            "/api/chat",
            json={"provider": "openai", "prompt": "hello"},
        )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


def test_generate_anthropic_timeout_returns_504(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    from anthropic import APITimeoutError

    with patch("app.services.anthropic_service.AsyncAnthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=APITimeoutError(request=MagicMock()))
        mock_client_cls.return_value = mock_client

        from app.api.routes.llm import llm_service

        llm_service.anthropic._client = None

        response = client.post(
            "/api/chat",
            json={"provider": "anthropic", "prompt": "hello"},
        )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


def test_generate_openai_rate_limit_returns_429(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from openai import RateLimitError

    with patch("app.services.openai_service.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                "rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
        )
        mock_client_cls.return_value = mock_client

        from app.api.routes.llm import llm_service

        llm_service.openai._client = None

        response = client.post(
            "/api/chat",
            json={"provider": "openai", "prompt": "hello"},
        )

    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_generate_openai_auth_failure_returns_502(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "bad-key")

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

        from app.api.routes.llm import llm_service

        llm_service.openai._client = None

        response = client.post(
            "/api/chat",
            json={"provider": "openai", "prompt": "hello"},
        )

    assert response.status_code == 502
    assert "authentication" in response.json()["detail"].lower()


def test_generate_groq_success_mocked(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "mocked groq response"
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=3, completion_tokens=4, total_tokens=7)

    with patch("app.services.groq_service.AsyncGroq") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from app.api.routes.llm import llm_service

        llm_service.groq._client = None

        response = client.post(
            "/api/chat",
            json={"provider": "groq", "prompt": "hello"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq"
    assert data["response"] == "mocked groq response"
    assert data["model"] == "openai/gpt-oss-120b"
    assert data["latency_ms"] >= 0
    assert data["usage"] == {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7}


def test_generate_groq_missing_key_returns_503(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = client.post(
        "/api/chat",
        json={"provider": "groq", "prompt": "hello"},
    )
    assert response.status_code == 503
