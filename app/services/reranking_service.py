"""Model-free lexical reranking baseline for RAG chunk candidates.

The score is normalized query-term coverage: the fraction of meaningful,
unique query terms that appear as whole tokens in the chunk. No models,
external services, or extra dependencies are involved.
"""

import re
import time
from collections.abc import Sequence

from app.core.logging import get_logger
from app.services.rag_retrieval_service import ChunkSearchResult

logger = get_logger(__name__)

DEFAULT_MIN_TERM_LENGTH = 2

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# Common English function words that carry no retrieval signal on their own.
DEFAULT_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "about",
        "after",
        "all",
        "also",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "between",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "during",
        "each",
        "few",
        "for",
        "from",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "him",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "just",
        "me",
        "more",
        "most",
        "my",
        "no",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


def _tokenize(text: str) -> list[str]:
    """Lowercase the text and split it into alphanumeric tokens."""
    return _TOKEN_PATTERN.findall((text or "").lower())


class RAGRerankingService:
    """Reranks retrieved chunks by normalized lexical query-term coverage."""

    def __init__(
        self,
        *,
        min_term_length: int = DEFAULT_MIN_TERM_LENGTH,
        stopwords: frozenset[str] | None = None,
    ) -> None:
        if min_term_length < 1:
            raise ValueError("min_term_length must be a positive integer")
        self.min_term_length = min_term_length
        self.stopwords = DEFAULT_STOPWORDS if stopwords is None else frozenset(stopwords)

    def meaningful_terms(self, query: str) -> list[str]:
        """Return unique query terms, excluding stopwords and short tokens."""
        terms: dict[str, None] = {}
        for token in _tokenize(query):
            if len(token) < self.min_term_length or token in self.stopwords:
                continue
            terms.setdefault(token, None)
        return list(terms)

    def score_chunk(self, query: str, chunk: ChunkSearchResult) -> float:
        """Return the fraction of meaningful query terms present in the chunk (0..1)."""
        terms = self.meaningful_terms(query)
        if not terms:
            return 0.0
        return self._coverage(terms, chunk)

    def rerank(
        self,
        query: str,
        candidates: Sequence[ChunkSearchResult],
        top_k: int | None = None,
    ) -> list[ChunkSearchResult]:
        """Rank candidates by lexical coverage, keeping input order for ties.

        Args:
            query: User query used to derive meaningful terms.
            candidates: Existing retrieval results to reorder.
            top_k: Optional maximum number of results to return.

        Returns:
            The original ``ChunkSearchResult`` objects, ordered by descending
            lexical score. When the query has no meaningful terms, candidates
            are returned unchanged (still respecting ``top_k``).

        Raises:
            ValueError: If ``top_k`` is not a positive integer.
        """
        if top_k is not None and top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        candidate_list = list(candidates)
        if not candidate_list:
            logger.info("service=reranking status=skipped reason=no_candidates")
            return []

        terms = self.meaningful_terms(query)
        if not terms:
            logger.warning(
                "service=reranking status=skipped reason=no_meaningful_query_terms candidates=%d",
                len(candidate_list),
            )
            return candidate_list if top_k is None else candidate_list[:top_k]

        start = time.perf_counter()
        # Descending score, then original retrieval order for deterministic ties.
        scored = [
            (self._coverage(terms, candidate), index, candidate)
            for index, candidate in enumerate(candidate_list)
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        results = [candidate for _, _, candidate in scored]
        if top_k is not None:
            results = results[:top_k]

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "service=reranking operation=rerank status=success candidates=%d results=%d query_terms=%d top_k=%s latency_ms=%.2f",
            len(candidate_list),
            len(results),
            len(terms),
            top_k,
            latency_ms,
        )
        return results

    def _coverage(self, terms: list[str], chunk: ChunkSearchResult) -> float:
        chunk_terms = set(_tokenize(chunk.content))
        matched = sum(1 for term in terms if term in chunk_terms)
        return matched / len(terms)
