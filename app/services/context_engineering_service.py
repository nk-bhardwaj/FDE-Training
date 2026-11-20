"""Context engineering for the RAG pipeline.

Turns retrieved ``ChunkSearchResult`` objects into a bounded, deduplicated,
fully attributed context block for the answer-generation stage.

This service never calls an LLM and never touches the database; it only
prepares context. Token counts use the same ``cl100k_base`` tiktoken encoding
as the chunking service and are approximations of Gemini's tokenizer.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

import tiktoken

from app.core.logging import get_logger
from app.services.chunking_service import ENCODING_NAME
from app.services.rag_retrieval_service import ChunkSearchResult

logger = get_logger(__name__)

DEFAULT_MAX_TOKENS = 2000


@lru_cache(maxsize=1)
def _get_encoding() -> tiktoken.Encoding:
    """Return a cached tiktoken encoding, matching the chunking service."""
    return tiktoken.get_encoding(ENCODING_NAME)


@dataclass(frozen=True)
class ContextChunk:
    """A retrieved chunk included in the assembled context, with citation data."""

    chunk_id: int
    document_id: int
    content: str
    source_id: str
    document_title: str
    chunk_index: int
    retrieval_rank: int
    token_count: int
    distance: float | None = None
    similarity: float | None = None
    rank: float | None = None
    rrf_score: float | None = None


@dataclass(frozen=True)
class AssembledContext:
    """Structured context ready for prompt construction.

    Attributes:
        chunks: Included chunks in retrieval order.
        total_tokens: Sum of included chunk content tokens.
        max_tokens: Token budget applied to this assembly.
        truncated: True when at least one candidate was skipped for the budget.
        duplicates_removed: Number of duplicate chunks skipped.
        sources: Unique source IDs in inclusion order, for attribution.
    """

    chunks: tuple[ContextChunk, ...]
    total_tokens: int
    max_tokens: int
    truncated: bool
    duplicates_removed: int
    sources: tuple[str, ...]


class ContextEngineeringService:
    """Assembles retrieved chunks into a bounded, attributed context."""

    def __init__(self, *, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")
        self.max_tokens = max_tokens

    def count_tokens(self, text: str) -> int:
        """Return the number of ``cl100k_base`` tokens in ``text``."""
        if not text:
            return 0
        return len(_get_encoding().encode(text))

    def assemble(
        self,
        chunks: Sequence[ChunkSearchResult],
        *,
        max_tokens: int | None = None,
    ) -> AssembledContext:
        """Build an attributed context from retrieved chunks.

        Chunks are kept in retrieval order and included while they fit the
        token budget. Duplicates (same ``source_id`` and ``chunk_index``) and
        empty chunks are skipped; a chunk that does not fit is skipped without
        blocking smaller later chunks.

        Args:
            chunks: Retrieved candidates, best first.
            max_tokens: Optional per-call token budget override.

        Returns:
            An :class:`AssembledContext` with citation metadata per chunk.

        Raises:
            ValueError: If the effective ``max_tokens`` is not positive.
        """
        budget = self.max_tokens if max_tokens is None else max_tokens
        if budget <= 0:
            raise ValueError("max_tokens must be a positive integer")

        candidates = list(chunks)
        if not candidates:
            logger.info(
                "service=context_engineering operation=assemble status=skipped reason=no_candidates"
            )
            return AssembledContext(
                chunks=(),
                total_tokens=0,
                max_tokens=budget,
                truncated=False,
                duplicates_removed=0,
                sources=(),
            )

        start = time.perf_counter()
        included: list[ContextChunk] = []
        seen: set[tuple[str, int]] = set()
        sources: dict[str, None] = {}
        duplicates_removed = 0
        truncated = False
        total_tokens = 0

        for retrieval_rank, candidate in enumerate(candidates, start=1):
            key = (candidate.source_id, candidate.chunk_index)
            if key in seen:
                duplicates_removed += 1
                continue
            seen.add(key)

            content = candidate.content or ""
            if not content.strip():
                continue

            token_count = self.count_tokens(content)
            if total_tokens + token_count > budget:
                truncated = True
                continue

            total_tokens += token_count
            sources.setdefault(candidate.source_id, None)
            included.append(
                ContextChunk(
                    chunk_id=candidate.id,
                    document_id=candidate.document_id,
                    content=content,
                    source_id=candidate.source_id,
                    document_title=candidate.document_title,
                    chunk_index=candidate.chunk_index,
                    retrieval_rank=retrieval_rank,
                    token_count=token_count,
                    distance=candidate.distance,
                    similarity=candidate.similarity,
                    rank=candidate.rank,
                    rrf_score=candidate.rrf_score,
                )
            )

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "service=context_engineering operation=assemble status=success candidates=%d included=%d duplicates_removed=%d truncated=%s total_tokens=%d max_tokens=%d latency_ms=%.2f",
            len(candidates),
            len(included),
            duplicates_removed,
            truncated,
            total_tokens,
            budget,
            latency_ms,
        )
        return AssembledContext(
            chunks=tuple(included),
            total_tokens=total_tokens,
            max_tokens=budget,
            truncated=truncated,
            duplicates_removed=duplicates_removed,
            sources=tuple(sources),
        )
