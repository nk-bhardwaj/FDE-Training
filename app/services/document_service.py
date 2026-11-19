import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psycopg
from dotenv import load_dotenv
from pgvector import Vector
from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.logging import get_logger
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)

load_dotenv()

MAX_SEARCH_LIMIT = 100
CONNECT_TIMEOUT_SECONDS = 10

_INSERT_SQL = """
    INSERT INTO documents (content, embedding, metadata)
    VALUES (%(content)s, %(embedding)s, %(metadata)s)
    RETURNING id
"""

_SEARCH_SQL = """
    SELECT
        id,
        content,
        metadata,
        created_at,
        embedding <=> %(query_embedding)s AS distance,
        1 - (embedding <=> %(query_embedding)s) AS similarity
    FROM documents
"""


class DocumentStoreError(Exception):
    """Raised when a document store operation fails."""


class DatabaseNotConfiguredError(DocumentStoreError):
    """Raised when DATABASE_URL is not configured."""


@dataclass(frozen=True)
class SearchResult:
    """A single semantic search hit ordered by cosine distance."""

    id: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    distance: float = 0.0
    similarity: float = 0.0


class DocumentService:
    """Stores documents and runs pgvector cosine-similarity search."""

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self.embedding_service = embedding_service or EmbeddingService()

    def _get_dsn(self) -> str:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise DatabaseNotConfiguredError("DATABASE_URL is not configured")
        return dsn

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[AsyncConnection[Any]]:
        dsn = self._get_dsn()
        try:
            conn = await AsyncConnection.connect(
                dsn,
                row_factory=dict_row,
                connect_timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except psycopg.Error as exc:
            logger.warning("store=documents status=failure reason=connection_error")
            raise DocumentStoreError("Could not connect to the document database") from exc

        try:
            # Teaches psycopg how to adapt/serialize VECTOR values for this connection.
            await register_vector_async(conn)
            yield conn
        finally:
            await conn.close()

    async def insert_document(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Embed and persist a document, returning its database id."""
        if not content or not content.strip():
            raise ValueError("Document content must not be empty")

        document_metadata = dict(metadata or {})
        embedding = await self.embedding_service.embed_document(content)
        vector = Vector(embedding)

        start = time.perf_counter()
        try:
            async with self._connect() as conn, conn.cursor() as cur:
                await cur.execute(
                    _INSERT_SQL,
                    {
                        "content": content,
                        "embedding": vector,
                        "metadata": Jsonb(document_metadata),
                    },
                )
                row = await cur.fetchone()
                await conn.commit()
        except DocumentStoreError:
            raise
        except psycopg.Error as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "store=documents operation=insert status=failure latency_ms=%.2f reason=database_error",
                latency_ms,
            )
            raise DocumentStoreError("Failed to insert document") from exc

        if not row or "id" not in row:
            logger.warning("store=documents operation=insert status=failure reason=no_id_returned")
            raise DocumentStoreError("Insert did not return a document id")

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "store=documents operation=insert status=success latency_ms=%.2f document_id=%s dimensions=%d metadata_keys=%d",
            latency_ms,
            row["id"],
            vector.dimensions(),
            len(document_metadata),
        )
        return int(row["id"])

    async def semantic_search(
        self,
        query: str,
        limit: int = 5,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Return documents ordered by pgvector cosine distance (closest first)."""
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        if limit <= 0:
            raise ValueError("Search limit must be a positive integer")
        if limit > MAX_SEARCH_LIMIT:
            raise ValueError(f"Search limit must not exceed {MAX_SEARCH_LIMIT}")

        embedding = await self.embedding_service.embed_query(query)
        vector = Vector(embedding)

        params: dict[str, Any] = {"query_embedding": vector, "limit": limit}
        sql = _SEARCH_SQL
        if metadata_filters:
            # Containment keeps the filter fully parameterized and GIN-index friendly.
            sql += " WHERE metadata @> %(filters)s"
            params["filters"] = Jsonb(dict(metadata_filters))
        sql += " ORDER BY embedding <=> %(query_embedding)s LIMIT %(limit)s"

        start = time.perf_counter()
        try:
            async with self._connect() as conn, conn.cursor() as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
        except DocumentStoreError:
            raise
        except psycopg.Error as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "store=documents operation=search status=failure latency_ms=%.2f reason=database_error",
                latency_ms,
            )
            raise DocumentStoreError("Failed to search documents") from exc

        results = [
            SearchResult(
                id=int(row["id"]),
                content=row["content"],
                metadata=row["metadata"] or {},
                created_at=row["created_at"],
                distance=float(row["distance"]),
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "store=documents operation=search status=success latency_ms=%.2f results=%d limit=%d filtered=%s",
            latency_ms,
            len(results),
            limit,
            bool(metadata_filters),
        )
        return results
