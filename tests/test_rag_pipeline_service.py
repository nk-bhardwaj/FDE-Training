"""Tests for the RAG pipeline orchestration service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.logging import get_logger
from app.schemas.llm import ProviderName, TokenUsage
from app.schemas.rag_answer import Citation, RAGAnswerResponse
from app.services.context_engineering_service import (
    AssembledContext,
    ContextChunk,
    ContextEngineeringService,
)
from app.services.document_service import DocumentStoreError
from app.services.llm_errors import LLMProviderError, LLMTimeoutError, MissingAPIKeyError
from app.services.rag_answer_service import RAGAnswerError, RAGAnswerService
from app.services.rag_pipeline_service import (
    RAGPipelineConfig,
    RAGPipelineError,
    RAGPipelineResponse,
    RAGPipelineService,
)
from app.services.rag_retrieval_service import ChunkSearchResult, RAGRetrievalService
from app.services.reranking_service import RAGRerankingService

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Fixtures / Helpers
# ----------------------------------------------------------------------


def _make_chunk(
    chunk_id: int,
    source_id: str = "doc1",
    chunk_index: int = 0,
    content: str = "Sample content",
) -> ChunkSearchResult:
    """Factory for ChunkSearchResult with sensible defaults."""
    return ChunkSearchResult(
        id=chunk_id,
        document_id=1,
        chunk_index=chunk_index,
        content=content,
        metadata={"source_id": source_id, "title": "Doc 1"},
        document_metadata={},
        source_id=source_id,
        document_title="Doc 1",
        created_at=None,
        distance=0.1,
        similarity=0.9,
        rank=0.5,
        rrf_score=0.5,
    )


def _make_assembled_context(
    chunks: list[ChunkSearchResult] | None = None,
    **overrides,
) -> AssembledContext:
    """Factory for AssembledContext."""
    if chunks is None:
        chunks = [_make_chunk(1)]

    context_chunks = [
        ContextChunk(
            chunk_id=c.id,
            document_id=c.document_id,
            content=c.content,
            source_id=c.source_id,
            document_title=c.document_title,
            chunk_index=c.chunk_index,
            retrieval_rank=i + 1,
            token_count=100,
            distance=c.distance,
            similarity=c.similarity,
            rank=c.rank,
            rrf_score=c.rrf_score,
        )
        for i, c in enumerate(chunks)
    ]
    return AssembledContext(
        chunks=tuple(context_chunks),
        total_tokens=len(context_chunks) * 100,
        max_tokens=2000,
        truncated=False,
        duplicates_removed=0,
        sources=("doc1",),
        **overrides,
    )


def _make_answer_response(
    provider: ProviderName = "openai",
    abstained: bool = False,
    **overrides,
) -> RAGAnswerResponse:
    """Factory for RAGAnswerResponse."""
    return RAGAnswerResponse(
        question="Test question",
        answer="Test answer",
        citations=[
            Citation(
                source_id="doc1",
                document_title="Doc 1",
                chunk_index=0,
                chunk_id=1,
                document_id=1,
            )
        ]
        if not abstained
        else [],
        abstained=abstained,
        provider=provider,
        model="gpt-4o-mini",
        latency_ms=100.0,
        usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        attempts=1,
        context_chunks=1,
        context_tokens=100,
    )


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


class TestRAGPipelineConfig:
    """Configuration validation tests."""

    def test_defaults(self):
        """Default config values are correct."""
        cfg = RAGPipelineConfig()
        assert cfg.retrieval_top_k == 5
        assert cfg.retrieval_candidate_pool is None
        assert cfg.rerank_enabled is True
        assert cfg.rerank_top_k is None
        assert cfg.context_max_tokens == 2000

    def test_post_init_validates_rerank_top_k(self):
        """rerank_top_k must be positive when set."""
        with pytest.raises(ValueError, match="rerank_top_k must be a positive integer"):
            RAGPipelineConfig(rerank_top_k=0)

    def test_invalid_retrieval_top_k(self):
        """Non-positive retrieval_top_k raises ValueError."""
        with pytest.raises(ValueError, match="retrieval_top_k must be a positive integer"):
            RAGPipelineConfig(retrieval_top_k=0)

    def test_invalid_retrieval_candidate_pool(self):
        """Non-positive candidate_pool raises ValueError."""
        with pytest.raises(ValueError, match="retrieval_candidate_pool must be a positive integer"):
            RAGPipelineConfig(retrieval_candidate_pool=0)

    def test_candidate_pool_less_than_top_k(self):
        """candidate_pool < top_k raises ValueError."""
        with pytest.raises(ValueError, match="candidate_pool must be >= retrieval_top_k"):
            RAGPipelineConfig(retrieval_top_k=10, retrieval_candidate_pool=5)

    def test_invalid_context_max_tokens(self):
        """Non-positive context_max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="context_max_tokens must be a positive integer"):
            RAGPipelineConfig(context_max_tokens=0)


class TestRAGPipelineService:
    """Integration tests for the pipeline service with mocked dependencies."""

    @pytest.fixture
    def mock_retrieval_service(self):
        svc = MagicMock(spec=RAGRetrievalService)
        svc.hybrid_search_chunks = AsyncMock(
            return_value=[_make_chunk(1), _make_chunk(2), _make_chunk(3)]
        )
        return svc

    @pytest.fixture
    def mock_reranking_service(self):
        svc = MagicMock(spec=RAGRerankingService)
        svc.rerank = MagicMock(return_value=[_make_chunk(2), _make_chunk(1)])
        return svc

    @pytest.fixture
    def mock_context_service(self):
        svc = MagicMock(spec=ContextEngineeringService)
        svc.assemble = MagicMock(return_value=_make_assembled_context())
        return svc

    @pytest.fixture
    def mock_answer_service(self):
        svc = MagicMock(spec=RAGAnswerService)
        svc.answer = AsyncMock(return_value=_make_answer_response())
        return svc

    @pytest.fixture
    def pipeline(
        self,
        mock_retrieval_service,
        mock_reranking_service,
        mock_context_service,
        mock_answer_service,
    ):
        return RAGPipelineService(
            retrieval_service=mock_retrieval_service,
            reranking_service=mock_reranking_service,
            context_service=mock_context_service,
            answer_service=mock_answer_service,
        )

    @pytest.mark.asyncio
    async def test_default_candidate_pool_calculation(self, pipeline, mock_retrieval_service):
        """candidate pool defaults to 2 * retrieval_top_k."""
        await pipeline.run("Test question", "openai", config=RAGPipelineConfig(retrieval_top_k=4))
        mock_retrieval_service.hybrid_search_chunks.assert_called_once()
        called_limit = mock_retrieval_service.hybrid_search_chunks.call_args.kwargs["limit"]
        assert called_limit == 8  # 4 * 2

    @pytest.mark.asyncio
    async def test_explicit_candidate_pool_override(self, pipeline, mock_retrieval_service):
        """Explicit candidate_pool is used when configured."""
        await pipeline.run(
            "Test question",
            "openai",
            config=RAGPipelineConfig(retrieval_top_k=3, retrieval_candidate_pool=20),
        )
        called_limit = mock_retrieval_service.hybrid_search_chunks.call_args.kwargs["limit"]
        assert called_limit == 20

    @pytest.mark.asyncio
    async def test_reranking_enabled(
        self, pipeline, mock_reranking_service, mock_retrieval_service
    ):
        """Reranking is invoked when enabled."""
        await pipeline.run("Test question", "openai", config=RAGPipelineConfig(retrieval_top_k=3))
        mock_reranking_service.rerank.assert_called_once()
        args = mock_reranking_service.rerank.call_args
        assert args.kwargs["top_k"] == 3  # default rerank_top_k = retrieval_top_k

    @pytest.mark.asyncio
    async def test_reranking_disabled(
        self, pipeline, mock_reranking_service, mock_retrieval_service, mock_context_service
    ):
        """Reranking is skipped when disabled; only top_k chunks passed to context."""
        await pipeline.run(
            "Test question",
            "openai",
            config=RAGPipelineConfig(retrieval_top_k=2, rerank_enabled=False),
        )
        mock_reranking_service.rerank.assert_not_called()
        # Context service should receive only first retrieval_top_k chunks
        passed_chunks = mock_context_service.assemble.call_args.kwargs["chunks"]
        assert len(passed_chunks) == 2

    @pytest.mark.asyncio
    async def test_rerank_top_k_limit(self, pipeline, mock_reranking_service):
        """rerank_top_k limits results after reranking."""
        await pipeline.run(
            "Test question",
            "openai",
            config=RAGPipelineConfig(retrieval_top_k=5, rerank_top_k=2),
        )
        args = mock_reranking_service.rerank.call_args
        assert args.kwargs["top_k"] == 2

    @pytest.mark.asyncio
    async def test_metadata_filters_passed_to_retrieval_only(
        self, pipeline, mock_retrieval_service, mock_context_service
    ):
        """metadata_filters passed to retrieval; not duplicated in context."""
        filters = {"source_id": "doc1"}
        await pipeline.run("Test question", "openai", metadata_filters=filters)
        # Retrieval receives filters
        ret_call = mock_retrieval_service.hybrid_search_chunks.call_args
        assert ret_call.kwargs["metadata_filters"] == filters
        # Context assemble called without filters (it doesn't accept them)
        ctx_call = mock_context_service.assemble.call_args
        assert "metadata_filters" not in str(ctx_call)

    @pytest.mark.asyncio
    async def test_empty_retrieval_results_in_abstention(
        self, pipeline, mock_retrieval_service, mock_answer_service
    ):
        """Empty retrieval leads to answer service abstention."""
        mock_retrieval_service.hybrid_search_chunks = AsyncMock(return_value=[])
        mock_answer_service.answer = AsyncMock(return_value=_make_answer_response(abstained=True))
        result = await pipeline.run("Test question", "openai")
        assert result.answer.abstained is True

    @pytest.mark.asyncio
    async def test_empty_context_results_in_abstention(
        self, pipeline, mock_context_service, mock_answer_service
    ):
        """Empty assembled context leads to answer service abstention."""
        mock_context_service.assemble = MagicMock(return_value=_make_assembled_context(chunks=[]))
        mock_answer_service.answer = AsyncMock(return_value=_make_answer_response(abstained=True))
        result = await pipeline.run("Test question", "openai")
        assert result.answer.abstained is True

    @pytest.mark.asyncio
    async def test_retrieval_error_wrapped(self, pipeline, mock_retrieval_service):
        """DocumentStoreError wrapped as RAGPipelineError with step=retrieval."""
        mock_retrieval_service.hybrid_search_chunks = AsyncMock(
            side_effect=DocumentStoreError("connection failed")
        )
        with pytest.raises(RAGPipelineError) as exc:
            await pipeline.run("Test question", "openai")
        assert exc.value.step == "retrieval"
        assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_reranking_config_error_wrapped(self, pipeline, mock_reranking_service):
        """Reranking ValueError wrapped with step=reranking."""
        mock_reranking_service.rerank = MagicMock(side_effect=ValueError("top_k must be positive"))
        with pytest.raises(RAGPipelineError) as exc:
            await pipeline.run("Test question", "openai")
        assert exc.value.step == "reranking"

    @pytest.mark.asyncio
    async def test_context_config_error_wrapped(self, pipeline, mock_context_service):
        """Context ValueError wrapped with step=context."""
        mock_context_service.assemble = MagicMock(
            side_effect=ValueError("max_tokens must be positive")
        )
        with pytest.raises(RAGPipelineError) as exc:
            await pipeline.run("Test question", "openai")
        assert exc.value.step == "context"

    @pytest.mark.asyncio
    async def test_answer_error_wrapped(self, pipeline, mock_answer_service):
        """RAGAnswerError wrapped with step=answer."""
        mock_answer_service.answer = AsyncMock(
            side_effect=RAGAnswerError("validation failed", status_code=502)
        )
        with pytest.raises(RAGPipelineError) as exc:
            await pipeline.run("Test question", "openai")
        assert exc.value.step == "answer"
        assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_missing_api_key_error_propagated(self, pipeline, mock_answer_service):
        """MissingAPIKeyError propagates unchanged."""
        mock_answer_service.answer = AsyncMock(side_effect=MissingAPIKeyError("API key not found"))
        with pytest.raises(MissingAPIKeyError):
            await pipeline.run("Test question", "openai")

    @pytest.mark.asyncio
    async def test_llm_timeout_error_propagated(self, pipeline, mock_answer_service):
        """LLMTimeoutError propagates unchanged."""
        mock_answer_service.answer = AsyncMock(side_effect=LLMTimeoutError("timeout"))
        with pytest.raises(LLMTimeoutError):
            await pipeline.run("Test question", "openai")

    @pytest.mark.asyncio
    async def test_llm_provider_error_propagated(self, pipeline, mock_answer_service):
        """LLMProviderError propagates unchanged."""
        mock_answer_service.answer = AsyncMock(side_effect=LLMProviderError("rate limited"))
        with pytest.raises(LLMProviderError):
            await pipeline.run("Test question", "openai")

    @pytest.mark.asyncio
    async def test_blank_question_rejected(self, pipeline):
        """Blank question raises ValueError before any pipeline step."""
        with pytest.raises(ValueError, match="question must not be empty"):
            await pipeline.run("", "openai")
        with pytest.raises(ValueError, match="question must not be empty"):
            await pipeline.run("   ", "openai")

    @pytest.mark.asyncio
    async def test_per_call_config_override(self, pipeline, mock_retrieval_service):
        """Per-call config overrides constructor defaults."""
        pipeline.default_config = RAGPipelineConfig(retrieval_top_k=10)
        await pipeline.run(
            "Test question",
            "openai",
            config=RAGPipelineConfig(retrieval_top_k=3),
        )
        called_limit = mock_retrieval_service.hybrid_search_chunks.call_args.kwargs["limit"]
        assert called_limit == 6  # 3 * 2

    @pytest.mark.asyncio
    async def test_execution_order(
        self,
        pipeline,
        mock_retrieval_service,
        mock_reranking_service,
        mock_context_service,
        mock_answer_service,
    ):
        """Services are called in the correct order."""
        call_order = []

        async def track_retrieval(*args, **kwargs):
            call_order.append("retrieval")
            return [_make_chunk(1)]

        def track_rerank(*args, **kwargs):
            call_order.append("reranking")
            return [_make_chunk(1)]

        def track_context(*args, **kwargs):
            call_order.append("context")
            return _make_assembled_context()

        async def track_answer(*args, **kwargs):
            call_order.append("answer")
            return _make_answer_response()

        mock_retrieval_service.hybrid_search_chunks = AsyncMock(side_effect=track_retrieval)
        mock_reranking_service.rerank = MagicMock(side_effect=track_rerank)
        mock_context_service.assemble = MagicMock(side_effect=track_context)
        mock_answer_service.answer = AsyncMock(side_effect=track_answer)

        await pipeline.run("Test question", "openai")
        assert call_order == ["retrieval", "reranking", "context", "answer"]

    @pytest.mark.asyncio
    async def test_response_contains_intermediate_artifacts(
        self,
        pipeline,
        mock_retrieval_service,
        mock_reranking_service,
        mock_context_service,
        mock_answer_service,
    ):
        """RAGPipelineResponse contains all intermediate artifacts."""
        raw_chunks = [_make_chunk(1), _make_chunk(2)]
        mock_retrieval_service.hybrid_search_chunks = AsyncMock(return_value=raw_chunks)
        mock_reranking_service.rerank = MagicMock(return_value=[raw_chunks[0]])
        context = _make_assembled_context(chunks=[raw_chunks[0]])
        mock_context_service.assemble = MagicMock(return_value=context)
        mock_answer_service.answer = AsyncMock(return_value=_make_answer_response())

        result = await pipeline.run("Test question", "openai")

        assert isinstance(result, RAGPipelineResponse)
        assert result.answer is not None
        assert result.assembled_context == context
        assert result.reranked_chunks == (raw_chunks[0],)
        assert result.raw_retrieval_chunks == tuple(raw_chunks)
        assert isinstance(result.config_used, RAGPipelineConfig)

    @pytest.mark.asyncio
    async def test_answer_service_awaited_and_response_processed(
        self, pipeline, mock_answer_service
    ):
        """Regression: run() awaits the async answer() and processes its result.

        If ``answer`` were called without ``await``, ``answer_result`` would be
        a coroutine and accessing ``answer_result.attempts`` would raise
        AttributeError. Using an AsyncMock for the answer service verifies the
        await is present and the returned RAGAnswerResponse is processed.
        """
        expected_answer = _make_answer_response(provider="groq")
        mock_answer_service.answer = AsyncMock(return_value=expected_answer)

        result = await pipeline.run("Test question", "groq")

        mock_answer_service.answer.assert_awaited_once()
        # The actual RAGAnswerResponse is returned and processed, not a coroutine
        assert result.answer is expected_answer
        assert result.answer.attempts == 1
        assert result.answer.latency_ms == 100.0
        assert result.answer.usage is not None
        assert result.answer.usage.total_tokens == 150


class TestRAGPipelineServiceDefaultConstruction:
    """Tests that default construction works without injected dependencies."""

    @pytest.mark.asyncio
    async def test_default_construction_uses_real_services(self):
        """Service can be constructed without any arguments."""
        # This test only verifies construction; actual services are not called
        with (
            patch("app.services.rag_pipeline_service.RAGRetrievalService") as mock_ret_cls,
            patch("app.services.rag_pipeline_service.RAGRerankingService") as mock_rerank_cls,
            patch("app.services.rag_pipeline_service.ContextEngineeringService") as mock_ctx_cls,
            patch("app.services.rag_pipeline_service.RAGAnswerService") as mock_ans_cls,
        ):
            RAGPipelineService()
            assert mock_ret_cls.called
            assert mock_rerank_cls.called
            assert mock_ctx_cls.called
            assert mock_ans_cls.called
