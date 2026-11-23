"""Pydantic schemas for RAG answer generation.

``RAGAnswerPayload`` is the only model-authored shape: it contains an answer,
citation *labels* (``C1``...``Cn``), and an abstention flag. ``Citation`` is
server-built from the supplied context and is never trusted from the model, so
the model cannot invent source identifiers.
"""

from pydantic import BaseModel, Field, model_validator

from app.schemas.llm import ProviderName, TokenUsage


class Citation(BaseModel):
    """An authoritative citation hydrated from the supplied context."""

    source_id: str = Field(min_length=1)
    document_title: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    chunk_id: int | None = None
    document_id: int | None = None


class RAGAnswerPayload(BaseModel):
    """The JSON object the model must return.

    Citations are opaque prompt labels rather than identifiers. An empty answer
    is tolerated only when the model explicitly abstains; the service always
    replaces it with the canonical abstention message.
    """

    answer: str = ""
    citations: list[str] = Field(default_factory=list)
    abstained: bool = False

    @model_validator(mode="after")
    def _require_answer_unless_abstained(self) -> "RAGAnswerPayload":
        if not self.abstained and not self.answer.strip():
            raise ValueError("answer must not be empty unless abstained is true")
        return self


class RAGAnswerRequest(BaseModel):
    """Request body for a future RAG answer API route."""

    provider: ProviderName
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class RAGAnswerResponse(BaseModel):
    """A grounded answer with hydrated citations and generation metadata."""

    question: str
    answer: str
    citations: list[Citation]
    abstained: bool
    provider: ProviderName
    model: str
    latency_ms: float
    usage: TokenUsage | None = None
    attempts: int
    context_chunks: int
    context_tokens: int
