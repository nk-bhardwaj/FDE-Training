"""Unit tests for the model-free RAG reranking baseline."""

import logging

import pytest

from app.services.rag_retrieval_service import ChunkSearchResult
from app.services.reranking_service import RAGRerankingService


def _make_chunk_result(**kwargs) -> ChunkSearchResult:
    """Helper to construct a ChunkSearchResult with sensible defaults."""
    params = {
        "id": 1,
        "document_id": 42,
        "chunk_index": 0,
        "content": "chunk content",
        "metadata": {"source_id": "doc1"},
        "document_metadata": {"title": "Doc 1"},
        "source_id": "doc1",
        "document_title": "Doc 1",
        "created_at": None,
        "distance": None,
        "similarity": None,
        "rank": None,
        "rrf_score": None,
    }
    params.update(kwargs)
    return ChunkSearchResult(**params)


@pytest.fixture
def service() -> RAGRerankingService:
    return RAGRerankingService()


def test_orders_by_query_term_coverage(service):
    """Chunks covering more query terms rank higher."""
    full = _make_chunk_result(id=1, content="Refund policy for returned items.")
    partial = _make_chunk_result(id=2, content="Refund policy details.")
    none = _make_chunk_result(id=3, content="Shipping times and labels.")

    results = service.rerank("refund policy returned items", [none, partial, full])

    assert [result.id for result in results] == [1, 2, 3]


def test_partial_match_scores_are_normalized(service):
    """Coverage is matched terms divided by all meaningful query terms."""
    chunk = _make_chunk_result(content="Refund policy details.")

    score = service.score_chunk("refund policy returned items", chunk)

    assert score == pytest.approx(2 / 4)


def test_scores_are_bounded_between_zero_and_one(service):
    """Coverage never exceeds 1 even with repeated query terms."""
    chunk = _make_chunk_result(content="refund refund refund")

    assert service.score_chunk("refund refund refund", chunk) == pytest.approx(1.0)
    assert service.score_chunk("refund shipping", chunk) == pytest.approx(0.5)
    assert service.score_chunk("shipping", chunk) == pytest.approx(0.0)


def test_duplicate_query_terms_do_not_inflate_score(service):
    """Repeated query terms count once, so coverage stays normalized."""
    chunk = _make_chunk_result(content="refund policy")

    assert service.meaningful_terms("refund refund policy policy") == ["refund", "policy"]
    assert service.score_chunk("refund refund policy policy", chunk) == pytest.approx(1.0)


def test_matching_is_case_and_punctuation_insensitive(service):
    """Tokens are lowercased and punctuation is ignored."""
    chunk = _make_chunk_result(content="Refund: the RETURN policy!")

    score = service.score_chunk("Refund, return?", chunk)

    assert score == pytest.approx(1.0)


def test_stopwords_and_short_tokens_are_ignored(service):
    """Function words and one-character tokens do not affect coverage."""
    assert service.meaningful_terms("How do I return an item?") == ["return", "item"]

    chunk = _make_chunk_result(content="Return the item within 30 days.")
    assert service.score_chunk("How do I return an item?", chunk) == pytest.approx(1.0)


def test_partial_match_ordering_preserves_relative_order(service):
    """Higher coverage sorts first, lower coverage after."""
    two_of_three = _make_chunk_result(id=1, content="refund policy")
    one_of_three = _make_chunk_result(id=2, content="refund details")
    zero_of_three = _make_chunk_result(id=3, content="shipping details")

    results = service.rerank("refund policy return", [zero_of_three, one_of_three, two_of_three])

    assert [result.id for result in results] == [1, 2, 3]
    assert service.score_chunk("refund policy return", two_of_three) == pytest.approx(2 / 3)
    assert service.score_chunk("refund policy return", one_of_three) == pytest.approx(1 / 3)


def test_ties_keep_original_input_order(service):
    """Equal scores preserve the retrieval order for determinism."""
    first = _make_chunk_result(id=1, content="refund policy")
    second = _make_chunk_result(id=2, content="policy refund")
    third = _make_chunk_result(id=3, content="refund and policy")

    results = service.rerank("refund policy", [first, second, third])

    assert [result.id for result in results] == [1, 2, 3]


def test_empty_query_returns_candidates_unchanged(service):
    """An empty query passes candidates through without reordering."""
    first = _make_chunk_result(id=1, content="shipping")
    second = _make_chunk_result(id=2, content="refund")

    results = service.rerank("", [first, second])

    assert results == [first, second]
    assert results[0] is first
    assert results[1] is second


def test_stopword_only_query_returns_candidates_unchanged(service, caplog):
    """A query with no meaningful terms is a safe no-op."""
    first = _make_chunk_result(id=1, content="shipping")
    second = _make_chunk_result(id=2, content="refund")

    with caplog.at_level(logging.WARNING):
        results = service.rerank("how do I", [first, second])

    assert [result.id for result in results] == [1, 2]
    assert "reason=no_meaningful_query_terms" in caplog.text


def test_empty_candidate_list_returns_empty(service):
    """No candidates yields an empty list, regardless of query."""
    assert service.rerank("refund policy", []) == []


def test_top_k_limits_results(service):
    """top_k truncates the ranked output."""
    chunks = [
        _make_chunk_result(id=1, content="refund policy return"),
        _make_chunk_result(id=2, content="refund policy"),
        _make_chunk_result(id=3, content="refund"),
    ]

    results = service.rerank("refund policy return", chunks, top_k=2)

    assert [result.id for result in results] == [1, 2]


def test_top_k_larger_than_candidates_returns_all(service):
    """top_k above the candidate count returns every candidate."""
    chunks = [
        _make_chunk_result(id=1, content="refund"),
        _make_chunk_result(id=2, content="shipping"),
    ]

    results = service.rerank("refund", chunks, top_k=10)

    assert len(results) == 2


@pytest.mark.parametrize("top_k", [0, -1])
def test_invalid_top_k_raises(service, top_k):
    """top_k must be positive, matching the retrieval services."""
    with pytest.raises(ValueError, match="top_k"):
        service.rerank("refund", [_make_chunk_result()], top_k=top_k)


def test_preserves_metadata_and_source_information(service):
    """Reranking returns the original objects with every field intact."""
    chunk = _make_chunk_result(
        id=7,
        document_id=3,
        chunk_index=2,
        content="Refund policy for returned items.",
        metadata={"source_id": "amazon_fba_return_policy", "chunk_index": 2},
        document_metadata={"title": "FBA Return Policy", "category": "returns_refunds"},
        source_id="amazon_fba_return_policy",
        document_title="FBA Return Policy",
        distance=0.21,
        similarity=0.79,
        rank=0.4,
        rrf_score=0.03,
    )

    results = service.rerank("refund policy", [chunk])

    assert results[0] is chunk
    assert results[0].metadata == {"source_id": "amazon_fba_return_policy", "chunk_index": 2}
    assert results[0].document_metadata == {
        "title": "FBA Return Policy",
        "category": "returns_refunds",
    }
    assert results[0].source_id == "amazon_fba_return_policy"
    assert results[0].document_title == "FBA Return Policy"
    assert results[0].distance == pytest.approx(0.21)
    assert results[0].similarity == pytest.approx(0.79)
    assert results[0].rank == pytest.approx(0.4)
    assert results[0].rrf_score == pytest.approx(0.03)


def test_constructor_allows_custom_stopwords_and_min_term_length():
    """Stopwords and minimum term length are configurable."""
    service = RAGRerankingService(min_term_length=4, stopwords=frozenset({"policy"}))

    assert service.meaningful_terms("refund policy items a") == ["refund", "items"]


def test_constructor_rejects_invalid_min_term_length():
    """A non-positive minimum term length is rejected."""
    with pytest.raises(ValueError, match="min_term_length"):
        RAGRerankingService(min_term_length=0)


def test_no_shared_terms_keeps_input_order(service):
    """Chunks with no matching terms all score zero and keep input order."""
    first = _make_chunk_result(id=1, content="shipping labels")
    second = _make_chunk_result(id=2, content="payment methods")

    results = service.rerank("refund", [first, second])

    assert [result.id for result in results] == [1, 2]
    assert service.score_chunk("refund", first) == 0.0
