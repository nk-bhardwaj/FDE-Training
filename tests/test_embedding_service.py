import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors

from app.services.embedding_service import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EmbeddingService,
)
from app.services.llm_errors import (
    LLMProviderError,
    LLMTimeoutError,
    MissingAPIKeyError,
)

SAMPLE_EMBEDDING = [0.001 * index for index in range(EMBEDDING_DIMENSIONS)]


def _fake_response(values: list[float] | None) -> MagicMock:
    response = MagicMock()
    response.embeddings = [MagicMock(values=values)] if values is not None else []
    return response


@pytest.fixture
def service(monkeypatch) -> EmbeddingService:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    return EmbeddingService()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.aio.models.embed_content = AsyncMock()
    with patch("app.services.embedding_service.genai.Client", return_value=client):
        yield client


def _request_config(mock_client) -> object:
    return mock_client.aio.models.embed_content.await_args.kwargs["config"]


async def test_embed_document_returns_list_of_floats(service, mock_client):
    mock_client.aio.models.embed_content.return_value = _fake_response(SAMPLE_EMBEDDING)

    embedding = await service.embed_document("Orders ship within 48 hours.")

    assert isinstance(embedding, list)
    assert len(embedding) == EMBEDDING_DIMENSIONS
    assert all(isinstance(value, float) for value in embedding)


async def test_embed_document_uses_document_task_type_and_model(service, mock_client):
    mock_client.aio.models.embed_content.return_value = _fake_response(SAMPLE_EMBEDDING)

    await service.embed_document("Refunds take five business days.")

    call = mock_client.aio.models.embed_content.await_args
    assert call.kwargs["model"] == EMBEDDING_MODEL
    assert call.kwargs["contents"] == "Refunds take five business days."
    assert _request_config(mock_client).task_type == "RETRIEVAL_DOCUMENT"
    assert _request_config(mock_client).output_dimensionality == EMBEDDING_DIMENSIONS


async def test_embed_query_uses_query_task_type(service, mock_client):
    mock_client.aio.models.embed_content.return_value = _fake_response(SAMPLE_EMBEDDING)

    await service.embed_query("how long do refunds take?")

    call = mock_client.aio.models.embed_content.await_args
    assert call.kwargs["contents"] == "how long do refunds take?"
    assert _request_config(mock_client).task_type == "RETRIEVAL_QUERY"
    assert _request_config(mock_client).output_dimensionality == EMBEDDING_DIMENSIONS


def test_model_and_dimensions_constants():
    assert EMBEDDING_MODEL == "gemini-embedding-001"
    assert EMBEDDING_DIMENSIONS == 768


async def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    service = EmbeddingService()

    with patch("app.services.embedding_service.genai.Client") as mock_client_cls:
        with pytest.raises(MissingAPIKeyError):
            await service.embed_document("some content")
        mock_client_cls.assert_not_called()


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
async def test_empty_text_rejected_without_api_call(service, mock_client, text):
    with pytest.raises(ValueError, match="must not be empty"):
        await service.embed_document(text)

    mock_client.aio.models.embed_content.assert_not_awaited()


async def test_unexpected_dimensions_raise_provider_error(service, mock_client):
    mock_client.aio.models.embed_content.return_value = _fake_response([0.1] * 3072)

    with pytest.raises(LLMProviderError, match="expected 768"):
        await service.embed_document("content")


async def test_empty_embeddings_raise_provider_error(service, mock_client):
    mock_client.aio.models.embed_content.return_value = _fake_response(None)

    with pytest.raises(LLMProviderError, match="no embeddings"):
        await service.embed_document("content")


async def test_rate_limit_maps_to_429(service, mock_client):
    mock_client.aio.models.embed_content.side_effect = errors.ClientError(
        429, {"error": {"code": 429, "message": "quota exceeded"}}
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await service.embed_query("query")

    assert exc_info.value.status_code == 429


async def test_client_error_maps_to_502(service, mock_client):
    mock_client.aio.models.embed_content.side_effect = errors.ClientError(
        400, {"error": {"code": 400, "message": "bad request"}}
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await service.embed_query("query")

    assert exc_info.value.status_code == 502


async def test_server_error_maps_to_502(service, mock_client):
    mock_client.aio.models.embed_content.side_effect = errors.ServerError(
        503, {"error": {"code": 503, "message": "unavailable"}}
    )

    with pytest.raises(LLMProviderError, match="unavailable") as exc_info:
        await service.embed_document("content")

    assert exc_info.value.status_code == 502


async def test_timeout_maps_to_timeout_error(service, mock_client):
    mock_client.aio.models.embed_content.side_effect = TimeoutError()

    with pytest.raises(LLMTimeoutError):
        await service.embed_document("content")


async def test_unexpected_error_maps_to_provider_error(service, mock_client):
    mock_client.aio.models.embed_content.side_effect = RuntimeError("boom")

    with pytest.raises(LLMProviderError) as exc_info:
        await service.embed_document("content")

    assert exc_info.value.status_code == 502


async def test_client_is_created_once_and_reused(service, mock_client):
    mock_client.aio.models.embed_content.return_value = _fake_response(SAMPLE_EMBEDDING)

    await service.embed_document("first")
    await service.embed_query("second")

    assert service._client is mock_client
    with patch("app.services.embedding_service.genai.Client") as mock_client_cls:
        await service.embed_document("third")
        mock_client_cls.assert_not_called()


async def test_api_key_is_never_logged(service, mock_client, caplog):
    mock_client.aio.models.embed_content.return_value = _fake_response(SAMPLE_EMBEDDING)

    with caplog.at_level(logging.DEBUG):
        await service.embed_document("content")

    assert "test-key" not in caplog.text
    assert "provider=gemini" in caplog.text
    assert "status=success" in caplog.text
