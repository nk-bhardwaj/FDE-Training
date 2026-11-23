"""End-to-end RAG answer evaluation.

Runs the live RAGPipelineService against the 10 Amazon policy evaluation questions.
Measures evidence phrase coverage, citation relevance, abstention rate, and
end-to-end latency. Read-only: no inserts, updates, deletes or migrations.
"""

import argparse
import asyncio
import os
import sys
import time
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass

from dotenv import load_dotenv

from app.core.logging import get_logger
from app.services.document_service import DocumentStoreError
from app.services.ingestion_service import LoadedDocument
from app.services.rag_pipeline_service import (
    RAGPipelineConfig,
    RAGPipelineService,
)
from scripts.evaluate_rag_retrieval import (
    EVALUATION_QUESTIONS,
    EvalQuestion,
    _resolve_expected_chunks,
)

try:
    import psycopg
    from pgvector.psycopg import register_vector_async
    from psycopg import AsyncConnection
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional for type-checking
    psycopg = None
    AsyncConnection = None
    dict_row = None
    register_vector_async = None

logger = get_logger(__name__)


def _get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise DocumentStoreError("DATABASE_URL is not configured")
    return dsn


async def _load_stored_chunks() -> list[LoadedDocument]:
    """Read stored chunks from the database (read-only) for evidence resolution."""
    if psycopg is None:
        raise RuntimeError("psycopg not installed")
    dsn = _get_dsn()
    conn = await AsyncConnection.connect(
        dsn,
        row_factory=dict_row,
        connect_timeout=10,
    )
    try:
        await register_vector_async(conn)
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT d.source_id, dc.chunk_index, dc.content
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                ORDER BY d.source_id, dc.chunk_index
                """
            )
            rows = await cur.fetchall()
    finally:
        await conn.close()

    return [
        LoadedDocument(
            source_id=row["source_id"],
            title=row["source_id"],
            content=row["content"],
            metadata={"chunk_index": row["chunk_index"]},
        )
        for row in rows
    ]


def _normalize_text(text: str) -> str:
    """Collapse whitespace and casefold for comparison."""
    return " ".join(text.casefold().split())


def evidence_phrase_coverage(answer: str, expected_evidence: Sequence[str]) -> bool:
    """Return True if at least one expected evidence phrase appears in the answer.

    Heuristic exact-phrase match after case/whitespace normalization.
    Does not establish factual faithfulness.
    """
    normalized_answer = _normalize_text(answer)
    return any(_normalize_text(phrase) in normalized_answer for phrase in expected_evidence)


@dataclass(frozen=True)
class CitationRelevance:
    """Citation relevance metrics for a single question."""

    total_citations: int
    expected_citations: int
    proportion_expected: float
    has_expected_citation: bool


def citation_evidence_relevance(
    citations: Sequence[tuple[str, int]],
    expected_chunks: AbstractSet[tuple[str, int]],
) -> CitationRelevance:
    """Compare returned citations against expected evidence-bearing chunks."""
    total = len(citations)
    if total == 0:
        return CitationRelevance(0, 0, 0.0, False)
    matched = sum(1 for citation in citations if citation in expected_chunks)
    proportion = matched / total
    return CitationRelevance(total, matched, proportion, matched > 0)


@dataclass(frozen=True)
class QuestionResult:
    """Per-question evaluation result."""

    question: str
    answer: str
    abstained: bool
    evidence_phrase_found: bool
    citation_relevance: CitationRelevance
    latency_ms: float
    error: str | None = None


@dataclass(frozen=True)
class AnswerEvalSummary:
    """Aggregate evaluation summary."""

    provider: str
    top_k: int
    total_questions: int
    evidence_phrase_coverage_rate: float
    abstention_rate: float
    mean_citation_precision: float
    fraction_with_expected_citation: float
    mean_latency_ms: float | None
    results: tuple[QuestionResult, ...]


def _aggregate_results(
    results: list[QuestionResult],
    provider: str,
    top_k: int,
) -> AnswerEvalSummary:
    """Compute aggregate metrics from per-question results."""
    total = len(results)
    if total == 0:
        return AnswerEvalSummary(
            provider=provider,
            top_k=top_k,
            total_questions=0,
            evidence_phrase_coverage_rate=0.0,
            abstention_rate=0.0,
            mean_citation_precision=0.0,
            fraction_with_expected_citation=0.0,
            mean_latency_ms=None,
            results=(),
        )

    coverage_rate = sum(1 for r in results if r.evidence_phrase_found) / total
    abstention_rate = sum(1 for r in results if r.abstained) / total
    mean_citation_precision = sum(r.citation_relevance.proportion_expected for r in results) / total
    fraction_with_expected = (
        sum(1 for r in results if r.citation_relevance.has_expected_citation) / total
    )
    successful_latencies = [r.latency_ms for r in results if r.error is None]
    mean_latency = (
        (sum(successful_latencies) / len(successful_latencies)) if successful_latencies else None
    )

    return AnswerEvalSummary(
        provider=provider,
        top_k=top_k,
        total_questions=total,
        evidence_phrase_coverage_rate=coverage_rate,
        abstention_rate=abstention_rate,
        mean_citation_precision=mean_citation_precision,
        fraction_with_expected_citation=fraction_with_expected,
        mean_latency_ms=mean_latency,
        results=tuple(results),
    )


async def _evaluate_question(
    pipeline: RAGPipelineService,
    eval_q: EvalQuestion,
    expected_chunks: AbstractSet[tuple[str, int]],
    provider: str,
    config: RAGPipelineConfig,
) -> QuestionResult:
    """Evaluate a single question through the full pipeline."""
    start = time.perf_counter()
    try:
        response = await pipeline.run(eval_q.question, provider, config=config)
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "service=rag_answer_eval question=%s status=failure reason=%s",
            _question_hash(eval_q.question),
            type(exc).__name__,
        )
        return QuestionResult(
            question=eval_q.question,
            answer="",
            abstained=False,
            evidence_phrase_found=False,
            citation_relevance=CitationRelevance(0, 0, 0.0, False),
            latency_ms=latency_ms,
            error=f"{type(exc).__name__}: {exc}",
        )

    latency_ms = (time.perf_counter() - start) * 1000
    answer_obj = response.answer
    citations = [(c.source_id, c.chunk_index) for c in answer_obj.citations]
    phrase_found = evidence_phrase_coverage(answer_obj.answer, eval_q.expected_evidence)
    relevance = citation_evidence_relevance(citations, expected_chunks)

    return QuestionResult(
        question=eval_q.question,
        answer=answer_obj.answer,
        abstained=answer_obj.abstained,
        evidence_phrase_found=phrase_found,
        citation_relevance=relevance,
        latency_ms=latency_ms,
        error=None,
    )


def _question_hash(question: str) -> str:
    import hashlib

    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:8]


async def evaluate_pipeline_answers(
    pipeline: RAGPipelineService,
    questions: Sequence[EvalQuestion],
    expected_chunks_list: Sequence[AbstractSet[tuple[str, int]]],
    provider: str,
    config: RAGPipelineConfig,
) -> AnswerEvalSummary:
    """Evaluate all questions through the pipeline."""
    results: list[QuestionResult] = []
    for eval_q, expected_chunks in zip(questions, expected_chunks_list, strict=False):
        results.append(
            await _evaluate_question(pipeline, eval_q, expected_chunks, provider, config)
        )
    return _aggregate_results(results, provider, config.retrieval_top_k)


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _print_per_question_table(summary: AnswerEvalSummary) -> None:
    header = (
        f"{'#':>2} | {'question':<45} | {'answer':<38} | "
        f"{'cov':>4} | {'abs':>4} | {'cit':>7} | {'prec':>6} | {'lat(ms)':>8}"
    )
    print(header)
    print("-" * len(header))
    for i, r in enumerate(summary.results, 1):
        if r.error:
            status = f"ERROR: {_truncate(r.error, 30)}"
            lat_str = f"{r.latency_ms:.2f}" if r.latency_ms is not None else "N/A"
            print(
                f"{i:>2} | {_truncate(r.question, 45):<45} | "
                f"{status:<38} | {'N/A':>4} | {'N/A':>4} | {'N/A':>7} | {'N/A':>6} | {lat_str:>8}"
            )
            continue

        answer = _truncate(r.answer, 38)
        cit_str = (
            f"{r.citation_relevance.expected_citations}/{r.citation_relevance.total_citations}"
        )
        lat_str = f"{r.latency_ms:.2f}" if r.latency_ms is not None else "N/A"
        print(
            f"{i:>2} | {_truncate(r.question, 45):<45} | "
            f"{answer:<38} | {int(r.evidence_phrase_found):>4} | {int(r.abstained):>4} | "
            f"{cit_str:>7} | {r.citation_relevance.proportion_expected:>6.2f} | {lat_str:>8}"
        )


def _print_summary_table(summary: AnswerEvalSummary) -> None:
    print("\n" + "=" * 100)
    print("AGGREGATE SUMMARY")
    print("=" * 100)
    print(
        f"Provider: {summary.provider}  |  Top-K: {summary.top_k}  |  Questions: {summary.total_questions}"
    )
    print("-" * 100)
    header = f"{'Metric':<40} | {'Value':>15}"
    print(header)
    print("-" * len(header))
    print(f"{'Evidence phrase coverage rate':<40} | {summary.evidence_phrase_coverage_rate:>15.3f}")
    print(f"{'Abstention rate':<40} | {summary.abstention_rate:>15.3f}")
    print(f"{'Mean citation precision':<40} | {summary.mean_citation_precision:>15.3f}")
    print(
        f"{'Fraction with >=1 expected citation':<40} | {summary.fraction_with_expected_citation:>15.3f}"
    )
    lat_str = f"{summary.mean_latency_ms:.2f}" if summary.mean_latency_ms is not None else "N/A"
    print(f"{'Mean latency (ms)':<40} | {lat_str:>15}")
    print("=" * 100)
    print("NOTE: Evidence phrase coverage is a heuristic, not a measure of factual faithfulness.")
    print("=" * 100)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate end-to-end RAG answer generation on Amazon policy documents."
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "groq"],
        default="openai",
        help="LLM provider (default: openai).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve (default: 5).",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.top_k <= 0:
        raise ValueError(f"--top-k must be positive, got {args.top_k}")


async def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = build_arg_parser().parse_args()

    _validate_args(args)

    load_dotenv()

    provider = args.provider
    top_k = args.top_k

    print("=" * 100)
    print("RAG ANSWER EVALUATION")
    print("=" * 100)
    print(f"Provider: {provider}  |  Top-K: {top_k}")
    print("Live pipeline evaluation requiring configured Gemini, Neon, and LLM credentials.")
    print("-" * 100)

    chunks = await _load_stored_chunks()
    print(f"Loaded {len(chunks)} stored chunks from database.")

    try:
        expected_chunks_list = _resolve_expected_chunks(EVALUATION_QUESTIONS, chunks)
    except ValueError as exc:
        print(f"\nERROR: {exc}\n")
        raise

    config = RAGPipelineConfig(retrieval_top_k=top_k)
    pipeline = RAGPipelineService()

    print(f"\nEvaluating {len(EVALUATION_QUESTIONS)} questions...\n")

    summary = await evaluate_pipeline_answers(
        pipeline, EVALUATION_QUESTIONS, expected_chunks_list, provider, config
    )

    _print_per_question_table(summary)
    _print_summary_table(summary)

    print("\n" + "=" * 100)
    print("EVALUATION COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.error("store=rag_answer_eval status=failure reason=runner_error error=%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
