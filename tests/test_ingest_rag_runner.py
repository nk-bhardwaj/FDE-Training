"""Tests for the RAG ingestion runner."""

from argparse import Namespace
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion_service import EmbeddedChunk, LoadedDocument
from scripts.ingest_rag import main


def _make_loaded_document(source_id: str, title: str, content: str) -> LoadedDocument:
    """Helper: create a minimal LoadedDocument with expected metadata."""
    return LoadedDocument(
        source_id=source_id,
        title=title,
        content=content,
        metadata={"source_id": source_id, "title": title},
    )


def _chunk_fixtures():
    """Build a minimal ``(chunk_docs, chunks, rag_result)`` triple."""
    chunk_docs = [
        LoadedDocument(
            source_id="doc1",
            title="Doc 1",
            content="Chunk 1.",
            metadata={"source_id": "doc1", "title": "Doc 1", "chunk_index": 0},
        )
    ]
    chunks = [EmbeddedChunk(document=chunk_docs[0], embedding=[0.1] * 768)]
    rag_result = {
        "documents_ingested": 1,
        "chunks_ingested": 1,
        "document_ids": {"doc1": 42},
    }
    return chunk_docs, chunks, rag_result


@contextmanager
def _patch_pipeline(docs, chunk_docs, chunks, rag_result):
    """Mock every pipeline stage and yield the ``load_and_chunk`` mock."""
    with (
        patch("scripts.ingest_rag.load_all_documents", return_value=docs),
        patch("scripts.ingest_rag.load_and_chunk", return_value=chunk_docs) as mock_chunk,
        patch(
            "scripts.ingest_rag.embed_document_chunks",
            AsyncMock(return_value=chunks),
        ),
        patch("scripts.ingest_rag.EmbeddingService", return_value=MagicMock()),
        patch(
            "scripts.ingest_rag.RagIngestionService",
            return_value=MagicMock(ingest=AsyncMock(return_value=rag_result)),
        ),
    ):
        yield mock_chunk


class TestIngestRagRunner:
    """Positive-flow tests for the runner entry-point."""

    @pytest.mark.asyncio
    async def test_default_configuration(self):
        """Default config is 500/75 and load_and_chunk is called accordingly."""
        docs = [_make_loaded_document("doc1", "Doc 1", "Content 1")]
        chunk_docs, chunks, rag_result = _chunk_fixtures()

        with _patch_pipeline(docs, chunk_docs, chunks, rag_result) as mock_chunk:
            await main()

        mock_chunk.assert_called_once_with(chunk_size=500, chunk_overlap=75)

    @pytest.mark.asyncio
    async def test_custom_configuration_300_50(self):
        """Custom config 300/50 is forwarded to load_and_chunk."""
        docs = [_make_loaded_document("doc1", "Doc 1", "Content 1")]
        chunk_docs, chunks, rag_result = _chunk_fixtures()

        with _patch_pipeline(docs, chunk_docs, chunks, rag_result) as mock_chunk:
            await main(Namespace(chunk_size=300, chunk_overlap=50))

        mock_chunk.assert_called_once_with(chunk_size=300, chunk_overlap=50)

    @pytest.mark.asyncio
    async def test_custom_configuration_800_100(self):
        """Custom config 800/100 is forwarded to load_and_chunk."""
        docs = [_make_loaded_document("doc1", "Doc 1", "Content 1")]
        chunk_docs, chunks, rag_result = _chunk_fixtures()

        with _patch_pipeline(docs, chunk_docs, chunks, rag_result) as mock_chunk:
            await main(Namespace(chunk_size=800, chunk_overlap=100))

        mock_chunk.assert_called_once_with(chunk_size=800, chunk_overlap=100)

    @pytest.mark.asyncio
    async def test_invalid_chunk_size_rejected(self):
        """A non-positive chunk size raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            await main(Namespace(chunk_size=0, chunk_overlap=50))

    @pytest.mark.asyncio
    async def test_invalid_chunk_size_negative_rejected(self):
        """A negative chunk size raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            await main(Namespace(chunk_size=-100, chunk_overlap=50))

    @pytest.mark.asyncio
    async def test_invalid_overlap_rejected(self):
        """A negative overlap raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            await main(Namespace(chunk_size=500, chunk_overlap=-10))

    @pytest.mark.asyncio
    async def test_overlap_not_smaller_than_chunk_size_rejected(self):
        """Overlap must be strictly smaller than chunk size."""
        with pytest.raises(ValueError, match="smaller"):
            await main(Namespace(chunk_size=500, chunk_overlap=500))
        with pytest.raises(ValueError, match="smaller"):
            await main(Namespace(chunk_size=300, chunk_overlap=400))

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Runner completes successfully on happy path (no exception)."""
        docs = [_make_loaded_document("doc1", "Doc 1", "Content 1")]
        chunk_docs, chunks, rag_result = _chunk_fixtures()

        with _patch_pipeline(docs, chunk_docs, chunks, rag_result):
            await main()

    @pytest.mark.asyncio
    async def test_failure_raises(self):
        """Runner raises an error when document loading fails."""
        with (
            patch(
                "scripts.ingest_rag.load_all_documents",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await main()
