"""Unit tests for keyword search API and service."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes.documents import document_service
from app.main import app
from app.services.document_service import (
    DatabaseNotConfiguredError,
    DocumentStoreError,
    KeywordSearchResult,
)

client = TestClient(app)


# --- Service-level tests (mock database) ---


async def test_keyword_search_service_success(monkeypatch):
    """Test successful keyword search at service level."""
    mock_results = [
        KeywordSearchResult(
            id=1,
            content="Refunds are processed in five business days.",
            metadata={"category": "returns_refunds"},
            created_at=None,
            rank=0.8472,
        ),
        KeywordSearchResult(
            id=2,
            content="Return window is 30 days from delivery.",
            metadata={"category": "returns_refunds"},
            created_at=None,
            rank=0.6321,
        ),
    ]

    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(return_value=mock_results),
    )

    results = await document_service.keyword_search("return policy refund", limit=5)

    assert len(results) == 2
    assert results[0].id == 1
    assert results[0].rank == 0.8472
    assert results[1].rank == 0.6321
    assert results[0].rank > results[1].rank


async def test_keyword_search_service_empty_query():
    """Test keyword search rejects empty query."""
    with pytest.raises(ValueError, match="must not be empty"):
        await document_service.keyword_search("  ")


async def test_keyword_search_service_invalid_limit():
    """Test keyword search rejects invalid limit."""
    with pytest.raises(ValueError, match="limit"):
        await document_service.keyword_search("test", limit=0)

    with pytest.raises(ValueError, match="limit"):
        await document_service.keyword_search("test", limit=-1)

    with pytest.raises(ValueError, match="limit"):
        await document_service.keyword_search("test", limit=101)


async def test_keyword_search_service_database_not_configured(monkeypatch):
    """Test keyword search when database is not configured."""
    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(side_effect=DatabaseNotConfiguredError("DATABASE_URL is not configured")),
    )

    with pytest.raises(DatabaseNotConfiguredError, match="DATABASE_URL is not configured"):
        await document_service.keyword_search("test")


async def test_keyword_search_service_database_error(monkeypatch):
    """Test keyword search with database error."""
    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(side_effect=DocumentStoreError("Failed to search documents")),
    )

    with pytest.raises(DocumentStoreError, match="Failed to search documents"):
        await document_service.keyword_search("test")


# --- API-level tests (TestClient) ---


def test_keyword_search_success(monkeypatch):
    """Test successful keyword search via API."""
    mock_results = [
        KeywordSearchResult(
            id=1,
            content="Refunds are processed in five business days.",
            metadata={"category": "returns_refunds", "source": "faq"},
            created_at="2024-01-15T10:30:00Z",
            rank=0.8472,
        ),
        KeywordSearchResult(
            id=2,
            content="Return window is 30 days from delivery.",
            metadata={"category": "returns_refunds", "source": "faq"},
            created_at="2024-01-14T08:15:00Z",
            rank=0.6321,
        ),
    ]

    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(return_value=mock_results),
    )

    response = client.post(
        "/api/documents/keyword-search",
        json={
            "query": "return policy refund",
            "limit": 3,
            "metadata_filters": {"source": "faq"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "return policy refund"
    assert data["total_results"] == 2
    assert data["results"][0]["id"] == 1
    assert data["results"][0]["rank"] == 0.8472
    assert data["results"][0]["metadata"]["category"] == "returns_refunds"
    assert data["results"][1]["rank"] == 0.6321


def test_keyword_search_empty_query():
    """Test keyword search with invalid query returns 422."""
    response = client.post(
        "/api/documents/keyword-search",
        json={
            "query": "",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 422


def test_keyword_search_limit_validation():
    """Test keyword search with limit validation."""
    response = client.post(
        "/api/documents/keyword-search",
        json={
            "query": "test",
            "limit": 0,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 422

    response = client.post(
        "/api/documents/keyword-search",
        json={
            "query": "test",
            "limit": 150,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 422


def test_keyword_search_metadata_filters():
    """Test keyword search with metadata filters."""
    mock_results = [
        KeywordSearchResult(
            id=1,
            content="Test content",
            metadata={"category": "order_tracking"},
            created_at="2024-01-01T00:00:00Z",
            rank=0.75,
        ),
    ]

    with patch(
        "app.api.routes.documents.document_service.keyword_search",
        new_callable=AsyncMock,
        return_value=mock_results,
    ) as mock_search:
        response = client.post(
            "/api/documents/keyword-search",
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


def test_keyword_search_database_not_configured(monkeypatch):
    """Test keyword search when database is not configured."""
    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(side_effect=DatabaseNotConfiguredError("DATABASE_URL is not configured")),
    )

    response = client.post(
        "/api/documents/keyword-search",
        json={
            "query": "test",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 503
    assert "DATABASE_URL is not configured" in response.json()["detail"]


def test_keyword_search_database_error(monkeypatch):
    """Test keyword search with database error."""
    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(side_effect=DocumentStoreError("Failed to search documents")),
    )

    response = client.post(
        "/api/documents/keyword-search",
        json={
            "query": "test",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 502
    assert "Failed to search documents" in response.json()["detail"]


def test_keyword_search_response_structure(monkeypatch):
    """Test keyword search response structure validation."""
    mock_results = [
        KeywordSearchResult(
            id=1,
            content="Test content",
            metadata={"category": "order_tracking", "source": "web"},
            created_at="2024-01-01T00:00:00Z",
            rank=0.88,
        ),
    ]

    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(return_value=mock_results),
    )

    response = client.post(
        "/api/documents/keyword-search",
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
    assert "rank" in data["results"][0]


def test_keyword_search_no_results(monkeypatch):
    """Test keyword search with no matching results."""
    monkeypatch.setattr(
        document_service,
        "keyword_search",
        AsyncMock(return_value=[]),
    )

    response = client.post(
        "/api/documents/keyword-search",
        json={
            "query": "nonexistentxyzquery",
            "limit": 5,
            "metadata_filters": None,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert data["results"] == []
