"""Unit tests for the RAG context engineering service."""

from dataclasses import FrozenInstanceError

import pytest
import tiktoken

from app.services.chunking_service import ENCODING_NAME
from app.services.context_engineering_service import (
    DEFAULT_MAX_TOKENS,
    AssembledContext,
    ContextEngineeringService,
)
from app.services.rag_retrieval_service import ChunkSearchResult


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


@pytest.fixture
def service() -> ContextEngineeringService:
    return ContextEngineeringService(max_tokens=1000)


# ---------------------------------------------------------------------------
# Ordering and attribution
# ---------------------------------------------------------------------------


def test_preserves_retrieval_order_and_assigns_ranks(service):
    """Chunks keep their input order and get 1-based retrieval ranks."""
    first = _make_chunk_result(id=11, chunk_index=0, content="first chunk")
    second = _make_chunk_result(id=22, chunk_index=1, content="second chunk")
    third = _make_chunk_result(id=33, chunk_index=2, content="third chunk")

    context = service.assemble([first, second, third])

    assert [chunk.chunk_id for chunk in context.chunks] == [11, 22, 33]
    assert [chunk.retrieval_rank for chunk in context.chunks] == [1, 2, 3]
    assert [chunk.content for chunk in context.chunks] == [
        "first chunk",
        "second chunk",
        "third chunk",
    ]


def test_preserves_source_attribution_fields(service):
    """Every included chunk keeps the fields needed for citations."""
    chunk = _make_chunk_result(
        id=7,
        document_id=3,
        chunk_index=4,
        content="Refunds are processed within five days.",
        source_id="amazon_fba_return_policy",
        document_title="FBA Return Policy",
    )

    context = service.assemble([chunk])
    included = context.chunks[0]

    assert included.chunk_id == 7
    assert included.document_id == 3
    assert included.source_id == "amazon_fba_return_policy"
    assert included.document_title == "FBA Return Policy"
    assert included.chunk_index == 4
    assert included.content == "Refunds are processed within five days."


def test_preserves_available_relevance_scores(service):
    """Retrieval scores are carried through unchanged."""
    chunk = _make_chunk_result(
        content="scored chunk",
        distance=0.12,
        similarity=0.88,
        rank=0.42,
        rrf_score=0.031,
    )

    included = service.assemble([chunk]).chunks[0]

    assert included.distance == pytest.approx(0.12)
    assert included.similarity == pytest.approx(0.88)
    assert included.rank == pytest.approx(0.42)
    assert included.rrf_score == pytest.approx(0.031)


def test_scores_are_optional(service):
    """Chunks without scores keep ``None`` rather than inventing values."""
    included = service.assemble([_make_chunk_result()]).chunks[0]

    assert included.distance is None
    assert included.similarity is None
    assert included.rank is None
    assert included.rrf_score is None


def test_sources_are_unique_and_in_inclusion_order(service):
    """Source IDs are de-duplicated while preserving first-seen order."""
    chunks = [
        _make_chunk_result(id=1, source_id="doc_b", chunk_index=0),
        _make_chunk_result(id=2, source_id="doc_a", chunk_index=0),
        _make_chunk_result(id=3, source_id="doc_b", chunk_index=1),
    ]

    context = service.assemble(chunks)

    assert context.sources == ("doc_b", "doc_a")


# ---------------------------------------------------------------------------
# Duplicate handling
# ---------------------------------------------------------------------------


def test_removes_duplicate_chunks_keeping_first(service):
    """The same (source_id, chunk_index) is included once, first occurrence wins."""
    original = _make_chunk_result(id=1, chunk_index=0, content="original content")
    duplicate = _make_chunk_result(id=1, chunk_index=0, content="duplicated content")

    context = service.assemble([original, duplicate])

    assert len(context.chunks) == 1
    assert context.chunks[0].content == "original content"
    assert context.duplicates_removed == 1


def test_duplicates_do_not_consume_token_budget(service):
    """A duplicate is skipped before token accounting."""
    original = _make_chunk_result(id=1, chunk_index=0, content="short text")
    duplicate = _make_chunk_result(id=1, chunk_index=0, content="short text")

    context = service.assemble([original, duplicate])

    assert context.total_tokens == service.count_tokens("short text")


def test_different_chunks_from_same_source_are_kept(service):
    """Distinct chunk indexes from one source are not duplicates."""
    chunks = [
        _make_chunk_result(id=1, source_id="doc1", chunk_index=0),
        _make_chunk_result(id=2, source_id="doc1", chunk_index=1),
    ]

    context = service.assemble(chunks)

    assert len(context.chunks) == 2
    assert context.duplicates_removed == 0


# ---------------------------------------------------------------------------
# Token limits
# ---------------------------------------------------------------------------


def test_respects_token_budget(service):
    """Chunks are included only while they fit the budget."""
    first = _make_chunk_result(id=1, chunk_index=0, content="alpha beta gamma")
    second = _make_chunk_result(id=2, chunk_index=1, content="delta epsilon")
    third = _make_chunk_result(id=3, chunk_index=2, content="zeta eta theta iota kappa")

    budget = service.count_tokens(first.content) + service.count_tokens(second.content)
    context = service.assemble([first, second, third], max_tokens=budget)

    assert [chunk.chunk_id for chunk in context.chunks] == [1, 2]
    assert context.total_tokens == budget
    assert context.total_tokens <= context.max_tokens
    assert context.truncated is True


def test_exact_budget_fit_is_included(service):
    """A chunk that exactly fills the remaining budget is included."""
    chunk = _make_chunk_result(content="exact fit text")
    budget = service.count_tokens(chunk.content)

    context = service.assemble([chunk], max_tokens=budget)

    assert len(context.chunks) == 1
    assert context.total_tokens == budget
    assert context.truncated is False


def test_not_truncated_when_everything_fits(service):
    """``truncated`` stays False when no candidate is dropped."""
    chunks = [
        _make_chunk_result(id=1, chunk_index=0, content="one"),
        _make_chunk_result(id=2, chunk_index=1, content="two"),
    ]

    context = service.assemble(chunks, max_tokens=500)

    assert len(context.chunks) == 2
    assert context.truncated is False


def test_oversized_chunk_is_skipped_without_blocking_later_chunks(service):
    """A chunk larger than the budget is dropped; smaller chunks still fit."""
    oversized = _make_chunk_result(id=1, chunk_index=0, content=" ".join(["overflow"] * 200))
    small = _make_chunk_result(id=2, chunk_index=1, content="small useful chunk")
    budget = service.count_tokens(small.content)

    context = service.assemble([oversized, small], max_tokens=budget)

    assert [chunk.chunk_id for chunk in context.chunks] == [2]
    assert context.chunks[0].retrieval_rank == 2
    assert context.truncated is True
    assert context.total_tokens <= context.max_tokens


def test_budget_smaller_than_any_chunk_returns_empty_context(service):
    """When nothing fits, the context is empty but still valid."""
    context = service.assemble([_make_chunk_result(content="some content")], max_tokens=1)

    assert context.chunks == ()
    assert context.total_tokens == 0
    assert context.truncated is True
    assert context.sources == ()


def test_per_call_budget_overrides_constructor_default(service):
    """``max_tokens`` passed to ``assemble`` wins over the instance default."""
    chunk = _make_chunk_result(content="a" * 400)
    small_budget = 5

    context = service.assemble([chunk], max_tokens=small_budget)

    assert context.max_tokens == small_budget
    assert context.chunks == ()
    assert context.truncated is True


def test_default_budget_is_used_when_not_overridden():
    """The constructor default is reported and applied."""
    service = ContextEngineeringService()

    context = service.assemble([_make_chunk_result(content="short")])

    assert context.max_tokens == DEFAULT_MAX_TOKENS


@pytest.mark.parametrize("max_tokens", [0, -1])
def test_constructor_rejects_non_positive_budget(max_tokens):
    """The instance budget must be positive."""
    with pytest.raises(ValueError, match="max_tokens"):
        ContextEngineeringService(max_tokens=max_tokens)


@pytest.mark.parametrize("max_tokens", [0, -1])
def test_assemble_rejects_non_positive_budget(service, max_tokens):
    """A per-call budget must be positive."""
    with pytest.raises(ValueError, match="max_tokens"):
        service.assemble([_make_chunk_result()], max_tokens=max_tokens)


# ---------------------------------------------------------------------------
# Empty input and token counting
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_context(service):
    """No candidates produce a valid, empty context."""
    context = service.assemble([])

    assert isinstance(context, AssembledContext)
    assert context.chunks == ()
    assert context.total_tokens == 0
    assert context.max_tokens == service.max_tokens
    assert context.truncated is False
    assert context.duplicates_removed == 0
    assert context.sources == ()


def test_empty_and_whitespace_chunks_are_skipped(service):
    """Blank content is not included and does not mark the context truncated."""
    chunks = [
        _make_chunk_result(id=1, chunk_index=0, content=""),
        _make_chunk_result(id=2, chunk_index=1, content="   \n\t "),
        _make_chunk_result(id=3, chunk_index=2, content="real content"),
    ]

    context = service.assemble(chunks)

    assert [chunk.chunk_id for chunk in context.chunks] == [3]
    assert context.truncated is False
    assert context.total_tokens == service.count_tokens("real content")


def test_count_tokens_matches_tiktoken_encoding(service):
    """Token counting uses the shared cl100k_base encoding."""
    encoding = tiktoken.get_encoding(ENCODING_NAME)
    text = "Refunds are processed within five business days."

    assert service.count_tokens(text) == len(encoding.encode(text))
    assert service.count_tokens("") == 0


def test_chunk_token_count_is_recorded(service):
    """Each included chunk reports its own token count."""
    chunk = _make_chunk_result(content="token accounting for this chunk")

    included = service.assemble([chunk]).chunks[0]

    assert included.token_count == service.count_tokens(chunk.content)
    assert included.token_count > 0


def test_total_tokens_equals_sum_of_included_chunks(service):
    """``total_tokens`` is the sum of included chunk token counts."""
    chunks = [
        _make_chunk_result(id=1, chunk_index=0, content="first piece of text"),
        _make_chunk_result(id=2, chunk_index=1, content="second piece of text"),
    ]

    context = service.assemble(chunks)

    assert context.total_tokens == sum(chunk.token_count for chunk in context.chunks)


def test_context_models_are_immutable(service):
    """Assembled context and its chunks cannot be mutated."""
    context = service.assemble([_make_chunk_result(content="immutable content")])

    with pytest.raises(FrozenInstanceError):
        context.total_tokens = 0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        context.chunks[0].content = "changed"  # type: ignore[misc]
