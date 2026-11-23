"""Tests for the RAG answer API endpoint."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.routes.rag import rag_pipeline_service
from app.main import app
from app.schemas.llm import TokenUsage
from app.schemas.rag_answer import Citation, RAGAnswerResponse
from app.services.llm_errors import LLMProviderError, LLMTimeoutError, MissingAPIKeyError
from app.services.rag_pipeline_service import (
    RAGPipelineConfig,
    RAGPipelineError,
    RAGPipelineResponse,
)

client = TestClient(app)

ENDPOINT = "/api/rag/answer"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_answer_response(
    *,
    abstained: bool = False,
    provider: str = "openai",
) -> RAGAnswerResponse:
    """Build a RAGAnswerResponse for route tests."""
    citations: list[Citation] = []
    if not abstained:
        citations = [
            Citation(
                source_id="doc1",
                document_title="Return Policy",
                chunk_index=0,
                chunk_id=1,
                document_id=1,
            )
        ]
    return RAGAnswerResponse(
        question="What is the return policy?",
        answer=(
            "I don't know based on the available information."
            if abstained
            else "Returns are processed within 30 days of delivery."
        ),
        citations=citations,
        abstained=abstained,
        provider=provider,
        model="gpt-4o-mini",
        latency_ms=123.0,
        usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        attempts=1,
        context_chunks=1,
        context_tokens=100,
    )


def _make_pipeline_response(
    *,
    abstained: bool = False,
    provider: str = "openai",
    top_k: int = 5,
) -> RAGPipelineResponse:
    """Build a RAGPipelineResponse with a real RAGAnswerResponse inside."""
    return RAGPipelineResponse(
        answer=_make_answer_response(abstained=abstained, provider=provider),
        assembled_context=MagicMock(),
        reranked_chunks=(),
        raw_retrieval_chunks=(),
        config_used=RAGPipelineConfig(retrieval_top_k=top_k),
    )


def _mock_run(return_value=None, side_effect=None):
    """Set the pipeline service run method to an AsyncMock."""
    mock = AsyncMock(return_value=return_value, side_effect=side_effect)
    rag_pipeline_service.run = mock
    return mock


# ----------------------------------------------------------------------
# Success tests
# ----------------------------------------------------------------------


def test_answer_success():
    """Successful answer response with answer text."""
    mock = _mock_run(return_value=_make_pipeline_response())

    response = client.post(
        ENDPOINT,
        json={
            "question": "What is the return policy?",
            "provider": "openai",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Returns are processed within 30 days of delivery."
    assert data["abstained"] is False
    assert data["provider"] == "openai"
    assert data["latency_ms"] == 123.0
    assert data["usage"] == {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
    assert data["retrieval_top_k"] == 5
    assert data["rerank_enabled"] is True
    assert data["context_max_tokens"] == 2000
    mock.assert_awaited_once()


def test_answer_success_with_citations():
    """Successful response includes hydrated citations."""
    _mock_run(return_value=_make_pipeline_response())

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) == 1
    citation = data["citations"][0]
    assert citation["source_id"] == "doc1"
    assert citation["document_title"] == "Return Policy"
    assert citation["chunk_index"] == 0
    assert citation["chunk_id"] == 1
    assert citation["document_id"] == 1


def test_answer_abstention():
    """Abstention response carries abstained=True and no citations."""
    _mock_run(return_value=_make_pipeline_response(abstained=True))

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["abstained"] is True
    assert data["citations"] == []
    assert data["answer"] == "I don't know based on the available information."


# ----------------------------------------------------------------------
# Validation tests
# ----------------------------------------------------------------------


def test_empty_question_returns_422():
    """Empty question fails Pydantic validation with 422."""
    response = client.post(
        ENDPOINT,
        json={"question": "", "provider": "openai"},
    )
    assert response.status_code == 422


def test_whitespace_only_question_returns_400():
    """Whitespace-only question reaches the pipeline and fails with 400."""
    _mock_run(side_effect=ValueError("question must not be empty"))

    response = client.post(
        ENDPOINT,
        json={"question": "   ", "provider": "openai"},
    )

    assert response.status_code == 400


def test_invalid_top_k_returns_422():
    """Out-of-range top_k fails Pydantic validation with 422."""
    response = client.post(
        ENDPOINT,
        json={"question": "q", "provider": "openai", "top_k": 0},
    )
    assert response.status_code == 422

    response = client.post(
        ENDPOINT,
        json={"question": "q", "provider": "openai", "top_k": 21},
    )
    assert response.status_code == 422


# ----------------------------------------------------------------------
# Error tests
# ----------------------------------------------------------------------


def test_rag_pipeline_error_returns_status_with_step():
    """RAGPipelineError maps to its status_code and preserves step."""
    _mock_run(
        side_effect=RAGPipelineError(
            "Retrieval failed: connection failed",
            status_code=502,
            step="retrieval",
        )
    )

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 502
    assert "Retrieval failed" in response.json()["detail"]
    assert "step=retrieval" in response.json()["detail"]


def test_missing_api_key_returns_503():
    """MissingAPIKeyError maps to 503."""
    _mock_run(side_effect=MissingAPIKeyError("OpenAI API key is not configured"))

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_llm_timeout_returns_504():
    """LLMTimeoutError maps to 504."""
    _mock_run(side_effect=LLMTimeoutError("OpenAI request timed out"))

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


def test_llm_provider_error_returns_its_status_code():
    """LLMProviderError maps to its status_code."""
    _mock_run(side_effect=LLMProviderError("Rate limited", status_code=502))

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 502
    assert "Rate limited" in response.json()["detail"]


def test_unexpected_exception_returns_502():
    """Unexpected exception maps to 502."""
    _mock_run(side_effect=RuntimeError("something broke"))

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 502


# ----------------------------------------------------------------------
# Argument forwarding tests
# ----------------------------------------------------------------------


def test_passes_question_provider_filters_and_config():
    """Route forwards question, provider, metadata_filters, and config."""
    mock = _mock_run(return_value=_make_pipeline_response(top_k=7))

    response = client.post(
        ENDPOINT,
        json={
            "question": "What is the return policy?",
            "provider": "anthropic",
            "top_k": 7,
            "metadata_filters": {"source_id": "returns"},
        },
    )

    assert response.status_code == 200
    mock.assert_awaited_once()
    call_kwargs = mock.call_args.kwargs
    assert call_kwargs["question"] == "What is the return policy?"
    assert call_kwargs["provider"] == "anthropic"
    assert call_kwargs["metadata_filters"] == {"source_id": "returns"}
    config = call_kwargs["config"]
    assert isinstance(config, RAGPipelineConfig)
    assert config.retrieval_top_k == 7


def test_default_config_when_top_k_omitted():
    """Omitted top_k defaults to 5 in the pipeline config."""
    mock = _mock_run(return_value=_make_pipeline_response())

    response = client.post(
        ENDPOINT,
        json={"question": "What is the return policy?", "provider": "openai"},
    )

    assert response.status_code == 200
    config = mock.call_args.kwargs["config"]
    assert isinstance(config, RAGPipelineConfig)
    assert config.retrieval_top_k == 5
