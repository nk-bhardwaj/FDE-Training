"""Compare semantic search and keyword search implementations."""

import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from app.core.logging import get_logger
from app.services.document_service import DocumentService

load_dotenv(Path(".env"))

logger = get_logger(__name__)

# These queries match scripts/evaluate_semantic_search.py exactly.
EVALUATION_QUERIES: list[dict[str, str]] = [
    {
        "category": "order_tracking",
        "query": "I placed an order recently but cannot figure out whether it has shipped or how to follow its progress.",
    },
    {
        "category": "delivery_delays",
        "query": "My package was supposed to arrive on Friday but it's now Monday and still not here.",
    },
    {
        "category": "returns_refunds",
        "query": "I want to send back the shoes I bought because they don't fit. How long for the refund?",
    },
    {
        "category": "cancellations",
        "query": "I accidentally ordered the wrong item and need to cancel before it leaves the warehouse.",
    },
    {
        "category": "payment_failures",
        "query": "My credit card was declined at checkout even though I have plenty of available credit.",
    },
    {
        "category": "damaged_products",
        "query": "The item I received has a cracked screen right out of the box. What are my options?",
    },
    {
        "category": "account_login_issues",
        "query": "I can't remember my password and the reset email isn't arriving in my inbox.",
    },
    {
        "category": "shipping_charges",
        "query": "Why is there a $12.99 delivery fee on my $40 order? That seems way too high.",
    },
    {
        "category": "exchanges",
        "query": "I got a medium shirt but need a large. Can I swap it without paying shipping again?",
    },
    {
        "category": "customer_support",
        "query": "I've been waiting for help on my missing order for two days with no response.",
    },
]

NUM_RESULTS = 3


def _truncate(text: str, width: int) -> str:
    """Truncate text to width characters, appending ellipsis when needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


async def _run_with_latency(method, query: str, limit: int) -> tuple[list, float | None]:
    """Run a search method, returning (results, latency_ms) or ([], None) on failure."""
    start = time.perf_counter()
    try:
        results = await method(query, limit=limit)
        latency_ms = (time.perf_counter() - start) * 1000
        return results, latency_ms
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "comparison=search status=failure method=%s latency_ms=%.2f reason=%s",
            getattr(method, "__name__", "unknown"),
            latency_ms,
            type(exc).__name__,
        )
        return [], None


REPORT_PATH = Path("docs/day-3-search-evaluation.md")


def _build_markdown_report(
    per_query: list[dict],
    total: int,
    semantic_top1_accuracy: float,
    keyword_top1_accuracy: float,
    semantic_top3_hit_rate: float,
    keyword_top3_hit_rate: float,
    semantic_avg_latency: float,
    keyword_avg_latency: float,
) -> str:
    """Build the Day 3 search evaluation Markdown report from run results."""
    lines: list[str] = [
        "# Day 3 — Search Method Evaluation Report",
        "",
        "## Evaluation Objective",
        "",
        "Evaluate and compare the semantic search and keyword search implementations.",
        "",
        "## Technology Stack",
        "",
        "- Gemini `gemini-embedding-001`.",
        "- Embedding dimensions: 768.",
        "- Neon PostgreSQL with pgvector.",
        "- PostgreSQL full-text search for keyword search.",
        "",
        "## Dataset",
        "",
        "- 30 sample documents across 10 categories.",
        "",
        "## Methodology",
        "",
        f"- Compared semantic and keyword search using {len(EVALUATION_QUERIES)} evaluation queries.",
        f"- Returned top-{NUM_RESULTS} results per method per query.",
        "- Top-1 accuracy compares the expected category with the top-1 returned category.",
        "- Top-3 accuracy checks whether the expected category appears in the top-3 returned categories.",
        "- Similarity and rank values are not compared numerically because scoring systems differ.",
        "",
        "## Results",
        "",
        "| # | Expected Category | Semantic Top-1 | Keyword Top-1 | Semantic Top-3 Categories | Keyword Top-3 Categories | Semantic Latency (ms) | Keyword Latency (ms) |",
        "|---|--------------------|----------------|---------------|---------------------------|--------------------------|----------------------|----------------------|",
    ]

    for row in per_query:
        sem_top1 = row.get("semantic_top1") or "none"
        key_top1 = row.get("keyword_top1") or "no results"
        sem_top3 = ", ".join(row.get("semantic_categories") or []) or "none"
        keyword_categories = row.get("keyword_categories") or []
        key_top3 = ", ".join(keyword_categories) or (
            "no results" if not row.get("keyword_has_results") else "none"
        )
        sem_status = row.get("semantic_status") or "unknown"
        key_status = row.get("keyword_status") or "unknown"
        sem_lat = row.get("semantic_latency_ms")
        key_lat = row.get("keyword_latency_ms")
        sem_lat_str = f"{sem_lat:.2f}" if sem_lat is not None else "N/A"
        key_lat_str = f"{key_lat:.2f}" if key_lat is not None else "N/A"

        if sem_status == "failure":
            sem_top1 = "failure"
        if key_status == "failure":
            key_top1 = "failure"

        lines.append(
            f"| {row.get('index', 0)} | {_truncate(row.get('expected') or 'unknown', 20)} | "
            f"{_truncate(sem_top1, 18)} | {_truncate(key_top1, 18)} | "
            f"{_truncate(sem_top3, 40)} | {_truncate(key_top3, 40)} | "
            f"{sem_lat_str:>14} | {key_lat_str:>16} |"
        )

    lines.extend(
        [
            "",
            "## Summary Metrics",
            "",
            "| Metric | Semantic Search | Keyword Search |",
            "|---|---|---|",
            f"| Top-1 Accuracy | {semantic_top1_accuracy:.1f}% | {keyword_top1_accuracy:.1f}% |",
            f"| Top-3 Accuracy | {semantic_top3_hit_rate:.1f}% | {keyword_top3_hit_rate:.1f}% |",
            f"| Average Latency | {semantic_avg_latency:.2f} ms | {keyword_avg_latency:.2f} ms |",
            "",
            "## Observations and Limitations",
            "",
            "- Failed searches are reported as failed and are excluded from latency averages.",
            "- Queries where keyword search returned no results are treated as incorrect.",
            "- Semantic similarity and keyword rank are not compared numerically.",
            "",
        ]
    )

    return "\n".join(lines)


async def main() -> None:
    """Compare semantic search and keyword search on the same queries."""
    document_service = DocumentService()

    per_query: list[dict] = []
    semantic_top1_correct = 0
    keyword_top1_correct = 0
    semantic_top3_hit = 0
    keyword_top3_hit = 0
    semantic_latencies: list[float] = []
    keyword_latencies: list[float] = []

    total = len(EVALUATION_QUERIES)

    print("=" * 120)
    print("SEARCH METHOD COMPARISON: SEMANTIC vs KEYWORD")
    print("=" * 120)
    print(
        f"Queries: {total}  |  Top-N results per method: {NUM_RESULTS}  |  "
        f"Metric: expected category vs returned category"
    )
    print(
        "Note: similarity (semantic) and rank (keyword) are NOT compared numerically "
        "because they use different scoring systems."
    )
    print("-" * 120)

    header = (
        f"{'#':>2} | {'expected':<18} | {'semantic top-1':<18} | "
        f"{'keyword top-1':<18} | {'semantic top-3':<42} | "
        f"{'keyword top-3':<42} | {'sem lat (ms)':>12} | {'key lat (ms)':>12}"
    )
    print(header)
    print("-" * len(header))

    for index, eval_item in enumerate(EVALUATION_QUERIES, 1):
        expected_category = eval_item["category"]
        query = eval_item["query"]

        # Semantic search
        semantic_results, semantic_latency = await _run_with_latency(
            document_service.semantic_search, query, NUM_RESULTS
        )
        semantic_categories = [r.metadata.get("category", "unknown") for r in semantic_results]
        semantic_top1 = semantic_categories[0] if semantic_categories else "none"
        semantic_top1_match = semantic_top1 == expected_category
        semantic_top3_match = expected_category in semantic_categories
        semantic_top1_correct += int(semantic_top1_match)
        semantic_top3_hit += int(semantic_top3_match)

        if semantic_latency is not None:
            semantic_latencies.append(semantic_latency)

        # Keyword search
        keyword_results, keyword_latency = await _run_with_latency(
            document_service.keyword_search, query, NUM_RESULTS
        )
        keyword_categories = [r.metadata.get("category", "unknown") for r in keyword_results]
        keyword_has_results = bool(keyword_categories)
        if keyword_has_results:
            keyword_top1 = keyword_categories[0]
            keyword_top1_match = keyword_top1 == expected_category
            keyword_top3_match = expected_category in keyword_categories
            keyword_top1_correct += int(keyword_top1_match)
            keyword_top3_hit += int(keyword_top3_match)
        else:
            keyword_top1 = "no results"
            keyword_top1_match = False
            keyword_top3_match = False

        if keyword_latency is not None:
            keyword_latencies.append(keyword_latency)

        per_query.append(
            {
                "index": index,
                "expected": expected_category,
                "query": query,
                "semantic_top1": semantic_top1,
                "keyword_top1": keyword_top1,
                "semantic_categories": semantic_categories,
                "keyword_categories": keyword_categories,
                "keyword_has_results": keyword_has_results,
                "semantic_status": "failure" if semantic_latency is None else "success",
                "keyword_status": "failure" if keyword_latency is None else "success",
                "semantic_latency_ms": semantic_latency,
                "keyword_latency_ms": keyword_latency,
            }
        )

        sem_top3_str = ", ".join(semantic_categories) or "none"
        key_top3_str = ", ".join(keyword_categories) or (
            "no results" if not keyword_has_results else "none"
        )
        key_lat_str = f"{keyword_latency:.2f}" if keyword_latency is not None else "N/A"

        print(
            f"{index:>2} | {_truncate(expected_category, 18):<18} | "
            f"{_truncate(semantic_top1, 18):<18} | "
            f"{_truncate(keyword_top1, 18):<18} | "
            f"{_truncate(sem_top3_str, 42):<42} | "
            f"{_truncate(key_top3_str, 42):<42} | "
            f"{(semantic_latency or 0.0):>11.2f} | {key_lat_str:>12}"
        )

    print("-" * 120)
    print("SUMMARY")
    print("-" * 120)

    semantic_top1_accuracy = semantic_top1_correct / total * 100
    keyword_top1_accuracy = keyword_top1_correct / total * 100
    semantic_top3_hit_rate = semantic_top3_hit / total * 100
    keyword_top3_hit_rate = keyword_top3_hit / total * 100
    semantic_avg_latency = (
        sum(semantic_latencies) / len(semantic_latencies) if semantic_latencies else 0.0
    )
    keyword_avg_latency = (
        sum(keyword_latencies) / len(keyword_latencies) if keyword_latencies else 0.0
    )

    print(f"Total queries:                     {total}")
    print("Top-1 category accuracy:")
    print(f"  Semantic search: {semantic_top1_accuracy:.1f}% ({semantic_top1_correct}/{total})")
    print(f"  Keyword search:  {keyword_top1_accuracy:.1f}% ({keyword_top1_correct}/{total})")
    print(f"Top-{NUM_RESULTS} category hit rate:")
    print(f"  Semantic search: {semantic_top3_hit_rate:.1f}% ({semantic_top3_hit}/{total})")
    print(f"  Keyword search:  {keyword_top3_hit_rate:.1f}% ({keyword_top3_hit}/{total})")
    print("Average latency:")
    print(f"  Semantic search: {semantic_avg_latency:.2f} ms")
    print(f"  Keyword search:  {keyword_avg_latency:.2f} ms")
    print(
        f"Queries where keyword returned no results: {sum(1 for r in per_query if not r['keyword_has_results'])}"
    )
    print("=" * 120)
    print("COMPARISON COMPLETE")
    print("=" * 120)

    markdown_report = _build_markdown_report(
        per_query=per_query,
        total=total,
        semantic_top1_accuracy=semantic_top1_accuracy,
        keyword_top1_accuracy=keyword_top1_accuracy,
        semantic_top3_hit_rate=semantic_top3_hit_rate,
        keyword_top3_hit_rate=keyword_top3_hit_rate,
        semantic_avg_latency=semantic_avg_latency,
        keyword_avg_latency=keyword_avg_latency,
    )

    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(markdown_report + "\n", encoding="utf-8")
        print(f"Markdown report written to: {REPORT_PATH}")
    except OSError as exc:
        logger.warning(
            "comparison=report status=failure path=%s reason=%s",
            REPORT_PATH,
            type(exc).__name__,
        )


if __name__ == "__main__":
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
        loop.run_until_complete(main())
        loop.close()
    else:
        asyncio.run(main())
