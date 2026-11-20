"""Unit tests for the semantic search API."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.api.routes.documents import document_service
from app.main import app
from app.services.document_service import (
    DatabaseNotConfiguredError,
    DocumentStoreError,
)
from app.services.llm_errors import LLMProviderError, LLMTimeoutError, MissingAPIKeyError

client = TestClient(app)


def test_semantic_search_success(monkeypatch):
    """Test successful semantic search with mocked service."""
    mock_results = [
        MagicMock(
            id=1,
            content="Refunds are processed in five business days.",
            metadata={"category": "returns_refunds"},
            created_at="2024-01-01T00:00:00",
            similarity=0.88,
        ),
        MagicMock(
            id=2,
            content="Shipping takes two days.",
            metadata={"category": "order_tracking"},
            created_at="2024-01-01T00:00:00",
            similarity=0.69,
        ),
    ]

    monkeypatch.setattr(
        document_service,
        "semantic_search",
        AsyncMock(return_value=mock_results),
    )

    response = client.post(
        "/api/documents/search",
        json={
            "query": "how long do refunds take?",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "how long do refunds take?"
    assert data["total_results"] == 2
    assert data["results"][0]["id"] == 1
    assert data["results"][0]["metadata"]["category"] == "returns_refunds"
    assert data["results"][0]["similarity"] == 0.88


def test_semantic_search_empty_query():
    """Test semantic search with invalid query returns 422."""
    response = client.post(
        "/api/documents/search",
        json={
            "query": "",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 422


def test_semantic_search_limit_validation():
    """Test semantic search with limit validation."""
    response = client.post(
        "/api/documents/search",
        json={
            "query": "test",
            "limit": 0,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 422

    response = client.post(
        "/api/documents/search",
        json={
            "query": "test",
            "limit": 150,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 422


def test_semantic_search_metadata_filters():
    """Test semantic search with metadata filters."""
    mock_results = [
        MagicMock(
            id=1,
            content="Test content",
            metadata={"category": "order_tracking"},
            created_at="2024-01-01T00:00:00",
            similarity=0.75,
        ),
    ]

    with patch(
        "app.api.routes.documents.document_service.semantic_search",
        new_callable=AsyncMock,
        return_value=mock_results,
    ) as mock_search:
        response = client.post(
            "/api/documents/search",
            json={
                "query": "order tracking",
                "limit": 5,
                "metadata_filters": {"source": "faq", "lang": "en"},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "order tracking"
    assert len(data["results"]) == 1
    mock_search.assert_awaited_once()


def test_semantic_search_database_not_configured(monkeypatch):
    """Test semantic search when database is not configured."""
    monkeypatch.setattr(
        document_service,
        "semantic_search",
        AsyncMock(side_effect=DatabaseNotConfiguredError("DATABASE_URL is not configured")),
    )

    response = client.post(
        "/api/documents/search",
        json={
            "query": "test",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 503
    assert "DATABASE_URL is not configured" in response.json()["detail"]


def test_semantic_search_database_error(monkeypatch):
    """Test semantic search with database error."""
    monkeypatch.setattr(
        document_service,
        "semantic_search",
        AsyncMock(side_effect=DocumentStoreError("Failed to search documents")),
    )

    response = client.post(
        "/api/documents/search",
        json={
            "query": "test",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 502
    assert "Failed to search documents" in response.json()["detail"]


def test_semantic_search_missing_api_key(monkeypatch):
    """Test semantic search when Gemini API key is missing."""
    monkeypatch.setattr(
        document_service,
        "semantic_search",
        AsyncMock(side_effect=MissingAPIKeyError("Gemini API key is not configured")),
    )

    response = client.post(
        "/api/documents/search",
        json={
            "query": "test",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 503
    assert "Gemini API key is not configured" in response.json()["detail"]


def test_semantic_search_timeout_error(monkeypatch):
    """Test semantic search with timeout error."""
    monkeypatch.setattr(
        document_service,
        "semantic_search",
        AsyncMock(side_effect=LLMTimeoutError("Gemini embedding request timed out")),
    )

    response = client.post(
        "/api/documents/search",
        json={
            "query": "test",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


def test_semantic_search_provider_error(monkeypatch):
    """Test semantic search with provider error."""
    monkeypatch.setattr(
        document_service,
        "semantic_search",
        AsyncMock(side_effect=LLMProviderError("Gemini embedding request failed", status_code=502)),
    )

    response = client.post(
        "/api/documents/search",
        json={
            "query": "test",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 502
    assert "Gemini embedding request failed" in response.json()["detail"]


def test_semantic_search_response_structure(monkeypatch):
    """Test semantic search response structure validation."""
    mock_results = [
        MagicMock(
            id=1,
            content="Test content",
            metadata={"category": "order_tracking", "source": "web"},
            created_at="2024-01-01T00:00:00",
            similarity=0.88,
        ),
    ]

    monkeypatch.setattr(
        document_service,
        "semantic_search",
        AsyncMock(return_value=mock_results),
    )

    response = client.post(
        "/api/documents/search",
        json={
            "query": "test query",
            "limit": 10,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data
    assert "total_results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 1
    assert "id" in data["results"][0]
    assert "content" in data["results"][0]
    assert "metadata" in data["results"][0]
    assert "similarity" in data["results"][0]
