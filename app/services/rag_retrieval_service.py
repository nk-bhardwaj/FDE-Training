"""RAG retrieval service: searches document_chunks using semantic, keyword, and hybrid retrieval."""

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
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
from app.services.document_service import (
    DocumentStoreError,
    _build_or_tsquery,
)
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)

load_dotenv()

MAX_SEARCH_LIMIT = 100
CONNECT_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class ChunkSearchResult:
    """A single chunk search hit with citation metadata."""

    id: int
    document_id: int
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    document_metadata: dict[str, Any]
    source_id: str
    document_title: str
    created_at: datetime | None
    distance: float | None = None
    similarity: float | None = None
    rank: float | None = None
    rrf_score: float | None = None


class RAGRetrievalService:
    """Retrieves chunks from document_chunks using semantic, keyword, and hybrid search."""

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self.embedding_service = embedding_service or EmbeddingService()

    def _get_dsn(self) -> str:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise DocumentStoreError("DATABASE_URL is not configured")
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
            logger.warning("store=rag_retrieval status=failure reason=connection_error")
            raise DocumentStoreError("Could not connect to the RAG retrieval database") from exc

        try:
            await register_vector_async(conn)
            yield conn
        finally:
            await conn.close()

    async def semantic_search_chunks(
        self,
        query: str,
        limit: int = 5,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[ChunkSearchResult]:
        """Return chunks ordered by pgvector cosine distance (closest first)."""
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        if limit <= 0:
            raise ValueError("Search limit must be a positive integer")
        if limit > MAX_SEARCH_LIMIT:
            raise ValueError(f"Search limit must not exceed {MAX_SEARCH_LIMIT}")

        embedding = await self.embedding_service.embed_query(query)
        vector = Vector(embedding)

        params: dict[str, Any] = {"query_embedding": vector, "limit": limit}
        sql = """
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.metadata,
                dc.created_at,
                d.metadata AS document_metadata,
                d.source_id,
                d.metadata->>'title' AS document_title,
                dc.embedding <=> %(query_embedding)s AS distance,
                1 - (dc.embedding <=> %(query_embedding)s) AS similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
        """
        if metadata_filters:
            sql += " WHERE dc.metadata @> %(filters)s"
            params["filters"] = Jsonb(dict(metadata_filters))
        sql += " ORDER BY dc.embedding <=> %(query_embedding)s LIMIT %(limit)s"

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
                "store=rag_retrieval operation=semantic_search status=failure latency_ms=%.2f reason=database_error",
                latency_ms,
            )
            raise DocumentStoreError("Failed to search chunks") from exc

        results = [
            ChunkSearchResult(
                id=int(row["id"]),
                document_id=int(row["document_id"]),
                chunk_index=int(row["chunk_index"]),
                content=row["content"],
                metadata=row["metadata"] or {},
                document_metadata=row["document_metadata"] or {},
                source_id=row["source_id"],
                document_title=row["document_title"] or "",
                created_at=row["created_at"],
                distance=float(row["distance"]),
                similarity=float(row["similarity"]),
                rank=None,
                rrf_score=None,
            )
            for row in rows
        ]

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "store=rag_retrieval operation=semantic_search status=success latency_ms=%.2f results=%d limit=%d filtered=%s",
            latency_ms,
            len(results),
            limit,
            bool(metadata_filters),
        )
        return results

    async def keyword_search_chunks(
        self,
        query: str,
        limit: int = 5,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[ChunkSearchResult]:
        """Return chunks ordered by PostgreSQL full-text search rank."""
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        if limit <= 0:
            raise ValueError("Search limit must be a positive integer")
        if limit > MAX_SEARCH_LIMIT:
            raise ValueError(f"Search limit must not exceed {MAX_SEARCH_LIMIT}")

        tsquery = _build_or_tsquery(query)
        if not tsquery:
            raise ValueError("Search query must contain at least one alphanumeric token")

        params: dict[str, Any] = {"tsquery": tsquery, "limit": limit}
        sql = """
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.metadata,
                dc.created_at,
                d.metadata AS document_metadata,
                d.source_id,
                d.metadata->>'title' AS document_title,
                ts_rank(dc.tsvector_content, to_tsquery('english', %(tsquery)s)) AS rank
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.tsvector_content @@ to_tsquery('english', %(tsquery)s)
        """
        if metadata_filters:
            sql += " AND dc.metadata @> %(filters)s"
            params["filters"] = Jsonb(dict(metadata_filters))
        sql += " ORDER BY rank DESC LIMIT %(limit)s"

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
                "store=rag_retrieval operation=keyword_search status=failure latency_ms=%.2f reason=database_error",
                latency_ms,
            )
            raise DocumentStoreError("Failed to search chunks") from exc

        results = [
            ChunkSearchResult(
                id=int(row["id"]),
                document_id=int(row["document_id"]),
                chunk_index=int(row["chunk_index"]),
                content=row["content"],
                metadata=row["metadata"] or {},
                document_metadata=row["document_metadata"] or {},
                source_id=row["source_id"],
                document_title=row["document_title"] or "",
                created_at=row["created_at"],
                distance=None,
                similarity=None,
                rank=float(row["rank"]),
                rrf_score=None,
            )
            for row in rows
        ]

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "store=rag_retrieval operation=keyword_search status=success latency_ms=%.2f results=%d limit=%d filtered=%s",
            latency_ms,
            len(results),
            limit,
            bool(metadata_filters),
        )
        return results

    async def hybrid_search_chunks(
        self,
        query: str,
        limit: int = 5,
        metadata_filters: dict[str, Any] | None = None,
        rrf_k: int = 60,
    ) -> list[ChunkSearchResult]:
        """Hybrid retrieval: combine semantic and keyword results using Reciprocal Rank Fusion.

        Args:
            query: Search query string.
            limit: Maximum number of final results to return.
            metadata_filters: Optional JSONB metadata filters.
            rrf_k: RRF constant (default 60). Must be positive.

        Returns:
            List of ChunkSearchResult ordered by descending RRF score.
        """
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        if limit <= 0:
            raise ValueError("Search limit must be a positive integer")
        if limit > MAX_SEARCH_LIMIT:
            raise ValueError(f"Search limit must not exceed {MAX_SEARCH_LIMIT}")
        if rrf_k <= 0:
            raise ValueError("rrf_k must be a positive integer")

        # Fetch semantic and keyword results in parallel using the same query embedding
        semantic_results = await self.semantic_search_chunks(
            query=query,
            limit=limit * 2,  # fetch more for better RRF fusion
            metadata_filters=metadata_filters,
        )

        keyword_results = await self.keyword_search_chunks(
            query=query,
            limit=limit * 2,
            metadata_filters=metadata_filters,
        )

        # Build rank maps: chunk_id -> rank (1-based)
        semantic_rank_map: dict[int, int] = {
            result.id: rank + 1 for rank, result in enumerate(semantic_results)
        }
        keyword_rank_map: dict[int, int] = {
            result.id: rank + 1 for rank, result in enumerate(keyword_results)
        }

        # Merge results by chunk id, keeping the best available scores
        merged: dict[int, ChunkSearchResult] = {}
        for result in semantic_results:
            merged[result.id] = result
        for result in keyword_results:
            if result.id in merged:
                # Keep semantic scores, add keyword rank
                existing = merged[result.id]
                merged[result.id] = ChunkSearchResult(
                    id=existing.id,
                    document_id=existing.document_id,
                    chunk_index=existing.chunk_index,
                    content=existing.content,
                    metadata=existing.metadata,
                    document_metadata=existing.document_metadata,
                    source_id=existing.source_id,
                    document_title=existing.document_title,
                    created_at=existing.created_at,
                    distance=existing.distance,
                    similarity=existing.similarity,
                    rank=result.rank,
                    rrf_score=None,
                )
            else:
                merged[result.id] = result

        # Calculate RRF scores
        for chunk_id, result in merged.items():
            sem_rank = semantic_rank_map.get(chunk_id)
            kw_rank = keyword_rank_map.get(chunk_id)

            rrf_score = 0.0
            if sem_rank is not None:
                rrf_score += 1.0 / (rrf_k + sem_rank)
            if kw_rank is not None:
                rrf_score += 1.0 / (rrf_k + kw_rank)

            merged[chunk_id] = ChunkSearchResult(
                id=result.id,
                document_id=result.document_id,
                chunk_index=result.chunk_index,
                content=result.content,
                metadata=result.metadata,
                document_metadata=result.document_metadata,
                source_id=result.source_id,
                document_title=result.document_title,
                created_at=result.created_at,
                distance=result.distance,
                similarity=result.similarity,
                rank=result.rank,
                rrf_score=rrf_score,
            )

        # Sort by RRF score descending and apply final limit
        sorted_results = sorted(merged.values(), key=lambda r: r.rrf_score or 0.0, reverse=True)
        return sorted_results[:limit]
