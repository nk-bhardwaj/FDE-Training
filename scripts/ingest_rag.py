"""RAG ingestion runner: loads Markdown docs, chunks, embeds, and persists.

Pipeline:
1. ``load_all_documents()`` reads the Markdown files from ``data/raw/``.
2. ``load_and_chunk(chunk_size=..., chunk_overlap=...)`` produces token-based
   chunks using tiktoken's ``cl100k_base`` encoding.
3. ``embed_document_chunks()`` generates 768-dimensional Gemini embeddings for
   every chunk using one shared ``EmbeddingService``.
4. ``RagIngestionService.ingest()`` embeds full documents and persists parent
   documents + chunks to Neon PostgreSQL idempotently.

Run from the project root:

    python scripts/ingest_rag.py
    python scripts/ingest_rag.py --chunk-size 300 --chunk-overlap 50
    python scripts/ingest_rag.py --chunk-size 800 --chunk-overlap 100

The chunking configuration is configurable via command-line flags; the source
IDs of the loaded documents are preserved unchanged and never suffixed.  This
script performs no database writes until explicitly invoked.  It does not
read, print, or log API keys, database URLs, or other ``.env`` secrets.
"""

import argparse
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

# Day 4 experiment defaults: 500-token chunks with 75-token overlap.
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 75


def _setup_windows_event_loop() -> None:
    """Switch to the SelectorEventLoop policy on Windows for psycopg async."""
    if sys.platform != "win32":
        return
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for the ingestion runner."""
    parser = argparse.ArgumentParser(
        description=("Load Markdown documents, chunk them, embed, and persist to Neon.")
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Maximum tokens per chunk (default: {DEFAULT_CHUNK_SIZE}).",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help=f"Overlap tokens between chunks (default: {DEFAULT_CHUNK_OVERLAP}).",
    )
    return parser


def _validate_chunk_config(chunk_size: int, chunk_overlap: int) -> None:
    """Validate chunking parameters, raising ``ValueError`` on invalid input."""
    if chunk_size <= 0:
        raise ValueError(f"--chunk-size must be positive, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"--chunk-overlap must be non-negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"--chunk-overlap ({chunk_overlap}) must be smaller than --chunk-size ({chunk_size})"
        )


async def main(args: argparse.Namespace | None = None) -> None:
    """Run the full RAG ingestion pipeline and print a summary.

    ``args`` is an ``argparse.Namespace`` with ``chunk_size`` and
    ``chunk_overlap`` attributes.  When omitted, the defaults (500/75) are
    used, which keeps ``python -m scripts.ingest_rag`` and tests working
    without parsing ``sys.argv``.
    """
    if args is None:
        args = argparse.Namespace(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )

    chunk_size = args.chunk_size
    chunk_overlap = args.chunk_overlap

    _validate_chunk_config(chunk_size, chunk_overlap)

    load_dotenv()

    print("=" * 72)
    print("RAG INGESTION RUNNER")
    print("=" * 72)
    print(f"  Chunk size:     {chunk_size}")
    print(f"  Chunk overlap:  {chunk_overlap}")

    # Step 1: Load source documents.
    documents = load_all_documents()
    print(f"Loaded {len(documents)} source document(s) from data/raw/")

    # Step 2: Chunk documents using the selected configuration.
    chunk_docs = load_and_chunk(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
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
    print(f"  Chunk size:               {chunk_size}")
    print(f"  Chunk overlap:            {chunk_overlap}")
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
        _args = build_arg_parser().parse_args()
        asyncio.run(main(_args))
    except Exception as exc:
        logger.error("store=rag_ingestion status=failure reason=runner_error error=%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
