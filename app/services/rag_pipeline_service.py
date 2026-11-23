"""RAG pipeline orchestration service.

Connects the existing retrieval, reranking, context engineering, and answer
generation services into a single end-to-end workflow.  All configuration is
via RAGPipelineConfig; services are dependency-injected for testability.

The execution order is:
    hybrid_search_chunks -> optional rerank -> assemble context -> generate answer.

Read-only: no inserts, updates, deletes or migrations.  No Gemini or Neon
calls unless individual services are invoked with live credentials.
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.schemas.rag_answer import RAGAnswerResponse
from app.services.context_engineering_service import (
    AssembledContext,
    ContextEngineeringService,
)
from app.services.document_service import DocumentStoreError
from app.services.rag_answer_service import RAGAnswerError, RAGAnswerService
from app.services.rag_retrieval_service import ChunkSearchResult, RAGRetrievalService
from app.services.reranking_service import RAGRerankingService

logger = get_logger(__name__)


def _question_hash(question: str) -> str:
    """Return a short non-reversible hash of the question for logging."""
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:8]


@dataclass(frozen=True)
class RAGPipelineConfig:
    """Configuration for the RAG pipeline execution.

    Attributes:
        retrieval_top_k: Final number of results to keep after retrieval/reranking.
        retrieval_candidate_pool: Number of initial candidates to fetch from
            hybrid_search_chunks.  When None (default), computed as
            retrieval_top_k * 2.  Must be >= retrieval_top_k if set.
        rerank_enabled: Whether to apply lexical reranking.
        rerank_top_k: Maximum results to keep after reranking.  When None,
            retrieval_top_k is used.
        context_max_tokens: Token budget for context assembly.
    """

    retrieval_top_k: int = 5
    retrieval_candidate_pool: int | None = None
    rerank_enabled: bool = True
    rerank_top_k: int | None = None
    context_max_tokens: int = 2000

    def __post_init__(self) -> None:
        if self.retrieval_top_k <= 0:
            raise ValueError("retrieval_top_k must be a positive integer")
        if self.retrieval_candidate_pool is not None:
            if self.retrieval_candidate_pool <= 0:
                raise ValueError("retrieval_candidate_pool must be a positive integer")
            if self.retrieval_candidate_pool < self.retrieval_top_k:
                raise ValueError("retrieval_candidate_pool must be >= retrieval_top_k")
        if self.context_max_tokens <= 0:
            raise ValueError("context_max_tokens must be a positive integer")
        if self.rerank_top_k is not None and self.rerank_top_k <= 0:
            raise ValueError("rerank_top_k must be a positive integer")

    @property
    def effective_candidate_pool(self) -> int:
        """Return the effective candidate pool size for retrieval."""
        pool = (
            self.retrieval_candidate_pool
            if self.retrieval_candidate_pool is not None
            else self.retrieval_top_k * 2
        )
        return max(pool, self.retrieval_top_k)

    @property
    def effective_rerank_top_k(self) -> int:
        """Return the effective top_k after reranking."""
        return self.rerank_top_k if self.rerank_top_k is not None else self.retrieval_top_k


class RAGPipelineError(Exception):
    """Raised when the pipeline cannot produce an answer at the given step."""

    def __init__(self, message: str, *, status_code: int = 502, step: str = "retrieval") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.step = step


@dataclass(frozen=True)
class RAGPipelineResponse:
    """Complete pipeline output for debugging and evaluation.

    All chunk collections are tuples (immutable) for safe reference.
    """

    answer: RAGAnswerResponse
    assembled_context: AssembledContext
    reranked_chunks: tuple[ChunkSearchResult, ...]
    raw_retrieval_chunks: tuple[ChunkSearchResult, ...]
    config_used: RAGPipelineConfig


class RAGPipelineService:
    """Orchestrates the complete RAG workflow from question to grounded answer.

    Execution flow:
        1. hybrid_search_chunks(question, candidate_pool, metadata_filters)
        2. optional RAGRerankingService.rerank()
        3. ContextEngineeringService.assemble()
        4. RAGAnswerService.answer()

    Dependencies are dependency-injected; defaults use existing constructors
    so the service can be used without any configuration.
    """

    def __init__(
        self,
        *,
        retrieval_service: RAGRetrievalService | None = None,
        reranking_service: RAGRerankingService | None = None,
        context_service: ContextEngineeringService | None = None,
        answer_service: RAGAnswerService | None = None,
        config: RAGPipelineConfig | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or RAGRetrievalService()
        self.reranking_service = reranking_service or RAGRerankingService()
        self.context_service = context_service or ContextEngineeringService()
        self.answer_service = answer_service or RAGAnswerService()
        self.default_config = config or RAGPipelineConfig()

    async def run(
        self,
        question: str,
        provider: str,
        *,
        config: RAGPipelineConfig | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> RAGPipelineResponse:
        """Run the full RAG pipeline and return a RAGPipelineResponse.

        Args:
            question: User question.  Must not be blank.
            provider: LLM provider name (``"openai"``, ``"anthropic"``,
                ``"groq"``).
            config: Per-call configuration override; falls back to constructor
                defaults.
            metadata_filters: JSONB-compatible filters passed to retrieval
                only.

        Returns:
            RAGPipelineResponse with answer, context, intermediate chunks,
            and effective configuration.

        Raises:
            ValueError: If ``question`` is blank (propagated as-is).
            RAGPipelineError: Wrapped step failures.
            Provider-specific exceptions (``MissingAPIKeyError`` etc.) are
                propagated unchanged from the answer service.
        """
        # ---- Validate question early -------------------------------------------------
        if not question or not question.strip():
            raise ValueError("question must not be empty")

        cfg = config or self.default_config
        qhash = _question_hash(question)

        # ---- Step 1: Hybrid retrieval -------------------------------------------------
        candidate_pool = cfg.effective_candidate_pool
        start_ms = time.perf_counter()
        try:
            raw_retrieval_chunks = await self.retrieval_service.hybrid_search_chunks(
                query=question,
                limit=candidate_pool,
                metadata_filters=metadata_filters,
            )
        except DocumentStoreError as exc:
            latency_ms = (time.perf_counter() - start_ms) * 1000
            logger.warning(
                "service=rag_pipeline operation=retrieval status=failure "
                "question_sha=%s provider=%s step=retrieval latency_ms=%.2f reason=document_store_error",
                qhash,
                provider,
                latency_ms,
            )
            raise RAGPipelineError(
                f"Retrieval failed: {exc}",
                status_code=502,
                step="retrieval",
            ) from exc

        retrieval_latency_ms = (time.perf_counter() - start_ms) * 1000
        logger.info(
            "service=rag_pipeline operation=retrieval status=success "
            "question_sha=%s provider=%s results=%d pool=%d latency_ms=%.2f",
            qhash,
            provider,
            len(raw_retrieval_chunks),
            candidate_pool,
            retrieval_latency_ms,
        )

        # ---- Step 2: Optional reranking ------------------------------------------------
        start_ms = time.perf_counter()
        try:
            if cfg.rerank_enabled:
                reranked_chunks = self.reranking_service.rerank(
                    query=question,
                    candidates=raw_retrieval_chunks,
                    top_k=cfg.effective_rerank_top_k,
                )
            else:
                # Reranking disabled: use only the first retrieval_top_k candidates
                reranked_chunks = raw_retrieval_chunks[: cfg.retrieval_top_k]
        except ValueError as exc:
            latency_ms = (time.perf_counter() - start_ms) * 1000
            logger.warning(
                "service=rag_pipeline operation=reranking status=failure "
                "question_sha=%s provider=%s step=reranking latency_ms=%.2f reason=%s",
                qhash,
                provider,
                latency_ms,
                exc,
            )
            raise RAGPipelineError(
                f"Reranking failed: {exc}",
                status_code=400,
                step="reranking",
            ) from exc

        rerank_latency_ms = (time.perf_counter() - start_ms) * 1000
        logger.info(
            "service=rag_pipeline operation=reranking status=success "
            "question_sha=%s provider=%s enabled=%s results_in=%d results_out=%d latency_ms=%.2f",
            qhash,
            provider,
            cfg.rerank_enabled,
            len(raw_retrieval_chunks),
            len(reranked_chunks),
            rerank_latency_ms,
        )

        # ---- Step 3: Context assembly --------------------------------------------------
        start_ms = time.perf_counter()
        try:
            assembled_context = self.context_service.assemble(
                chunks=reranked_chunks,
                max_tokens=cfg.context_max_tokens,
            )
        except ValueError as exc:
            latency_ms = (time.perf_counter() - start_ms) * 1000
            logger.warning(
                "service=rag_pipeline operation=context_assemble status=failure "
                "question_sha=%s provider=%s step=context latency_ms=%.2f reason=%s",
                qhash,
                provider,
                latency_ms,
                exc,
            )
            raise RAGPipelineError(
                f"Context assembly failed: {exc}",
                status_code=400,
                step="context",
            ) from exc

        context_latency_ms = (time.perf_counter() - start_ms) * 1000
        logger.info(
            "service=rag_pipeline operation=context_assemble status=success "
            "question_sha=%s provider=%s candidates_in=%d included=%d "
            "duplicates_removed=%d truncated=%s latency_ms=%.2f",
            qhash,
            provider,
            len(reranked_chunks),
            len(assembled_context.chunks),
            assembled_context.duplicates_removed,
            assembled_context.truncated,
            context_latency_ms,
        )

        # ---- Step 4: Answer generation -------------------------------------------------
        start_ms = time.perf_counter()
        try:
            answer_result = await self.answer_service.answer(
                provider=provider,
                question=question,
                context=assembled_context,
            )
        except RAGAnswerError as exc:
            latency_ms = (time.perf_counter() - start_ms) * 1000
            logger.warning(
                "service=rag_pipeline operation=answer status=failure "
                "question_sha=%s provider=%s step=answer latency_ms=%.2f reason=rag_answer_error",
                qhash,
                provider,
                latency_ms,
            )
            raise RAGPipelineError(
                f"Answer generation failed: {exc}",
                status_code=exc.status_code,
                step="answer",
            ) from exc
        # Provider-specific exceptions (MissingAPIKeyError, LLMTimeoutError,
        # LLMProviderError) and ValueError from the answer service propagate
        # unchanged per requirements.

        answer_latency_ms = (time.perf_counter() - start_ms) * 1000
        logger.info(
            "service=rag_pipeline operation=answer status=success "
            "question_sha=%s provider=%s latency_ms=%.2f attempts=%d "
            "context_chunks=%d context_tokens=%d abstained=%s",
            qhash,
            provider,
            answer_latency_ms,
            answer_result.attempts,
            len(assembled_context.chunks),
            assembled_context.total_tokens,
            answer_result.abstained,
        )

        # ---- Return response ---------------------------------------------------------
        return RAGPipelineResponse(
            answer=answer_result,
            assembled_context=assembled_context,
            reranked_chunks=tuple(reranked_chunks),
            raw_retrieval_chunks=tuple(raw_retrieval_chunks),
            config_used=cfg,
        )
