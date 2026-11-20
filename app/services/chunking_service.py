"""Token-based document chunking service.

Splits text into overlapping token-based chunks using tiktoken's
``cl100k_base`` encoding. Token counts are approximations and do not
represent Gemini's exact tokenizer.
"""

from dataclasses import dataclass

import tiktoken

ENCODING_NAME = "cl100k_base"


@dataclass(frozen=True)
class DocumentChunk:
    """A single token-based chunk of a document."""

    chunk_index: int
    content: str
    token_count: int
    start_token: int
    end_token: int


def _get_encoding() -> tiktoken.Encoding:
    """Return a cached tiktoken encoding for cl100k_base."""
    return tiktoken.get_encoding(ENCODING_NAME)


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[DocumentChunk]:
    """Split ``text`` into overlapping token-based chunks.

    Args:
        text: The document text to chunk.
        chunk_size: Maximum number of tokens per chunk. Must be positive.
        chunk_overlap: Number of tokens to overlap between consecutive
            chunks. Must be non-negative and strictly smaller than
            ``chunk_size``.

    Returns:
        A list of :class:`DocumentChunk` instances ordered by
        ``chunk_index`` starting at 0. An empty list is returned for
        empty or whitespace-only input.

    Raises:
        ValueError: If ``chunk_size`` is not positive or if
            ``chunk_overlap`` is negative or not smaller than
            ``chunk_size``.
    """
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be a non-negative integer")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    encoding = _get_encoding()
    token_ids = encoding.encode(text)

    if not token_ids:
        return []

    chunks: list[DocumentChunk] = []
    step = chunk_size - chunk_overlap
    index = 0

    for start in range(0, len(token_ids), step):
        end = min(start + chunk_size, len(token_ids))
        chunk_tokens = token_ids[start:end]
        if not chunk_tokens:
            continue

        content = encoding.decode(chunk_tokens)
        chunks.append(
            DocumentChunk(
                chunk_index=index,
                content=content,
                token_count=len(chunk_tokens),
                start_token=start,
                end_token=end,
            )
        )
        index += 1

    return chunks


# Three experiment configurations used for Day 4 evaluation.
EXPERIMENT_CONFIGS: list[dict[str, int]] = [
    {"chunk_size": 300, "chunk_overlap": 50},
    {"chunk_size": 500, "chunk_overlap": 75},
    {"chunk_size": 800, "chunk_overlap": 100},
]
