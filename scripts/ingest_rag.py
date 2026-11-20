"""RAG ingestion runner: loads Markdown docs, chunks, embeds, and persists.

Pipeline:
1. ``load_all_documents()`` reads the three Markdown files from ``data/raw/``.
2. ``load_and_chunk(chunk_size=500, chunk_overlap=75)`` produces token-based
   chunks using tiktoken's ``cl100k_base`` encoding.
3. ``embed_document_chunks()`` generates 768-dimensional Gemini embeddings for
   every chunk using one shared ``EmbeddingService``.
4. ``RagIngestionService.ingest()`` embeds full documents and persists parent
   documents + chunks to Neon PostgreSQL idempotently.

Run from the project root:

    python scripts/ingest_rag.py

This script performs no database writes until explicitly invoked.  It does
not read, print, or log API keys, database URLs, or other ``.env`` secrets.
"""

import asyncio
import sys

from dotenv import load_dotenv

from app.core.logging import get_logger
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import (
    embed_document_chunks,
    load_all_documents,
    load_and_chunk,
)
from app.services.rag_ingestion_service import RagIngestionService

logger = get_logger(__name__)

# Day 4 experiment configuration: 500-token chunks with 75-token overlap.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 75


def _setup_windows_event_loop() -> None:
    """Switch to the SelectorEventLoop policy on Windows for psycopg async."""
    if sys.platform != "win32":
        return
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main() -> None:
    """Run the full RAG ingestion pipeline and print a summary."""
    load_dotenv()

    print("=" * 72)
    print("RAG INGESTION RUNNER")
    print("=" * 72)

    # Step 1: Load source documents.
    documents = load_all_documents()
    print(f"Loaded {len(documents)} source document(s) from data/raw/")

    # Step 2: Chunk documents using the 500/75 experiment configuration.
    chunk_docs = load_and_chunk(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    print(f"Generated {len(chunk_docs)} chunk(s)")

    # Step 3: Embed chunks using one shared embedding service.
    embedding_service = EmbeddingService()
    embedded_chunks = await embed_document_chunks(chunk_docs, embedding_service=embedding_service)
    print(f"Generated {len(embedded_chunks)} chunk embedding(s)")

    # Step 4: Persist documents and chunks via RagIngestionService.
    rag_service = RagIngestionService(embedding_service=embedding_service)
    result = await rag_service.ingest(documents, embedded_chunks)

    print("-" * 72)
    print("SUMMARY")
    print("-" * 72)
    print(f"  Source documents loaded:  {len(documents)}")
    print(f"  Chunks generated:         {len(chunk_docs)}")
    print(f"  Documents ingested:       {result['documents_ingested']}")
    print(f"  Chunks ingested:          {result['chunks_ingested']}")
    print(f"  Document IDs:             {result['document_ids']}")
    print("=" * 72)
    print("INGESTION COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    _setup_windows_event_loop()
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.error("store=rag_ingestion status=failure reason=runner_error error=%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
