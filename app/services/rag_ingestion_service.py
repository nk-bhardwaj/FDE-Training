"""RAG ingestion service: persists documents and their chunks to the database.

This service orchestrates the full RAG ingestion pipeline:
- Embeds full documents using EmbeddingService (chunk embeddings are reused
  from ``EmbeddedChunk``, already produced by ``IngestionService``).
- Saves parent documents in the ``documents`` table.
- Saves chunks in the ``document_chunks`` table with correct document_id.
- Implements idempotent ingestion via the dedicated ``documents.source_id``
  column (upsert on ``source_id``).
- Uses transactions so parent and chunk changes succeed or fail together.
- Handles concurrent ingestion safely via PostgreSQL advisory locks.

Design notes:
- Gemini embedding calls happen BEFORE opening a DB transaction to avoid
  holding locks during slow external calls.  Only full-document embeddings
  are generated here; chunk embeddings are reused as-is from ``EmbeddedChunk``.
- The transaction covers only the database writes (document upsert + chunk
  replace).
- Advisory locks prevent concurrent ingestion of the same source_id from
  creating duplicate documents or inconsistent chunk states.
"""

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from dotenv import load_dotenv
from pgvector import Vector
from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.logging import get_logger
from app.services.document_service import DocumentStoreError
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import EmbeddedChunk, LoadedDocument

logger = get_logger(__name__)

load_dotenv()

EMBEDDING_DIMENSIONS = 768
CONNECT_TIMEOUT_SECONDS = 10

# SQL: upsert document by source_id, returning the document id.
_UPSERT_DOCUMENT_SQL = """
    INSERT INTO documents (content, embedding, metadata, source_id)
    VALUES (%(content)s, %(embedding)s, %(metadata)s, %(source_id)s)
    ON CONFLICT (source_id) DO UPDATE
        SET content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata
    RETURNING id
"""

# SQL: delete all chunks for a document.
_DELETE_CHUNKS_SQL = """
    DELETE FROM document_chunks WHERE document_id = %(document_id)s
"""

# SQL: insert a chunk.
_INSERT_CHUNK_SQL = """
    INSERT INTO document_chunks (document_id, chunk_index, content, embedding, metadata)
    VALUES (%(document_id)s, %(chunk_index)s, %(content)s, %(embedding)s, %(metadata)s)
    ON CONFLICT (document_id, chunk_index) DO UPDATE
        SET content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata
"""

# SQL: pg_advisory_xact_lock keyed on source_id hash for concurrency control.
_ADVISORY_LOCK_SQL = """
    SELECT pg_advisory_xact_lock(hashtext(%(source_id)s))
"""


class RagIngestionService:
    """Persists documents and their chunks to the database idempotently.

    Idempotency is based on the ``documents.source_id`` column (upsert on
    ``ON CONFLICT (source_id)``).  Re-ingesting the same ``source_id`` updates
    the parent document and replaces all its chunks.  Each ``source_id`` is
    protected by a PostgreSQL advisory lock to prevent concurrent ingestion
    from creating duplicates or inconsistent states.
    """

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self.embedding_service = embedding_service or EmbeddingService()

    def _get_dsn(self) -> str:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise DocumentStoreError("DATABASE_URL is not configured")
        return dsn

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[AsyncConnection[Any]]:
        """Async context manager yielding a registered psycopg connection."""
        dsn = self._get_dsn()
        try:
            conn = await AsyncConnection.connect(
                dsn,
                row_factory=dict_row,
                connect_timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except psycopg.Error as exc:
            logger.warning("store=rag_ingestion status=failure reason=connection_error")
            raise DocumentStoreError("Could not connect to the RAG ingestion database") from exc

        try:
            await register_vector_async(conn)
            yield conn
        finally:
            await conn.close()

    async def _embed_documents(
        self,
        documents: list[LoadedDocument],
    ) -> list[list[float]]:
        """Embed all full documents outside of any DB transaction.

        Chunk embeddings are NOT regenerated here -- they are reused directly
        from each ``EmbeddedChunk`` instance passed to :meth:`ingest`.

        Returns:
            A list of 768-dimensional document embeddings, one per input
            document, in the same order as ``documents``.
        """
        document_embeddings: list[list[float]] = []
        for doc in documents:
            embedding = await self.embedding_service.embed_document(doc.content)
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Document embedding for source_id={doc.source_id} "
                    f"has {len(embedding)} dimensions, expected {EMBEDDING_DIMENSIONS}"
                )
            document_embeddings.append(embedding)
        return document_embeddings

    @staticmethod
    def _validate_chunk_embeddings(chunks: list[EmbeddedChunk]) -> None:
        """Validate that every chunk embedding has exactly 768 dimensions.

        Does not call any embedding provider; chunk embeddings are expected
        to already be present on the ``EmbeddedChunk`` instances.
        """
        for chunk in chunks:
            embedding = chunk.embedding
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Chunk embedding for source_id={chunk.document.source_id} "
                    f"chunk_index={chunk.document.metadata.get('chunk_index') if chunk.document.metadata else 'N/A'} "
                    f"has {len(embedding)} dimensions, expected {EMBEDDING_DIMENSIONS}"
                )

    @staticmethod
    def _validate_unique_source_ids(documents: list[LoadedDocument]) -> None:
        """Reject duplicate ``source_id`` values in the input document list."""
        seen: set[str] = set()
        for doc in documents:
            if doc.source_id in seen:
                raise ValueError(f"Duplicate source_id in input documents: {doc.source_id!r}")
            seen.add(doc.source_id)

    @staticmethod
    def _validate_unique_chunk_indexes(chunks: list[EmbeddedChunk]) -> None:
        """Validate every chunk has a valid ``chunk_index`` and reject duplicates.

        Each chunk must have a non-negative integer ``chunk_index`` in its
        metadata.  Boolean values are rejected even though Python treats
        ``bool`` as a subclass of ``int``.  Duplicate
        ``(source_id, chunk_index)`` pairs are also rejected.

        All validation is performed here, before any embedding or database
        operation, so callers can rely on this being the single source of
        truth for chunk index validity.
        """
        seen: set[tuple[str, int]] = set()
        for chunk in chunks:
            source_id = chunk.document.source_id
            metadata = chunk.document.metadata
            chunk_index = metadata.get("chunk_index") if metadata else None

            if chunk_index is None:
                raise ValueError(f"Chunk for source_id={source_id} missing chunk_index in metadata")
            # Reject bool explicitly: bool is a subclass of int in Python.
            if isinstance(chunk_index, bool) or not isinstance(chunk_index, int):
                raise ValueError(
                    f"Invalid chunk_index for source_id={source_id}: "
                    f"chunk_index={chunk_index!r} (must be a non-negative integer)"
                )
            if chunk_index < 0:
                raise ValueError(
                    f"Invalid chunk_index for source_id={source_id}: "
                    f"chunk_index={chunk_index} (must be non-negative)"
                )

            key = (source_id, chunk_index)
            if key in seen:
                raise ValueError(
                    f"Duplicate chunk_index for source_id={source_id}: chunk_index={chunk_index}"
                )
            seen.add(key)

    async def ingest(
        self,
        documents: list[LoadedDocument],
        chunks: list[EmbeddedChunk],
    ) -> dict[str, Any]:
        """Persist documents and their chunks to the database.

        Performs idempotent ingestion:
        - Identifies existing documents by ``documents.source_id``.
        - Updates the document row in place (preserving its id).
        - Replaces old chunks with new chunks -- deletes chunks for every
          document being ingested, even when the incoming chunk list is empty.
        - Reuses chunk embeddings from ``EmbeddedChunk`` instead of re-embedding.
        - Uses a transaction so all changes succeed or fail together.
        - Uses an advisory lock keyed on source_id to prevent concurrent
          ingestion of the same source from creating duplicates.

        Parameters:
            documents: List of ``LoadedDocument`` instances to persist.
            chunks: List of ``EmbeddedChunk`` instances (each containing a
                ``LoadedDocument`` and its pre-computed embedding vector).

        Returns:
            A summary dict with counts and per-source document ids.
        """
        if not documents:
            if chunks:
                raise ValueError("Chunks cannot be ingested without parent documents")
            return {"documents_ingested": 0, "chunks_ingested": 0, "document_ids": {}}

        # Validate input consistency: every chunk must belong to a document.
        document_source_ids = {doc.source_id for doc in documents}
        for chunk in chunks:
            chunk_source_id = chunk.document.source_id
            if chunk_source_id not in document_source_ids:
                raise ValueError(
                    f"Chunk source_id={chunk_source_id} does not match any "
                    "input document. Ensure chunks are derived from the provided documents."
                )

        # Reject duplicate source_id values before embedding.
        self._validate_unique_source_ids(documents)

        # Reject duplicate (source_id, chunk_index) pairs before opening a transaction.
        self._validate_unique_chunk_indexes(chunks)

        # Step 1: Validate chunk embeddings first so we fail before making any
        # Gemini calls for full-document embeddings.
        self._validate_chunk_embeddings(chunks)

        # Step 2: Embed only full documents OUTSIDE the transaction to avoid
        # holding database locks during slow Gemini calls.
        start = time.perf_counter()
        document_embeddings = await self._embed_documents(documents)
        embedding_latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "store=rag_ingestion operation=embed status=success "
            "documents=%d chunks=%d latency_ms=%.2f",
            len(documents),
            len(chunks),
            embedding_latency_ms,
        )

        # Step 3: Acquire advisory locks for each source_id to prevent
        # concurrent ingestion. We sort source_ids for deterministic lock
        # acquisition order to avoid deadlocks.
        sorted_source_ids = sorted(document_source_ids)

        # Step 4: Open transaction and perform DB writes.
        start = time.perf_counter()
        try:
            async with self._connect() as conn, conn.transaction():
                # Acquire advisory locks (sorted to avoid deadlock).
                async with conn.cursor() as cur:
                    for source_id in sorted_source_ids:
                        await cur.execute(_ADVISORY_LOCK_SQL, {"source_id": source_id})

                # Upsert documents and collect document_ids.
                document_ids: dict[str, int] = {}
                doc_embedding_iter = iter(document_embeddings)
                async with conn.cursor() as cur:
                    for doc in documents:
                        embedding_vec = next(doc_embedding_iter)
                        await cur.execute(
                            _UPSERT_DOCUMENT_SQL,
                            {
                                "content": doc.content,
                                "embedding": Vector(embedding_vec),
                                "metadata": Jsonb(doc.metadata or {}),
                                "source_id": doc.source_id,
                            },
                        )
                        row = await cur.fetchone()
                        if not row:
                            raise DocumentStoreError(
                                f"Failed to upsert document for source_id={doc.source_id}"
                            )
                        document_ids[doc.source_id] = int(row["id"])

                # Delete old chunks for every document being ingested.  We
                # iterate over documents (not chunks) so that a document with
                # zero incoming chunks still has its existing chunks removed.
                async with conn.cursor() as cur:
                    for doc in documents:
                        doc_id = document_ids[doc.source_id]
                        await cur.execute(
                            _DELETE_CHUNKS_SQL,
                            {"document_id": doc_id},
                        )

                # Insert new chunks, reusing pre-computed embeddings.
                async with conn.cursor() as cur:
                    for chunk in chunks:
                        doc_id = document_ids[chunk.document.source_id]
                        chunk_index = chunk.document.metadata["chunk_index"]
                        await cur.execute(
                            _INSERT_CHUNK_SQL,
                            {
                                "document_id": doc_id,
                                "chunk_index": chunk_index,
                                "content": chunk.document.content,
                                "embedding": Vector(chunk.embedding),
                                "metadata": Jsonb(chunk.document.metadata or {}),
                            },
                        )

        except DocumentStoreError:
            raise
        except psycopg.Error as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "store=rag_ingestion operation=ingest status=failure "
                "latency_ms=%.2f reason=database_error",
                latency_ms,
            )
            raise DocumentStoreError(
                "Failed to ingest documents and chunks into the database"
            ) from exc

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "store=rag_ingestion operation=ingest status=success "
            "documents=%d chunks=%d latency_ms=%.2f",
            len(documents),
            len(chunks),
            latency_ms,
        )

        return {
            "documents_ingested": len(documents),
            "chunks_ingested": len(chunks),
            "document_ids": document_ids,
        }
