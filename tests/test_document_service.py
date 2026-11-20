import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest
from pgvector import Vector
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.services.document_service import (
    DatabaseNotConfiguredError,
    DocumentService,
    DocumentStoreError,
    SearchResult,
)

DATABASE_URL = "postgresql://demo_user:s3cret-pass@ep-demo.neon.tech/neondb"
SAMPLE_EMBEDDING = [0.01 * index for index in range(768)]


class FakeCursor:
    def __init__(self, row=None, rows=None) -> None:
        self.row = row
        self.rows = rows or []
        self.executed: list[tuple[str, dict | None]] = []

    async def execute(self, sql, params=None) -> None:
        self.executed.append((sql, params))

    async def fetchone(self):
        return self.row

    async def fetchall(self):
        return self.rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


class FakeConnection:
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
    service = MagicMock()
    service.embed_document = AsyncMock(return_value=SAMPLE_EMBEDDING)
    service.embed_query = AsyncMock(return_value=SAMPLE_EMBEDDING)
    return service


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    cursor = FakeCursor(row={"id": 42})
    conn = FakeConnection(cursor)
    with (
        patch(
            "app.services.document_service.AsyncConnection.connect",
            new=AsyncMock(return_value=conn),
        ) as connect_mock,
        patch(
            "app.services.document_service.register_vector_async",
            new=AsyncMock(),
        ) as register_mock,
    ):
        yield SimpleNamespace(
            conn=conn,
            cursor=cursor,
            connect=connect_mock,
            register=register_mock,
        )


@pytest.fixture
def service(embedding_service) -> DocumentService:
    return DocumentService(embedding_service=embedding_service)


async def test_insert_document_returns_id_and_commits(service, embedding_service, db):
    document_id = await service.insert_document("Orders ship within 48 hours.")

    assert document_id == 42
    embedding_service.embed_document.assert_awaited_once_with("Orders ship within 48 hours.")
    assert db.conn.committed is True
    assert db.conn.closed is True
    assert db.register.await_count == 1


async def test_insert_document_persists_content_vector_and_jsonb_metadata(service, db):
    await service.insert_document("Refunds take five days.", {"source": "faq", "lang": "en"})

    sql, params = db.cursor.executed[0]
    assert params["content"] == "Refunds take five days."
    assert isinstance(params["embedding"], Vector)
    assert params["embedding"].dimensions() == 768
    assert isinstance(params["metadata"], Jsonb)
    assert params["metadata"].obj == {"source": "faq", "lang": "en"}
    # Values are bound as parameters, never interpolated into the SQL text.
    assert "Refunds take five days." not in sql


async def test_insert_document_defaults_metadata_to_empty_object(service, db):
    await service.insert_document("Shipping policy")

    _, params = db.cursor.executed[0]
    assert params["metadata"].obj == {}


async def test_insert_document_rejects_empty_content_without_side_effects(
    service, embedding_service, db
):
    with pytest.raises(ValueError, match="must not be empty"):
        await service.insert_document("   ")

    embedding_service.embed_document.assert_not_awaited()
    db.connect.assert_not_awaited()


async def test_insert_document_raises_when_no_id_returned(service, db):
    db.cursor.row = None

    with pytest.raises(DocumentStoreError, match="did not return a document id"):
        await service.insert_document("content")


async def test_insert_document_wraps_database_errors(service, db):
    db.cursor.execute = AsyncMock(side_effect=psycopg.OperationalError("connection lost"))

    with pytest.raises(DocumentStoreError, match="Failed to insert document"):
        await service.insert_document("content")


async def test_semantic_search_returns_ordered_results(service, embedding_service, db):
    db.cursor.rows = [
        {
            "id": 7,
            "content": "Refunds are processed in five business days.",
            "metadata": {"source": "faq"},
            "created_at": None,
            "distance": 0.12,
            "similarity": 0.88,
        },
        {
            "id": 3,
            "content": "Shipping takes two days.",
            "metadata": {},
            "created_at": None,
            "distance": 0.31,
            "similarity": 0.69,
        },
    ]

    results = await service.semantic_search("how long do refunds take?", limit=2)

    assert [result.id for result in results] == [7, 3]
    assert all(isinstance(result, SearchResult) for result in results)
    assert results[0].distance == pytest.approx(0.12)
    assert results[0].similarity == pytest.approx(0.88)
    assert results[0].distance <= results[1].distance
    embedding_service.embed_query.assert_awaited_once_with("how long do refunds take?")


async def test_semantic_search_uses_cosine_distance_and_bound_limit(service, db):
    await service.semantic_search("refund policy", limit=3)

    sql, params = db.cursor.executed[0]
    assert "embedding <=> %(query_embedding)s" in sql
    assert "ORDER BY embedding <=> %(query_embedding)s" in sql
    assert "LIMIT %(limit)s" in sql
    assert params["limit"] == 3
    assert "LIMIT 3" not in sql
    assert isinstance(params["query_embedding"], Vector)


async def test_semantic_search_without_filters_has_no_where_clause(service, db):
    await service.semantic_search("shipping")

    sql, params = db.cursor.executed[0]
    assert "WHERE" not in sql
    assert "filters" not in params


async def test_semantic_search_applies_parameterized_metadata_filter(service, db):
    await service.semantic_search("shipping", limit=5, metadata_filters={"source": "faq"})

    sql, params = db.cursor.executed[0]
    assert "WHERE metadata @> %(filters)s" in sql
    assert isinstance(params["filters"], Jsonb)
    assert params["filters"].obj == {"source": "faq"}
    assert "faq" not in sql


@pytest.mark.parametrize("limit", [0, -1, 101])
async def test_semantic_search_rejects_invalid_limit(service, embedding_service, db, limit):
    with pytest.raises(ValueError, match="limit"):
        await service.semantic_search("query", limit=limit)

    embedding_service.embed_query.assert_not_awaited()
    db.connect.assert_not_awaited()


async def test_semantic_search_rejects_empty_query(service, db):
    with pytest.raises(ValueError, match="must not be empty"):
        await service.semantic_search("  ")


async def test_semantic_search_wraps_database_errors(service, db):
    db.cursor.execute = AsyncMock(side_effect=psycopg.ProgrammingError("bad sql"))

    with pytest.raises(DocumentStoreError, match="Failed to search documents"):
        await service.semantic_search("query")


async def test_connection_uses_dict_rows(service, db):
    await service.semantic_search("query")

    assert db.connect.await_args.kwargs["row_factory"] is dict_row


async def test_missing_database_url_raises_before_connecting(service, db, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(DatabaseNotConfiguredError, match="DATABASE_URL is not configured"):
        await service.insert_document("content")

    db.connect.assert_not_awaited()


async def test_connection_failure_is_wrapped(service, db):
    db.connect.side_effect = psycopg.OperationalError("could not connect")

    with pytest.raises(DocumentStoreError, match="Could not connect"):
        await service.insert_document("content")


async def test_credentials_are_never_logged(service, db, caplog):
    with caplog.at_level(logging.DEBUG):
        await service.insert_document("content")
        await service.semantic_search("content")

    assert "s3cret-pass" not in caplog.text
    assert DATABASE_URL not in caplog.text
    assert "store=documents operation=insert status=success" in caplog.text
    assert "store=documents operation=search status=success" in caplog.text
