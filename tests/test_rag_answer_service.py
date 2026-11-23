"""Unit tests for the RAG answer generation service.

All LLM calls are mocked; no provider or database calls are made.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.context_engineering_service import AssembledContext, ContextChunk
from app.services.llm_errors import LLMProviderError, LLMTimeoutError, MissingAPIKeyError
from app.services.llm_service import LLMService
from app.services.rag_answer_service import (
    ABSTENTION_MESSAGE,
    RAGAnswerError,
    RAGAnswerService,
)

PROVIDER = "openai"


def _chunk(
    *,
    chunk_id: int = 1,
    document_id: int = 10,
    source_id: str = "doc1",
    document_title: str = "Doc 1",
    chunk_index: int = 0,
    content: str = "chunk content",
    retrieval_rank: int = 1,
    token_count: int = 2,
) -> ContextChunk:
    return ContextChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        content=content,
        source_id=source_id,
        document_title=document_title,
        chunk_index=chunk_index,
        retrieval_rank=retrieval_rank,
        token_count=token_count,
    )


def _context(*chunks: ContextChunk) -> AssembledContext:
    return AssembledContext(
        chunks=chunks,
        total_tokens=sum(chunk.token_count for chunk in chunks),
        max_tokens=2000,
        truncated=False,
        duplicates_removed=0,
        sources=tuple(dict.fromkeys(chunk.source_id for chunk in chunks)),
    )


def _payload(
    answer: str = "Refunds are processed within five business days.",
    citations: list[str] | None = None,
    abstained: bool = False,
) -> str:
    return json.dumps(
        {
            "answer": answer,
            "citations": citations if citations is not None else ["C1"],
            "abstained": abstained,
        }
    )


def _generation(
    text: str,
    *,
    model: str = "gpt-4o-mini",
    latency_ms: float = 10.0,
    usage: dict[str, int | None] | None = None,
) -> tuple[str, str, float, dict[str, int | None] | None]:
    if usage is None:
        usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    return (text, model, latency_ms, usage)


@pytest.fixture
def llm_service() -> MagicMock:
    return MagicMock(spec=LLMService)


@pytest.fixture
def service(llm_service: MagicMock) -> RAGAnswerService:
    return RAGAnswerService(llm_service=llm_service)


# ---------------------------------------------------------------------------
# Grounded answers and citations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grounded_answer_with_valid_citation(service, llm_service):
    """A cited answer is returned with hydrated, authoritative metadata."""
    chunk = _chunk(
        chunk_id=7,
        document_id=3,
        source_id="amazon_fba_return_policy",
        document_title="FBA Return Policy",
        chunk_index=4,
        content="Refunds are processed within five business days.",
    )
    context = _context(chunk)
    llm_service.generate_response = AsyncMock(
        return_value=_generation(_payload("Refunds take five business days.", ["C1"]))
    )

    response = await service.answer(PROVIDER, "How long do refunds take?", context)

    assert response.abstained is False
    assert response.answer == "Refunds take five business days."
    assert len(response.citations) == 1
    citation = response.citations[0]
    assert citation.source_id == "amazon_fba_return_policy"
    assert citation.document_title == "FBA Return Policy"
    assert citation.chunk_index == 4
    assert citation.chunk_id == 7
    assert citation.document_id == 3
    assert response.provider == PROVIDER
    assert response.model == "gpt-4o-mini"
    assert response.usage is not None
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 20
    assert response.usage.total_tokens == 30
    assert response.latency_ms == pytest.approx(10.0)
    assert response.attempts == 1
    assert response.context_chunks == 1
    assert response.context_tokens == chunk.token_count


@pytest.mark.asyncio
async def test_prompt_contains_question_context_and_system_prompt(service, llm_service):
    """Generation uses the built prompt and the RAG system prompt."""
    chunk = _chunk(source_id="doc_a", document_title="Doc A", chunk_index=2)
    llm_service.generate_response = AsyncMock(return_value=_generation(_payload()))

    await service.answer(PROVIDER, "What is the policy?", _context(chunk))

    call = llm_service.generate_response.await_args
    assert call.kwargs["provider"] == PROVIDER
    assert "Question: What is the policy?" in call.kwargs["prompt"]
    assert "source_id=doc_a" in call.kwargs["prompt"]
    assert "document_title=Doc A" in call.kwargs["prompt"]
    assert "chunk_index=2" in call.kwargs["prompt"]
    assert call.kwargs["system_prompt"] == service.system_prompt
    assert "untrusted" in call.kwargs["system_prompt"].lower()


@pytest.mark.asyncio
async def test_citations_preserve_first_occurrence_order(service, llm_service):
    """Valid citations keep the order the model listed them in."""
    context = _context(
        _chunk(chunk_id=1, source_id="doc_a", document_title="Doc A", chunk_index=0),
        _chunk(chunk_id=2, source_id="doc_b", document_title="Doc B", chunk_index=0),
    )
    llm_service.generate_response = AsyncMock(
        return_value=_generation(_payload(citations=["C2", "C1"]))
    )

    response = await service.answer(PROVIDER, "question", context)

    assert [citation.source_id for citation in response.citations] == ["doc_b", "doc_a"]


@pytest.mark.asyncio
async def test_citation_labels_are_whitespace_tolerant(service, llm_service):
    """Surrounding whitespace around a label does not make it invalid."""
    llm_service.generate_response = AsyncMock(
        return_value=_generation(_payload(citations=[" C1 "]))
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is False
    assert len(response.citations) == 1
    assert response.citations[0].source_id == "doc1"


@pytest.mark.asyncio
async def test_unknown_citation_label_triggers_retry(service, llm_service):
    """An unknown label is rejected and the model is retried once."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(_payload(citations=["C9"])),
            _generation(_payload(citations=["C1"])),
        ]
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is False
    assert response.attempts == 2
    assert llm_service.generate_response.await_count == 2
    retry_prompt = llm_service.generate_response.await_args_list[1].kwargs["prompt"]
    assert "Validation error" in retry_prompt
    assert "Unknown citation label" in retry_prompt


@pytest.mark.asyncio
async def test_unknown_citation_label_twice_raises(service, llm_service):
    """Unknown labels on every attempt surface as RAGAnswerError."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(_payload(citations=["C9"])),
            _generation(_payload(citations=["C9"])),
        ]
    )

    with pytest.raises(RAGAnswerError) as exc_info:
        await service.answer(PROVIDER, "question", _context(_chunk()))

    assert exc_info.value.status_code == 502
    assert llm_service.generate_response.await_count == 2


@pytest.mark.asyncio
async def test_source_id_used_as_label_is_rejected(service, llm_service):
    """A source identifier is not a valid citation label."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(_payload(citations=["doc1"])),
            _generation(_payload(citations=["doc1"])),
        ]
    )

    with pytest.raises(RAGAnswerError):
        await service.answer(PROVIDER, "question", _context(_chunk(source_id="doc1")))

    retry_prompt = llm_service.generate_response.await_args_list[1].kwargs["prompt"]
    assert "Unknown citation label" in retry_prompt


@pytest.mark.asyncio
async def test_duplicate_citation_label_triggers_retry(service, llm_service):
    """A repeated label is rejected and the model is retried."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(_payload(citations=["C1", "C1"])),
            _generation(_payload(citations=["C1"])),
        ]
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is False
    assert response.attempts == 2
    assert len(response.citations) == 1
    retry_prompt = llm_service.generate_response.await_args_list[1].kwargs["prompt"]
    assert "Duplicate citation label" in retry_prompt


@pytest.mark.asyncio
async def test_duplicate_citation_label_twice_raises(service, llm_service):
    """Repeated duplicate labels surface as RAGAnswerError."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(_payload(citations=["C1", "C1"])),
            _generation(_payload(citations=["C1", "C1"])),
        ]
    )

    with pytest.raises(RAGAnswerError):
        await service.answer(PROVIDER, "question", _context(_chunk()))


# ---------------------------------------------------------------------------
# Abstention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_context_abstains_without_calling_llm(service, llm_service):
    """No context means immediate abstention with no generation attempt."""
    llm_service.generate_response = AsyncMock()

    response = await service.answer(PROVIDER, "question", _context())

    assert response.abstained is True
    assert response.answer == ABSTENTION_MESSAGE
    assert response.citations == []
    assert response.usage is None
    assert response.latency_ms == 0.0
    assert response.attempts == 0
    assert response.model == ""
    assert response.context_chunks == 0
    assert response.context_tokens == 0
    llm_service.generate_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_model_abstention_returns_canonical_message_and_no_citations(service, llm_service):
    """When the model abstains, its answer and citations are replaced."""
    llm_service.generate_response = AsyncMock(
        return_value=_generation(
            _payload(
                answer="Some confident but unsupported answer.", citations=["C1"], abstained=True
            )
        )
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is True
    assert response.answer == ABSTENTION_MESSAGE
    assert response.citations == []
    assert response.attempts == 1
    assert llm_service.generate_response.await_count == 1


@pytest.mark.asyncio
async def test_model_abstention_keeps_generation_metadata(service, llm_service):
    """Abstention still reports the model, latency, and aggregated usage."""
    llm_service.generate_response = AsyncMock(
        return_value=_generation(
            _payload(answer="", citations=[], abstained=True),
            model="claude-3-5-haiku",
            latency_ms=42.0,
            usage={"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
        )
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is True
    assert response.model == "claude-3-5-haiku"
    assert response.latency_ms == pytest.approx(42.0)
    assert response.usage is not None
    assert response.usage.total_tokens == 10


@pytest.mark.asyncio
async def test_missing_citations_triggers_retry_then_succeeds(service, llm_service):
    """A non-abstained answer with no citations is retried."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(_payload(citations=[])),
            _generation(_payload(citations=["C1"])),
        ]
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is False
    assert response.attempts == 2
    retry_prompt = llm_service.generate_response.await_args_list[1].kwargs["prompt"]
    assert "cite at least one context label" in retry_prompt


@pytest.mark.asyncio
async def test_missing_citations_after_retry_abstains(service, llm_service):
    """An uncited answer after the retry abstains instead of raising."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(_payload(citations=[])),
            _generation(_payload(citations=[])),
        ]
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is True
    assert response.answer == ABSTENTION_MESSAGE
    assert response.citations == []
    assert response.attempts == 2
    assert response.usage is not None
    assert response.usage.total_tokens == 60
    assert response.latency_ms == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_missing_citations_with_no_retries_abstains(llm_service):
    """With retries disabled, one uncited answer abstains immediately."""
    service = RAGAnswerService(llm_service=llm_service, max_retries=0)
    llm_service.generate_response = AsyncMock(return_value=_generation(_payload(citations=[])))

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is True
    assert response.attempts == 1
    assert llm_service.generate_response.await_count == 1


# ---------------------------------------------------------------------------
# Malformed output and retries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_malformed_json_triggers_retry_then_succeeds(service, llm_service):
    """Malformed JSON is retried with the validation error appended."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation("not json"),
            _generation(_payload(citations=["C1"])),
        ]
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is False
    assert response.attempts == 2
    retry_prompt = llm_service.generate_response.await_args_list[1].kwargs["prompt"]
    assert "Validation error" in retry_prompt


@pytest.mark.asyncio
async def test_malformed_json_twice_raises(service, llm_service):
    """Malformed JSON on every attempt raises RAGAnswerError."""
    llm_service.generate_response = AsyncMock(
        side_effect=[_generation("not json"), _generation("{still broken")]
    )

    with pytest.raises(RAGAnswerError) as exc_info:
        await service.answer(PROVIDER, "question", _context(_chunk()))

    assert exc_info.value.status_code == 502
    assert llm_service.generate_response.await_count == 2


@pytest.mark.asyncio
async def test_missing_required_field_raises_after_retries(service, llm_service):
    """A payload missing the answer field is invalid and retried."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(json.dumps({"citations": ["C1"], "abstained": False})),
            _generation(json.dumps({"citations": ["C1"], "abstained": False})),
        ]
    )

    with pytest.raises(RAGAnswerError):
        await service.answer(PROVIDER, "question", _context(_chunk()))


@pytest.mark.asyncio
async def test_fenced_json_is_tolerated(service, llm_service):
    """A markdown code fence around otherwise valid JSON is accepted."""
    fenced = f"```json\n{_payload(citations=['C1'])}\n```"
    llm_service.generate_response = AsyncMock(return_value=_generation(fenced))

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.abstained is False
    assert response.attempts == 1
    assert len(response.citations) == 1


# ---------------------------------------------------------------------------
# Metadata aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usage_and_latency_are_aggregated_across_attempts(service, llm_service):
    """Token usage and latency sum over every attempt."""
    llm_service.generate_response = AsyncMock(
        side_effect=[
            _generation(
                "not json",
                latency_ms=10.0,
                usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            ),
            _generation(
                _payload(citations=["C1"]),
                latency_ms=15.0,
                usage={"input_tokens": 4, "output_tokens": 6, "total_tokens": 10},
            ),
        ]
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.attempts == 2
    assert response.latency_ms == pytest.approx(25.0)
    assert response.usage is not None
    assert response.usage.input_tokens == 14
    assert response.usage.output_tokens == 26
    assert response.usage.total_tokens == 40


@pytest.mark.asyncio
async def test_missing_usage_is_reported_as_none(service, llm_service):
    """When the provider returns no token counts, usage stays ``None``."""
    llm_service.generate_response = AsyncMock(
        return_value=_generation(_payload(citations=["C1"]), usage={})
    )

    response = await service.answer(PROVIDER, "question", _context(_chunk()))

    assert response.usage is None


@pytest.mark.asyncio
async def test_context_metadata_is_reported(service, llm_service):
    """Response metadata reflects the assembled context that was used."""
    chunks = [
        _chunk(chunk_id=1, chunk_index=0, token_count=3),
        _chunk(chunk_id=2, chunk_index=1, token_count=5),
    ]
    context = _context(*chunks)
    llm_service.generate_response = AsyncMock(return_value=_generation(_payload(citations=["C1"])))

    response = await service.answer(PROVIDER, "question", context)

    assert response.context_chunks == 2
    assert response.context_tokens == 8


# ---------------------------------------------------------------------------
# Provider errors and input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        MissingAPIKeyError("missing key"),
        LLMTimeoutError("timed out"),
        LLMProviderError("rate limited", status_code=429),
        ValueError("unsupported provider"),
    ],
)
async def test_provider_errors_propagate_unchanged(service, llm_service, error):
    """Provider-layer errors are not swallowed or wrapped."""
    llm_service.generate_response = AsyncMock(side_effect=error)

    with pytest.raises(type(error)):
        await service.answer(PROVIDER, "question", _context(_chunk()))

    assert llm_service.generate_response.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("question", ["", "   ", "\n\t "])
async def test_blank_question_raises_value_error(service, llm_service, question):
    """A blank question is rejected before generation."""
    llm_service.generate_response = AsyncMock()

    with pytest.raises(ValueError, match="question"):
        await service.answer(PROVIDER, question, _context(_chunk()))

    llm_service.generate_response.assert_not_awaited()


def test_negative_max_retries_is_rejected(llm_service):
    """Retries cannot be negative."""
    with pytest.raises(ValueError, match="max_retries"):
        RAGAnswerService(llm_service=llm_service, max_retries=-1)
