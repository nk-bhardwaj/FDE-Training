"""Unit tests for the RAG retrieval service."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app.services.document_service import DocumentStoreError
from app.services.embedding_service import EmbeddingService
from app.services.rag_retrieval_service import ChunkSearchResult, RAGRetrievalService

DATABASE_URL = "postgresql://demo_user:s3cret-pass@ep-demo.neon.tech/neondb"
SAMPLE_EMBEDDING = [0.01 * index for index in range(768)]


class FakeCursor:
    """In-memory cursor double for async psycopg."""

    def __init__(self, row=None, rows=None) -> None:
        self.row = row
        self.rows = rows or []
        self.executed: list[tuple[str, dict]] = []

    async def execute(self, sql: str, params: dict | None = None) -> None:
        self.executed.append((sql, params or {}))

    async def fetchone(self):
        return self.row

    async def fetchall(self):
        return self.rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


class FakeConnection:
    """Minimal async connection double for psycopg."""

    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self._cursor

    async def commit(self) -> None:
        self.committed = True

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def embedding_service() -> MagicMock:
    service = MagicMock(spec=EmbeddingService)
    service.embed_query = AsyncMock(return_value=SAMPLE_EMBEDDING)
    return service


@pytest.fixture
def service(embedding_service: MagicMock) -> RAGRetrievalService:
    return RAGRetrievalService(embedding_service=embedding_service)


def _make_chunk_result(**kwargs) -> ChunkSearchResult:
    """Helper to construct a ChunkSearchResult with sensible defaults."""
    params = {
        "id": 1,
        "document_id": 42,
        "chunk_index": 0,
        "content": "chunk content",
        "metadata": {"source_id": "doc1"},
        "document_metadata": {"title": "Doc 1"},
        "source_id": "doc1",
        "document_title": "Doc 1",
        "created_at": None,
        "distance": None,
        "similarity": None,
        "rank": None,
        "rrf_score": None,
    }
    params.update(kwargs)
    return ChunkSearchResult(**params)


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


class TestSemanticSearchChunks:
    @pytest.mark.asyncio
    async def test_returns_ordered_results_with_similarity(
        self, service: RAGRetrievalService, embedding_service: MagicMock
    ):
        """Semantic search returns results ordered by cosine distance, similarity = 1 - distance."""
        rows = [
            {
                "id": 7,
                "document_id": 42,
                "chunk_index": 0,
                "content": "Refunds are processed in five business days.",
                "metadata": {"source_id": "doc1", "title": "Doc 1"},
                "created_at": None,
                "distance": 0.12,
                "similarity": 0.88,
                "source_id": "doc1",
                "document_title": "Doc 1",
                "document_metadata": {"source_id": "doc1", "title": "Doc 1"},
            },
            {
                "id": 3,
                "document_id": 42,
                "chunk_index": 1,
                "content": "Shipping takes two days.",
                "metadata": {"source_id": "doc1"},
                "created_at": None,
                "distance": 0.31,
                "similarity": 0.69,
                "source_id": "doc1",
                "document_title": "Doc 1",
                "document_metadata": {"source_id": "doc1"},
            },
        ]
        cursor = FakeCursor(rows=rows)
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
        ):
            results = await service.semantic_search_chunks("how long do refunds take?", limit=5)

        assert [r.id for r in results] == [7, 3]
        assert results[0].distance == pytest.approx(0.12)
        assert results[0].similarity == pytest.approx(0.88)
        assert results[0].similarity + results[0].distance == pytest.approx(1.0)
        assert results[0].source_id == "doc1"
        assert results[0].document_title == "Doc 1"
        embedding_service.embed_query.assert_awaited_once_with("how long do refunds take?")

    @pytest.mark.asyncio
    async def test_uses_cosine_distance_and_bound_limit(self, service: RAGRetrievalService):
        """SQL uses cosine distance operator and parameterized LIMIT."""
        cursor = FakeCursor(rows=[])
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
        ):
            await service.semantic_search_chunks("refund policy", limit=3)

        sql, params = cursor.executed[0]
        assert "dc.embedding <=> %(query_embedding)s" in sql
        assert "ORDER BY dc.embedding <=> %(query_embedding)s" in sql
        assert "LIMIT %(limit)s" in sql
        assert params["limit"] == 3
        assert "LIMIT 3" not in sql

    @pytest.mark.asyncio
    async def test_no_where_clause_without_filters(self, service: RAGRetrievalService):
        """No WHERE clause when no metadata filters provided."""
        cursor = FakeCursor(rows=[])
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
        ):
            await service.semantic_search_chunks("shipping")

        sql, params = cursor.executed[0]
        assert "WHERE" not in sql
        assert "filters" not in params

    @pytest.mark.asyncio
    async def test_applies_parameterized_metadata_filter(self, service: RAGRetrievalService):
        """WHERE dc.metadata @> %(filters)s with Jsonb when metadata filters provided."""
        cursor = FakeCursor(rows=[])
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
        ):
            await service.semantic_search_chunks(
                "shipping", limit=5, metadata_filters={"source": "faq"}
            )

        sql, params = cursor.executed[0]
        assert "WHERE dc.metadata @> %(filters)s" in sql
        assert isinstance(params["filters"], Jsonb)
        assert params["filters"].obj == {"source": "faq"}
        assert "faq" not in sql

    @pytest.mark.asyncio
    async def test_rejects_empty_query(self, service: RAGRetrievalService):
        with pytest.raises(ValueError, match="Search query must not be empty"):
            await service.semantic_search_chunks("  ", limit=5)

    @pytest.mark.asyncio
    async def test_rejects_invalid_limits(self, service: RAGRetrievalService):
        for limit in (0, -1, 101):
            with pytest.raises(ValueError, match="limit"):
                await service.semantic_search_chunks("query", limit=limit)

    @pytest.mark.asyncio
    async def test_wraps_database_errors(self, service: RAGRetrievalService):
        """psycopg errors are wrapped in DocumentStoreError."""
        cursor = FakeCursor()
        cursor.execute = AsyncMock(side_effect=psycopg.ProgrammingError("bad sql"))
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
            pytest.raises(DocumentStoreError, match="Failed to search chunks"),
        ):
            await service.semantic_search_chunks("query")

    @pytest.mark.asyncio
    async def test_missing_database_url(self, service: RAGRetrievalService, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(DocumentStoreError, match="DATABASE_URL is not configured"):
            await service.semantic_search_chunks("query")

    @pytest.mark.asyncio
    async def test_credentials_never_logged(
        self, service: RAGRetrievalService, monkeypatch, caplog
    ):
        monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
        rows = [
            {
                "id": 1,
                "document_id": 1,
                "chunk_index": 0,
                "content": "chunk",
                "metadata": {},
                "created_at": None,
                "distance": 0.1,
                "similarity": 0.9,
                "source_id": "doc1",
                "document_title": "Doc 1",
                "document_metadata": {},
            }
        ]
        cursor = FakeCursor(rows=rows)
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
            caplog.at_level(logging.INFO),
        ):
            await service.semantic_search_chunks("content")

        assert "s3cret-pass" not in caplog.text
        assert DATABASE_URL not in caplog.text


# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------


class TestKeywordSearchChunks:
    @pytest.mark.asyncio
    async def test_returns_ranked_results(
        self, service: RAGRetrievalService, embedding_service: MagicMock
    ):
        """Keyword search returns results ordered by ts_rank, rank populated."""
        rows = [
            {
                "id": 1,
                "document_id": 42,
                "chunk_index": 0,
                "content": "Refunds are processed in five business days.",
                "metadata": {"category": "returns_refunds"},
                "created_at": None,
                "rank": 0.8472,
                "source_id": "doc1",
                "document_title": "Doc 1",
                "document_metadata": {"category": "returns_refunds"},
            },
            {
                "id": 2,
                "document_id": 42,
                "chunk_index": 1,
                "content": "Return window is 30 days from delivery.",
                "metadata": {"category": "returns_refunds"},
                "created_at": None,
                "rank": 0.6321,
                "source_id": "doc1",
                "document_title": "Doc 1",
                "document_metadata": {"category": "returns_refunds"},
            },
        ]
        cursor = FakeCursor(rows=rows)
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
        ):
            results = await service.keyword_search_chunks("return policy refund", limit=5)

        assert [r.id for r in results] == [1, 2]
        assert results[0].rank == pytest.approx(0.8472)
        assert results[1].rank == pytest.approx(0.6321)
        assert results[0].rank > results[1].rank
        # Keyword search must NOT call the embedding service.
        embedding_service.embed_query.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_uses_ts_rank_and_tsquery(self, service: RAGRetrievalService):
        """SQL uses ts_rank and to_tsquery, parameterized."""
        cursor = FakeCursor(rows=[])
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
        ):
            await service.keyword_search_chunks("return policy", limit=3)

        sql, _params = cursor.executed[0]
        assert "ts_rank(dc.tsvector_content, to_tsquery('english', %(tsquery)s))" in sql
        assert "dc.tsvector_content @@ to_tsquery('english', %(tsquery)s)" in sql
        assert "LIMIT %(limit)s" in sql
        assert "LIMIT 3" not in sql

    @pytest.mark.asyncio
    async def test_applies_metadata_filter(self, service: RAGRetrievalService):
        """AND dc.metadata @> %(filters)s when metadata filters provided."""
        cursor = FakeCursor(rows=[])
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
        ):
            await service.keyword_search_chunks(
                "order tracking", limit=5, metadata_filters={"source": "faq"}
            )

        sql, params = cursor.executed[0]
        assert "AND dc.metadata @> %(filters)s" in sql
        assert isinstance(params["filters"], Jsonb)
        assert params["filters"].obj == {"source": "faq"}

    @pytest.mark.asyncio
    async def test_rejects_empty_query(self, service: RAGRetrievalService):
        with pytest.raises(ValueError, match="Search query must not be empty"):
            await service.keyword_search_chunks("  ")

    @pytest.mark.asyncio
    async def test_rejects_query_without_tokens(self, service: RAGRetrievalService):
        with pytest.raises(
            ValueError,
            match="Search query must contain at least one alphanumeric token",
        ):
            await service.keyword_search_chunks("!!! ???")

    @pytest.mark.asyncio
    async def test_rejects_invalid_limit(self, service: RAGRetrievalService):
        for limit in (0, -1, 101):
            with pytest.raises(ValueError, match="limit"):
                await service.keyword_search_chunks("test", limit=limit)

    @pytest.mark.asyncio
    async def test_wraps_database_errors(self, service: RAGRetrievalService):
        cursor = FakeCursor()
        cursor.execute = AsyncMock(side_effect=psycopg.ProgrammingError("bad sql"))
        conn = FakeConnection(cursor)

        with (
            patch(
                "app.services.rag_retrieval_service.AsyncConnection.connect",
                new=AsyncMock(return_value=conn),
            ),
            patch(
                "app.services.rag_retrieval_service.register_vector_async",
                new=AsyncMock(),
            ),
            pytest.raises(DocumentStoreError, match="Failed to search chunks"),
        ):
            await service.keyword_search_chunks("query")

    @pytest.mark.asyncio
    async def test_missing_database_url(self, service: RAGRetrievalService, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(DocumentStoreError, match="DATABASE_URL is not configured"):
            await service.keyword_search_chunks("query")


# ---------------------------------------------------------------------------
# Hybrid retrieval (RRF)
# ---------------------------------------------------------------------------


class TestHybridSearchChunks:
    @pytest.mark.asyncio
    async def test_semantic_embedding_called_once(
        self, service: RAGRetrievalService, embedding_service: MagicMock
    ):
        """Hybrid retrieval generates the query embedding exactly once."""
        service.semantic_search_chunks = AsyncMock(return_value=[])
        service.keyword_search_chunks = AsyncMock(return_value=[])

        await service.hybrid_search_chunks("test query", limit=3, rrf_k=60)

        # The embedding is generated inside semantic_search_chunks once.
        assert embedding_service.embed_query.await_count == 0
        # semantic_search_chunks called with the query (so embed_query would
        # have been called once inside it in a real run)
        service.semantic_search_chunks.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rrf_score_calculation_combined(self, service: RAGRetrievalService):
        """Chunk in both lists: RRF = 1/(k+1) + 1/(k+1) = 2/61 with rrf_k=60."""
        service.semantic_search_chunks = AsyncMock(
            return_value=[_make_chunk_result(id=1, distance=0.2, similarity=0.8)],
        )
        service.keyword_search_chunks = AsyncMock(
            return_value=[_make_chunk_result(id=1, rank=0.7)],
        )

        results = await service.hybrid_search_chunks("test", limit=5, rrf_k=60)

        assert len(results) == 1
        expected_rrf = 2.0 / 61.0
        assert results[0].rrf_score == pytest.approx(expected_rrf, abs=1e-6)
        # Both semantic and keyword scores preserved.
        assert results[0].distance == pytest.approx(0.2)
        assert results[0].rank == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_rrf_chunk_only_in_semantic(self, service: RAGRetrievalService):
        """Chunk only in semantic list: RRF = 1/(k+1) = 1/61."""
        service.semantic_search_chunks = AsyncMock(
            return_value=[_make_chunk_result(id=1, distance=0.2, similarity=0.8)],
        )
        service.keyword_search_chunks = AsyncMock(return_value=[])

        results = await service.hybrid_search_chunks("test", limit=5, rrf_k=60)

        assert len(results) == 1
        expected_rrf = 1.0 / 61.0
        assert results[0].rrf_score == pytest.approx(expected_rrf, abs=1e-6)
        assert results[0].distance == pytest.approx(0.2)
        assert results[0].rank is None

    @pytest.mark.asyncio
    async def test_rrf_chunk_only_in_keyword(self, service: RAGRetrievalService):
        """Chunk only in keyword list: RRF = 1/(k+1) = 1/61."""
        service.semantic_search_chunks = AsyncMock(return_value=[])
        service.keyword_search_chunks = AsyncMock(
            return_value=[_make_chunk_result(id=1, rank=0.7)],
        )

        results = await service.hybrid_search_chunks("test", limit=5, rrf_k=60)

        assert len(results) == 1
        expected_rrf = 1.0 / 61.0
        assert results[0].rrf_score == pytest.approx(expected_rrf, abs=1e-6)
        assert results[0].rank == pytest.approx(0.7)
        assert results[0].distance is None

    @pytest.mark.asyncio
    async def test_deduplicates_chunks(self, service: RAGRetrievalService):
        """Duplicate chunk IDs appearing in both lists are merged into one result."""
        service.semantic_search_chunks = AsyncMock(
            return_value=[
                _make_chunk_result(id=1, distance=0.2, similarity=0.8),
                _make_chunk_result(id=2, distance=0.3, similarity=0.7),
            ],
        )
        service.keyword_search_chunks = AsyncMock(
            return_value=[_make_chunk_result(id=2, rank=0.6)],
        )

        results = await service.hybrid_search_chunks("test", limit=5, rrf_k=60)

        # Two unique chunk ids.
        assert len(results) == 2
        ids = [r.id for r in results]
        assert len(set(ids)) == len(ids)

    @pytest.mark.asyncio
    async def test_sorts_by_descending_rrf(self, service: RAGRetrievalService):
        """Results sorted by descending RRF score."""
        service.semantic_search_chunks = AsyncMock(
            return_value=[
                _make_chunk_result(id=1, distance=0.2, similarity=0.8),
                _make_chunk_result(id=3, distance=0.5, similarity=0.5),
            ],
        )
        service.keyword_search_chunks = AsyncMock(
            return_value=[
                _make_chunk_result(id=2, rank=0.7),
                _make_chunk_result(id=3, rank=0.4),
            ],
        )

        results = await service.hybrid_search_chunks("test", limit=5, rrf_k=60)

        # Chunk 3: semantic rank 2 + keyword rank 2 -> 1/62 + 1/62 = 2/62
        # Chunk 1: semantic rank 1 only -> 1/61
        # Chunk 2: keyword rank 1 only -> 1/61
        assert results[0].id == 3
        assert results[0].rrf_score == pytest.approx(2.0 / 62.0, abs=1e-6)
        assert len(results[1:]) == 2

    @pytest.mark.asyncio
    async def test_respects_final_limit(self, service: RAGRetrievalService):
        """Hybrid returns at most `limit` final results."""
        sem = [
            _make_chunk_result(id=i, distance=0.1 * i, similarity=1 - 0.1 * i) for i in range(1, 6)
        ]
        kw = [_make_chunk_result(id=i, rank=0.7 - 0.1 * i) for i in range(1, 6)]
        service.semantic_search_chunks = AsyncMock(return_value=sem)
        service.keyword_search_chunks = AsyncMock(return_value=kw)

        results = await service.hybrid_search_chunks("test", limit=3, rrf_k=60)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rejects_invalid_rrf_k(self, service: RAGRetrievalService):
        with pytest.raises(ValueError, match="rrf_k must be a positive integer"):
            await service.hybrid_search_chunks("test", limit=5, rrf_k=0)

    @pytest.mark.asyncio
    async def test_rejects_negative_rrf_k(self, service: RAGRetrievalService):
        with pytest.raises(ValueError, match="rrf_k must be a positive integer"):
            await service.hybrid_search_chunks("test", limit=5, rrf_k=-10)

    @pytest.mark.asyncio
    async def test_rejects_empty_query(self, service: RAGRetrievalService):
        with pytest.raises(ValueError, match="Search query must not be empty"):
            await service.hybrid_search_chunks("", limit=5)

    @pytest.mark.asyncio
    async def test_rejects_invalid_limit(self, service: RAGRetrievalService):
        with pytest.raises(ValueError, match="Search limit must be a positive integer"):
            await service.hybrid_search_chunks("test", limit=0)

    @pytest.mark.asyncio
    async def test_semantic_and_keyword_called(self, service: RAGRetrievalService):
        """Hybrid calls both semantic and keyword sub-searches."""
        service.semantic_search_chunks = AsyncMock(return_value=[])
        service.keyword_search_chunks = AsyncMock(return_value=[])

        await service.hybrid_search_chunks("test", limit=5)

        service.semantic_search_chunks.assert_awaited_once()
        service.keyword_search_chunks.assert_awaited_once()
