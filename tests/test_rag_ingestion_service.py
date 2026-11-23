"""Tests for the RAG ingestion service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest

from app.services.document_service import DocumentStoreError
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import EmbeddedChunk, LoadedDocument
from app.services.rag_ingestion_service import RagIngestionService


def _make_mock_connection() -> tuple[MagicMock, MagicMock]:
    """Create a mock async connection and cursor.

    The connection and its cursor/transaction context managers are wired up
    so that ``async with conn``, ``async with conn.cursor()``, and
    ``async with conn.transaction()`` all work against mocks.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchone = AsyncMock()

    mock_cursor_ctx = MagicMock()
    mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor_ctx

    mock_tx_ctx = MagicMock()
    mock_tx_ctx.__aenter__ = AsyncMock(return_value=None)
    mock_tx_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction.return_value = mock_tx_ctx

    mock_conn.close = AsyncMock()
    return mock_conn, mock_cursor


def _patch_database(mock_conn):
    """Return a patch context that makes _connect yield ``mock_conn``."""
    connect_patch = patch(
        "app.services.rag_ingestion_service.AsyncConnection.connect",
        new=AsyncMock(return_value=mock_conn),
    )
    register_patch = patch(
        "app.services.rag_ingestion_service.register_vector_async",
        new=AsyncMock(return_value=None),
    )
    return connect_patch, register_patch


class TestRagIngestionServiceInit:
    def test_creates_default_embedding_service(self):
        service = RagIngestionService()
        assert isinstance(service.embedding_service, EmbeddingService)

    def test_accepts_injected_embedding_service(self):
        mock_service = MagicMock(spec=EmbeddingService)
        service = RagIngestionService(embedding_service=mock_service)
        assert service.embedding_service is mock_service


class TestRagIngestionServiceIngestEmpty:
    def test_empty_input_returns_zero_counts(self):
        service = RagIngestionService()
        result = asyncio.run(service.ingest([], []))
        assert result == {"documents_ingested": 0, "chunks_ingested": 0, "document_ids": {}}


class TestRagIngestionServiceEmbedValidation:
    def test_invalid_document_embedding_dimensions_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 100)

        service = RagIngestionService(embedding_service=mock_embedding_service)
        documents = [
            LoadedDocument(
                source_id="test",
                title="Test Doc",
                content="Content.",
                metadata={"source_id": "test", "title": "Test Doc"},
            )
        ]

        with pytest.raises(ValueError, match="has 100 dimensions, expected 768"):
            asyncio.run(service._embed_documents(documents))

    def test_invalid_chunk_embedding_dimensions_raises(self):
        service = RagIngestionService()
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test Doc",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test Doc", "chunk_index": 0},
                ),
                embedding=[0.2] * 50,
            )
        ]

        with pytest.raises(ValueError, match="has 50 dimensions, expected 768"):
            service._validate_chunk_embeddings(chunks)

    def test_invalid_chunk_embedding_skips_document_embedding(self):
        """Regression: chunk embedding validation runs before Gemini document calls."""
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="test",
                title="Test Doc",
                content="Full document.",
                metadata={"source_id": "test", "title": "Test Doc"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test Doc",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test Doc", "chunk_index": 0},
                ),
                embedding=[0.2] * 50,  # wrong dimension
            )
        ]

        with pytest.raises(ValueError, match="has 50 dimensions, expected 768"):
            asyncio.run(service.ingest(documents, chunks))

        # Embedding service must not have been called for the document.
        mock_embedding_service.embed_document.assert_not_awaited()


class TestRagIngestionServiceValidation:
    def test_chunk_source_id_mismatch_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)

        service = RagIngestionService(embedding_service=mock_embedding_service)
        documents = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="Content.",
                metadata={"source_id": "doc1", "title": "Doc 1"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="doc2",
                    title="Doc 2",
                    content="Chunk.",
                    metadata={"source_id": "doc2", "title": "Doc 2", "chunk_index": 0},
                ),
                embedding=[0.1] * 768,
            )
        ]

        with pytest.raises(ValueError, match="does not match any input document"):
            asyncio.run(service.ingest(documents, chunks))


class TestRagIngestionServiceChunkIndexValidation:
    """Regression tests for chunk_index validation before embedding or DB access."""

    def test_missing_chunk_index_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)
        documents = [
            LoadedDocument(
                source_id="test",
                title="Test Doc",
                content="Content.",
                metadata={"source_id": "test", "title": "Test Doc"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test Doc",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test Doc"},  # no chunk_index
                ),
                embedding=[0.1] * 768,
            )
        ]

        with pytest.raises(ValueError, match="missing chunk_index in metadata"):
            asyncio.run(service.ingest(documents, chunks))

        # Validation must happen before embedding: no Gemini calls made.
        mock_embedding_service.embed_document.assert_not_awaited()

    def test_negative_chunk_index_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)
        documents = [
            LoadedDocument(
                source_id="test",
                title="Test Doc",
                content="Content.",
                metadata={"source_id": "test", "title": "Test Doc"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test Doc",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test Doc", "chunk_index": -1},
                ),
                embedding=[0.1] * 768,
            )
        ]

        with pytest.raises(ValueError, match=r"Invalid chunk_index.*non-negative"):
            asyncio.run(service.ingest(documents, chunks))

        mock_embedding_service.embed_document.assert_not_awaited()

    def test_string_chunk_index_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)
        documents = [
            LoadedDocument(
                source_id="test",
                title="Test Doc",
                content="Content.",
                metadata={"source_id": "test", "title": "Test Doc"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test Doc",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test Doc", "chunk_index": "0"},
                ),
                embedding=[0.1] * 768,
            )
        ]

        with pytest.raises(ValueError, match=r"Invalid chunk_index.*non-negative integer"):
            asyncio.run(service.ingest(documents, chunks))

        mock_embedding_service.embed_document.assert_not_awaited()

    def test_boolean_chunk_index_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)
        documents = [
            LoadedDocument(
                source_id="test",
                title="Test Doc",
                content="Content.",
                metadata={"source_id": "test", "title": "Test Doc"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test Doc",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test Doc", "chunk_index": True},
                ),
                embedding=[0.1] * 768,
            )
        ]

        with pytest.raises(ValueError, match=r"Invalid chunk_index.*non-negative integer"):
            asyncio.run(service.ingest(documents, chunks))

        mock_embedding_service.embed_document.assert_not_awaited()

    def test_duplicate_chunk_indexes_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)
        documents = [
            LoadedDocument(
                source_id="multi",
                title="Multi Chunk",
                content="Content.",
                metadata={"source_id": "multi", "title": "Multi Chunk"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="multi",
                    title="Multi Chunk",
                    content="Chunk 1.",
                    metadata={"source_id": "multi", "title": "Multi Chunk", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="multi",
                    title="Multi Chunk",
                    content="Chunk 2.",
                    metadata={"source_id": "multi", "title": "Multi Chunk", "chunk_index": 0},
                ),
                embedding=[0.3] * 768,
            ),
        ]

        with pytest.raises(ValueError, match=r"Duplicate chunk_index.*source_id=multi"):
            asyncio.run(service.ingest(documents, chunks))

        mock_embedding_service.embed_document.assert_not_awaited()


class TestRagIngestionServiceOrphanChunks:
    """Regression tests for orphan chunk rejection."""

    def test_empty_documents_with_non_empty_chunks_raises(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="orphan",
                    title="Orphan",
                    content="Chunk.",
                    metadata={"source_id": "orphan", "title": "Orphan", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            )
        ]

        with pytest.raises(ValueError, match="Chunks cannot be ingested without parent documents"):
            asyncio.run(service.ingest([], chunks))

        mock_embedding_service.embed_document.assert_not_awaited()

    def test_empty_documents_and_empty_chunks_returns_zero_counts(self):
        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        result = asyncio.run(service.ingest([], []))
        assert result == {"documents_ingested": 0, "chunks_ingested": 0, "document_ids": {}}

        mock_embedding_service.embed_document.assert_not_awaited()


class TestRagIngestionServiceDatabase:
    def test_new_document_insertion(self):
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 42})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="test_doc",
                title="Test Document",
                content="Full document content.",
                metadata={"source_id": "test_doc", "title": "Test Document", "category": "test"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test_doc",
                    title="Test Document",
                    content="Chunk 1.",
                    metadata={
                        "source_id": "test_doc",
                        "title": "Test Document",
                        "chunk_index": 0,
                        "category": "test",
                    },
                ),
                embedding=[0.2] * 768,
            ),
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test_doc",
                    title="Test Document",
                    content="Chunk 2.",
                    metadata={
                        "source_id": "test_doc",
                        "title": "Test Document",
                        "chunk_index": 1,
                        "category": "test",
                    },
                ),
                embedding=[0.3] * 768,
            ),
        ]

        with connect_patch, register_patch:
            result = asyncio.run(service.ingest(documents, chunks))

        assert result["documents_ingested"] == 1
        assert result["chunks_ingested"] == 2
        assert result["document_ids"] == {"test_doc": 42}

        # Verify upsert was called (SQL contains INSERT INTO documents)
        upsert_calls = [
            c for c in mock_cursor.execute.call_args_list if "INSERT INTO documents" in str(c)
        ]
        assert len(upsert_calls) == 1
        upsert_params = upsert_calls[0][0][1]
        assert upsert_params["source_id"] == "test_doc"

        # Verify chunks inserted reuse stored embeddings
        insert_calls = [
            c for c in mock_cursor.execute.call_args_list if "INSERT INTO document_chunks" in str(c)
        ]
        assert len(insert_calls) == 2

        # Verify chunk delete was called for the document
        delete_calls = [
            c for c in mock_cursor.execute.call_args_list if "DELETE FROM document_chunks" in str(c)
        ]
        assert len(delete_calls) == 1
        delete_params = delete_calls[0][0][1]
        assert delete_params["document_id"] == 42

    def test_multiple_documents(self):
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(
            side_effect=[
                {"id": 100},  # doc 1 id
                {"id": 200},  # doc 2 id
            ]
        )
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="Content 1.",
                metadata={"source_id": "doc1", "title": "Doc 1"},
            ),
            LoadedDocument(
                source_id="doc2",
                title="Doc 2",
                content="Content 2.",
                metadata={"source_id": "doc2", "title": "Doc 2"},
            ),
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="doc1",
                    title="Doc 1",
                    content="Chunk 1.",
                    metadata={"source_id": "doc1", "title": "Doc 1", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="doc2",
                    title="Doc 2",
                    content="Chunk 2.",
                    metadata={"source_id": "doc2", "title": "Doc 2", "chunk_index": 0},
                ),
                embedding=[0.3] * 768,
            ),
        ]

        with connect_patch, register_patch:
            result = asyncio.run(service.ingest(documents, chunks))

        assert result["documents_ingested"] == 2
        assert result["chunks_ingested"] == 2
        assert result["document_ids"] == {"doc1": 100, "doc2": 200}

    def test_re_ingestion_updates_existing_document(self):
        """Test that re-ingesting same source_id updates document and replaces chunks."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 55})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="existing_doc",
                title="Existing Document",
                content="Updated content.",
                metadata={"source_id": "existing_doc", "title": "Existing Document"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="existing_doc",
                    title="Existing Document",
                    content="New chunk.",
                    metadata={
                        "source_id": "existing_doc",
                        "title": "Existing Document",
                        "chunk_index": 0,
                    },
                ),
                embedding=[0.2] * 768,
            ),
        ]

        with connect_patch, register_patch:
            result = asyncio.run(service.ingest(documents, chunks))

        assert result["documents_ingested"] == 1
        assert result["chunks_ingested"] == 1
        assert result["document_ids"] == {"existing_doc": 55}

        # Verify delete chunks was called for the document
        delete_calls = [
            c for c in mock_cursor.execute.call_args_list if "DELETE FROM document_chunks" in str(c)
        ]
        assert len(delete_calls) == 1
        delete_params = delete_calls[0][0][1]
        assert delete_params["document_id"] == 55

    def test_chunk_conflict_update(self):
        """Test that ON CONFLICT for chunks works (same chunk_index)."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 10})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="test",
                title="Test",
                content="Content.",
                metadata={"source_id": "test", "title": "Test"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test",
                    content="Updated chunk.",
                    metadata={"source_id": "test", "title": "Test", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
        ]

        with connect_patch, register_patch:
            result = asyncio.run(service.ingest(documents, chunks))

        assert result["chunks_ingested"] == 1
        # Verify insert chunk was called with ON CONFLICT
        insert_calls = [
            c for c in mock_cursor.execute.call_args_list if "INSERT INTO document_chunks" in str(c)
        ]
        assert len(insert_calls) == 1
        assert "ON CONFLICT" in str(insert_calls[0])

    def test_metadata_preservation(self):
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 1})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="meta_test",
                title="Meta Test",
                content="Content.",
                metadata={
                    "source_id": "meta_test",
                    "title": "Meta Test",
                    "custom_field": "custom_value",
                    "numeric": 42,
                    "tags": ["a", "b"],
                },
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="meta_test",
                    title="Meta Test",
                    content="Chunk.",
                    metadata={
                        "source_id": "meta_test",
                        "title": "Meta Test",
                        "custom_field": "custom_value",
                        "numeric": 42,
                        "tags": ["a", "b"],
                        "chunk_index": 0,
                        "chunk_size": 500,
                        "chunk_overlap": 50,
                    },
                ),
                embedding=[0.2] * 768,
            ),
        ]

        with connect_patch, register_patch:
            result = asyncio.run(service.ingest(documents, chunks))

        assert result["documents_ingested"] == 1

        # Verify upsert was called with full metadata
        upsert_calls = [
            c for c in mock_cursor.execute.call_args_list if "INSERT INTO documents" in str(c)
        ]
        assert len(upsert_calls) == 1
        params = upsert_calls[0][0][1]
        metadata = params["metadata"]
        if hasattr(metadata, "obj"):
            metadata = metadata.obj
        assert metadata["custom_field"] == "custom_value"
        assert metadata["numeric"] == 42
        assert metadata["tags"] == ["a", "b"]

    def test_document_with_zero_chunks_still_deletes_existing_chunks(self):
        """Regression: re-ingesting a source that now yields zero chunks must still
        clear any previously stored chunks for that document."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 77})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="empty_doc",
                title="Empty Doc",
                content="Content.",
                metadata={"source_id": "empty_doc", "title": "Empty Doc"},
            )
        ]

        with connect_patch, register_patch:
            result = asyncio.run(service.ingest(documents, []))

        assert result["documents_ingested"] == 1
        assert result["chunks_ingested"] == 0

        delete_calls = [
            c for c in mock_cursor.execute.call_args_list if "DELETE FROM document_chunks" in str(c)
        ]
        assert len(delete_calls) == 1
        delete_params = delete_calls[0][0][1]
        assert delete_params["document_id"] == 77

    def test_chunk_embeddings_reused_not_re_embedded(self):
        """Regression: chunk embeddings must be reused from EmbeddedChunk instead of
        triggering new Gemini embedding calls."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 42})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="test_doc",
                title="Test Document",
                content="Full document content.",
                metadata={"source_id": "test_doc", "title": "Test Document"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test_doc",
                    title="Test Document",
                    content="Chunk 1.",
                    metadata={"source_id": "test_doc", "title": "Test Document", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test_doc",
                    title="Test Document",
                    content="Chunk 2.",
                    metadata={"source_id": "test_doc", "title": "Test Document", "chunk_index": 1},
                ),
                embedding=[0.3] * 768,
            ),
        ]

        with connect_patch, register_patch:
            asyncio.run(service.ingest(documents, chunks))

        # Only the full-document embedding should have been generated; chunk
        # embeddings were reused.
        assert mock_embedding_service.embed_document.await_count == 1

    def test_database_connection_error_raises(self):
        connect_patch = patch(
            "app.services.rag_ingestion_service.AsyncConnection.connect",
            new=AsyncMock(side_effect=psycopg.Error("Connection refused")),
        )

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="test",
                title="Test",
                content="Content.",
                metadata={"source_id": "test", "title": "Test"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
        ]

        with connect_patch, pytest.raises(DocumentStoreError, match="Could not connect"):
            asyncio.run(service.ingest(documents, chunks))

    def test_database_error_during_ingest_raises(self):
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.execute = AsyncMock(side_effect=psycopg.Error("Deadlock"))
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="test",
                title="Test",
                content="Content.",
                metadata={"source_id": "test", "title": "Test"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="test",
                    title="Test",
                    content="Chunk.",
                    metadata={"source_id": "test", "title": "Test", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
        ]

        with (
            connect_patch,
            register_patch,
            pytest.raises(DocumentStoreError, match="Failed to ingest"),
        ):
            asyncio.run(service.ingest(documents, chunks))

    def test_advisory_lock_acquisition_order(self):
        """Test that advisory locks are acquired in sorted order to avoid deadlocks."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(
            side_effect=[
                {"id": 1},
                {"id": 2},
            ]
        )
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="z_last",
                title="Z",
                content="C.",
                metadata={"source_id": "z_last", "title": "Z"},
            ),
            LoadedDocument(
                source_id="a_first",
                title="A",
                content="C.",
                metadata={"source_id": "a_first", "title": "A"},
            ),
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="z_last",
                    title="Z",
                    content="C.",
                    metadata={"source_id": "z_last", "title": "Z", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="a_first",
                    title="A",
                    content="C.",
                    metadata={"source_id": "a_first", "title": "A", "chunk_index": 0},
                ),
                embedding=[0.3] * 768,
            ),
        ]

        with connect_patch, register_patch:
            asyncio.run(service.ingest(documents, chunks))

        # Find advisory lock calls
        lock_calls = [
            c for c in mock_cursor.execute.call_args_list if "pg_advisory_xact_lock" in str(c)
        ]
        # Should acquire a_first before z_last
        assert len(lock_calls) == 2
        assert lock_calls[0].args[1]["source_id"] == "a_first"
        assert lock_calls[1].args[1]["source_id"] == "z_last"

    def test_concurrent_ingestion_same_source_id(self):
        """Test that advisory locks prevent concurrent modification of same source_id."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 1})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="shared",
                title="Shared",
                content="C.",
                metadata={"source_id": "shared", "title": "Shared"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="shared",
                    title="Shared",
                    content="C.",
                    metadata={"source_id": "shared", "title": "Shared", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
        ]

        with connect_patch, register_patch:
            asyncio.run(service.ingest(documents, chunks))

        # Advisory lock was acquired
        lock_calls = [
            c for c in mock_cursor.execute.call_args_list if "pg_advisory_xact_lock" in str(c)
        ]
        assert len(lock_calls) == 1
        assert lock_calls[0].args[1]["source_id"] == "shared"


class TestRagIngestionServiceDuplicates:
    """Regression tests for duplicate detection before ingestion."""

    def test_duplicate_document_source_ids_raises(self):
        """Duplicate source_id values in the input list are rejected."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 42})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="shared",
                title="First Doc",
                content="Content A.",
                metadata={"source_id": "shared", "title": "First Doc"},
            ),
            LoadedDocument(
                source_id="shared",
                title="Second Doc",
                content="Content B.",
                metadata={"source_id": "shared", "title": "Second Doc"},
            ),
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="shared",
                    title="First Doc",
                    content="Chunk A.",
                    metadata={"source_id": "shared", "title": "First Doc", "chunk_index": 0},
                ),
                embedding=[0.2] * 768,
            ),
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="shared",
                    title="Second Doc",
                    content="Chunk B.",
                    metadata={"source_id": "shared", "title": "Second Doc", "chunk_index": 0},
                ),
                embedding=[0.3] * 768,
            ),
        ]

        with (
            connect_patch,
            register_patch,
            pytest.raises(ValueError, match="Duplicate source_id"),
        ):
            asyncio.run(service.ingest(documents, chunks))

    def test_duplicate_chunk_indexes_raises(self):
        """Duplicate (source_id, chunk_index) pairs are rejected."""
        mock_conn, mock_cursor = _make_mock_connection()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 42})
        connect_patch, register_patch = _patch_database(mock_conn)

        mock_embedding_service = MagicMock(spec=EmbeddingService)
        mock_embedding_service.embed_document = AsyncMock(return_value=[0.1] * 768)
        service = RagIngestionService(embedding_service=mock_embedding_service)

        documents = [
            LoadedDocument(
                source_id="multi_chunk",
                title="Multi Chunk Doc",
                content="Content.",
                metadata={"source_id": "multi_chunk", "title": "Multi Chunk Doc"},
            )
        ]
        chunks = [
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="multi_chunk",
                    title="Multi Chunk Doc",
                    content="Chunk 1.",
                    metadata={
                        "source_id": "multi_chunk",
                        "title": "Multi Chunk Doc",
                        "chunk_index": 0,
                    },
                ),
                embedding=[0.2] * 768,
            ),
            EmbeddedChunk(
                document=LoadedDocument(
                    source_id="multi_chunk",
                    title="Multi Chunk Doc",
                    content="Chunk 2.",
                    metadata={
                        "source_id": "multi_chunk",
                        "title": "Multi Chunk Doc",
                        "chunk_index": 0,
                    },
                ),
                embedding=[0.3] * 768,
            ),
        ]

        with (
            connect_patch,
            register_patch,
            pytest.raises(ValueError, match="Duplicate chunk_index"),
        ):
            asyncio.run(service.ingest(documents, chunks))


class TestRagIngestionServiceHelper:
    pass
