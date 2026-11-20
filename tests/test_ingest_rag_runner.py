"""Tests for the RAG ingestion runner."""

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


class TestIngestRagRunner:
    """Positive-flow tests for the runner entry-point."""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Runner completes successfully on happy path (no exception)."""
        docs = [_make_loaded_document("doc1", "Doc 1", "Content 1")]

        chunk_docs = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="Chunk 1.",
                metadata={"source_id": "doc1", "title": "Doc 1", "chunk_index": 0},
            )
        ]

        chunks = [
            EmbeddedChunk(document=chunk_docs[0], embedding=[0.1] * 768),
        ]

        rag_result = {
            "documents_ingested": 1,
            "chunks_ingested": 1,
            "document_ids": {"doc1": 42},
        }

        with (
            patch("scripts.ingest_rag.load_all_documents", return_value=docs),
            patch("scripts.ingest_rag.load_and_chunk", return_value=chunk_docs),
            patch("scripts.ingest_rag.embed_document_chunks", AsyncMock(return_value=chunks)),
            patch("scripts.ingest_rag.EmbeddingService", return_value=MagicMock()),
            patch(
                "scripts.ingest_rag.RagIngestionService",
                return_value=MagicMock(ingest=AsyncMock(return_value=rag_result)),
            ),
        ):
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
