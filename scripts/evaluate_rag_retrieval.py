"""Evaluate RAG retrieval on the three Amazon policy documents.

Runs semantic, keyword, and hybrid retrieval against the configured Neon
database using real Gemini embeddings. Reports Precision@k, Recall@k,
and MRR for each strategy with per-query results and latency.

Read-only: no inserts, updates, deletes or migrations.
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.core.logging import get_logger
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import load_and_chunk
from app.services.rag_retrieval_service import RAGRetrievalService

load_dotenv(Path(".env"))

logger = get_logger(__name__)


@dataclass(frozen=True)
class EvalQuestion:
    """An evaluation question with expected evidence phrases."""

    question: str
    expected_evidence: tuple[str, ...]  # phrases that should appear in relevant chunks


# 10 realistic questions derived from the three Amazon policy documents.
# Expected evidence phrases reference key concepts; chunk assignment is resolved
# at runtime from the actual chunk content so it works with any chunk_size/chunk_overlap.
EVALUATION_QUESTIONS: list[EvalQuestion] = [
    EvalQuestion(
        question="How long does a customer have to return an item?",
        expected_evidence=("30 days", "45 days"),
    ),
    EvalQuestion(
        question="What makes a returned unit unsellable?",
        expected_evidence=("unsellable", "defective", "damaged"),
    ),
    EvalQuestion(
        question="When does Amazon reimburse sellers for returned items?",
        expected_evidence=("45 days", "reimbursement"),
    ),
    EvalQuestion(
        question="How do I issue a refund to a customer?",
        expected_evidence=("refund", "full refund", "Select the Partial Refund tab"),
    ),
    EvalQuestion(
        question="What is an RMA number and when is it used?",
        expected_evidence=("RMA", "Return Merchandise Authorisation"),
    ),
    EvalQuestion(
        question="How do I close a return request?",
        expected_evidence=("close", "return request"),
    ),
    EvalQuestion(
        question="How do I contact a buyer about a return?",
        expected_evidence=("Contact buyer", "email"),
    ),
    EvalQuestion(
        question="Are return labels prepaid for seller-fulfilled returns?",
        expected_evidence=("prepaid", "return label"),
    ),
    EvalQuestion(
        question="How quickly must I respond to a return request?",
        expected_evidence=("24 hours", "respond"),
    ),
    EvalQuestion(
        question="How are FBA order returns handled?",
        expected_evidence=("Fulfilment by Amazon", "FBA"),
    ),
]


@dataclass
class QueryMetrics:
    """Per-query metrics for one strategy."""

    question: str
    retrieved_chunks: list[tuple[str, int]]  # (source_id, chunk_index)
    expected_chunks: set[tuple[str, int]]
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    latency_ms: float | None
    error: str | None = None


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all queries for one strategy."""

    strategy_name: str
    mean_precision_at_k: float
    mean_recall_at_k: float
    mrr: float
    mean_latency_ms: float | None
    queries: list[QueryMetrics]


def _truncate(text: str, width: int) -> str:
    """Truncate text to width characters, appending ellipsis when needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


async def _run_strategy(
    strategy_name: str,
    method,
    query: str,
    limit: int,
) -> tuple[list[tuple[str, int]], float | None, str | None]:
    """Run a retrieval strategy, returning (retrieved_chunks, latency_ms, error)."""
    start = time.perf_counter()
    try:
        results = await method(query, limit=limit)
        latency_ms = (time.perf_counter() - start) * 1000
        retrieved = [(r.source_id, r.chunk_index) for r in results]
        return retrieved, latency_ms, None
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "eval=rag_retrieval status=failure strategy=%s latency_ms=%.2f reason=%s",
            strategy_name,
            latency_ms,
            type(exc).__name__,
        )
        return [], None, f"{type(exc).__name__}: {exc}"


def _calculate_metrics(
    query: str,
    expected: set[tuple[str, int]],
    retrieved: list[tuple[str, int]],
    latency_ms: float | None,
    error: str | None,
    *,
    k: int,
) -> QueryMetrics:
    """Calculate Precision@k, Recall@k, and RR for a single query.

    ``k`` is the requested top-k for the run and is always the Precision@k
    denominator, even when fewer than ``k`` results are retrieved.
    """
    if error:
        return QueryMetrics(
            question=query,
            retrieved_chunks=retrieved,
            expected_chunks=expected,
            precision_at_k=0.0,
            recall_at_k=0.0,
            reciprocal_rank=0.0,
            latency_ms=latency_ms,
            error=error,
        )

    retrieved_set = set(retrieved)
    relevant_retrieved = retrieved_set & expected

    # Precision@k = |relevant retrieved| / k (k = requested top-k, not the
    # number of results actually returned, so short result lists are penalized)
    precision = len(relevant_retrieved) / k if k > 0 else 0.0

    # Recall@k = |relevant retrieved| / |expected|
    recall = len(relevant_retrieved) / len(expected) if expected else 0.0

    # Reciprocal Rank: 1 / rank of first relevant result (1-indexed), 0 if none
    rr = 0.0
    for rank, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in expected:
            rr = 1.0 / rank
            break

    return QueryMetrics(
        question=query,
        retrieved_chunks=retrieved,
        expected_chunks=expected,
        precision_at_k=precision,
        recall_at_k=recall,
        reciprocal_rank=rr,
        latency_ms=latency_ms,
        error=None,
    )


def _resolve_expected_chunks(
    questions: list[EvalQuestion],
    chunks: list,
) -> list[set[tuple[str, int]]]:
    """Resolve evidence phrases to (source_id, chunk_index) at runtime.

    After ``load_and_chunk()``, scans each chunk's content for the expected
    evidence phrases.  If any phrase is not found in any chunk for a given
    source_id, raises ``ValueError`` so the caller knows the configuration
    does not produce the expected evidence.

    Returns a list of ``set[tuple[str, int]]`` one per question, each
    containing the (source_id, chunk_index) pairs that match the expected
    evidence for that question.
    """
    # Build a map: source_id -> list of (chunk_index, content)
    src_chunks: dict[str, list[tuple[int, str]]] = {}
    for chunk in chunks:
        chunk_index = chunk.metadata.get("chunk_index", 0) if chunk.metadata else 0
        src_chunks.setdefault(chunk.source_id, []).append((chunk_index, chunk.content))

    results: list[set[tuple[str, int]]] = []
    for q in questions:
        expected_chunks: set[tuple[str, int]] = set()
        for phrase in q.expected_evidence:
            found = False
            for src_id, chunk_list in src_chunks.items():
                for idx, content in chunk_list:
                    if phrase in content:
                        expected_chunks.add((src_id, idx))
                        found = True
                        break
                if found:
                    break
            if not found:
                raise ValueError(
                    f"Evaluation error: evidence phrase '{phrase!r}' not found in "
                    f"any chunk for question '{q.question}'.  This may be because "
                    f"the chunk_size/chunk_overlap configuration changed the chunk "
                    f"boundaries.  Consider adjusting the evidence phrases or "
                    f"chunking parameters."
                )
        results.append(expected_chunks)
    return results


async def _evaluate_strategy(
    strategy_name: str,
    method,
    questions: list[EvalQuestion],
    expected_chunks_list: list[set[tuple[str, int]]],
    limit: int,
) -> AggregateMetrics:
    """Evaluate one retrieval strategy across all questions."""
    query_metrics: list[QueryMetrics] = []
    latencies: list[float] = []

    for eval_q, expected_chunks in zip(questions, expected_chunks_list, strict=False):
        retrieved, latency_ms, error = await _run_strategy(
            strategy_name, method, eval_q.question, limit
        )
        # Only count latency for successful queries (no error)
        if latency_ms is not None and error is None:
            latencies.append(latency_ms)
        metrics = _calculate_metrics(
            eval_q.question, expected_chunks, retrieved, latency_ms, error, k=limit
        )
        query_metrics.append(metrics)

    mean_precision = sum(m.precision_at_k for m in query_metrics) / len(query_metrics)
    mean_recall = sum(m.recall_at_k for m in query_metrics) / len(query_metrics)
    mrr = sum(m.reciprocal_rank for m in query_metrics) / len(query_metrics)
    mean_latency = sum(latencies) / len(latencies) if latencies else None

    return AggregateMetrics(
        strategy_name=strategy_name,
        mean_precision_at_k=mean_precision,
        mean_recall_at_k=mean_recall,
        mrr=mrr,
        mean_latency_ms=mean_latency,
        queries=query_metrics,
    )


def _print_per_query_table(metrics: AggregateMetrics) -> None:
    """Print per-query results table."""
    header = (
        f"{'#':>2} | {'question':<45} | {'retrieved (src,idx)':<30} | "
        f"{'P@k':>5} | {'R@k':>5} | {'RR':>5} | {'latency (ms)':>12}"
    )
    print(header)
    print("-" * len(header))

    for i, qm in enumerate(metrics.queries, 1):
        if qm.error:
            status = f"ERROR: {_truncate(qm.error, 30)}"
            print(
                f"{i:>2} | {_truncate(qm.question, 45):<45} | "
                f"{status:<30} | {'N/A':>5} | {'N/A':>5} | {'N/A':>5} | "
                f"{(qm.latency_ms or 0.0):>11.2f}"
            )
            continue

        retrieved_str = ", ".join(f"({_truncate(s, 8)},{idx})" for s, idx in qm.retrieved_chunks)
        if not retrieved_str:
            retrieved_str = "none"

        lat_str = f"{qm.latency_ms:.2f}" if qm.latency_ms is not None else "N/A"
        print(
            f"{i:>2} | {_truncate(qm.question, 45):<45} | "
            f"{_truncate(retrieved_str, 30):<30} | "
            f"{qm.precision_at_k:>5.2f} | {qm.recall_at_k:>5.2f} | "
            f"{qm.reciprocal_rank:>5.2f} | {lat_str:>12}"
        )


def _print_summary_table(all_metrics: list[AggregateMetrics]) -> None:
    """Print aggregate summary table."""
    print("\n" + "=" * 100)
    print("AGGREGATE SUMMARY")
    print("=" * 100)
    header = (
        f"{'Strategy':<18} | {'Mean P@k':>9} | {'Mean R@k':>9} | {'MRR':>7} | "
        f"{'Mean Latency (ms)':>18}"
    )
    print(header)
    print("-" * len(header))
    for m in all_metrics:
        lat_str = f"{m.mean_latency_ms:.2f}" if m.mean_latency_ms is not None else "N/A"
        print(
            f"{m.strategy_name:<18} | {m.mean_precision_at_k:>9.3f} | "
            f"{m.mean_recall_at_k:>9.3f} | {m.mrr:>7.3f} | {lat_str:>18}"
        )


def _print_per_query_details(all_metrics: list[AggregateMetrics]) -> None:
    """Print detailed per-query results including expected vs retrieved."""
    print("\n" + "=" * 100)
    print("PER-QUERY DETAILS")
    print("=" * 100)
    for m in all_metrics:
        print(f"\n--- {m.strategy_name} ---")
        for i, qm in enumerate(m.queries, 1):
            print(f"  Q{i}: {qm.question}")
            print(f"    Expected: {sorted(qm.expected_chunks)}")
            print(f"    Retrieved: {qm.retrieved_chunks}")
            if qm.error:
                print(f"    ERROR: {qm.error}")
            latency_str = f"{qm.latency_ms:.2f}" if qm.latency_ms is not None else "N/A"
            print(
                f"    P@k={qm.precision_at_k:.3f} R@k={qm.recall_at_k:.3f} RR={qm.reciprocal_rank:.3f} "
                f"lat={latency_str} ms"
            )


def _print_chunking_config(
    chunk_size: int, chunk_overlap: int, top_k: int, source_ids: list[str], total_chunks: int
) -> None:
    """Print the chunking configuration and summary stats."""
    print("=" * 100)
    print("RAG RETRIEVAL EVALUATION")
    print("=" * 100)
    print(
        f"Documents: {len(source_ids)}  |  Total chunks: {total_chunks}  |  "
        f"Config: chunk_size={chunk_size}, overlap={chunk_overlap}  |  Top-K: {top_k}"
    )
    print(f"Sources: {source_ids}")
    print("-" * 100)


async def main() -> None:
    """Run RAG retrieval evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate RAG retrieval on Amazon policy documents."
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Maximum tokens per chunk (default: 500).",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=75,
        help="Overlap tokens between chunks (default: 75).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Return top-k results per query (default: 3).",
    )
    args = parser.parse_args()

    chunk_size = args.chunk_size
    chunk_overlap = args.chunk_overlap
    top_k = args.top_k

    # Validate parameters
    if chunk_size <= 0:
        raise ValueError(f"--chunk-size must be positive, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"--chunk-overlap must be non-negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"--chunk-overlap ({chunk_overlap}) must be smaller than --chunk-size ({chunk_size})"
        )
    if top_k <= 0:
        raise ValueError(f"--top-k must be positive, got {top_k}")

    # Initialize services
    embedding_service = EmbeddingService()
    rag_service = RAGRetrievalService(embedding_service=embedding_service)

    # Load chunks using the selected configuration
    chunks = load_and_chunk(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    total_chunks = len(chunks)
    source_ids = sorted({c.source_id for c in chunks})

    # Resolve expected chunks from evidence phrases
    try:
        expected_chunks_list = _resolve_expected_chunks(EVALUATION_QUESTIONS, chunks)
    except ValueError as exc:
        print(f"\nERROR: {exc}\n")
        raise

    # Print chunking config and summary
    _print_chunking_config(chunk_size, chunk_overlap, top_k, source_ids, total_chunks)

    # Evaluate all three strategies
    print(f"\nEvaluating {len(EVALUATION_QUESTIONS)} questions...\n")

    all_metrics: list[AggregateMetrics] = []

    # Semantic search
    print("Running semantic_search_chunks...")
    semantic_metrics = await _evaluate_strategy(
        "semantic",
        rag_service.semantic_search_chunks,
        EVALUATION_QUESTIONS,
        expected_chunks_list,
        top_k,
    )
    all_metrics.append(semantic_metrics)
    print("Done.\n")

    # Keyword search
    print("Running keyword_search_chunks...")
    keyword_metrics = await _evaluate_strategy(
        "keyword",
        rag_service.keyword_search_chunks,
        EVALUATION_QUESTIONS,
        expected_chunks_list,
        top_k,
    )
    all_metrics.append(keyword_metrics)
    print("Done.\n")

    # Hybrid search
    print("Running hybrid_search_chunks...")
    hybrid_metrics = await _evaluate_strategy(
        "hybrid",
        rag_service.hybrid_search_chunks,
        EVALUATION_QUESTIONS,
        expected_chunks_list,
        top_k,
    )
    all_metrics.append(hybrid_metrics)
    print("Done.\n")

    # Print results
    _print_per_query_table(all_metrics[0])
    print()
    _print_per_query_table(all_metrics[1])
    print()
    _print_per_query_table(all_metrics[2])

    _print_summary_table(all_metrics)
    _print_per_query_details(all_metrics)

    print("\n" + "=" * 100)
    print("EVALUATION COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
