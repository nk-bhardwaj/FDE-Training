"""Unit tests for RAG retrieval evaluation metrics."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rag_retrieval_service import ChunkSearchResult, RAGRetrievalService
from scripts.evaluate_rag_retrieval import (
    EvalQuestion,
    _calculate_metrics,
    _evaluate_strategy,
)


class TestCalculateMetrics:
    """Tests for the metric calculation helpers."""

    def test_perfect_match(self):
        """All expected chunks retrieved in correct order."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved = [("doc1", 0), ("doc1", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        assert qm.precision_at_k == 1.0
        assert qm.recall_at_k == 1.0
        assert qm.reciprocal_rank == 1.0

    def test_partial_match_precision(self):
        """Some expected chunks retrieved, extra non-relevant chunks."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved = [("doc1", 0), ("doc2", 0), ("doc3", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        # 1 relevant out of 3 retrieved
        assert qm.precision_at_k == pytest.approx(1.0 / 3.0)
        # 1 relevant out of 2 expected
        assert qm.recall_at_k == pytest.approx(1.0 / 2.0)
        # First relevant at rank 1
        assert qm.reciprocal_rank == 1.0

    def test_partial_match_recall(self):
        """More expected than retrieved."""
        expected = {("doc1", 0), ("doc1", 1), ("doc1", 2)}
        retrieved = [("doc1", 0), ("doc1", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        # 2 relevant out of 2 retrieved
        assert qm.precision_at_k == 1.0
        # 2 relevant out of 3 expected
        assert qm.recall_at_k == pytest.approx(2.0 / 3.0)
        assert qm.reciprocal_rank == 1.0

    def test_no_relevant_retrieved(self):
        """None of the expected chunks retrieved."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved = [("doc2", 0), ("doc2", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0

    def test_relevant_at_rank_2(self):
        """First relevant at rank 2."""
        expected = {("doc1", 1)}
        retrieved = [("doc2", 0), ("doc1", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        assert qm.reciprocal_rank == pytest.approx(1.0 / 2.0)

    def test_relevant_at_rank_3(self):
        """First relevant at rank 3."""
        expected = {("doc1", 2)}
        retrieved = [("doc2", 0), ("doc3", 0), ("doc1", 2)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        assert qm.reciprocal_rank == pytest.approx(1.0 / 3.0)

    def test_empty_retrieved(self):
        """No results returned."""
        expected = {("doc1", 0)}
        retrieved = []
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0

    def test_empty_expected(self):
        """No expected chunks (edge case)."""
        expected = set()
        retrieved = [("doc1", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None)
        assert qm.recall_at_k == 0.0

    def test_error_case(self):
        """Error during retrieval."""
        expected = {("doc1", 0)}
        retrieved = []
        qm = _calculate_metrics("test", expected, retrieved, 10.0, "ConnectionError")
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0
        assert qm.error == "ConnectionError"


class TestEvaluateStrategy:
    """Tests for the strategy evaluation orchestrator."""

    @pytest.fixture
    def mock_rag_service(self):
        """Mock RAGRetrievalService with controllable methods."""
        return MagicMock(spec=RAGRetrievalService)

    @pytest.fixture
    def questions(self):
        """Sample evaluation questions."""
        return [
            EvalQuestion(
                question="Test question 1",
                expected_chunks={("doc1", 0), ("doc1", 1)},
            ),
            EvalQuestion(
                question="Test question 2",
                expected_chunks={("doc2", 0)},
            ),
        ]

    @pytest.mark.asyncio
    async def test_evaluates_all_questions(self, mock_rag_service, questions):
        """Strategy called once per question."""
        mock_rag_service.semantic_search_chunks = AsyncMock(
            return_value=[
                ChunkSearchResult(
                    id=1,
                    document_id=1,
                    chunk_index=0,
                    content="",
                    metadata={"source_id": "doc1"},
                    document_metadata={},
                    source_id="doc1",
                    document_title="Doc 1",
                    created_at=None,
                    distance=0.1,
                    similarity=0.9,
                    rank=None,
                    rrf_score=None,
                ),
                ChunkSearchResult(
                    id=2,
                    document_id=1,
                    chunk_index=1,
                    content="",
                    metadata={"source_id": "doc1"},
                    document_metadata={},
                    source_id="doc1",
                    document_title="Doc 1",
                    created_at=None,
                    distance=0.2,
                    similarity=0.8,
                    rank=None,
                    rrf_score=None,
                ),
            ]
        )

        metrics = await _evaluate_strategy(
            "semantic", mock_rag_service.semantic_search_chunks, questions, 3
        )

        assert mock_rag_service.semantic_search_chunks.await_count == 2
        assert len(metrics.queries) == 2

    @pytest.mark.asyncio
    async def test_correctly_aggregates_metrics(self, mock_rag_service, questions):
        """Aggregate metrics are correctly computed."""
        # Q1: perfect match (P=1, R=1, RR=1)
        # Q2: expects doc2_0, retrieves doc1_0, doc2_0
        #     P@3 = 1/2 = 0.5, R@3 = 1/1 = 1.0, RR = 1/2 = 0.5 (first relevant at rank 2)
        mock_rag_service.semantic_search_chunks = AsyncMock(
            side_effect=[
                [
                    ChunkSearchResult(
                        id=1,
                        document_id=1,
                        chunk_index=0,
                        content="",
                        metadata={"source_id": "doc1"},
                        document_metadata={},
                        source_id="doc1",
                        document_title="Doc 1",
                        created_at=None,
                        distance=0.1,
                        similarity=0.9,
                        rank=None,
                        rrf_score=None,
                    ),
                    ChunkSearchResult(
                        id=2,
                        document_id=1,
                        chunk_index=1,
                        content="",
                        metadata={"source_id": "doc1"},
                        document_metadata={},
                        source_id="doc1",
                        document_title="Doc 1",
                        created_at=None,
                        distance=0.2,
                        similarity=0.8,
                        rank=None,
                        rrf_score=None,
                    ),
                ],
                [
                    ChunkSearchResult(
                        id=3,
                        document_id=1,
                        chunk_index=0,
                        content="",
                        metadata={"source_id": "doc1"},
                        document_metadata={},
                        source_id="doc1",
                        document_title="Doc 1",
                        created_at=None,
                        distance=0.1,
                        similarity=0.9,
                        rank=None,
                        rrf_score=None,
                    ),
                    ChunkSearchResult(
                        id=4,
                        document_id=2,
                        chunk_index=0,
                        content="",
                        metadata={"source_id": "doc2"},
                        document_metadata={},
                        source_id="doc2",
                        document_title="Doc 2",
                        created_at=None,
                        distance=0.2,
                        similarity=0.8,
                        rank=None,
                        rrf_score=None,
                    ),
                ],
            ]
        )

        metrics = await _evaluate_strategy(
            "semantic", mock_rag_service.semantic_search_chunks, questions, 3
        )

        # Q1: P@3=1.0, R@3=1.0, RR=1.0
        # Q2: P@3=0.5 (1/2), R@3=1.0 (1/1), RR=0.5 (first relevant at rank 2)
        assert metrics.mean_precision_at_k == pytest.approx((1.0 + 0.5) / 2)
        assert metrics.mean_recall_at_k == pytest.approx((1.0 + 1.0) / 2)
        assert metrics.mrr == pytest.approx((1.0 + 0.5) / 2)

    @pytest.mark.asyncio
    async def test_handles_errors(self, mock_rag_service, questions):
        """Errors are captured and metrics set to zero."""
        mock_rag_service.semantic_search_chunks = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        metrics = await _evaluate_strategy(
            "semantic", mock_rag_service.semantic_search_chunks, questions, 3
        )

        for qm in metrics.queries:
            assert qm.error is not None
            assert qm.precision_at_k == 0.0
            assert qm.recall_at_k == 0.0
            assert qm.reciprocal_rank == 0.0

    @pytest.mark.asyncio
    async def test_latency_aggregation(self, mock_rag_service, questions):
        """Mean latency excludes failed queries."""
        # Patch _run_strategy directly to control latencies
        with patch("scripts.evaluate_rag_retrieval._run_strategy") as mock_run:
            # Q1: success with 15ms latency
            # Q2: failure with 20ms latency (but error=True, so excluded from mean)
            mock_run.side_effect = [
                ([("doc1", 0)], 15.0, None),  # Q1 success
                ([], 20.0, "ConnectionError"),  # Q2 failure
            ]

            metrics = await _evaluate_strategy(
                "semantic", mock_rag_service.semantic_search_chunks, questions, 3
            )

        # Only Q1 latency counted (15ms), Q2 error excluded
        assert metrics.mean_latency_ms == pytest.approx(15.0)

    def test_format_latency_string_with_value(self):
        """Format latency string with a numeric value."""
        # Simulate the formatting logic from _print_per_query_details
        latency_ms = 15.47
        latency_str = f"{latency_ms:.2f}" if latency_ms is not None else "N/A"
        assert latency_str == "15.47"

    def test_format_latency_string_with_none(self):
        """Format latency string with None value."""
        latency_ms = None
        latency_str = f"{latency_ms:.2f}" if latency_ms is not None else "N/A"
        assert latency_str == "N/A"
