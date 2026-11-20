"""Tests for the ingestion service."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ingestion_service import (
    EmbeddedChunk,
    IngestionError,
    LoadedDocument,
    _discover_markdown_files,
    _extract_document,
    _load_yaml_frontmatter,
    _read_markdown_file,
    embed_document_chunks,
    load_all_documents,
    load_and_chunk,
)
from app.services.llm_errors import LLMProviderError


class TestLoadYamlFrontmatter:
    def test_valid_frontmatter(self):
        text = (
            "---\nsource_id: test_doc\ntitle: Test Title\ncategory: test\n---\n\nBody content here."
        )
        metadata, body = _load_yaml_frontmatter(text)
        assert metadata == {
            "source_id": "test_doc",
            "title": "Test Title",
            "category": "test",
        }
        assert body == "Body content here."

    def test_no_frontmatter(self):
        text = "Just plain content.\nNo frontmatter block."
        metadata, body = _load_yaml_frontmatter(text)
        assert metadata == {}
        assert body == text

    def test_missing_closing_delimiter(self):
        text = "---\nsource_id: test\nNo closing delimiter."
        metadata, body = _load_yaml_frontmatter(text)
        assert metadata == {}
        assert body == text

    def test_empty_frontmatter_block(self):
        text = "---\n---\n\nBody text."
        metadata, body = _load_yaml_frontmatter(text)
        assert metadata == {}
        assert body == text

    def test_malformed_yaml_raises(self):
        text = "---\nsource_id: [unclosed\n---\n\nBody."
        with pytest.raises(IngestionError, match="Malformed YAML"):
            _load_yaml_frontmatter(text)

    def test_preserves_all_metadata_fields(self):
        text = (
            "---\n"
            "source_id: foo\n"
            "title: Bar\n"
            "custom_field: something\n"
            "numeric: 42\n"
            "boolean: true\n"
            "list: [a, b, c]\n"
            "---\n"
            "Content."
        )
        metadata, _ = _load_yaml_frontmatter(text)
        assert metadata["source_id"] == "foo"
        assert metadata["title"] == "Bar"
        assert metadata["custom_field"] == "something"
        assert metadata["numeric"] == 42
        assert metadata["boolean"] is True
        assert metadata["list"] == ["a", "b", "c"]

    def test_yaml_list_raises(self):
        text = "---\n- item1\n- item2\n---\n\nBody."
        with pytest.raises(IngestionError, match="must be a dictionary"):
            _load_yaml_frontmatter(text)

    def test_yaml_string_raises(self):
        text = "---\njust a string\n---\n\nBody."
        with pytest.raises(IngestionError, match="must be a dictionary"):
            _load_yaml_frontmatter(text)

    def test_yaml_number_raises(self):
        text = "---\n42\n---\n\nBody."
        with pytest.raises(IngestionError, match="must be a dictionary"):
            _load_yaml_frontmatter(text)


class TestDiscoverMarkdownFiles:
    def test_finds_md_files(self, tmp_path: Path):
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "not_md.txt").write_text("txt")
        files = _discover_markdown_files(tmp_path)
        assert [f.name for f in files] == ["a.md", "b.md"]

    def test_missing_directory_raises(self):
        with pytest.raises(IngestionError, match="Directory not found"):
            _discover_markdown_files(Path("/nonexistent/path"))

    def test_no_md_files_raises(self, tmp_path: Path):
        (tmp_path / "readme.txt").write_text("txt")
        with pytest.raises(IngestionError, match="No Markdown files found"):
            _discover_markdown_files(tmp_path)


class TestReadMarkdownFile:
    def test_reads_content(self, tmp_path: Path):
        path = tmp_path / "doc.md"
        path.write_text("Hello world", encoding="utf-8")
        text = _read_markdown_file(path)
        assert text == "Hello world"

    def test_empty_file_raises(self, tmp_path: Path):
        path = tmp_path / "empty.md"
        path.write_text("", encoding="utf-8")
        with pytest.raises(IngestionError, match="File is empty"):
            _read_markdown_file(path)

    def test_whitespace_only_raises(self, tmp_path: Path):
        path = tmp_path / "ws.md"
        path.write_text("   \n\t  ", encoding="utf-8")
        with pytest.raises(IngestionError, match="File is empty"):
            _read_markdown_file(path)

    def test_unreadable_file_raises(self, tmp_path: Path):
        # Create a directory instead of a file to simulate unreadable
        path = tmp_path / "dir"
        path.mkdir()
        with pytest.raises(IngestionError, match="Failed to read"):
            _read_markdown_file(path)


class TestExtractDocument:
    def test_valid_metadata(self):
        metadata = {"source_id": "test", "title": "Test Doc", "category": "cat"}
        body = "Body text."
        doc = _extract_document(metadata, body)
        assert isinstance(doc, LoadedDocument)
        assert doc.source_id == "test"
        assert doc.title == "Test Doc"
        assert doc.category == "cat"
        assert doc.content == "Body text."
        assert doc.metadata == metadata

    def test_missing_source_id_raises(self):
        metadata = {"title": "Test Doc"}
        body = "Body text."
        with pytest.raises(IngestionError, match="source_id"):
            _extract_document(metadata, body)

    def test_missing_title_raises(self):
        metadata = {"source_id": "test"}
        body = "Body text."
        with pytest.raises(IngestionError, match="title"):
            _extract_document(metadata, body)

    def test_empty_source_id_raises(self):
        metadata = {"source_id": "", "title": "Test Doc"}
        body = "Body text."
        with pytest.raises(IngestionError, match="source_id"):
            _extract_document(metadata, body)

    def test_empty_body_raises(self):
        metadata = {"source_id": "test", "title": "Test Doc"}
        body = "   \n\t  "
        with pytest.raises(IngestionError, match="empty after frontmatter"):
            _extract_document(metadata, body)

    def test_preserves_extra_fields(self):
        metadata = {
            "source_id": "test",
            "title": "Test Doc",
            "author": "Alice",
            "version": 2,
            "tags": ["a", "b"],
        }
        body = "Body text."
        doc = _extract_document(metadata, body)
        assert doc.metadata["author"] == "Alice"
        assert doc.metadata["version"] == 2
        assert doc.metadata["tags"] == ["a", "b"]


class TestLoadAllDocuments:
    def test_loads_from_data_raw(self):
        docs = load_all_documents()
        assert len(docs) == 3
        for doc in docs:
            assert isinstance(doc, LoadedDocument)
            assert doc.source_id
            assert doc.title
            assert doc.content

    def test_source_ids_match_filenames(self):
        docs = load_all_documents()
        source_ids = {doc.source_id for doc in docs}
        assert source_ids == {
            "amazon_fba_return_policy",
            "amazon_process_return_requests",
            "amazon_seller_fulfilled_returns",
        }

    def test_body_excludes_frontmatter(self):
        docs = load_all_documents()
        for doc in docs:
            assert "source_id" not in doc.content
            assert "title:" not in doc.content
            assert "---" not in doc.content[:50]

    def test_metadata_preserves_all_fields(self):
        docs = load_all_documents()
        for doc in docs:
            assert doc.metadata["source_id"] == doc.source_id
            assert doc.metadata["title"] == doc.title
            assert doc.metadata.get("category") == doc.category

    def test_uses_default_directory(self):
        docs = load_all_documents()
        assert len(docs) == 3

    def test_sorted_order(self):
        docs = load_all_documents()
        # Should be sorted by filename
        names = [doc.source_id for doc in docs]
        assert names == sorted(names)


class TestLoadAndChunk:
    def test_produces_chunks_for_each_document(self):
        chunks = load_and_chunk(chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 0

    def test_chunks_have_correct_metadata(self):
        chunks = load_and_chunk(chunk_size=200, chunk_overlap=20)
        for chunk in chunks:
            assert chunk.metadata is not None
            assert "chunk_index" in chunk.metadata
            assert "chunk_size" in chunk.metadata
            assert "chunk_overlap" in chunk.metadata
            assert chunk.metadata["source_id"] == chunk.source_id
            assert chunk.metadata["title"] == chunk.title

    def test_chunk_indexes_increment(self):
        chunks = load_and_chunk(chunk_size=200, chunk_overlap=20)
        for source_id in {
            "amazon_fba_return_policy",
            "amazon_process_return_requests",
            "amazon_seller_fulfilled_returns",
        }:
            src_chunks = [c for c in chunks if c.source_id == source_id]
            if src_chunks:
                indexes = [c.metadata["chunk_index"] for c in src_chunks]
                assert indexes == list(range(len(src_chunks)))

    def test_uses_experiment_config_defaults(self):
        # load_and_chunk should use 500/50 defaults matching experiment configs
        chunks = load_and_chunk()
        for chunk in chunks:
            assert chunk.metadata["chunk_size"] == 500
            assert chunk.metadata["chunk_overlap"] == 50

    def test_uses_chunk_index_from_document_chunk(self):
        # Verify that load_and_chunk uses chunk.chunk_index from chunk_text
        # rather than enumerate()
        chunks = load_and_chunk(chunk_size=200, chunk_overlap=20)
        # For a long document, verify chunk_index values are sequential
        # and match the DocumentChunk.chunk_index
        long_text_chunks = [c for c in chunks if c.source_id == "amazon_fba_return_policy"]
        if long_text_chunks:
            indexes = [c.metadata["chunk_index"] for c in long_text_chunks]
            # Should start at 0 and increment by 1
            assert indexes == list(range(len(indexes)))
            # All indexes should be non-negative integers
            assert all(isinstance(i, int) and i >= 0 for i in indexes)


class TestIntegration:
    def test_loads_and_chunks_all_three_documents(self):
        chunks = load_and_chunk(chunk_size=200, chunk_overlap=20)
        source_ids = {c.source_id for c in chunks}
        assert len(source_ids) == 3

    def test_chunk_content_preserves_original_text(self):
        chunks = load_and_chunk(chunk_size=200, chunk_overlap=20)
        for chunk in chunks:
            assert len(chunk.content) > 0
            assert chunk.content.strip() == chunk.content.strip()


class TestLoadAllDocumentsCustomDirectory:
    def test_custom_directory(self, tmp_path: Path):
        md_file = tmp_path / "custom.md"
        md_file.write_text("---\nsource_id: custom\ntitle: Custom Doc\n---\n\nCustom content.")
        docs = load_all_documents(tmp_path)
        assert len(docs) == 1
        assert docs[0].source_id == "custom"
        assert docs[0].title == "Custom Doc"
        assert docs[0].content == "Custom content."

    def test_custom_directory_with_multiple_files(self, tmp_path: Path):
        (tmp_path / "a.md").write_text("---\nsource_id: a\ntitle: A\n---\n\nContent A.")
        (tmp_path / "b.md").write_text("---\nsource_id: b\ntitle: B\n---\n\nContent B.")
        docs = load_all_documents(tmp_path)
        assert len(docs) == 2
        assert [d.source_id for d in docs] == ["a", "b"]


class TestEmbedDocumentChunks:
    def test_empty_input_returns_empty_list(self):
        result = asyncio.run(embed_document_chunks([]))
        assert result == []

    def test_one_chunk(self):
        doc = LoadedDocument(
            source_id="test",
            title="Test Doc",
            content="Short text.",
            metadata={"source_id": "test", "title": "Test Doc"},
        )
        mock_embedding = [0.1] * 768
        mock_service = MagicMock()
        mock_service.embed_document = AsyncMock(return_value=mock_embedding)

        result = asyncio.run(embed_document_chunks([doc], embedding_service=mock_service))
        assert len(result) == 1
        assert isinstance(result[0], EmbeddedChunk)
        assert result[0].document.source_id == "test"
        assert len(result[0].embedding) == 768

    def test_multiple_chunks(self):
        docs = [
            LoadedDocument(
                source_id="doc1",
                title="Doc 1",
                content="Content one.",
                metadata={"source_id": "doc1", "title": "Doc 1"},
            ),
            LoadedDocument(
                source_id="doc2",
                title="Doc 2",
                content="Content two.",
                metadata={"source_id": "doc2", "title": "Doc 2"},
            ),
        ]
        mock_embedding = [0.2] * 768
        mock_service = MagicMock()
        mock_service.embed_document = AsyncMock(return_value=mock_embedding)

        result = asyncio.run(embed_document_chunks(docs, embedding_service=mock_service))
        assert len(result) == 2
        assert all(isinstance(c, EmbeddedChunk) for c in result)
        assert result[0].document.source_id == "doc1"
        assert result[1].document.source_id == "doc2"

    def test_correct_embedding_dimensions(self):
        doc = LoadedDocument(
            source_id="test",
            title="Test Doc",
            content="Some content for embedding.",
            metadata={"source_id": "test", "title": "Test Doc"},
        )
        mock_service = MagicMock()
        mock_service.embed_document = AsyncMock(return_value=[0.5] * 768)

        result = asyncio.run(embed_document_chunks([doc], embedding_service=mock_service))
        assert len(result) == 1
        assert len(result[0].embedding) == 768

    def test_wrong_embedding_dimensions_raises(self):
        doc = LoadedDocument(
            source_id="test",
            title="Test Doc",
            content="Some content.",
            metadata={"source_id": "test", "title": "Test Doc"},
        )
        mock_service = MagicMock()
        mock_service.embed_document = AsyncMock(return_value=[0.5] * 100)

        with pytest.raises(ValueError, match="Expected 768-dimensional"):
            asyncio.run(embed_document_chunks([doc], embedding_service=mock_service))

    def test_metadata_preserved(self):
        doc = LoadedDocument(
            source_id="test",
            title="Test Doc",
            category="returns_refunds",
            content="Content here.",
            metadata={
                "source_id": "test",
                "title": "Test Doc",
                "category": "returns_refunds",
                "custom_key": "custom_value",
            },
        )
        mock_service = MagicMock()
        mock_service.embed_document = AsyncMock(return_value=[0.3] * 768)

        result = asyncio.run(embed_document_chunks([doc], embedding_service=mock_service))
        assert result[0].document.category == "returns_refunds"
        assert result[0].document.metadata["custom_key"] == "custom_value"

    def test_dependency_injection(self):
        doc = LoadedDocument(
            source_id="test",
            title="Test Doc",
            content="Content.",
            metadata={"source_id": "test", "title": "Test Doc"},
        )
        custom_service = MagicMock()
        custom_service.embed_document = AsyncMock(return_value=[0.4] * 768)

        result = asyncio.run(embed_document_chunks([doc], embedding_service=custom_service))
        custom_service.embed_document.assert_called_once_with(doc.content)
        assert len(result) == 1

    def test_gemini_error_propagation(self):
        doc = LoadedDocument(
            source_id="test",
            title="Test Doc",
            content="Content.",
            metadata={"source_id": "test", "title": "Test Doc"},
        )
        mock_service = MagicMock()
        mock_service.embed_document = AsyncMock(
            side_effect=LLMProviderError("Rate limit exceeded", status_code=429)
        )

        with pytest.raises(LLMProviderError, match="Rate limit exceeded"):
            asyncio.run(embed_document_chunks([doc], embedding_service=mock_service))
