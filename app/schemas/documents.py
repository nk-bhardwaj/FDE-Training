"""Pydantic schemas for document semantic and keyword search API."""

from datetime import datetime

from pydantic import BaseModel, Field

# --- Semantic Search Schemas ---


class SemanticSearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=100)
    metadata_filters: dict[str, str | int | bool] | None = None


class SearchResultResponse(BaseModel):
    """A single semantic search result."""

    id: int
    content: str
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    similarity: float


class SemanticSearchResponse(BaseModel):
    """Response body for semantic search."""

    query: str
    results: list[SearchResultResponse]
    total_results: int


# --- Keyword Search Schemas ---


class KeywordSearchRequest(BaseModel):
    """Request body for keyword search."""

    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=100)
    metadata_filters: dict[str, str | int | bool] | None = None


class KeywordSearchResultResponse(BaseModel):
    """A single keyword search result."""

    id: int
    content: str
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    rank: float


class KeywordSearchResponse(BaseModel):
    """Response body for keyword search."""

    query: str
    results: list[KeywordSearchResultResponse]
    total_results: int
