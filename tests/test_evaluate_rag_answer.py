"""Unit tests for end-to-end RAG answer evaluation metrics and orchestration.

All LLM, embedding, and database calls are mocked. No provider or database is used.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.rag_answer import Citation, RAGAnswerResponse
from app.services.context_engineering_service import AssembledContext
from app.services.rag_pipeline_service import RAGPipelineConfig, RAGPipelineResponse
from scripts.evaluate_rag_answer import (
    CitationRelevance,
    QuestionResult,
    _aggregate_results,
    _evaluate_question,
    _validate_args,
    build_arg_parser,
    citation_evidence_relevance,
    evaluate_pipeline_answers,
    evidence_phrase_coverage,
)
from scripts.evaluate_rag_retrieval import EvalQuestion

PROVIDER = "openai"


def _response(answer="Refunds take 30 days.", abstained=False, citations=None):
    """Build a RAGPipelineResponse with the given parameters.

    When ``abstained`` is True the answer is replaced with the canonical
    abstention message to avoid coincidental phrase matches.
    """
    if abstained:
        answer = "I don't know based on the available information."
    citation_objs = [
        Citation(source_id=s, document_title="Doc", chunk_index=i) for s, i in (citations or [])
    ]
    answer_obj = RAGAnswerResponse(
        question="q",
        answer=answer,
        citations=citation_objs,
        abstained=abstained,
        provider=PROVIDER,
        model="gpt-4o-mini",
        latency_ms=1.0,
        usage=None,
        attempts=1,
        context_chunks=1,
        context_tokens=10,
    )
    return RAGPipelineResponse(
        answer=answer_obj,
        assembled_context=AssembledContext(
            chunks=(),
            total_tokens=0,
            max_tokens=2000,
            truncated=False,
            duplicates_removed=0,
            sources=(),
        ),
        reranked_chunks=(),
        raw_retrieval_chunks=(),
        config_used=RAGPipelineConfig(),
    )


def _question(text="How long does a customer have to return an item?", evidence=("30 days",)):
    return EvalQuestion(question=text, expected_evidence=evidence)


class TestEvidencePhraseCoverage:
    def test_phrase_found(self):
        assert evidence_phrase_coverage("Refunds take 30 days.", ("30 days",)) is True

    def test_phrase_absent(self):
        assert evidence_phrase_coverage("No relevant information.", ("30 days",)) is False

    def test_case_insensitive(self):
        assert evidence_phrase_coverage("REFUNDS Take 30 DAYS.", ("30 days",)) is True

    def test_whitespace_normalized(self):
        assert evidence_phrase_coverage("Refunds take   30   days.", ("30 days",)) is True

    def test_empty_answer(self):
        assert evidence_phrase_coverage("", ("30 days",)) is False

    def test_empty_expected_evidence(self):
        assert evidence_phrase_coverage("some answer", ()) is False

    def test_any_phrase_matches(self):
        assert (
            evidence_phrase_coverage("Reimbursement after 45 days.", ("30 days", "45 days")) is True
        )


class TestCitationEvidenceRelevance:
    def test_citation_matches_expected_chunk(self):
        result = citation_evidence_relevance([("doc1", 0)], {("doc1", 0)})
        assert result.total_citations == 1
        assert result.expected_citations == 1
        assert result.proportion_expected == 1.0
        assert result.has_expected_citation is True

    def test_citation_non_evidence_chunk(self):
        result = citation_evidence_relevance([("doc9", 0)], {("doc1", 0)})
        assert result.total_citations == 1
        assert result.expected_citations == 0
        assert result.proportion_expected == 0.0
        assert result.has_expected_citation is False

    def test_multiple_citations_mixed_relevance(self):
        result = citation_evidence_relevance(
            [("doc1", 0), ("doc9", 0), ("doc1", 1)], {("doc1", 0), ("doc1", 1)}
        )
        assert result.total_citations == 3
        assert result.expected_citations == 2
        assert result.proportion_expected == pytest.approx(2.0 / 3)
        assert result.has_expected_citation is True

    def test_empty_citations(self):
        result = citation_evidence_relevance([], {("doc1", 0)})
        assert result.total_citations == 0
        assert result.expected_citations == 0
        assert result.proportion_expected == 0.0
        assert result.has_expected_citation is False

    def test_empty_expected_with_citations(self):
        result = citation_evidence_relevance([("doc1", 0)], set())
        assert result.total_citations == 1
        assert result.expected_citations == 0
        assert result.proportion_expected == 0.0
        assert result.has_expected_citation is False


class TestAggregateResults:
    def test_aggregate_metrics(self):
        results = [
            QuestionResult(
                question="q1",
                answer="a",
                abstained=False,
                evidence_phrase_found=True,
                citation_relevance=CitationRelevance(2, 1, 0.5, True),
                latency_ms=10.0,
            ),
            QuestionResult(
                question="q2",
                answer="a",
                abstained=True,
                evidence_phrase_found=False,
                citation_relevance=CitationRelevance(0, 0, 0.0, False),
                latency_ms=20.0,
            ),
            QuestionResult(
                question="q3",
                answer="a",
                abstained=False,
                evidence_phrase_found=True,
                citation_relevance=CitationRelevance(1, 1, 1.0, True),
                latency_ms=30.0,
            ),
        ]
        summary = _aggregate_results(results, PROVIDER, 3)
        assert summary.total_questions == 3
        assert summary.evidence_phrase_coverage_rate == pytest.approx(2.0 / 3)
        assert summary.abstention_rate == pytest.approx(1.0 / 3)
        assert summary.mean_citation_precision == pytest.approx((0.5 + 0.0 + 1.0) / 3)
        assert summary.fraction_with_expected_citation == pytest.approx(2.0 / 3)
        assert summary.mean_latency_ms == pytest.approx(20.0)

    def test_zero_questions(self):
        summary = _aggregate_results([], PROVIDER, 5)
        assert summary.total_questions == 0
        assert summary.evidence_phrase_coverage_rate == 0.0
        assert summary.abstention_rate == 0.0
        assert summary.mean_citation_precision == 0.0
        assert summary.fraction_with_expected_citation == 0.0
        assert summary.mean_latency_ms is None
        assert summary.results == ()


class TestEvaluateQuestion:
    @pytest.mark.asyncio
    async def test_success_populates_result_fields(self):
        pipeline = SimpleNamespace(run=AsyncMock(return_value=_response(abstained=False)))
        config = RAGPipelineConfig(retrieval_top_k=3)
        result = await _evaluate_question(pipeline, _question(), {("doc1", 0)}, PROVIDER, config)

        pipeline.run.assert_awaited_once_with(_question().question, PROVIDER, config=config)
        assert result.question == _question().question
        assert result.answer == "Refunds take 30 days."
        assert result.abstained is False
        assert result.evidence_phrase_found is True
        assert result.citation_relevance.total_citations == 0
        assert result.latency_ms >= 0.0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_abstention_records_no_citations(self):
        pipeline = SimpleNamespace(
            run=AsyncMock(return_value=_response(abstained=True, citations=[]))
        )
        result = await _evaluate_question(
            pipeline, _question(), {("doc1", 0)}, PROVIDER, RAGPipelineConfig()
        )
        assert result.abstained is True
        assert result.evidence_phrase_found is False
        assert result.citation_relevance.has_expected_citation is False

    @pytest.mark.asyncio
    async def test_citations_compared_against_expected_chunks(self):
        pipeline = SimpleNamespace(
            run=AsyncMock(return_value=_response(citations=[("doc1", 0), ("doc9", 5)]))
        )
        result = await _evaluate_question(
            pipeline, _question(), {("doc1", 0), ("doc2", 1)}, PROVIDER, RAGPipelineConfig()
        )
        assert result.citation_relevance.total_citations == 2
        assert result.citation_relevance.expected_citations == 1
        assert result.citation_relevance.proportion_expected == pytest.approx(0.5)
        assert result.citation_relevance.has_expected_citation is True

    @pytest.mark.asyncio
    async def test_pipeline_error_recorded(self):
        async def _fails(*args, **kwargs):
            raise ValueError("boom")

        pipeline = SimpleNamespace(run=_fails)
        result = await _evaluate_question(
            pipeline, _question(), {("doc1", 0)}, PROVIDER, RAGPipelineConfig()
        )
        assert result.error == "ValueError: boom"
        assert result.evidence_phrase_found is False
        assert result.abstained is False
        assert result.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_latency_measured_around_run(self):
        async def _slow(*args, **kwargs):
            await asyncio.sleep(0.02)
            return _response()

        pipeline = SimpleNamespace(run=_slow)
        result = await _evaluate_question(
            pipeline, _question(), {("doc1", 0)}, PROVIDER, RAGPipelineConfig()
        )
        # Wall-clock wrapping must capture the sleep (>= ~15 ms, allow tolerance).
        assert result.latency_ms >= 15.0


class TestEvaluatePipelineAnswers:
    @pytest.mark.asyncio
    async def test_runs_all_questions_and_aggregates(self):
        async def _run(question, provider, *, config=None):
            if "refund" in question.lower():
                return _response(answer="Refunds take 30 days.", citations=[("doc1", 0)])
            return _response(answer="Unknown.", abstained=True, citations=[])

        pipeline = SimpleNamespace(run=AsyncMock(side_effect=_run))
        config = RAGPipelineConfig(retrieval_top_k=3)
        questions = [
            _question("How do I issue a refund to a customer?", ("refund",)),
            _question("How long does a customer have to return an item?", ("30 days",)),
        ]
        expected = [{("doc1", 0)}, {("doc1", 0)}]

        summary = await evaluate_pipeline_answers(pipeline, questions, expected, PROVIDER, config)

        assert pipeline.run.await_count == 2
        assert summary.total_questions == 2
        assert summary.evidence_phrase_coverage_rate == pytest.approx(0.5)
        assert summary.abstention_rate == pytest.approx(0.5)
        assert summary.mean_latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_zero_questions(self):
        summary = await evaluate_pipeline_answers(
            SimpleNamespace(run=AsyncMock()), [], [], PROVIDER, RAGPipelineConfig()
        )
        assert summary.total_questions == 0
        assert summary.mean_latency_ms is None


class TestCLI:
    def test_defaults(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.provider == "openai"
        assert args.top_k == 5

    def test_explicit_values(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--provider", "groq", "--top-k", "3"])
        assert args.provider == "groq"
        assert args.top_k == 3

    def test_invalid_provider_exits(self):
        parser = build_arg_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--provider", "badprovider"])

    def test_validate_negative_top_k_raises(self):
        args = SimpleNamespace(top_k=-1)
        with pytest.raises(ValueError, match="top-k"):
            _validate_args(args)

    def test_validate_zero_top_k_raises(self):
        args = SimpleNamespace(top_k=0)
        with pytest.raises(ValueError, match="top-k"):
            _validate_args(args)
