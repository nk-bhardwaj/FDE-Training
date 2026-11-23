"""Ingestion service: loads Markdown documents and produces ready-to-store
document records from the ``data/raw/`` directory.

Responsibilities:
- Discover and read Markdown files from ``data/raw/``.
- Extract YAML frontmatter into a metadata dictionary; strip it from the
  document body.
- Validate that required fields (``source_id``, ``title``) are present.
- Preserve all other metadata fields without hardcoding Amazon-specific keys.
- Raise informative errors for missing frontmatter, malformed YAML, missing
  required metadata, empty files, and missing directories.
- Keep file I/O separate from database/embedding operations so the returned
  dataclass can be used by any downstream pipeline.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingService


@dataclass(frozen=True)
class LoadedDocument:
    """A fully loaded document ready for embedding and storage.

    Attributes:
        source_id: The unique source identifier (e.g. ``amazon_fba_return_policy``).
        title: The document title (human-readable).
        category: Optional category tag.
        content: The Markdown body text (frontmatter stripped).
        metadata: All frontmatter fields as a dictionary (includes
            ``source_id`` and ``title``).
    """

    source_id: str
    title: str
    category: str | None = None
    content: str = ""
    metadata: dict[str, Any] | None = None


class IngestionError(Exception):
    """Raised when ingestion of a document fails for any reason."""


def _load_yaml_frontmatter(text: str) -> tuple[dict[str, Any], str | None]:
    """Parse the leading ``---``...``---`` block as YAML frontmatter.

    Returns
    -------
        A tuple of ``(metadata_dict, body_text)``.  If no frontmatter is
        present, ``metadata_dict`` is empty and *body_text* is the original
        text unchanged.
    """
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()

    # Find the closing delimiter starting from line 1.
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            yaml_block = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :]).lstrip("\n")

            if not yaml_block.strip():
                return {}, text

            try:
                metadata = yaml.safe_load(yaml_block) or {}
            except yaml.YAMLError as exc:
                raise IngestionError(f"Malformed YAML frontmatter: {exc}") from exc

            if not isinstance(metadata, dict):
                raise IngestionError(
                    f"YAML frontmatter must be a dictionary, got {type(metadata).__name__}"
                )

            return metadata, body

    # No closing delimiter found - treat entire text as body.
    return {}, text


def _discover_markdown_files(directory: Path) -> list[Path]:
    """Return a sorted list of ``.md`` files in *directory*.

    Raises ``IngestionError`` if the directory does not exist or contains
    no Markdown files.
    """
    if not directory.is_dir():
        raise IngestionError(f"Directory not found or not a directory: {directory}")

    files = sorted(directory.glob("*.md"))
    if not files:
        raise IngestionError(
            f"No Markdown files found in {directory}. Place ``*.md`` files in ``data/raw/``."
        )

    return files


def _read_markdown_file(path: Path) -> str:
    """Read raw Markdown content from *path*.

    Raises ``IngestionError`` if the file cannot be read or is empty.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise IngestionError(f"Failed to read {path}: {exc}") from exc

    if not text or not text.strip():
        raise IngestionError(f"File is empty: {path}")

    return text


def _extract_document(metadata: dict[str, Any], body: str) -> LoadedDocument:
    """Build a ``LoadedDocument`` from extracted metadata and body.

    Validates that ``source_id`` and ``title`` are present.  Other frontmatter
    fields are preserved verbatim; no Amazon-specific keys are hardcoded.
    """
    source_id = metadata.get("source_id")
    title = metadata.get("title")
    category = metadata.get("category")

    if not source_id:
        raise IngestionError("Missing required metadata: source_id")

    if not title:
        raise IngestionError("Missing required metadata: title")

    if not isinstance(content := body.strip(), str) or not content:
        raise IngestionError(
            f"Document body is empty after frontmatter removal: source_id={source_id}"
        )

    # Preserve all frontmatter keys; do not drop or rename anything.
    effective_metadata = dict(metadata)

    # Body is the Markdown after the frontmatter block.
    effective_content = body.strip()

    return LoadedDocument(
        source_id=source_id,
        title=title,
        category=category,
        content=effective_content,
        metadata=effective_metadata,
    )


def load_all_documents(directory: Path | str | None = None) -> list[LoadedDocument]:
    """Load all Markdown documents from *directory*.

    Parameters:
        directory: Path to a directory containing ``*.md`` files. Defaults to
            ``data/raw/`` relative to the project root.

    Returns
    -------
        A list of ``LoadedDocument`` instances, one per file, in sorted order.

    Raises:
        ``IngestionError``: If the directory is missing, a file cannot be read,
            frontmatter is malformed, or required metadata is absent.
    """
    if directory is None:
        directory = Path(__file__).resolve().parent.parent.parent / "data" / "raw"

    files = _discover_markdown_files(Path(directory))

    documents: list[LoadedDocument] = []
    for path in files:
        raw_text = _read_markdown_file(path)
        metadata, body = _load_yaml_frontmatter(raw_text)
        document = _extract_document(metadata, body)
        documents.append(document)

    return documents


def load_and_chunk(
    directory: Path | str | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[LoadedDocument]:
    """Load documents and immediately split them into token-based chunks.

    This is a convenience helper for the RAG ingestion pipeline.  It returns
    a flat list of ``LoadedDocument`` chunks; each chunk retains the original
    ``source_id`` and ``title`` metadata so the chunk can always be traced
    back to its parent document.

    Parameters:
        directory: Path to ``data/raw/`` or another Markdown directory.
        chunk_size: Maximum tokens per chunk (passed to :func:`chunk_text`).
        chunk_overlap: Overlap tokens between consecutive chunks.

    Returns:
        A list of ``LoadedDocument`` instances, each representing one chunk.
        The list is ordered first by original file order, then by chunk index.
    """
    documents = load_all_documents(directory)

    chunks: list[LoadedDocument] = []
    for doc in documents:
        if not doc.content.strip():
            # Skip documents with no body content after frontmatter removal.
            continue

        chunk_list = chunk_text(
            doc.content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk in chunk_list:
            chunk_metadata = dict(doc.metadata) if doc.metadata else {}
            # Append chunk-specific indexing metadata.
            chunk_metadata["chunk_index"] = chunk.chunk_index
            chunk_metadata["chunk_size"] = chunk_size
            chunk_metadata["chunk_overlap"] = chunk_overlap

            chunk_doc = LoadedDocument(
                source_id=doc.source_id,
                title=doc.title,
                category=doc.category,
                content=chunk.content,
                metadata=chunk_metadata,
            )
            chunks.append(chunk_doc)

    return chunks


@dataclass(frozen=True)
class EmbeddedChunk:
    """A document chunk paired with its embedding vector."""

    document: LoadedDocument
    embedding: list[float]


async def embed_document_chunks(
    chunks: list[LoadedDocument],
    embedding_service: EmbeddingService | None = None,
) -> list[EmbeddedChunk]:
    """Generate embeddings for a list of document chunks.

    Parameters:
        chunks: List of ``LoadedDocument`` instances to embed.
        embedding_service: Optional :class:`EmbeddingService` instance for
            dependency injection. If not provided, a new instance is created.

    Returns:
        A list of ``EmbeddedChunk`` instances, each containing the original
        ``LoadedDocument`` and its 768-dimensional embedding vector.

    Raises:
        ValueError: If any embedding does not have exactly 768 dimensions.
        IngestionError: If the input list is None.
    """
    if chunks is None:
        raise IngestionError("Chunks list cannot be None")

    if not chunks:
        return []

    service = embedding_service or EmbeddingService()

    results: list[EmbeddedChunk] = []
    for chunk in chunks:
        embedding = await service.embed_document(chunk.content)

        if len(embedding) != 768:
            raise ValueError(
                f"Expected 768-dimensional embedding for source_id={chunk.source_id} "
                f"chunk_index={chunk.metadata.get('chunk_index')}, got {len(embedding)}"
            )

        results.append(EmbeddedChunk(document=chunk, embedding=embedding))

    return results
