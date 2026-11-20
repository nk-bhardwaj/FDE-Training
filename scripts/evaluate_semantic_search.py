"""Evaluate semantic search quality with representative e-commerce support queries."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.core.logging import get_logger
from app.services.document_service import DocumentService

load_dotenv(Path(".env"))

logger = get_logger(__name__)

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


async def main() -> None:
    """Run semantic search evaluation queries and print results."""
    document_service = DocumentService()

    print("=" * 80)
    print("SEMANTIC SEARCH EVALUATION")
    print("=" * 80)

    for eval_item in EVALUATION_QUERIES:
        query = eval_item["query"]
        expected_category = eval_item["category"]

        print(f"\nQuery [{expected_category}]: {query}")
        print("-" * 80)

        try:
            results = await document_service.semantic_search(query, limit=3)

            if not results:
                print("  No results found.")
                continue

            for i, result in enumerate(results, 1):
                category = result.metadata.get("category", "unknown")
                similarity = result.similarity
                doc_id = result.id
                print(f"  {i}. ID={doc_id} | Category={category} | Similarity={similarity:.4f}")

        except Exception as exc:
            logger.warning(
                "evaluation=semantic_search status=failure query_category=%s reason=%s",
                expected_category,
                type(exc).__name__,
            )
            print(f"  ERROR: {type(exc).__name__}")

    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
        loop.run_until_complete(main())
        loop.close()
    else:
        asyncio.run(main())
