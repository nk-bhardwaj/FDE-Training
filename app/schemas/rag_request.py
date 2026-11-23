"""Pydantic schemas for the RAG answer API endpoint."""

from pydantic import BaseModel, Field

from app.schemas.llm import ProviderName, TokenUsage
from app.schemas.rag_answer import Citation


class RAGRequest(BaseModel):
    """Request body for the RAG answer endpoint."""

    question: str = Field(min_length=1, max_length=2000)
    provider: ProviderName
    top_k: int = Field(default=5, ge=1, le=20)
    metadata_filters: dict[str, str | int | bool] | None = None


class RAGAnswerApiResponse(BaseModel):
    """Clean API response for the RAG answer endpoint.

    Exposes only answer-facing metadata: answer text, hydrated citations,
    abstention status, generation latency/usage, and effective configuration.
    Internal chunks, embeddings, and service objects are not exposed.
    """

    answer: str
    citations: list[Citation]
    abstained: bool
    provider: ProviderName
    model: str
    latency_ms: float
    usage: TokenUsage | None = None
    context_chunks: int
    context_tokens: int
    retrieval_top_k: int
    retrieval_candidate_pool: int | None
    rerank_enabled: bool
    rerank_top_k: int | None
    context_max_tokens: int
