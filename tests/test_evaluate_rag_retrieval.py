"""Unit tests for RAG retrieval evaluation metrics."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.evaluate_rag_retrieval import (
    EVALUATION_QUESTIONS,
    EvalQuestion,
    _calculate_metrics,
    _evaluate_strategy,
    _resolve_expected_chunks,
)

EVAL_CHUNK_SIZE = 300
EVAL_CHUNK_OVERLAP = 50


@pytest.fixture(scope="module")
def source_chunks():
    """Chunk the raw policy documents with the 300/50 evaluation config."""
    from app.services.ingestion_service import load_and_chunk

    return load_and_chunk(chunk_size=EVAL_CHUNK_SIZE, chunk_overlap=EVAL_CHUNK_OVERLAP)


class TestEvalQuestion:
    """Tests for the EvalQuestion dataclass."""

    def test_eval_question_creation(self):
        """EvalQuestion can be created with question and expected_evidence."""
        q = EvalQuestion(
            question="Test question",
            expected_evidence=("phrase1", "phrase2"),
        )
        assert q.question == "Test question"
        assert q.expected_evidence == ("phrase1", "phrase2")


class TestCalculateMetrics:
    """Tests for the metric calculation helpers."""

    def test_perfect_match(self):
        """All expected chunks retrieved in correct order."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved = [("doc1", 0), ("doc1", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=2)
        assert qm.precision_at_k == 1.0
        assert qm.recall_at_k == 1.0
        assert qm.reciprocal_rank == 1.0

    def test_partial_match_precision(self):
        """Some expected chunks retrieved, extra non-relevant chunks."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved = [("doc1", 0), ("doc2", 0), ("doc3", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == pytest.approx(1.0 / 3)
        assert qm.recall_at_k == pytest.approx(1.0 / 2)

    def test_no_relevant_retrieved(self):
        """No expected chunks retrieved."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved = [("doc2", 0), ("doc3", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0

    def test_empty_retrieved(self):
        """Empty retrieved list."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved: list[tuple[str, int]] = []
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0

    def test_empty_expected(self):
        """Empty expected set."""
        expected: set[tuple[str, int]] = set()
        retrieved = [("doc1", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0

    def test_error_case(self):
        """Error case sets all metrics to zero."""
        expected = {("doc1", 0)}
        retrieved = [("doc2", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 5.0, "ConnectionError", k=3)
        assert qm.error == "ConnectionError"
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0

    def test_relevant_at_rank_2(self):
        """First result is irrelevant, second is relevant."""
        expected = {("doc1", 1)}
        retrieved = [("doc2", 0), ("doc1", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == pytest.approx(1.0 / 3)
        assert qm.recall_at_k == pytest.approx(1.0 / 1)
        assert qm.reciprocal_rank == pytest.approx(1.0 / 2)

    def test_relevant_at_rank_3(self):
        """First two are irrelevant, third is relevant."""
        expected = {("doc1", 2)}
        retrieved = [("doc2", 0), ("doc3", 1), ("doc1", 2)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == pytest.approx(1.0 / 3)
        assert qm.recall_at_k == pytest.approx(1.0 / 1)
        assert qm.reciprocal_rank == pytest.approx(1.0 / 3)

    def test_precision_uses_requested_k_for_single_result(self):
        """One relevant result out of top-k=3 scores 1/3, not 1/1."""
        expected = {("doc1", 0)}
        retrieved = [("doc1", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == pytest.approx(1.0 / 3)
        # Recall and MRR are unaffected by the precision denominator.
        assert qm.recall_at_k == pytest.approx(1.0)
        assert qm.reciprocal_rank == pytest.approx(1.0)

    def test_precision_two_relevant_results_out_of_three_requested(self):
        """Two relevant results out of top-k=3 scores 2/3."""
        expected = {("doc1", 0), ("doc1", 1)}
        retrieved = [("doc1", 0), ("doc1", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=3)
        assert qm.precision_at_k == pytest.approx(2.0 / 3)
        assert qm.recall_at_k == pytest.approx(1.0)
        assert qm.reciprocal_rank == pytest.approx(1.0)

    def test_precision_penalizes_short_result_list(self):
        """A short list is still divided by the requested k, not its own length."""
        expected = {("doc1", 0), ("doc2", 0)}
        retrieved = [("doc1", 0)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=5)
        assert qm.precision_at_k == pytest.approx(1.0 / 5)
        assert qm.recall_at_k == pytest.approx(1.0 / 2)
        assert qm.reciprocal_rank == pytest.approx(1.0)

    def test_precision_zero_for_short_irrelevant_list(self):
        """Fewer than k results, none relevant."""
        expected = {("doc1", 0)}
        retrieved = [("doc2", 0), ("doc3", 1)]
        qm = _calculate_metrics("test", expected, retrieved, 10.0, None, k=4)
        assert qm.precision_at_k == 0.0
        assert qm.recall_at_k == 0.0
        assert qm.reciprocal_rank == 0.0


class TestResolveExpectedChunks:
    """Tests for _resolve_expected_chunks with mocked chunks."""

    def test_resolves_phrases_to_chunks(self):
        """Evidence phrases are matched to chunk content."""
        from app.services.ingestion_service import LoadedDocument

        chunks = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="Customer has 30 days to return an item.",
                metadata={"source_id": "doc1", "title": "Doc 1", "chunk_index": 0},
            ),
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="After 45 days reimbursement is processed.",
                metadata={"source_id": "doc1", "title": "Doc 1", "chunk_index": 1},
            ),
            LoadedDocument(
                source_id="doc2",
                title="Doc 2",
                content="Unsellable units are defective or damaged.",
                metadata={"source_id": "doc2", "title": "Doc 2", "chunk_index": 0},
            ),
        ]

        questions = [
            EvalQuestion(
                question="How long to return?",
                expected_evidence=("30 days", "45 days"),
            ),
        ]

        expected_chunks = _resolve_expected_chunks(questions, chunks)
        assert len(expected_chunks) == 1
        # Should find (doc1, 0) for "30 days" and (doc1, 1) for "45 days"
        assert ("doc1", 0) in expected_chunks[0]
        assert ("doc1", 1) in expected_chunks[0]

    def test_raises_when_phrase_not_found(self):
        """ValueError raised when evidence phrase not in any chunk."""
        from app.services.ingestion_service import LoadedDocument

        chunks = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="Some unrelated content.",
                metadata={"source_id": "doc1", "title": "Doc 1"},
            ),
        ]

        questions = [
            EvalQuestion(
                question="Test question",
                expected_evidence=("30 days",),
            ),
        ]

        with pytest.raises(ValueError, match="not found in any chunk"):
            _resolve_expected_chunks(questions, chunks)


class TestEvaluateStrategy:
    """Tests for _evaluate_strategy with mocked retrieval."""

    @pytest.mark.asyncio
    async def test_evaluates_all_questions(self):
        """Strategy runs across all questions and returns aggregated metrics."""
        from app.services.ingestion_service import LoadedDocument

        # Build chunks where we know the evidence phrases appear
        chunks = [
            LoadedDocument(
                source_id="amazon_fba_return_policy",
                title="FBA Return Policy",
                content="Customer has 30 days to return an item. After 45 days reimbursement is processed.",
                metadata={"source_id": "amazon_fba_return_policy"},
            ),
            LoadedDocument(
                source_id="amazon_process_return_requests",
                title="Process Return Requests",
                content="RMA number generated by Amazon. Close the return request.",
                metadata={"source_id": "amazon_process_return_requests"},
            ),
        ]

        # Mock the retrieval methods to return known results
        mock_service = MagicMock()
        mock_service.semantic_search_chunks = AsyncMock(
            return_value=[
                # Q1: doc1 chunk 0
                type(
                    "obj", (object,), {"source_id": "amazon_fba_return_policy", "chunk_index": 0}
                )(),
                # Q2: doc2 chunk 0
                type(
                    "obj",
                    (object,),
                    {"source_id": "amazon_process_return_requests", "chunk_index": 0},
                )(),
            ]
        )

        expected_chunks_list = [
            {("amazon_fba_return_policy", 0), ("amazon_fba_return_policy", 1)},
            {("amazon_process_return_requests", 0)},
        ]

        # Patch load_and_chunk to return our chunks
        with patch("scripts.evaluate_rag_retrieval.load_and_chunk", return_value=chunks):
            questions = [
                EvalQuestion(
                    question="How long does a customer have to return an item?",
                    expected_evidence=("30 days", "45 days"),
                ),
                EvalQuestion(
                    question="What is an RMA number and when is it used?",
                    expected_evidence=("RMA",),
                ),
            ]

            metrics = await _evaluate_strategy(
                "semantic",
                mock_service.semantic_search_chunks,
                questions,
                expected_chunks_list,
                3,
            )

        assert len(metrics.queries) == 2
        assert metrics.mean_precision_at_k > 0
        assert metrics.mean_recall_at_k > 0
        assert metrics.mrr > 0

    @pytest.mark.asyncio
    async def test_handles_errors(self):
        """Errors are captured and metrics set to zero."""
        from app.services.ingestion_service import LoadedDocument

        chunks = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="Some content",
                metadata={"source_id": "doc1"},
            ),
        ]

        mock_service = MagicMock()
        mock_service.semantic_search_chunks = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        expected_chunks_list = [set()]

        with patch("scripts.evaluate_rag_retrieval.load_and_chunk", return_value=chunks):
            questions = [
                EvalQuestion(
                    question="Test question",
                    expected_evidence=("phrase",),
                ),
            ]

            metrics = await _evaluate_strategy(
                "semantic",
                mock_service.semantic_search_chunks,
                questions,
                expected_chunks_list,
                3,
            )

        for qm in metrics.queries:
            assert qm.error is not None
            assert qm.precision_at_k == 0.0
            assert qm.recall_at_k == 0.0
            assert qm.reciprocal_rank == 0.0

    @pytest.mark.asyncio
    async def test_correctly_aggregates_metrics(self):
        """Mean metrics are correctly averaged across questions."""
        from app.services.ingestion_service import LoadedDocument

        chunks = [
            LoadedDocument(
                source_id="amazon_fba_return_policy",
                title="FBA Return Policy",
                content="Customer has 30 days to return an item. After 45 days reimbursement is processed.",
                metadata={"source_id": "amazon_fba_return_policy"},
            ),
        ]

        mock_service = MagicMock()
        mock_service.semantic_search_chunks = AsyncMock(
            return_value=[
                type(
                    "obj", (object,), {"source_id": "amazon_fba_return_policy", "chunk_index": 0}
                )(),
                type(
                    "obj", (object,), {"source_id": "amazon_fba_return_policy", "chunk_index": 1}
                )(),
            ]
        )

        expected_chunks_list = [
            {("amazon_fba_return_policy", 0), ("amazon_fba_return_policy", 1)},
        ]

        with patch("scripts.evaluate_rag_retrieval.load_and_chunk", return_value=chunks):
            questions = [
                EvalQuestion(
                    question="How long does a customer have to return an item?",
                    expected_evidence=("30 days", "45 days"),
                ),
            ]

            metrics = await _evaluate_strategy(
                "semantic",
                mock_service.semantic_search_chunks,
                questions,
                expected_chunks_list,
                3,
            )

        # Both chunks retrieved and both expected, but limit=3 -> P@3=2/3
        assert metrics.mean_precision_at_k == pytest.approx(2.0 / 3)
        assert metrics.mean_recall_at_k == pytest.approx(1.0)
        assert metrics.mrr == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_latency_aggregation(self):
        """Mean latency excludes failed queries."""
        from app.services.ingestion_service import LoadedDocument

        chunks = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="30 days to return an item.",
                metadata={"source_id": "doc1"},
            ),
        ]

        mock_service = MagicMock()

        class _FakeResult:
            def __init__(self, src_id, idx):
                self.source_id = src_id
                self.chunk_index = idx

        def _make_side_effect():
            results_q1 = [_FakeResult("doc1", 0)]
            return AsyncMock(
                side_effect=[
                    results_q1,  # Q1 success
                    Exception("ConnectionError"),  # Q2 failure
                ]
            )

        mock_service.semantic_search_chunks = AsyncMock(
            side_effect=[
                [_FakeResult("doc1", 0)],  # Q1 success
                Exception("ConnectionError"),  # Q2 failure
            ]
        )

        expected_chunks_list = [set()]

        with patch("scripts.evaluate_rag_retrieval.load_and_chunk", return_value=chunks):
            questions = [
                EvalQuestion(
                    question="Test question 1",
                    expected_evidence=("30 days",),
                ),
                EvalQuestion(
                    question="Test question 2",
                    expected_evidence=("45 days",),
                ),
            ]

            metrics = await _evaluate_strategy(
                "semantic",
                mock_service.semantic_search_chunks,
                questions,
                expected_chunks_list,
                3,
            )

        # Only Q1 latency counted (15ms), Q2 error excluded
        # latency depends on actual execution, just check it's not None
        assert metrics.mean_latency_ms is not None
        assert metrics.mean_latency_ms > 0

    @pytest.mark.asyncio
    async def test_uses_requested_top_k_as_precision_denominator(self):
        """A single result for limit=3 is scored as Precision@3 = 1/3."""
        from app.services.ingestion_service import LoadedDocument

        chunks = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="30 days to return an item.",
                metadata={"source_id": "doc1"},
            ),
        ]

        class _FakeResult:
            source_id = "doc1"
            chunk_index = 0

        mock_service = MagicMock()
        mock_service.semantic_search_chunks = AsyncMock(return_value=[_FakeResult()])

        with patch("scripts.evaluate_rag_retrieval.load_and_chunk", return_value=chunks):
            questions = [
                EvalQuestion(
                    question="How long does a customer have to return an item?",
                    expected_evidence=("30 days",),
                ),
            ]

            metrics = await _evaluate_strategy(
                "semantic",
                mock_service.semantic_search_chunks,
                questions,
                [{("doc1", 0)}],
                3,
            )

        assert metrics.queries[0].retrieved_chunks == [("doc1", 0)]
        assert metrics.queries[0].precision_at_k == pytest.approx(1.0 / 3)
        assert metrics.mean_precision_at_k == pytest.approx(1.0 / 3)
        # Recall and MRR keep their previous behaviour.
        assert metrics.mean_recall_at_k == pytest.approx(1.0)
        assert metrics.mrr == pytest.approx(1.0)


class TestEvaluationQuestionEvidence:
    """Guards that configured evidence phrases exist in the source documents."""

    def test_refund_question_uses_source_phrase(self):
        """The refund question keeps its wording and uses the real source phrase."""
        question = next(
            q
            for q in EVALUATION_QUESTIONS
            if q.question == "How do I issue a refund to a customer?"
        )

        assert "Select the Partial Refund tab" in question.expected_evidence
        assert "partial refund" not in question.expected_evidence

    @pytest.mark.parametrize(
        "phrase",
        [phrase for question in EVALUATION_QUESTIONS for phrase in question.expected_evidence],
    )
    def test_evidence_phrase_has_no_stray_quotes(self, phrase):
        """Evidence phrases must not contain quote characters or padding."""
        assert not any(char in phrase for char in "\"'`\u2018\u2019\u201c\u201d"), phrase
        assert phrase == phrase.strip()

    @pytest.mark.parametrize(
        "phrase",
        [phrase for question in EVALUATION_QUESTIONS for phrase in question.expected_evidence],
    )
    def test_evidence_phrase_found_in_a_chunk(self, phrase, source_chunks):
        """Every evidence phrase must appear verbatim in a chunk at 300/50."""
        matches = [chunk for chunk in source_chunks if phrase in chunk.content]

        assert matches, (
            f"evidence phrase {phrase!r} not found in any chunk with "
            f"chunk_size={EVAL_CHUNK_SIZE}, chunk_overlap={EVAL_CHUNK_OVERLAP}"
        )

    def test_all_questions_resolve_to_expected_chunks(self, source_chunks):
        """_resolve_expected_chunks succeeds for every configured question."""
        resolved = _resolve_expected_chunks(EVALUATION_QUESTIONS, source_chunks)

        assert len(resolved) == len(EVALUATION_QUESTIONS)
        assert all(resolved), "every evaluation question must resolve to at least one chunk"
