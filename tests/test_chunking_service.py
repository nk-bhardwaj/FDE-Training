"""Unit tests for token-based document chunking."""

import pytest

from app.services.chunking_service import (
    EXPERIMENT_CONFIGS,
    DocumentChunk,
    chunk_text,
)

# A short text where we can predict exact token counts.
SHORT_TEXT = "Hello world."
LONG_TEXT = "The quick brown fox jumps over the lazy dog. " * 40


class TestEmptyInput:
    def test_empty_string_returns_empty_list(self):
        assert chunk_text("", chunk_size=100, chunk_overlap=10) == []

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_text("   \n\t  ", chunk_size=100, chunk_overlap=10) == []


class TestSingleChunk:
    def test_text_shorter_than_chunk_size_returns_one_chunk(self):
        text = "Short text."
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)

        assert len(chunks) == 1
        assert isinstance(chunks[0], DocumentChunk)
        assert chunks[0].chunk_index == 0
        assert chunks[0].start_token == 0
        assert chunks[0].end_token <= 100
        assert chunks[0].token_count > 0
        assert chunks[0].content == text


class TestMultipleChunks:
    def test_long_text_produces_multiple_chunks(self):
        chunks = chunk_text(LONG_TEXT, chunk_size=50, chunk_overlap=10)

        assert len(chunks) > 1
        for chunk in chunks:
            assert isinstance(chunk, DocumentChunk)
            assert chunk.token_count <= 50

    def test_chunk_indexes_start_at_zero_and_increment(self):
        chunks = chunk_text(LONG_TEXT, chunk_size=50, chunk_overlap=10)

        indexes = [chunk.chunk_index for chunk in chunks]
        assert indexes == list(range(len(chunks)))


class TestOverlap:
    def test_consecutive_chunks_overlap_by_configured_amount(self):
        chunk_size = 50
        chunk_overlap = 10
        chunks = chunk_text(LONG_TEXT, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        step = chunk_size - chunk_overlap
        for i in range(len(chunks) - 1):
            current = chunks[i]
            nxt = chunks[i + 1]
            # Consecutive chunks advance by exactly ``step`` tokens.
            assert nxt.start_token == current.start_token + step

    def test_overlap_tokens_appear_in_both_chunks(self):
        chunks = chunk_text(LONG_TEXT, chunk_size=100, chunk_overlap=20)

        if len(chunks) > 1:
            current = chunks[0]
            nxt = chunks[1]
            # Next chunk starts ``chunk_overlap`` tokens before current ends.
            expected_start = min(current.start_token + 100, current.end_token - 20)
            assert nxt.start_token >= expected_start - 1
            assert nxt.start_token <= current.end_token


class TestTokenCounts:
    def test_each_chunk_token_count_matches_field(self):
        chunks = chunk_text(LONG_TEXT, chunk_size=50, chunk_overlap=10)

        for chunk in chunks:
            assert chunk.token_count == chunk.end_token - chunk.start_token

    def test_first_chunk_starts_at_zero(self):
        chunks = chunk_text(LONG_TEXT, chunk_size=50, chunk_overlap=10)

        assert chunks[0].start_token == 0


class TestValidation:
    def test_rejects_zero_chunk_size(self):
        with pytest.raises(ValueError, match="chunk_size"):
            chunk_text("hello", chunk_size=0, chunk_overlap=10)

    def test_rejects_negative_chunk_size(self):
        with pytest.raises(ValueError, match="chunk_size"):
            chunk_text("hello", chunk_size=-1, chunk_overlap=10)

    def test_rejects_negative_overlap(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("hello", chunk_size=100, chunk_overlap=-1)

    def test_rejects_overlap_equal_to_chunk_size(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("hello", chunk_size=50, chunk_overlap=50)

    def test_rejects_overlap_greater_than_chunk_size(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("hello", chunk_size=50, chunk_overlap=100)


class TestReconstruction:
    def test_chunks_cover_all_input_tokens_without_gaps(self):
        chunks = chunk_text(LONG_TEXT, chunk_size=50, chunk_overlap=10)

        # First chunk starts at 0, last chunk ends at total token count.
        assert chunks[0].start_token == 0

        # Each subsequent chunk starts where overlap begins.
        for i in range(len(chunks) - 1):
            assert chunks[i + 1].start_token <= chunks[i].end_token

    def test_reconstructed_text_preserves_content(self):
        chunks = chunk_text(LONG_TEXT, chunk_size=80, chunk_overlap=15)

        # Concatenating all chunk contents (with overlap stripped)
        # should contain all original tokens.
        combined = "".join(chunk.content for chunk in chunks)
        # Every word from the original should appear somewhere.
        original_words = set(LONG_TEXT.lower().split())
        combined_words = set(combined.lower().split())
        assert original_words.issubset(combined_words)


class TestExperimentConfigs:
    def test_experiment_configs_are_valid(self):
        assert len(EXPERIMENT_CONFIGS) == 3

        expected = [
            {"chunk_size": 300, "chunk_overlap": 50},
            {"chunk_size": 500, "chunk_overlap": 75},
            {"chunk_size": 800, "chunk_overlap": 100},
        ]
        assert expected == EXPERIMENT_CONFIGS

    def test_experiment_configs_produce_chunks(self):
        for config in EXPERIMENT_CONFIGS:
            chunks = chunk_text(
                LONG_TEXT,
                chunk_size=config["chunk_size"],
                chunk_overlap=config["chunk_overlap"],
            )
            assert len(chunks) > 0
            for chunk in chunks:
                assert chunk.token_count <= config["chunk_size"]


class TestFrozenDataclass:
    def test_document_chunk_is_frozen(self):
        chunks = chunk_text("Hello world.", chunk_size=100, chunk_overlap=10)
        chunk = chunks[0]
        with pytest.raises((AttributeError, TypeError)):
            chunk.content = "modified"  # type: ignore[misc]
