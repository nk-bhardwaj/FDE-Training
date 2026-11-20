"""Seed script to insert sample documents into Neon PostgreSQL."""

import asyncio
import sys

from app.core.logging import get_logger
from app.data.sample_documents import SAMPLE_DOCUMENTS
from app.services.document_service import DocumentService

logger = get_logger(__name__)


async def main() -> None:
    """Insert all sample documents into the document store."""
    document_service = DocumentService()

    success_count = 0
    failed_count = 0

    for document in SAMPLE_DOCUMENTS:
        try:
            await document_service.insert_document(
                document["content"],
                document["metadata"],
            )
            success_count += 1
        except Exception:
            failed_count += 1
            logger.warning("store=documents operation=seed status=failure reason=insert_error")

    print(f"Seeding complete: {success_count} inserted, {failed_count} failed")


if __name__ == "__main__":
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
        loop.run_until_complete(main())
        loop.close()
    else:
        asyncio.run(main())
